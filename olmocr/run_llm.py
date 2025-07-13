import os
import torch
import argparse
import asyncio
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)

import transformers

# Suppress verbose logging from transformers
transformers.logging.set_verbosity_error()

def setup_device():
    """Sets up and returns the appropriate device for torch."""
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def get_input_text(args):
    """Reads input text from a file or uses the direct text argument."""
    if args.input_file:
        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: Input file not found at {args.input_file}")
            return None
    elif args.input_text:
        return args.input_text
    return None

async def main():
    device = setup_device()
    # print(f"Using device: {device}")

    parser = argparse.ArgumentParser(description="Running LLM for summarization")
    parser.add_argument("--input_file", type=str, help="Path to the input text file.")
    parser.add_argument("--input_text", type=str, help="Direct input text.")
    parser.add_argument("--model", default="unsloth/Llama-3.2-3B-Instruct", help="Model to use for summarization.")
    parser.add_argument("--prediction", action="store_true", help="Enable prediction mode.")

    args = parser.parse_args()

    input_text = get_input_text(args)
    if not input_text:
        print("Error: No input text provided. Use --input_file or --input_text.")
        return

    # Configuration for model quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    # Load model and tokenizer
    try:
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            torch_dtype=torch.float16,
            #quantization_config=bnb_config,
            device_map="auto",
            attn_implementation="eager",
        )
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        tokenizer.pad_token_id = tokenizer.eos_token_id
        tokenizer.padding_side = "right"
    except Exception as e:
        print(f"Error loading model or tokenizer: {e}")
        return

    # Prepare the prompt
    system_prediction_prompt='''คุณคือผู้เชี่ยวชาญด้านการจำแนกเอกสาร โดยมีหน้าที่วิเคราะห์เนื้อหาของเอกสารที่ได้รับเข้ามา และระบุว่าควรส่งต่อไปยังหน่วยงานใดจากรายการต่อไปนี้:\n
        กองแผนและโครงการ: รับผิดชอบเอกสารเกี่ยวกับการวางแผน, โครงการพัฒนา, นโยบาย, แผนยุทธศาสตร์, การสำรวจความเป็นไปได้ของโครงการ, และการประเมินผลโครงการ\n
        กองเขตแดน: รับผิดชอบเอกสารเกี่ยวกับเขตแดน, การปักปันเขตแดน, สนธิสัญญาที่เกี่ยวข้องกับเขตแดน, ปัญหาข้อพิพาทเขตแดน, และการเจรจาชายแดน\n
        กองบิน: รับผิดชอบเอกสารเกี่ยวกับการบิน, อากาศยาน, น่านฟ้า, การควบคุมการจราจรทางอากาศ, กฎระเบียบการบิน, และการดำเนินการด้านการบินพลเรือนหรือทหาร\n
        แผนกงบประมาณ: รับผิดชอบเอกสารที่เกี่ยวข้องกับงบประมาณ, การจัดสรรงบประมาณ, การเบิกจ่าย, การตรวจสอบทางการเงิน, รายรับ-รายจ่าย, และการจัดทำประมาณการทางการเงิน\n
        ศูนย์ข้อมูล: รับผิดชอบเอกสารเกี่ยวกับการจัดการข้อมูล, ฐานข้อมูล, ระบบสารสนเทศ, การประมวลผลข้อมูล, การจัดเก็บข้อมูล, การวิเคราะห์ข้อมูล, และความปลอดภัยของข้อมูล'''

    user_prediction_prompt="โปรดวิเคราะห์เอกสารที่ให้มาและระบุ หน่วยงานที่ควรส่งต่อเอกสารนี้ ที่เหมาะสมที่สุดเพียงหน่วยงานเดียว เฉพาะชื่อหน่วยงานเท่านั้น"

    summary_prompt      = "You are a helpful assistant that summarizes text."

    user_summary_prompt = """
        โปรดอ่านและวิเคราะห์เอกสารทางราชการที่ได้รับเข้ามา และสรุปเนื้อหาให้ครอบคลุมประเด็นหลัก ดังตัวอย่างต่อไปนี้:\n
            เรื่อง/หัวข้อหลักของเอกสาร: เอกสารฉบับนี้เกี่ยวกับอะไร\n
            หน่วยงาน/ผู้ที่ออกเอกสาร: ใครเป็นผู้จัดทำหรือออกเอกสารฉบับนี้\n
            วันที่ออกเอกสาร: เอกสารถูกออกเมื่อไหร่ (ถ้ามี)\n
            วัตถุประสงค์หลัก: เอกสารนี้มีเจตนาเพื่ออะไร (เช่น แจ้งให้ทราบ, ขออนุมัติ, กำหนดแนวปฏิบัติ, สั่งการ)\n
            สาระสำคัญ/ประเด็นหลักที่ต้องการสื่อสาร: ข้อมูลสำคัญที่สุดที่เอกสารต้องการแจ้งคืออะไร มีรายละเอียดอะไรบ้างที่จำเป็นต้องรู้\n
            ข้อสรุป/การดำเนินการที่ต้องทำ (ถ้ามี): มีข้อสรุป หรือข้อกำหนดให้ดำเนินการอะไรต่อไปหรือไม่ ใครต้องทำอะไร อย่างไร
        """

    if args.prediction:
        messages = [
            {"role": "system", "content": f"{system_prediction_prompt}"},
            {"role": "user", "content": f"{user_prediction_prompt}\n\n{input_text}"}
        ]
    else:
        messages = [
            {"role": "system", "content": f"{summary_prompt}"},
            {"role": "user", "content": f"{user_summary_prompt}\n\n{input_text}"}
        ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    # Generate the summary
    inputs = tokenizer(prompt, return_tensors='pt', padding=True, truncation=True).to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=1024,  # Limit the length of the summary
        temperature=0.1,
        repetition_penalty=1.2,
        no_repeat_ngram_size=3
    )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Extract only the assistant's part of the response
    try:
        # The split logic might need adjustment based on the exact model output format
        answer = response.split("assistant\n")[-1].strip()
        print(answer)
    except IndexError:
        print(response) # Fallback to printing the whole response if split fails

if __name__ == "__main__":
    asyncio.run(main())