from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Union

from nanotron.config.parallelism_config import ParallelismArgs
from nanotron.generation.sampler import SamplerType

DEFAULT_GENERATION_SEED = 42


@dataclass
class GenerationArgs:
    sampler: Optional[Union[str, SamplerType]] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    n_samples: Optional[int] = None
    eos: Optional[str] = None
    seed: Optional[int] = None
    use_cache: Optional[bool] = False

    def __post_init__(self):
        if isinstance(self.sampler, str):
            self.sampler = SamplerType[self.sampler.upper()]
        if self.seed is None:
            self.seed = DEFAULT_GENERATION_SEED


@dataclass
class LightEvalLoggingArgs:
    """Arguments related to logging for LightEval"""

    logging_dir: str
    save_results: bool = True
    save_details: bool = False
    save_to_tensorboard: bool = False
    tensorboard_metric_prefix: str = "eval"

@dataclass
class LightEvalTasksArgs:
    """Arguments related to tasks for LightEval"""

    tasks: str
    custom_tasks: Optional[str] = None
    max_samples: Optional[int] = None
    num_fewshot_seeds: Optional[int] = None

    dataset_loading_processes: int = 8
    multichoice_continuations_start_space: Optional[bool] = None
    no_multichoice_continuations_start_space: Optional[bool] = None


@dataclass
class LightEvalWandbLoggerConfig:
    """Arguments related to the local Wandb logger"""

    wandb_project: str = ""
    wandb_entity: Optional[str] = None
    wandb_run_name: Optional[str] = None

    def __post_init__(self):
        assert self.wandb_project != "", "Please specify a wandb_project"


@dataclass
class LightEvalConfig:
    """Arguments related to running LightEval on checkpoints.

    All is optional because you can also use this class to later supply arguments to override
    the saved config when running LightEval after training.
    """

    logging: LightEvalLoggingArgs
    tasks: LightEvalTasksArgs
    parallelism: ParallelismArgs
    slurm_template: Optional[str] = None
    slurm_script_dir: Optional[str] = None

    checkpoints_path: Optional[str] = None
    batch_size: Optional[int] = None
    generation: Optional[Union[GenerationArgs, Dict[str, GenerationArgs]]] = None
    wandb: Optional[LightEvalWandbLoggerConfig] = None
