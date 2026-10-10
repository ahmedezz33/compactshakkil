# -*- coding: utf-8 -*-
"""diag_ocr.py — يشخّص لماذا يعتذر OCR بدل القراءة.
يفحص وصول بكسلات الصورة بالمعالج وحده (سريع) ثم يحمّل النموذج."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ocr_engine as OE

def has_pix(x):
    try: return x is not None and ("pixel_values" in x) and x["pixel_values"] is not None
    except Exception: return False

def main():
    img_path = sys.argv[1] if len(sys.argv)>1 else ""
    import transformers, torch
    try: import qwen_vl_utils; qv=getattr(qwen_vl_utils,"__version__","?")
    except Exception as e: qv="غير مثبّت: %r"%e
    print("="*50)
    print("transformers :", transformers.__version__)
    print("qwen_vl_utils:", qv)
    print("torch cuda   :", torch.cuda.is_available())
    print("OCR_MODEL    :", OE.MODEL_ID)
    print("OCR_DEVICE   :", os.environ.get("OCR_DEVICE","gpu"), "| OCR_4BIT:", os.environ.get("OCR_4BIT","0"))
    if not img_path or not os.path.exists(img_path):
        print("\n[!] لا صورة. مرّر مسارًا أو ضع _inspect/page_26.png"); return
    print("صورة:", img_path)

    # (A) فحص البكسلات بالمعالج فقط — سريع، لا يحمّل النموذج
    from transformers import AutoProcessor
    proc=AutoProcessor.from_pretrained(OE.MODEL_ID)
    img=OE._prep(img_path)
    msgs=[{"role":"user","content":[{"type":"image","image":img},
          {"type":"text","text":OE.PROMPT}]}]
    print("\n--- فحص حقن الصورة (بالمعالج وحده) ---")
    try:
        u=proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True,
                                   return_dict=True, return_tensors="pt")
        print("  المسار الموحّد  pixel_values؟", has_pix(u))
    except Exception as e:
        print("  المسار الموحّد فشل:", repr(e))
    try:
        from qwen_vl_utils import process_vision_info
        chat=proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        vi=process_vision_info(msgs); ii,vv=vi[0],vi[1]
        m=proc(text=[chat], images=ii, videos=vv, padding=True, return_tensors="pt")
        print("  المسار اليدويّ  pixel_values؟", has_pix(m), "| عدد الصور:", 0 if ii is None else len(ii))
    except Exception as e:
        print("  المسار اليدويّ فشل:", repr(e))

    # (B) تشغيل فعليّ عبر الدالة المصحَّحة (يحمّل النموذج)
    print("\n--- تحميل النموذج وتشغيل _ocr_pil (قد يأخذ دقائق) ---")
    try:
        out=OE._ocr_pil(img)
        print("model class:", type(OE._MODEL).__name__)
        print("=== الناتج (أول 500 حرف) ===")
        print(out[:500] if out else "(فارغ)")
    except Exception as e:
        print("خطأ في التشغيل:", repr(e))

if __name__=="__main__": main()
