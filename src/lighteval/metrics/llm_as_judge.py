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


import time
from typing import Callable, Literal

from lighteval.logging.hierarchical_logger import hlog_warn


class JudgeLM:
    """
    A class representing a judge for evaluating answers using either the OpeanAI or Transformers library.

    Args:
        model (str): The name of the model.
        templates (Callable): A function taking into account the question, options, answer, and gold and returning the judge prompt.
        process_judge_response (Callable): A function for processing the judge's response.
        judge_backend (Literal["openai", "transformers", "tgi", "vllm"]): The backend for the judge.
        url (str | None): The URL for the OpenAI API.
        api_key (str | None): The API key for the OpenAI API (either OpenAI or HF key).

    Attributes:
        model (str): The name of the model.
        template (Callable): A function taking into account the question, options, answer, and gold and returning the judge prompt.
        API_MAX_RETRY (int): The maximum number of retries for the API.
        API_RETRY_SLEEP (int): The time to sleep between retries.
        client (Any): The OpenAI client.
        pipe (Any): The Transformers or vllm pipeline.
        process_judge_response (Callable): A function for processing the judge's response.
        url (str | None): The URL for the OpenAI API.
        api_key (str | None): The API key for the OpenAI API (either OpenAI or HF key).
        backend (Literal["openai", "transformers", "tgi", "vllm"]): The backend for the judge

    Methods:
        evaluate_answer: Evaluates an answer using the OpenAI API or Transformers library.
        __lazy_load_client: Lazy loads the OpenAI client or Transformers pipeline.
        __call_api: Calls the API to get the judge's response.
        __call_transformers: Calls the Transformers pipeline to get the judge's response.
        __call_vllm: Calls the VLLM pipeline to get the judge's response.
    """

    def __init__(
        self,
        model: str,
        templates: Callable,
        process_judge_response: Callable,
        judge_backend: Literal["openai", "transformers", "tgi", "vllm"],
        url: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model
        self.template = templates

        self.API_MAX_RETRY = 3
        self.API_RETRY_SLEEP = 1

        self.client = None
        self.pipe = None
        self.process_judge_response = process_judge_response

        self.url = url
        self.api_key = api_key
        self.backend = judge_backend

    def __lazy_load_client(self):
        match self.backend:
            case "openai" | "tgi":
                if self.client is None:
                    from openai import OpenAI

                    if self.url is None:
                        self.client = OpenAI(api_key=self.api_key)
                    else:
                        self.client = OpenAI(base_url=self.url, api_key=self.api_key)
                return self.__call_api
            case "transformers":
                if self.pipe is None:
                    import torch
                    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

                    transformers_model = AutoModelForCausalLM.from_pretrained(
                        self.model, torch_dtype=torch.bfloat16, trust_remote_code=False, device_map="cuda"
                    )
                    tokenizer = AutoTokenizer.from_pretrained(self.model)
                    self.pipe = pipeline(
                        "text-generation",
                        model=transformers_model,
                        tokenizer=tokenizer,
                        max_new_tokens=256,
                    )
                return self.__call_transformers
            case "vllm":
                if self.pipe is None:
                    from vllm import LLM, SamplingParams

                    self.sampling_params = SamplingParams(temperature=0.8, top_p=0.95, max_tokens=512)
                    self.pipe = LLM(model=self.model, max_model_len=4096, gpu_memory_utilization=0.5)
                return self.__call_vllm
            case _:
                return lambda x: x

    def evaluate_answer(self, question: str, answer: str, options: list[str] | None = None, gold: str | None = None):
        """
        Evaluates an answer using either Transformers or OpenAI API.

        Args:
            questions (list[str]): The prompt asked to the evaluated model
            answers (list[str]): Answer given by the evaluated model
            references (list[str]): A list of reference answers

        Returns:
            A tuple containing the score, prompts, and judgment.
        """
        # lazy loading of the pipeline
        judge_function = self.__lazy_load_client()
        prompt = self.template(question=question, options=options, answer=answer, gold=gold)
        response = judge_function(prompt)
        score = self.process_judge_response(response)

        return score, prompt, response

    def __call_transformers(self, prompt):
        response = self.pipe(prompt)[0]["generated_text"]
        response = response[-1]["content"]
        return response

    def __call_vllm(self, prompt):
        output = self.pipe.chat(prompt, self.sampling_params, use_tqdm=False)[0]
        return output.outputs[0].text

    def __call_api(self, prompt):
        for _ in range(self.API_MAX_RETRY):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=prompt,
                    max_tokens=512,
                    n=1,
                )
                return response.choices[0].message.content
            except Exception as e:
                hlog_warn(f"{type(e), e}")
                time.sleep(self.API_RETRY_SLEEP)
        raise Exception("Failed to get response from the API")
