import os, torch

import argparse
import asyncio

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    pipeline,
    logging,
)

import transformers
transformers.logging.set_verbosity_error()

device = "cuda" if torch.cuda.is_available() else "cpu"
if torch.backends.mps.is_available():
    device = "mps"
print(f"Using device : {device}")

async def main():

    parser = argparse.ArgumentParser(description="Running LLM")

    # Change this line: --input is now the input file path
    parser.add_argument("--input_file", type=str, default="", help="Path to the input text file")
    parser.add_argument(
        "--model",
        help="Model name or path", # Added help description
        default="unsloth/Llama-3.2-3B-Instruct",
    )

    args = parser.parse_args()

    # Read content from the input file
    if not args.input_file:
        print("Error: Please provide an input file using --input_file argument.")
        return

    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            input_text = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found at {args.input_file}")
        return
    except Exception as e:
        print(f"Error reading file {args.input_file}: {e}")
        return

    base_model   = args.model

    # QLoRA config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        torch_dtype=torch.float16,
        load_in_8bit=False,
        device_map="auto",
        attn_implementation="eager",
    )

    # Load tokenizer
    tokenizer              = AutoTokenizer.from_pretrained(base_model)
    tokenizer.pad_token_id = tokenizer.eos_token_id
    tokenizer.padding_side = "right"

    PAD_TOKEN = "<|pad|>"
    tokenizer.add_special_tokens({"pad_token": PAD_TOKEN})


    messages = [
        {"role": "system","content": "You are a expert summarization in Thai documents" },
        {"role": "user", "content": input_text} # Use the content read from the file
    ]

    prompt  = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs  = tokenizer(prompt, return_tensors='pt', padding=True, truncation=True).to("cuda")
    outputs = model.generate(
        **inputs,
        max_length=2048,
        num_return_sequences=1,
        temperature=0.1,
        repetition_penalty=1.2,
        no_repeat_ngram_size=4
        )

    response    = tokenizer.decode(outputs[0], skip_special_tokens=True)
    answer      = response.split("assistant")[1]
    print(f"{answer}")
    print(len(answer))


if __name__ == "__main__":
    asyncio.run(main())