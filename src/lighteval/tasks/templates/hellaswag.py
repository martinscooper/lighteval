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

import re
from typing import Callable

from typing_extensions import NotRequired, TypedDict

from lighteval.tasks.templates.continuation import get_continuation_prompt_function
from lighteval.tasks.templates.multichoice import create_adapter_from_dict
from lighteval.tasks.templates.utils.formatting_utils import (
    capitalize,
    fix_capitalization,
    fix_ending_punct,
    is_ended_sentence,
)
from lighteval.tasks.templates.utils.formulation import Formulation, MCFFormulation
from lighteval.tasks.templates.utils.translation_literals import TRANSLATION_LITERALS
from lighteval.utils.language import Language


# NLI Cause/Effect (Copa)
HELLASWAG_QUERY = "{activity_label}{ctx}"


class HellaswagInput(TypedDict):
    ctx_a: str
    continuations: list[str]
    gold_idx: int | list[int]
    instruction: NotRequired[str]
    activity_label: NotRequired[str]
    ctx_b: NotRequired[str]


class HellaswagAdapter(TypedDict):
    ctx_a: str
    continuations: str
    gold_idx: str
    instruction: NotRequired[str]
    activity_label: NotRequired[str]
    ctx_b: NotRequired[str]


def get_hellaswag_prompt_function(
    language: Language,
    adapter: Callable[[dict], HellaswagInput] | HellaswagAdapter,
    formulation: Formulation = MCFFormulation(),
    dot_replacement: list[str] = [" [title]"],
):
    """
    Create a templated prompt function for a Hellaswag task.

    Format:
    Context Premise thefore/cause | (Continuation 1, Continuation 2, Continuation 3)

    Args:
        language (Language): The language of the Hellaswag task.
        adapter (Callable[[dict], HellaswagInput] | HellaswagAdapter): A function or dictionary to adapt the input data to the required HellaswagInput format.
            Must map data from the dataset row to the HellaswagInput format.
            Note: The gold_idx must be an index or list of indices in the continuations list, indicating the correct continuation(s).
        formulation (Formulation, optional): The formulation to use for the task. Defaults to MCFFormulation().
        dot_replacement (list[str], optional): A list of strings to replace with dot. We have to replace the the texts with dots because
            of wikihow source.

    Returns:
        Callable: A function that generates COPA prompts based on the given parameters.
    """

    translation_literals = TRANSLATION_LITERALS[language]

    def preprocess(text):
        """Comes from AiHarness"""
        # text = text.strip()
        # NOTE: Brackets are artifacts of the WikiHow dataset portion of HellaSwag.
        for dot_repl in dot_replacement:
            text = text.replace(dot_repl, ". ")
        text = re.sub("\\[.*?\\]", "", text)
        text = text.replace("  ", " ")
        text = text.replace(r"\.+", r"\.")
        return text.strip()

    def process_context(ctx):
        if ctx == "":
            return ""
        return capitalize(fix_ending_punct(preprocess(ctx), translation_literals))

    def join_ctxs(ctx_a, ctx_b):
        space = (
            translation_literals.sentence_space
            if is_ended_sentence(ctx_a, translation_literals)
            else translation_literals.word_space
        )
        return f"{ctx_a.rstrip()}{space}{fix_capitalization(ctx_a, ctx_b, translation_literals)}"

    adapter_fn: Callable[[dict], HellaswagInput] = (
        create_adapter_from_dict(adapter) if isinstance(adapter, dict) else adapter  # type: ignore
    )
    continuation_prompt_fn = get_continuation_prompt_function(
        language, {"context": "context", "continuations": "continuations", "gold_idx": "gold_idx"}, formulation
    )

    def hellaswag_prompt(
        line: dict,
        task_name: str,
    ):
        input_data = adapter_fn(line)
        activity_label = input_data.get("activity_label", "")
        activity_label = f"{capitalize(activity_label)}:\n" if activity_label else ""

        # Last one should be left as is
        ctx_a, ctx_b = capitalize(input_data["ctx_a"]), input_data.get("ctx_b", "")
        if ctx_b:
            ctx_a = join_ctxs(process_context(ctx_a), process_context(ctx_b))

        # Removoal of the [header] can happen and we need the first letter to be capital afterwards
        full_context = HELLASWAG_QUERY.format(activity_label=activity_label, ctx=ctx_a)
        choices = [preprocess(continuation) for continuation in input_data["continuations"]]

        # It can happen that the continuations are empty we thus skip the task
        # if any(len(c.strip()) == 0 for c in choices):
        #     return None

        return continuation_prompt_fn(
            {
                "instruction": input_data.get("instruction", ""),
                "context": full_context,
                "continuations": choices,
                "gold_idx": input_data["gold_idx"],
            },
            task_name,
        )

    return hellaswag_prompt