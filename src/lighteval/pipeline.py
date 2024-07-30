# MIT License

# Copyright (c) 2024 The HuggingFace Team

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import random
import shutil
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum, auto

import numpy as np

from lighteval.evaluator import evaluate, make_results_table
from lighteval.logging.evaluation_tracker import EvaluationTracker
from lighteval.logging.hierarchical_logger import hlog, htrack_block
from lighteval.models.model_loader import load_model
from lighteval.tasks.lighteval_task import LightevalTask, create_requests_from_tasks
from lighteval.tasks.registry import Registry, get_custom_tasks, taskinfo_selector
from lighteval.utils import (
    NO_ACCELERATE_ERROR_MSG,
    NO_NANOTRON_ERROR_MSG,
    NO_TGI_ERROR_MSG,
    EnvConfig,
    is_accelerate_available,
    is_nanotron_available,
    is_tgi_available,
)
from lighteval.utils_parallelism import test_all_gather


if is_accelerate_available():
    from accelerate import Accelerator, InitProcessGroupKwargs
if is_nanotron_available():
    from nanotron import distributed as dist
    from nanotron.parallel.context import ParallelContext
    from nanotron.utils import local_ranks_zero_first

    from lighteval.models.nanotron_model import NanotronLightevalModel


class ParallelismManager(Enum):
    ACCELERATE = auto()
    NANOTRON = auto()
    TGI = auto()
    NONE = auto()


@dataclass
class PipelineParameters:
    launcher_type: ParallelismManager
    # Env parameters
    env_config: EnvConfig = EnvConfig()
    job_id: int = 0
    dataset_loading_processes: int = 1
    nanotron_checkpoint_path: str = None  # only for nanotron models
    # Dataset
    custom_tasks_directory: str = None
    # Generation parameters
    override_batch_size: int = None
    num_fewshot_seeds: int = 1
    max_samples: int = None
    use_chat_template: bool = False
    system_prompt: str = None

    def __post_init__(self):
        if self.launcher_type == ParallelismManager.ACCELERATE:
            if not is_accelerate_available():
                raise ImportError(NO_ACCELERATE_ERROR_MSG)
        elif self.launcher_type == ParallelismManager.TGI:
            if not is_tgi_available():
                raise ImportError(NO_TGI_ERROR_MSG)
        elif self.launcher_type == ParallelismManager.NANOTRON:
            if not is_nanotron_available():
                raise ImportError(NO_NANOTRON_ERROR_MSG)


