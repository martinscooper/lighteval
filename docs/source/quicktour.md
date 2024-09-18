# Quicktour

We provide two main entry points to evaluate models:

- `lighteval accelerate` : evaluate models on CPU or one or more GPUs using [🤗
  Accelerate](https://github.com/huggingface/accelerate)
- `lighteval nanotron`: evaluate models in distributed settings using [⚡️
  Nanotron](https://github.com/huggingface/nanotron)

## Accelerate

### Evaluate a model on a GPU

To evaluate `GPT-2` on the Truthful QA benchmark, run:

```bash
lighteval accelerate \
     --model_args "pretrained=gpt2" \
     --tasks "leaderboard|truthfulqa:mc|0|0" \
     --override_batch_size 1 \
     --output_dir="./evals/"
```

Here, `--tasks` refers to either a comma-separated list of supported tasks from
the [tasks_list](tasks) in the format:

```bash
{suite}|{task}|{num_few_shot}|{0 or 1 to automatically reduce `num_few_shot` if prompt is too long}
```

or a file path like
[examples/tasks/recommended_set.txt](https://github.com/huggingface/lighteval/blob/main/examples/tasks/recommended_set.txt)
which specifies multiple task configurations.

Tasks details can be found in the
[file](https://github.com/huggingface/lighteval/blob/main/src/lighteval/tasks/default_tasks.py)
implementing them.

### Evaluate a model on one or more GPUs

#### Data parallelism

To evaluate a model on one or more GPUs, first create a multi-gpu config by running.

```bash
accelerate config
```

You can then evaluate a model using data parallelism on 8 GPUs like follows:

```bash
accelerate launch --multi_gpu --num_processes=8 -m \
    lighteval accelerate \
    --model_args "pretrained=gpt2" \
    --tasks "leaderboard|truthfulqa:mc|0|0" \
    --override_batch_size 1 \
    --output_dir="./evals/"
```

Here, `--override_batch_size` defines the batch size per device, so the effective
batch size will be `override_batch_size * num_gpus`.

### Model Arguments

The `--model_args` argument takes a string representing a list of model
argument. The arguments allowed vary depending on the backend you use (vllm or
accelerate).

#### Accelerate

- **pretrained** (str):
    HuggingFace Hub model ID name or the path to a pre-trained
    model to load. This is effectively the `pretrained_model_name_or_path`
    argument of `from_pretrained` in the HuggingFace `transformers` API.
- **tokenizer** (Optional[str]): HuggingFace Hub tokenizer ID that will be
    used for tokenization.
- **multichoice_continuations_start_space** (Optional[bool]): Whether to add a
    space at the start of each continuation in multichoice generation.
    For example, context: "What is the capital of France?" and choices: "Paris", "London".
    Will be tokenized as: "What is the capital of France? Paris" and "What is the capital of France? London".
    True adds a space, False strips a space, None does nothing
- **subfolder** (Optional[str]): The subfolder within the model repository.
- **revision** (str): The revision of the model.
- **max_gen_toks** (Optional[int]): The maximum number of tokens to generate.
- **max_length** (Optional[int]): The maximum length of the generated output.
- **add_special_tokens** (bool, optional, defaults to True): Whether to add special tokens to the input sequences.
   If `None`, the default value will be set to `True` for seq2seq models (e.g. T5) and
    `False` for causal models.
- **model_parallel** (bool, optional, defaults to False):
    True/False: force to use or not the `accelerate` library to load a large
    model across multiple devices.
    Default: None which corresponds to comparing the number of processes with
        the number of GPUs. If it's smaller => model-parallelism, else not.
- **dtype** (Union[str, torch.dtype], optional, defaults to None):):
    Converts the model weights to `dtype`, if specified. Strings get
    converted to `torch.dtype` objects (e.g. `float16` -> `torch.float16`).
    Use `dtype="auto"` to derive the type from the model's weights.
- **device** (Union[int, str]): device to use for model training.
- **quantization_config** (Optional[BitsAndBytesConfig]): quantization
    configuration for the model, manually provided to load a normally floating point
    model at a quantized precision. Needed for 4-bit and 8-bit precision.
- **trust_remote_code** (bool): Whether to trust remote code during model
    loading.

#### VLLM

- **pretrained** (str): HuggingFace Hub model ID name or the path to a pre-trained model to load.
- **gpu_memory_utilisation** (float): The fraction of GPU memory to use.
- **batch_size** (int): The batch size for model training.
- **revision** (str): The revision of the model.
- **dtype** (str, None): The data type to use for the model.
- **tensor_parallel_size** (int): The number of tensor parallel units to use.
- **data_parallel_size** (int): The number of data parallel units to use.
- **max_model_length** (int): The maximum length of the model.
- **swap_space** (int): The CPU swap space size (GiB) per GPU.
- **seed** (int): The seed to use for the model.
- **trust_remote_code** (bool): Whether to trust remote code during model loading.
- **use_chat_template** (bool): Whether to use the chat template or not.
- **add_special_tokens** (bool): Whether to add special tokens to the input sequences.
- **multichoice_continuations_start_space** (bool): Whether to add a space at the start of each continuation in multichoice generation.
- **subfolder** (Optional[str]): The subfolder within the model repository.


#### Pipeline parallelism

To evaluate a model using pipeline parallelism on 2 or more GPUs, run:

```bash
lighteval accelerate \
    --model_args "pretrained=gpt2,model_parallel=True" \
    --tasks "leaderboard|truthfulqa:mc|0|0" \
    --override_batch_size 1 \
    --output_dir="./evals/"
```

This will automatically use accelerate to distribute the model across the GPUs.

<Tip>
Both data and pipeline parallelism can be combined by setting
`model_parallel=True` and using accelerate to distribute the data across the
GPUs.
</Tip>

## Nanotron

To evaluate a model trained with nanotron on a single gpu.

<Tip warning={true}>
Nanotron models cannot be evaluated without torchrun.
</Tip>

```bash
 torchrun --standalone --nnodes=1 --nproc-per-node=1  \
 src/lighteval/__main__.py nanotron \
 --checkpoint_config_path ../nanotron/checkpoints/10/config.yaml \
 --lighteval_config_path examples/nanotron/lighteval_config_override_template.yaml
 ```

The `nproc-per-node` argument should match the data, tensor and pipeline
parallelism confidured in the `lighteval_config_template.yaml` file.
That is: `nproc-per-node = data_parallelism * tensor_parallelism *
pipeline_parallelism`.