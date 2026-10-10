# -*- coding: utf-8 -*-
"""probe_prompts.py — يحمّل نموذج OCR مرّة ويجرّب عدة صيغ أوامر على صفحة،
ليكشف أيّ صياغة تجعل Qwen2.5-VL ينسخ النص بدل أن يعتذر."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ocr_engine as OE
import torch
from qwen_vl_utils import process_vision_info

PROMPTS = {
 "1_current" : "انسخ النص العربي في الصورة كما هو بكل الحركات، سطرًا بسطر.",
 "2_ar_firm" : "اكتب حرفيًّا كل النص العربي الظاهر في الصورة، بالتشكيل الكامل، سطرًا بسطر. أخرِج النص فقط، دون أي مقدمة أو تعليق أو اعتذار.",
 "3_ar_simple": "استخرج كل النص من الصورة.",
 "4_en_firm" : "Transcribe all Arabic text in this image verbatim, preserving every diacritic, line by line. Output only the transcribed text, no commentary, no refusal.",
 "5_en_simple": "Read all the text in the image and output it exactly.",
 "6_completion": "النص المكتوب في الصورة بالتشكيل الكامل:\n",
}

def run(proc, img, prompt):
    msgs=[{"role":"user","content":[{"type":"image","image":img},
          {"type":"text","text":prompt}]}]
    try:
        inp=proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True,
                                     return_dict=True, return_tensors="pt")
    except Exception:
        chat=proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        vi=process_vision_info(msgs)
        inp=proc(text=[chat], images=vi[0], videos=vi[1], padding=True, return_tensors="pt")
    inp=inp.to(OE._MODEL.device)
    with torch.inference_mode():
        g=OE._MODEL.generate(**inp, max_new_tokens=200, do_sample=False)
    t=[o[len(i):] for i,o in zip(inp.input_ids, g)]
    return proc.batch_decode(t, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

def main():
    img_path = sys.argv[1] if len(sys.argv)>1 else "_inspect/page_26.png"
    if not os.path.exists(img_path):
        print("لا صورة:", img_path); return
    OE._load()
    from transformers import AutoProcessor
    proc=AutoProcessor.from_pretrained(OE.MODEL_ID)
    img=OE._prep(img_path)
    print("النموذج:", OE.MODEL_ID, "| صفحة:", img_path)
    print("="*60)
    for k,p in PROMPTS.items():
        out=run(proc, img, p)
        refuse = any(w in out for w in ("عذرا","عذراً","لا يمكنني","مساعد ذكاء","I cannot","I'm sorry","as an AI"))
        tag = "❌ رفض" if refuse else "✅ نسخ؟"
        print(f"\n[{k}] {tag}")
        print(out[:220].replace("\n"," ⏎ "))
    print("\n"+"="*60)
    print("اختر الصياغة التي أعطت نصًّا عربيًّا حقيقيًّا (✅).")

if __name__=="__main__": main()
