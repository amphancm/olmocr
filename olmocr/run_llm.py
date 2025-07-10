 
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

#from IPython.display import Markdown, display

import transformers
transformers.logging.set_verbosity_error()

device = "cuda" if torch.cuda.is_available() else "cpu"
if torch.backends.mps.is_available():
    device = "mps"
print(f"Using device : {device}")
 
async def main():
 
    parser = argparse.ArgumentParser(description="Running LLM")

    parser.add_argument("--input", type=str, default="", help="")
    parser.add_argument(
        "--model",
        help="",
        default="unsloth/Llama-3.2-3B-Instruct",
    )

    args = parser.parse_args()

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
        
        {"role": "system","content": "You are a friendly chatbot who always responds in the style of a programmer" },

        {"role": "user", "content": {args.input}}   
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