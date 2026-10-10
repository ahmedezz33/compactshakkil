# -*- coding: utf-8 -*-
"""compare_ocr.py — يقارن نموذجين على نفس الصفحة بالأمر الجديد نفسِه."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ocr_engine as OE

MODELS=[
  ("Qwen2.5-VL-3B (عامّ)",       "Qwen/Qwen2.5-VL-3B-Instruct"),
  ("Qari-OCR-2B (متخصّص عربي)",  "NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct"),
]

def ocr_with(model_id, img_path):
    try: OE.unload()
    except Exception: pass
    OE.MODEL_ID=model_id; OE._MODEL=None; OE._PROC=None
    return OE.ocr_image(img_path)

def main():
    img = sys.argv[1] if len(sys.argv)>1 else "_inspect/page_26.png"
    if not os.path.exists(img): print("لا صورة:", img); return
    print("صفحة:", img, "| الأمر المستعمَل:\n ", OE.PROMPT[:90], "...\n")
    for name,mid in MODELS:
        print("="*62); print("#", name, "|", mid)
        try:
            out=ocr_with(mid, img)
            print(out[:700] if out else "(فارغ)")
        except Exception as e:
            print("خطأ:", repr(e))
    print("="*62)
    print("قارنْ: أيُّهما أدقُّ حروفًا وأصحُّ حركاتٍ؟")

if __name__=="__main__": main()
