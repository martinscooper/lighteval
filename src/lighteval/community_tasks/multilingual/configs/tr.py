from typing import get_args

from ..tasks.utils.tasks_helpers import tasks_to_string
from ..tasks.mqa.exams import ExamsTask
from ..tasks.qa.tquad import Tquad2Task
from ..tasks.suites.turkish_leaderboard import ARCEasyTrTask, HellaSwagTrTask, MMLUTaskTr, TruthfulQATrTask, WinogradeTrTask, MMLU_SUBSETS
from ..tasks.mqa_with_context.belebele import BelebeleTask
from ..tasks.mqa_with_context.xquad import XquadTask
from ..tasks.nli.xnli import XNLITask
from ..tasks.mqa.xcopa import XCopaTask


_GENERATIVE_TASKS = [
    XquadTask(lang="tr"),
    Tquad2Task(),
]

_MC_TASKS = [
    BelebeleTask(lang="tr"),
    XNLITask(lang="tr"),
    XCopaTask(lang="tr"),
    ExamsTask(lang="tr"),
    HellaSwagTrTask(),
    TruthfulQATrTask("mc1"),
    TruthfulQATrTask("mc2"),
    ARCEasyTrTask(),
    WinogradeTrTask(),
    *[MMLUTaskTr(subset) for subset in get_args(MMLU_SUBSETS)]
]

_ALL_TASKS = list(set(_GENERATIVE_TASKS + _MC_TASKS))
TASKS_GROUPS = {
    "all": tasks_to_string(_ALL_TASKS),
    "generative": tasks_to_string(_GENERATIVE_TASKS),
    "mc": tasks_to_string(_MC_TASKS),
    "xnli": tasks_to_string([XNLITask(lang="tr")]),
}

TASKS_TABLE = [task.as_dict() for task in _ALL_TASKS]

if __name__ == "__main__":
    print([t for t in TASKS_TABLE])
    print(len(TASKS_TABLE))
