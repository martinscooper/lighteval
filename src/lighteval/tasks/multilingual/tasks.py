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

from langcodes import Language as LangCodeLanguage
from langcodes import standardize_tag

from lighteval.metrics.dynamic_metrics import loglikelihood_acc_metric
from lighteval.metrics.normalizations import LogProbTokenNorm
from lighteval.tasks.lighteval_task import LightevalTaskConfig
from lighteval.tasks.templates.copa import get_copa_prompt_function
from lighteval.tasks.templates.hellaswag import get_hellaswag_prompt_function
from lighteval.tasks.templates.nli import get_nli_prompt_function
from lighteval.tasks.templates.utils.formulation import (
    CFFormulation,
    HybridFormulation,
    MCFFormulation,
)
from lighteval.utils.language import Language


# ------------------------------- NLI Tasks ------------------------------- #

xnli_tasks = [
    LightevalTaskConfig(
        name=f"xnli_{language.value}_{formulation.name.lower()}",
        suite=["custom"],
        metric=[loglikelihood_acc_metric(normalization=LogProbTokenNorm())],
        prompt_function=get_nli_prompt_function(
            language=language,
            adapter=lambda line: {
                "premise": line["premise"],
                "hypothesis": line["hypothesis"],
                # Since we ignore the neural label
                "gold_idx": {0: 0, 2: 1}[line["label"]],
            },
            relations=["entailment", "contradiction"],
            formulation=formulation,
        ),
        hf_filter=lambda line: line["label"] in [0, 2],
        hf_repo="facebook/xnli",
        hf_subset=standardize_tag(language.value),
        evaluation_splits=["validation"],
        few_shots_split="train",
    )
    for language in [
        Language.ARABIC,
        Language.ENGLISH,
        Language.FRENCH,
        Language.SPANISH,
        Language.BULGARIAN,
        Language.GERMAN,
        Language.GREEK,
        Language.ENGLISH,
        Language.FRENCH,
        Language.HINDI,
        Language.RUSSIAN,
        Language.SWAHILI,
        Language.THAI,
        Language.TURKISH,
        Language.URDU,
        Language.VIETNAMESE,
        Language.CHINESE,
    ]
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

xnli2_tasks = [
    LightevalTaskConfig(
        name=f"xnli2.0_{language.value}_{formulation.name.lower()}",
        suite=["custom"],
        metric=[loglikelihood_acc_metric(normalization=LogProbTokenNorm())],
        prompt_function=get_nli_prompt_function(
            language=language,
            adapter=lambda line: {
                "premise": line["premise"],
                "hypothesis": line["hypothesis"],
                # Since we ignore the neural label
                "gold_idx": {0: 0, 2: 1}[line["label"]],
            },
            relations=["entailment", "contradiction"],
            formulation=formulation,
        ),
        hf_filter=lambda line: line["label"] in [0, 2],
        hf_repo=f"Harsit/xnli2.0_train_{LangCodeLanguage(standardize_tag(language.value)).language_name().lower()}",
        hf_subset="default",
        evaluation_splits=["train"],
    )
    for language in [
        Language.ENGLISH,
        Language.FRENCH,
        Language.PUNJABI,
        Language.GUJARATI,
        Language.KANNADA,
        Language.ASSAMESE,
        Language.BENGALI,
        Language.MARATHI,
        Language.SANSKRIT,
        Language.TAMIL,
        Language.GERMAN,
        Language.ENGLISH,
        Language.URDU,
        Language.VIETNAMESE,
        Language.TURKISH,
        Language.THAI,
        Language.SWAHILI,
        Language.SPANISH,
        Language.RUSSIAN,
        Language.HINDI,
        Language.GREEK,
        Language.CHINESE,
        Language.BULGARIAN,
        Language.ARABIC,
        # Theoretically also: Bhojpuri, Gujarati, Odiya
    ]
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

xnli_indic_tasks = [
    LightevalTaskConfig(
        name=f"indicnxnli_{language.value}_{formulation.name.lower()}",
        suite=["custom"],
        prompt_function=get_nli_prompt_function(
            language=language,
            adapter=lambda line: {
                "premise": line["premise"],
                "hypothesis": line["hypothesis"],
                # Since we ignore the neural label
                "gold_idx": {0: 0, 2: 1}[line["label"]],
            },
            relations=["entailment", "contradiction"],
            formulation=formulation,
        ),
        hf_repo="Divyanshu/indicxnli",
        hf_subset=standardize_tag(language.value),
        # Ignore neutral
        hf_filter=lambda x: int(x["label"]) in [0, 2],
        evaluation_splits=["validation"],
        few_shots_split="train",
        few_shots_select=None,
        generation_size=-1,
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
    )
    for language in [
        Language.ASSAMESE,
        Language.BENGALI,
        Language.GUJARATI,
        Language.HINDI,
        Language.KANNADA,
        Language.MALAYALAM,
        Language.MARATHI,
        Language.ORIYA,
        Language.PUNJABI,
        Language.TAMIL,
        Language.TELUGU,
    ]
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

paws_x_tasks = [
    LightevalTaskConfig(
        name=f"pawsx_{language.value}_{formulation.name.lower()}",
        suite=("custom",),
        prompt_function=get_nli_prompt_function(
            language=language,
            adapter=lambda line: {
                "premise": line["sentence1"],
                "hypothesis": line["sentence2"],
                # Since we ignore the neural label
                "gold_idx": int(line["label"]),
            },
            relations=["entailment", "contradiction"],
            formulation=formulation,
        ),
        hf_repo="google-research-datasets/paws-x",
        hf_subset=standardize_tag(language.value),
        evaluation_splits=("test",),
        few_shots_split="train",
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
    )
    for language in [
        Language.GERMAN,
        Language.ENGLISH,
        Language.SPANISH,
        Language.FRENCH,
        Language.JAPANESE,
        Language.KOREAN,
        Language.CHINESE,
    ]
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

rcb_tasks = [
    LightevalTaskConfig(
        name=f"rcb_{Language.RUSSIAN.value}_{formulation.name.lower()}",
        prompt_function=get_nli_prompt_function(
            language=Language.RUSSIAN,
            adapter=lambda line: {
                "premise": line["inputs"]["premise"],
                "hypothesis": line["inputs"]["hypothesis"],
                # Since we ignore the neural label
                "gold_idx": int(line["outputs"]) - 1,
            },
            relations=["entailment", "contradiction"],
            formulation=formulation,
        ),
        suite=("custom",),
        hf_repo="ai-forever/MERA",
        hf_subset="rcb",
        # Ignore neutral label
        hf_filter=lambda x: int(x["outputs"] or "0") in [1, 2],
        evaluation_splits=("train", "validation"),
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
    )
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

# Non translated chinese task
ocnli_tasks = [
    LightevalTaskConfig(
        name=f"ocnli_{Language.CHINESE.value}_{formulation.name.lower()}",
        prompt_function=get_nli_prompt_function(
            language=Language.CHINESE,
            adapter=lambda line: {
                "premise": line["sentence1"],
                "hypothesis": line["sentence2"],
                # Since we ignore the neural label
                "gold_idx": {1: 0, 2: 1}[line["label"]],
            },
            relations=["entailment", "contradiction"],
            formulation=formulation,
        ),
        suite=("custom",),
        hf_repo="clue/clue",
        hf_subset="ocnli",
        # Only keep the positive and negative examples
        hf_filter=lambda x: int(x["label"]) in [1, 2],
        evaluation_splits=("validation",),
        few_shots_split="train",
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
    )
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

cmnli_tasks = [
    LightevalTaskConfig(
        name=f"cmnli_{Language.CHINESE.value}_{formulation.name.lower()}",
        prompt_function=get_nli_prompt_function(
            language=Language.CHINESE,
            adapter=lambda line: {
                "premise": line["sentence1"],
                "hypothesis": line["sentence2"],
                # Since we ignore the neural label
                "gold_idx": {"entailment": 0, "contradiction": 1}[line["label"]],
            },
            relations=["entailment", "contradiction"],
            formulation=formulation,
        ),
        suite=("custom",),
        hf_repo="fenffef/cmnli",
        hf_subset="default",
        hf_filter=lambda x: x["label"] in ["entailment", "contradiction"],
        # Only keep the positive and negative examples
        evaluation_splits=("validation",),
        few_shots_split="train",
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
    )
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

# ------------------------------- Copa Tasks ------------------------------- #

copa_tasks = [
    LightevalTaskConfig(
        name=f"xcopa_{language.value}_{formulation.name.lower()}",
        suite=["custom"],
        prompt_function=get_copa_prompt_function(
            language,
            adapter=lambda line: {
                "context": line["premise"],
                "cause_effect": line["question"],
                "continuations": [line["choice1"], line["choice2"]],
                "gold_idx": int(line["label"]),
            },
            formulation=formulation,
        ),
        hf_repo="OALL/AlGhafa-Arabic-LLM-Benchmark-Translated" if language == Language.ARABIC else "xcopa",
        hf_subset="copa_ext_ar" if language == Language.ARABIC else standardize_tag(language.value),
        evaluation_splits=["test"],
        few_shots_split="validation",
        generation_size=-1,
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
    )
    for language in [
        Language.ESTONIAN,
        Language.INDONESIAN,
        Language.ITALIAN,
        Language.SWAHILI,
        Language.TAMIL,
        Language.THAI,
        Language.TURKISH,
        Language.VIETNAMESE,
        Language.CHINESE,
        # Optionally: Haitian, Quechu
    ]
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

copa_indic_tasks = [
    LightevalTaskConfig(
        name=f"indicxcopa_{language.value}_{formulation.name.lower()}",
        suite=["custom"],
        prompt_function=get_copa_prompt_function(
            language,
            adapter=lambda line: {
                "context": line["premise"],
                "cause_effect": line["question"],
                "continuations": [line["choice1"], line["choice2"]],
                "gold_idx": int(line["label"]),
            },
            formulation=formulation,
        ),
        hf_repo="ai4bharat/IndicCOPA",
        hf_subset=f"translation-{standardize_tag(language.value)}",
        evaluation_splits=["test"],
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
        trust_dataset=True,
    )
    for language in [
        Language.ASSAMESE,
        Language.BENGALI,
        Language.GUJARATI,
        Language.HINDI,
        Language.KANNADA,
        Language.MALAYALAM,
        Language.MARATHI,
        Language.NEPALI,
        Language.ORIYA,
        Language.PUNJABI,
        Language.SANSKRIT,
        Language.SINDHI,
        Language.TAMIL,
        Language.TELUGU,
        Language.URDU,
        # Optionally: Maithili, Santali, Sindhi, Konkani
    ]
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

parus_tasks = [
    LightevalTaskConfig(
        name=f"parus_{Language.RUSSIAN.value}_{formulation.name.lower()}",
        suite=["custom"],
        prompt_function=get_copa_prompt_function(
            language=Language.RUSSIAN,
            adapter=lambda line: {
                "context": line["inputs"]["premise"],
                "cause_effect": line["meta"]["task"],
                "continuations": [line["inputs"]["choice1"], line["inputs"]["choice2"]],
                "gold_idx": int(line["outputs"]) - 1,
            },
            formulation=formulation,
        ),
        hf_repo="ai-forever/MERA",
        hf_subset="parus",
        evaluation_splits=["train"],
        few_shots_split="validation",
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
    )
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]


# ------------------------------- Hellaswag Tasks ------------------------------- #

mlmm_hellaswag_tasks = [
    LightevalTaskConfig(
        name=f"hellaswag_{lang.value}_{formulation.name.lower()}",
        suite=["custom"],
        prompt_function=get_hellaswag_prompt_function(
            language=lang,
            adapter=lambda line: {
                # We don't use activity_label they are not available
                "ctx_a": line["ctx_a"],
                "ctx_b": line["ctx_b"],
                "continuations": line["endings"],
                "gold_idx": int(line["label"]),
            },
            formulation=formulation,
        ),
        hf_repo="jon-tow/okapi_hellaswag",
        hf_subset=standardize_tag(lang.value),
        hf_revision="96ed8e0dfc6172dad1d3df338d7b8ba6c1ff9d83",
        trust_dataset=True,
        evaluation_splits=["validation"],
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
    )
    for lang in [
        Language.ARABIC,
        Language.BENGALI,
        Language.CATALAN,
        Language.DANISH,
        Language.GERMAN,
        Language.SPANISH,
        Language.BASQUE,
        Language.FRENCH,
        Language.GUJARATI,
        Language.HINDI,
        Language.CROATIAN,
        Language.HUNGARIAN,
        Language.ARMENIAN,
        Language.INDONESIAN,
        Language.ICELANDIC,
        Language.ITALIAN,
        Language.KANNADA,
        Language.MALAYALAM,
        Language.MARATHI,
        Language.NORWEGIAN,
        Language.NEPALI,
        Language.DUTCH,
        Language.PORTUGUESE,
        Language.ROMANIAN,
        Language.RUSSIAN,
        Language.SLOVAK,
        Language.SERBIAN,
        Language.SWEDISH,
        Language.TAMIL,
        Language.TELUGU,
        Language.UKRAINIAN,
        Language.VIETNAMESE,
        Language.CHINESE,
    ]
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

hellaswag_tur_tasks = [
    LightevalTaskConfig(
        name=f"hellaswag_{Language.TURKISH.value}_{formulation.name.lower()}",
        suite=["custom"],
        prompt_function=get_hellaswag_prompt_function(
            language=Language.TURKISH,
            adapter=lambda line: {
                "ctx_a": line["ctx_a"],
                "ctx_b": line["ctx_b"],
                "continuations": line["endings"],
                "gold_idx": int(line["label"]),
            },
            formulation=formulation,
            # https://github.com/malhajar17/lm-evaluation-harness_turkish/blob/main/lm_eval/tasks/hellaswag_tr-v0.2/utils.py
            dot_replacement=[" [title]", " [başlık]", " [adım]", " [header]"],
        ),
        hf_repo="malhajar/hellaswag_tr-v0.2",
        hf_subset="default",
        evaluation_splits=["validation"],
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
    )
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

hellaswag_tha_tasks = [
    LightevalTaskConfig(
        name=f"hellaswag_{Language.THAI.value}_{formulation.name.lower()}",
        suite=["custom"],
        prompt_function=get_hellaswag_prompt_function(
            language=Language.THAI,
            adapter=lambda line: {
                "ctx_a": line["ctx_a"],
                "ctx_b": line["ctx_b"],
                "continuations": line["endings"],
                "gold_idx": int(line["label"]),
            },
            formulation=formulation,
        ),
        hf_repo="HuggingFaceFW-Dev/hellaswag_thai",
        hf_subset="default",
        evaluation_splits=["validation"],
        few_shots_split="train",
        metric=[
            loglikelihood_acc_metric(normalization=LogProbTokenNorm()),
        ],
    )
    for formulation in [MCFFormulation(), CFFormulation(), HybridFormulation()]
]

TASKS_TABLE = [
    *xnli_tasks,
    *xnli2_tasks,
    *xnli_indic_tasks,
    *paws_x_tasks,
    *rcb_tasks,
    *ocnli_tasks,
    *cmnli_tasks,
    *copa_tasks,
    *copa_indic_tasks,
    *parus_tasks,
    *mlmm_hellaswag_tasks,
    *hellaswag_tur_tasks,
    *hellaswag_tha_tasks,
]
