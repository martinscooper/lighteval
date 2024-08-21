from lighteval.metrics.metrics import Metrics
from lighteval.metrics.normalizations import PMINorm
from lighteval.metrics.utils import Metric
from lighteval.models.model_output import GenerateReturn, LoglikelihoodReturn
from lighteval.tasks.lighteval_task import LightevalTask, LightevalTaskConfig
from lighteval.tasks.requests import Doc, LoglikelihoodRequest, RequestType
from tests.utils import FakeModel, run_fake_task
from lighteval.tasks.default_tasks import xstory_cloze_en_lighteval



# Doesn't matter as won't be used
def dummy_prompt_fc(line, task_name: str = None):
    return Doc(task_name=task_name, query=line["input_sentence_1"], unconditioned_query="", gold_index=0, choices=["Hello", "World"])

def get_pmi_task(metrics: list[Metric]):
    return LightevalTaskConfig(
        name="pmi_test_task",
        metric=metrics,
        prompt_function=dummy_prompt_fc,
        hf_repo=xstory_cloze_en_lighteval.hf_repo,
        hf_subset=xstory_cloze_en_lighteval.hf_subset,
        evaluation_splits=xstory_cloze_en_lighteval.evaluation_splits,

)

def test_pmi_request():
    """
    Test that the PMI requests are correctly routed and computed
    """
    fake_model = FakeModel(loglikelihood_responses=[
        LoglikelihoodReturn(
            result=(0.9, True),
            generated_tokens=[0],
            input_tokens=[0],
        ),
        LoglikelihoodReturn(
            result=(0.2, False),
            generated_tokens=[0],
            input_tokens=[0],
        ),
        # Normalization loglikehioods
        LoglikelihoodReturn(
            result=(0.85, True),
            generated_tokens=[0],
            input_tokens=[0],
      
        ),
        LoglikelihoodReturn(
            result=(0.1, False),
            generated_tokens=[0],
            input_tokens=[0],
      
        ),
    ])

    metric = Metrics.loglikelihood_acc_metric(normalization=PMINorm())
    pmi_test_config = get_pmi_task(metrics=[metric])
    pmi_test_config.metric = (metric,)
    task = LightevalTask(pmi_test_config.name, pmi_test_config)
    result = run_fake_task(task, fake_model, max_samples=1)
    # Correc choice after norm should be the second one so 0 acc
    assert result[f"{task.name}|0"][metric.metric_name][0] == 0
    

def test_pmi_request_with_generative_metric():
    """
    Test that the PMI requests are correctly routed even with other metrics to compute
    This is mostly that results are mutated in place, which can quickly backfire if we don't
    do it in correct order.
    """
    fake_model = FakeModel(loglikelihood_responses=[
        LoglikelihoodReturn(
            result=(0.9, True),
            generated_tokens=[0],
            input_tokens=[0],
        ),
        LoglikelihoodReturn(
            result=(0.2, False),
            generated_tokens=[0],
            input_tokens=[0],
        ),
        # Normalization loglikehioods
        LoglikelihoodReturn(
            result=(0.85, True),
            generated_tokens=[0],
            input_tokens=[0],
        ),
        LoglikelihoodReturn(
            result=(0.1, False),
            generated_tokens=[0],
            input_tokens=[0],
        )
    ],
    greedy_until_responses=[
            GenerateReturn(
                result="Hello",
                generated_tokens=[0],
                input_tokens=[0],
            )
        ]
    ) 

    metrics = [Metrics.loglikelihood_acc_metric(normalization=PMINorm()), Metrics.exact_match.value]
    pmi_test_config = get_pmi_task(metrics=metrics)
    task = LightevalTask(pmi_test_config.name, pmi_test_config)
    results = run_fake_task(task, fake_model, max_samples=1)
    assert results[f"{task.name}|0"][metrics[0].metric_name][0] == 0
    assert results[f"{task.name}|0"][metrics[1].metric_name][0] == 1
    