class Pipeline:
    def __init__(
        self,
        tasks: str,
        pipeline_parameters: PipelineParameters,
        evaluation_tracker: EvaluationTracker,
        model=None,
        model_config=None,
    ):
        if not (model or model_config):
            raise ValueError("Must provide either a model or model config when creating a pipeline.")

        self.pipeline_parameters = pipeline_parameters
        self.launcher_type = self.pipeline_parameters.launcher_type
        if self.pipeline_parameters.max_samples:
            hlog(
                "WARNING: --max_samples WAS SET. THESE NUMBERS ARE ONLY PARTIAL AND SHOULD NOT BE USED FOR COMPARISON UNLESS YOU KNOW WHAT YOU ARE DOING."
            )

        self.accelerator, self.parallel_context = self._init_parallelism_manager()

        self.evaluation_tracker = evaluation_tracker
        self.model_config = model_config
        self.model = self._init_model(model_config, model)

        self.evaluation_tracker.general_config_logger.log_model_info(self.model.model_info)
        self._init_tasks_and_requests(tasks=tasks)
        self._init_random_seeds()

    def _init_parallelism_manager(self):
        accelerator, parallel_context = None, None
        with htrack_block("Test all gather"):
            if self.launcher_type == ParallelismManager.ACCELERATE:
                if not is_accelerate_available():
                    raise ValueError("You are trying to launch an accelerate model, but accelerate is not installed")
                accelerator = Accelerator(kwargs_handlers=[InitProcessGroupKwargs(timeout=timedelta(seconds=3000))])
                test_all_gather(accelerator=accelerator)
            elif self.launcher_type == ParallelismManager.NANOTRON:
                if not is_nanotron_available():
                    raise ValueError("You are trying to launch a nanotron model, but nanotron is not installed")
                dist.initialize_torch_distributed()
                parallel_context = ParallelContext(
                    tensor_parallel_size=self.model_config.parallelism.tp,
                    pipeline_parallel_size=self.model_config.parallelism.pp,
                    data_parallel_size=self.model_config.parallelism.dp,
                )
                test_all_gather(parallel_context=parallel_context)

            return accelerator, parallel_context

    def _init_model(self, model_config, model):
        with htrack_block("Model loading"):
            if model_config is not None:
                if self.parallel_context:
                    return NanotronLightevalModel(
                        checkpoint_path=os.path.dirname(self.pipeline_parameters.nanotron_checkpoint_path),
                        nanotron_config=self.model_config,
                        parallel_context=self.accelerator,
                        debug_one_layer_model=False,
                        model_class=None,
                        env_config=self.pipeline_parameters.env_config,
                    )
                else:
                    with self.accelerator.main_process_first() if self.accelerator is not None else nullcontext():
                        return load_model(config=model_config, env_config=self.pipeline_parameters.env_config)
            return model

    def _init_tasks_and_requests(self, tasks):
        with htrack_block("Tasks loading"):
            with local_ranks_zero_first() if self.launcher_type == ParallelismManager.NANOTRON else nullcontext():
                # If some tasks are provided as task groups, we load them separately
                custom_tasks = self.pipeline_parameters.custom_tasks_directory
                tasks_groups_dict = None
                if custom_tasks:
                    _, tasks_groups_dict = get_custom_tasks(custom_tasks)
                if tasks_groups_dict and tasks in tasks_groups_dict:
                    tasks = tasks_groups_dict[tasks]

                # Loading all tasks
                task_names_list, fewshots_dict = taskinfo_selector(tasks)
                task_dict = Registry(cache_dir=self.pipeline_parameters.env_config.cache_dir).get_task_dict(
                    task_names_list, custom_tasks=custom_tasks
                )
                LightevalTask.load_datasets(task_dict.values(), self.pipeline_parameters.dataset_loading_processes)

                self.evaluation_tracker.task_config_logger.log(task_dict)

                hlog("Loading documents, and requests")
                requests, docs = create_requests_from_tasks(
                    task_dict=task_dict,
                    fewshot_dict=fewshots_dict,
                    num_fewshot_seeds=self.pipeline_parameters.num_fewshot_seeds,
                    lm=self.model,
                    max_samples=self.pipeline_parameters.max_samples,
                    evaluation_tracker=self.evaluation_tracker,
                    use_chat_template=self.pipeline_parameters.use_chat_template,
                    system_prompt=self.pipeline_parameters.system_prompt,
                )

                self.task_names_list = task_names_list
                self.task_dict = task_dict
                self.fewshot_dict = fewshots_dict
                self.requests = requests
                self.docs = docs

    def _init_random_seeds(self):
        with htrack_block("Setting seeds and waiting for all processes"):
            hlog(f"setting seed to {1234} for random and numpy")
            random.seed(1234)
            np.random.seed(1234)
            if self.accelerator is not None:
                self.accelerator.wait_for_everyone()
            if self.parallel_context is not None:
                dist.barrier()

    def evaluate(self):
        with htrack_block("Evaluation"):
            self.evaluation_tracker.general_config_logger.log_args_info(
                num_fewshot_seeds=self.pipeline_parameters.num_fewshot_seeds,
                override_batch_size=self.pipeline_parameters.override_batch_size,
                max_samples=self.pipeline_parameters.max_samples,
                job_id=self.pipeline_parameters.job_id,
                config=self.model_config,
            )

            hlog(f"Evaluate on {len(self.task_names_list)} tasks.")
            self.evaluation_tracker = evaluate(
                lm=self.model,
                requests_dict=self.requests,
                docs=self.docs,
                task_dict=self.task_dict,
                override_bs=self.pipeline_parameters.override_batch_size,
                evaluation_tracker=self.evaluation_tracker,
            )

        if self.accelerator:
            context = self.accelerator.is_main_process
        elif self.parallel_context:
            context = dist.get_rank(self.parallel_context.world_pg) == 0
        else:
            context = nullcontext()

        if context:
            with htrack_block("Compiling results"):
                self.evaluation_tracker.general_config_logger.log_end_time()
                self.evaluation_tracker.metrics_logger.aggregate(task_dict=self.task_dict, bootstrap_iters=1000)
                self.evaluation_tracker.details_logger.aggregate()

        with htrack_block("Cleaninp up"):  # For non nanotron models
            for weights in ["delta", "adapter"]:
                try:
                    tmp_weights_dir = f"{self.evaluation_tracker.general_config_logger.model_name}-{weights}-applied"
                    shutil.rmtree(tmp_weights_dir)
                    hlog(f"Removed {tmp_weights_dir}")
                except OSError:
                    pass
            self.model.cleanup()

    def save_and_push_results(self):
        self.evaluation_tracker.save()

    def show_results(self):
        final_dict = self.evaluation_tracker.generate_final_dict()
        print(make_results_table(final_dict))
        return final_dict
