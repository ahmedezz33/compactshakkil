# -*- coding: utf-8 -*-
"""eval_ocr_qwen25.py — مقارنةٌ مُقاسة: Qari (الحاليّ) مقابل Qwen2.5-VL-3B، نفسُ الصفحاتِ ونفسُ CER.
بيئة: OCR_LIMIT (افتراضي 20؛ 0=61) · OCR_MAX_SIDE (1600) · QWEN_ID (Qwen/Qwen2.5-VL-3B-Instruct)."""
import os, sys
BASE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE,"scripts")); sys.path.insert(0, BASE)
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
ROOT="data/ocr_classical_pages_test"; MAN=os.path.join(ROOT,"manifest.tsv")
LIMIT=int(os.environ.get("OCR_LIMIT","20")); MAXSIDE=int(os.environ.get("OCR_MAX_SIDE","1600"))
def cer(ref,hyp):
    r,h=list(ref),list(hyp); n,m=len(r),len(h)
    if n==0: return 0.0 if m==0 else 1.0
    dp=list(range(m+1))
    for i in range(1,n+1):
        prev=dp[0]; dp[0]=i
        for j in range(1,m+1):
            cur=dp[j]; dp[j]=min(dp[j]+1,dp[j-1]+1,prev+(r[i-1]!=h[j-1])); prev=cur
    return dp[m]/n
rows=[]
for ln in open(MAN,encoding="utf-8"):
    p=ln.rstrip("\n").split("\t")
    if len(p)>=2: rows.append((os.path.join(ROOT,p[0]), p[1].strip()))
if LIMIT>0: rows=rows[:LIMIT]
print(f"صفحات: {len(rows)} · MAX_SIDE={MAXSIDE}")

def eval_qari():
    import ocr_engine as OE
    os.environ["OCR_PREPROCESS"]="0"; OE.MAX_SIDE=MAXSIDE
    tot=0.0;n=0
    for path,gold in rows:
        try: out=OE.ocr_image(path).strip()
        except Exception as e: print("  Qari خطأ:",os.path.basename(path),repr(e)[:50]); continue
        tot+=cer(gold,out); n+=1
    # تحريرُ الذاكرة قبلَ Qwen
    try:
        import torch
        for a in ("_MODEL","_MODEL_OCR","MODEL"): 
            if hasattr(OE,a): setattr(OE,a,None)
        torch.cuda.empty_cache()
    except Exception: pass
    return 100*tot/max(1,n)

def eval_qwen():
    import torch
    from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
    from qwen_vl_utils import process_vision_info
    from PIL import Image
    mid=os.environ.get("QWEN_ID","Qwen/Qwen2.5-VL-3B-Instruct")
    print("تحميل:", mid)
    bnb=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
    proc=AutoProcessor.from_pretrained(mid)
    model=Qwen2_5_VLForConditionalGeneration.from_pretrained(mid, quantization_config=bnb,
            torch_dtype=torch.float16, device_map="auto"); model.eval()
    PROMPT=os.environ.get("QWEN_PROMPT","انسخِ النصَّ العربيَّ في الصورةِ حرفيًّا بالكامل مع كلِّ الحركات (التشكيل)، دونَ أيِّ شرحٍ أو إضافة.")
    def one(path):
        im=Image.open(path).convert("RGB"); w,h=im.size; m=max(w,h)
        if m>MAXSIDE: r=MAXSIDE/float(m); im=im.resize((max(1,int(w*r)),max(1,int(h*r))))
        msgs=[{"role":"user","content":[{"type":"image","image":im},{"type":"text","text":PROMPT}]}]
        chat=proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ii,vi=process_vision_info(msgs)
        inp=proc(text=[chat], images=ii, videos=vi, padding=True, return_tensors="pt").to(model.device)
        with torch.no_grad():
            g=model.generate(**inp, max_new_tokens=2048, do_sample=False,
                             repetition_penalty=1.3, no_repeat_ngram_size=3)
        gen=g[:, inp.input_ids.shape[1]:]
        return proc.batch_decode(gen, skip_special_tokens=True)[0].strip()
    tot=0.0;n=0
    for path,gold in rows:
        try: out=one(path)
        except Exception as e: print("  Qwen خطأ:",os.path.basename(path),repr(e)[:60]); continue
        tot+=cer(gold,out); n+=1
    return 100*tot/max(1,n)

print("="*54)
q=eval_qari(); print(f"[Qari v... الحاليّ]      CER={q:.2f}%")
w=eval_qwen(); print(f"[Qwen2.5-VL-3B]        CER={w:.2f}%")
print("="*54)
print(f"الأفضل: {'Qari' if q<w else 'Qwen2.5-VL-3B'}  (الفرق {abs(q-w):.2f} نقطة)")
print("الأقلُّ CER أفضل.")
