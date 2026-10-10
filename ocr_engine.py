# -*- coding: utf-8 -*-
"""
ocr_engine.py — OCR عربيٌّ محلّيٌّ عالي الدقّة (QARI-OCR / Qwen2-VL 2B).
يلتقطُ النصَّ **بالحركات الكاملة** (لا الحروفَ فقط) — مناسبٌ للمصحف والمطبوع،
ولجمع بياناتٍ لتحسين نموذج التشكيل لاحقًا. تحميلٌ كسولٌ لمرّةٍ واحدة.
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_MODEL=None; _PROC=None
MODEL_ID=os.environ.get("OCR_MODEL","NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct")
PROMPT_EN=("Transcribe all the Arabic text in this image exactly as written, "
    "preserving every diacritic (tashkeel) on every letter, line by line. "
    "Output only the Arabic text itself — no translation, no explanation, "
    "no introduction, and do not refuse.")
PROMPT_AR="انسخ النص العربي في الصورة كما هو بكل الحركات، سطرًا بسطر."
PROMPT=os.environ.get("OCR_PROMPT", PROMPT_EN)   # توافقٌ للأدوات التي تقرأ PROMPT
MAX_SIDE=int(os.environ.get("OCR_MAX_SIDE","2600"))

_TAG=re.compile(r"</?[A-Za-z][^>]*>")
def _strip_markup(t):
    """يزيلُ وسومَ HTML/Markdown ويُبقي النصَّ العربيَّ وحركاتِه فقط."""
    if not t: return ""
    t=_TAG.sub(" ", t)
    out=[]
    for ln in t.splitlines():
        ss=ln.strip()
        if not ss: continue
        if re.fullmatch(r"[|\-:_=~ـ—–\.\s]{3,}", ss): continue   # خطوطُ الفصل وفواصلُ الجداول
        if re.fullmatch(r"[\u0660-\u0669\d]{1,4}", ss): continue   # رقمُ صفحةٍ مفرد
        ss=ss.replace("|"," ").replace("`"," ").replace("*"," ")
        ss=re.sub(r"[ \t]{2,}"," ",ss).strip()
        if ss: out.append(ss)
    return "\n".join(out).strip()



STRUCT_PROMPT=("Transcribe the Arabic text of this page exactly, preserving all "
    "diacritics (tashkeel), split into three sections using these exact markers:\n"
    "=العنوان=\n(the top header / running head, if any)\n"
    "=المتن=\n(the main body text, line by line, as written)\n"
    "=الحواشي=\n(the footnotes after the separator line, if any)\n"
    "If a section is absent, leave it empty after its marker. Output only the text; "
    "do not add, translate, explain, or refuse.")
STRUCT_PROMPT_EN=STRUCT_PROMPT
STRUCT_PROMPT_AR=("انسخ محتوى الصفحة العربيّ بكل الحركات والتشكيل، مقسّمًا إلى ثلاثة أقسامٍ "
    "بهذه العلامات حرفيًا:\n=العنوان=\n(الترويسة/رأس الصفحة العلويّ إن وُجد)\n"
    "=المتن=\n(النصّ الأساسيّ، سطرًا بسطر كما هو)\n"
    "=الحواشي=\n(الحواشي السفليّة بعد خطّ الفصل إن وُجدت)\n"
    "إن غاب قسمٌ اترك ما بعد علامته فارغًا. لا تُضِف شيئًا من عندك.")

def _pick_prompt(structured=False):
    """يختارُ الأمرَ حسبَ النموذج: Qari/Qwen2-VL ← عربيّ مجرَّب؛ وإلّا ← إنجليزيّ حازم.
    تجاوزُ OCR_PROMPT إن ضُبِط يغلبُ على الكلّ (لغير المهيكَل)."""
    env=os.environ.get("OCR_PROMPT")
    mid=(MODEL_ID or "").lower()
    is_qari = ("qari" in mid) or ("qwen2-vl" in mid) or ("qwen2vl" in mid)
    if structured:
        return STRUCT_PROMPT_AR if is_qari else STRUCT_PROMPT_EN
    if env: return env
    return PROMPT_AR if is_qari else PROMPT_EN

_SEC_RE=__import__("re").compile(r"=\s*(العنوان|المتن|الحواشي)\s*=")
import re as _re2
_PAGE_NUM=_re2.compile(r"^[\s\-—._:]*[\u0660-\u06690-9]{1,4}[\s\-—._:]*$")
_ORNAMENT=_re2.compile(r"^[\s\W_]+$")                 # زخارف/رموزٌ بلا حروف
_FOOT_START=_re2.compile(r"^\s*[\(\[]?\s*[\u0660-\u06690-9]{1,3}\s*[\)\]]")   # (١) أو [1]
def _is_noise(ss):
    """سطرٌ لا يُقرَأ: رقمُ صفحةٍ مفرد، أو زخرفةٌ خالصة."""
    if not ss: return True
    if _PAGE_NUM.match(ss): return True
    if _ORNAMENT.match(ss) and not _re2.search(r"[\u0621-\u064a]", ss): return True
    return False
def _looks_header(ss):
    """ترويسةٌ علويّة: قصيرةٌ وتحوي كتاب/باب/فصل، أو جزآن عنوانيّان."""
    w=ss.split()
    if len(w)>8: return False
    return bool(_re2.search(r"\b(كتاب|باب|فصل|مبحث|الجزء|المجلد)\b", ss))

def split_sections(text):
    """يقسّمُ ناتجَ OCR المهيكَل إلى {'العنوان','المتن','الحواشي'}."""
    if not text: return {"العنوان":"","المتن":"","الحواشي":""}
    parts={"العنوان":"","المتن":"","الحواشي":""}
    cur=None; buf=[]
    import re as _re
    for ln in text.split("\n"):
        m=_re.match(r"\s*=\s*(العنوان|المتن|الحواشي)\s*=\s*$", ln)
        if m:
            if cur is not None: parts[cur]="\n".join(buf).strip()
            cur=m.group(1); buf=[]
        else:
            buf.append(ln)
    if cur is not None: parts[cur]="\n".join(buf).strip()
    if any(parts.values()):                  # النموذجُ التزمَ بالعلامات
        return _denoise_parts(parts)
    return _heuristic_sections(text)         # وإلّا: كشفٌ حرّاريّ

def _denoise_parts(parts):
    for k in parts:
        parts[k]="\n".join(l for l in parts[k].split("\n") if not _is_noise(l.strip())).strip()
    return parts

def _heuristic_sections(text):
    """بلا علاماتٍ من النموذج: افصلْ ترويسةً علويّةً وحواشيَ سفليّةً وأزِلِ الضجيج."""
    lines=[l for l in text.split("\n") if not _is_noise(l.strip())]
    parts={"العنوان":"","المتن":"","الحواشي":""}
    if not lines: return parts
    body=lines[:]
    # ترويسة: أوّلُ سطرٍ إن بدا ترويسةً
    if body and _looks_header(body[0].strip()):
        parts["العنوان"]=body.pop(0).strip()
    # حواشٍ: كتلةٌ متتاليةٌ في الآخِرِ تبدأُ بـ (رقم)
    foot=[]
    while body and _FOOT_START.match(body[-1].strip()):
        foot.insert(0, body.pop().strip())
    # اجمعْ أيَّ أسطرِ حاشيةٍ إضافيّةٍ فوقَها مباشرةً (تكملةُ الحاشية)
    parts["الحواشي"]="\n".join(foot).strip()
    parts["المتن"]="\n".join(body).strip()
    return parts

def matn_of(text):
    """يرجعُ المتنَ فقط (للقراءة) — بلا عنوانٍ ولا حواشٍ."""
    p=split_sections(text)
    return p["المتن"] or text


# ─── عرضٌ مُعَنوَنٌ + استخراجُ المتن للقراءة ───────────────────────────────
_LBL={"العنوان":"▓▓▓ العنوان (رأس الصفحة) ▓▓▓",
      "المتن":"▓▓▓ المتن ▓▓▓",
      "الحواشي":"▓▓▓ الحواشي (الهوامش) ▓▓▓"}
def format_sections(text):
    """يحوّلُ ناتجَ OCR المهيكَل إلى نصٍّ مُعَنوَنٍ للعرض (يحذفُ الأقسامَ الفارغة)."""
    p=split_sections(text)
    if not any(p[k] for k in ("العنوان","الحواشي")):   # لا عنوانَ ولا حواشٍ ← نصٌّ عاديّ
        return p["المتن"] or (text or "")
    out=[]
    for k in ("العنوان","المتن","الحواشي"):
        if p.get(k,"").strip():
            out.append(_LBL[k]); out.append(p[k].strip()); out.append("")
    return "\n".join(out).strip()

def matn_for_reading(text):
    """يُرجِعُ المتنَ فقط من نصٍّ مُعَنوَنٍ للعرض (للقراءةِ الصوتيّة) — بلا عنوانٍ ولا حواشٍ."""
    if not text: return text
    import re as _re
    if "▓▓▓ المتن ▓▓▓" in text:                       # الصيغةُ المعروضة
        seg=text.split("▓▓▓ المتن ▓▓▓",1)[1]
        seg=_re.split(r"▓▓▓ .+? ▓▓▓", seg)[0]
        return seg.strip() or text
    if _re.search(r"=\s*المتن\s*=", text):             # الصيغةُ الخام
        return matn_of(text)
    return text

def available():
    try:
        import torch, transformers, qwen_vl_utils  # noqa: F401
        return True
    except Exception:
        return False

def _load():
    global _MODEL,_PROC
    if _MODEL is not None: return
    import os as _os, torch, transformers as _tf
    from transformers import AutoProcessor
    _PROC=AutoProcessor.from_pretrained(MODEL_ID)
    # اختَرْ فئةَ النموذجِ الصحيحةَ (Qwen2.5-VL ← Qwen2-VL ← عامّ)
    # اختَرِ الفئةَ حسبَ نوعِ النموذجِ في إعداداتِه (لا "أوّل متاح")،
    # وإلّا صادمَ Qari (qwen2_vl) فئةَ Qwen2.5-VL ← size mismatch.
    mtype=""
    try:
        from transformers import AutoConfig
        mtype=getattr(AutoConfig.from_pretrained(MODEL_ID), "model_type", "")
    except Exception as _e:
        print("تعذّر قراءةُ الإعدادات:", _e)
    _M=None
    if mtype=="qwen2_5_vl" and hasattr(_tf,"Qwen2_5_VLForConditionalGeneration"):
        _M=_tf.Qwen2_5_VLForConditionalGeneration
    elif mtype=="qwen2_vl" and hasattr(_tf,"Qwen2VLForConditionalGeneration"):
        _M=_tf.Qwen2VLForConditionalGeneration
    if _M is None:                               # عامّ: دعِ Auto يختار من الإعدادات
        for nm in ("AutoModelForImageTextToText","Qwen2_5_VLForConditionalGeneration","Qwen2VLForConditionalGeneration"):
            if hasattr(_tf, nm): _M=getattr(_tf, nm); break
    if _M is None:
        from transformers import AutoModelForCausalLM as _M
    print("فئة النموذج:", getattr(_M,"__name__",_M), "| model_type:", mtype or "?")
    use_gpu = torch.cuda.is_available()
    # إعدادٌ ذكيٌّ حسب الحجم: الكبيرُ (7B+) ← تفريغ+4bit؛ الصغيرُ ← GPU/fp16.
    # يُتجاوَزُ يدويًّا بـ OCR_DEVICE (gpu|offload|cpu) وOCR_4BIT (0|1).
    _big = any(t in (MODEL_ID or "").lower() for t in ("7b","8b","13b","32b","72b"))
    _dev_env = _os.environ.get("OCR_DEVICE")
    mode = (_dev_env.lower() if _dev_env else ("offload" if _big else "gpu"))
    if not use_gpu: mode="cpu"
    if mode=="cpu":
        dmap="cpu"
    elif mode=="offload":
        dmap="auto"          # هجين: GPU ما يسعُه + المعالج للفائض
    else:
        dmap={"": 0}         # GPU فقط
    kw=dict(device_map=dmap)
    _q_env = _os.environ.get("OCR_4BIT")
    want4 = ((_q_env=="1") if _q_env is not None else _big) and mode!="cpu"
    if want4:                                              # تكميمٌ 4-bit (GPU/هجين)
        try:
            from transformers import BitsAndBytesConfig
            kw["quantization_config"]=BitsAndBytesConfig(load_in_4bit=True,
                bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16,
                llm_int8_enable_fp32_cpu_offload=(mode=="offload"))
        except Exception as _e: print("4bit غير متاح:", _e); kw["torch_dtype"]="auto"
    else:
        kw["torch_dtype"]= (torch.float32 if mode=="cpu" else torch.float16)
    print(f"تحميل OCR: {MODEL_ID} | وضع={mode} | 4bit={want4}")
    _MODEL=_M.from_pretrained(MODEL_ID, **kw).eval()
    # محوّلات LoRA اختياريّة (OCR_LORA=1 → outputs_ocr_lora، أو مسارٌ صريح). افتراضيًّا مطفأة.
    _lora=_os.environ.get("OCR_LORA","")
    if _lora:
        ldir = "outputs_ocr_lora" if _lora=="1" else _lora
        if _os.path.exists(_os.path.join(ldir,"adapter_config.json")):
            try:
                from peft import PeftModel
                _MODEL=PeftModel.from_pretrained(_MODEL, ldir); _MODEL.eval()
                print("LoRA محمّل:", ldir)
            except Exception as _e:
                print("تعذّر تحميل LoRA:", _e)
        else:
            print("لا محوّلات في:", ldir)
    try:
        dev0=next(_MODEL.parameters()).device; print("النموذج حُمِّل على:", dev0)
    except Exception: pass

def _preprocess(im):
    """تحسينٌ مسبقٌ للصورة يرفعُ دقّةَ تعرّفِ الحركاتِ الصغيرة:
    تدرّجٌ رماديّ + تباينٌ تلقائيّ + حِدّةٌ خفيفة، وتقويمُ ميلٍ إن توفّر cv2.
    آمنٌ: أيُّ فشلٍ يُعيدُ الصورةَ كما هي. يُعطَّلُ بـ OCR_PREPROCESS=0."""
    if os.environ.get("OCR_PREPROCESS","1")!="1":
        return im
    try:
        from PIL import ImageOps, ImageFilter
        g=ImageOps.grayscale(im)
        g=ImageOps.autocontrast(g, cutoff=1)       # يمدّ المدى فتبرزُ الحركات
        # تقويمُ الميل (اختياريّ، يحتاج cv2+numpy)
        try:
            import numpy as _np, cv2 as _cv2
            a=_np.array(g)
            inv=255-a
            _,bw=_cv2.threshold(inv,0,255,_cv2.THRESH_BINARY+_cv2.THRESH_OTSU)
            ys,xs=_np.where(bw>0)
            if len(xs)>50:
                ang=_cv2.minAreaRect(_np.column_stack((xs,ys)))[-1]
                if ang<-45: ang=90+ang
                if abs(ang)>0.5 and abs(ang)<15:       # نُقوّمُ ميلًا بسيطًا فقط
                    h,w=a.shape
                    M=_cv2.getRotationMatrix2D((w/2,h/2),ang,1.0)
                    a=_cv2.warpAffine(a,M,(w,h),flags=_cv2.INTER_CUBIC,
                                      borderMode=_cv2.BORDER_REPLICATE)
                    from PIL import Image as _I; g=_I.fromarray(a)
        except Exception:
            pass
        g=g.filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=2))
        return g.convert("RGB")
    except Exception:
        return im


def _prep(path):
    from PIL import Image
    im=Image.open(path).convert("RGB")
    w,h=im.size; m=max(w,h)
    if m>MAX_SIDE:
        r=MAX_SIDE/float(m); im=im.resize((max(1,int(w*r)),max(1,int(h*r))))
    return _preprocess(im)


def _drop_prompt(t):
    """يحذفُ أيَّ تسرّبٍ لنصّ التوجيه من مخرجات النموذج."""
    if not t: return t
    import unicodedata
    def norm(x): return "".join(c for c in x if not unicodedata.combining(c))
    bad=("انسخ النص العربي","استخرج النص العربي","بكل الحركات","سطرا بسطر",
         "لا تخرج","وسوم","الكلمات العربية فقط","Markdown","HTML","تعليق او ترجمة",
         "النص المكتوب في الصورة","النص العربي الظاهر في الصورة","النص في الصورة هو",
         "هو:","The text in the image","Here is the","transcription of")
    out=[]
    for ln in t.split("\n"):
        n=norm(ln)
        if any(b in n or b in ln for b in bad) and len(ln)<160:
            continue
        out.append(ln)
    return "\n".join(out).strip()

def _ocr_pil(img, structured=False):
    """OCR على صورة PIL جاهزة ← نصّ. يحقن الصورة عبر المسار الموحّد
    (apply_chat_template بالترميز) المتوافق مع transformers 4.4x و5.x؛
    إن تعذّر يسقط للمسار اليدويّ؛ ثمّ يتحقّق أنّ بكسلات الصورة وصلت قبل
    التوليد، فلا يعتذر النموذجُ صامتًا حين لا يرى الصورة."""
    import torch
    _load()
    prompt=_pick_prompt(structured)
    messages=[{"role":"user","content":[
        {"type":"image","image":img},
        {"type":"text","text":prompt}]}]

    def _has_pixels(x):
        try:
            return x is not None and ("pixel_values" in x) and (x["pixel_values"] is not None)
        except Exception:
            return False

    inputs=None
    # (1) المسار الموحّد الموصى به في transformers الحديثة: يجلب الصورة من الرسائل نفسها
    try:
        inputs=_PROC.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt")
    except Exception:
        inputs=None
    # (2) المسار اليدويّ القديم إن لم يحقنِ الأوّلُ بكسلات الصورة
    if not _has_pixels(inputs):
        from qwen_vl_utils import process_vision_info
        chat=_PROC.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        vi=process_vision_info(messages)          # قد تُرجِع قيمتين أو ثلاثًا حسب النسخة
        image_inputs, video_inputs = vi[0], vi[1]
        inputs=_PROC(text=[chat], images=image_inputs, videos=video_inputs,
                     padding=True, return_tensors="pt")
    # (3) تحقّقٌ صارم: الصورةُ يجب أن تكون قد دخلت
    if not _has_pixels(inputs):
        raise RuntimeError("الصورةُ لم تصلْ إلى النموذج (pixel_values مفقودة) — "
                           "تعارضُ نسخةِ transformers/qwen_vl_utils مع المعالج. "
                           "ثبّتْ نسخةً متوافقة (مثلًا transformers>=4.49).")
    try:
        inputs=inputs.to(_MODEL.device)
    except Exception:
        pass
    # كوابحُ ضدَّ حلقةِ التكرار الجامحة (كما في التقييم: خفّضت CER من 121% إلى 15%)
    _eos=[_PROC.tokenizer.eos_token_id] if getattr(_PROC,"tokenizer",None) and _PROC.tokenizer.eos_token_id is not None else None
    try:
        _im_end=_PROC.tokenizer.convert_tokens_to_ids("<|im_end|>")
        if _im_end is not None and _im_end>=0:
            _eos=(_eos or [])+[_im_end]
    except Exception:
        pass
    _genkw=dict(
        max_new_tokens=int(os.environ.get("OCR_MAX_TOKENS","8192")),
        do_sample=False,
        repetition_penalty=float(os.environ.get("OCR_REP_PENALTY","1.3")),
        no_repeat_ngram_size=int(os.environ.get("OCR_NO_REPEAT","3")),
    )
    if _eos: _genkw["eos_token_id"]=_eos
    with torch.inference_mode():
        gen=_MODEL.generate(**inputs, **_genkw)
    trimmed=[o[len(i):] for i,o in zip(inputs.input_ids, gen)]
    out=_PROC.batch_decode(trimmed, skip_special_tokens=True,
                           clean_up_tokenization_spaces=False)[0]
    return _strip_markup(_drop_prompt(out))

def ocr_image(path, structured=False):
    """يرجع النصَّ المستخرَجَ (بالحركات) أو رسالةً تبدأ بـ⚠️ عند التعذّر."""
    if not path or not os.path.exists(path): return "⚠️ لا صورة."
    if not available():
        return "⚠️ OCR غير مُعَدّ بعد. شغّل run_setup_ocr.bat مرّةً واحدة."
    try:
        return _ocr_pil(_prep(path), structured=structured) or "⚠️ لم يُستخرَج نصّ."
    except Exception as e:
        return f"⚠️ تعذّر الـ OCR: {e}"



def _harakat_ratio(t):
    """نسبةُ الحركات إلى الحروف العربيّة (لكشف: أمشكَّلٌ النصّ أم حروفٌ فقط)."""
    if not t: return 0.0
    letters=sum(1 for c in t if "\u0621"<=c<="\u064a")
    marks=sum(1 for c in t if "\u064b"<=c<="\u0652" or c=="\u0670")
    return (marks/letters) if letters else 0.0

def _fix_bidi(txt):
    """يصحّحُ ترتيبَ نصّ PDF العربيّ (كثيرًا ما يُستخرَج بترتيبٍ بصريٍّ معكوس)."""
    try:
        from bidi.algorithm import get_display
    except Exception:
        return txt
    out=[]
    for ln in txt.split("\n"):
        try: out.append(get_display(ln))
        except Exception: out.append(ln)
    return "\n".join(out)

def _ar_count(t):
    return sum(1 for c in (t or "") if "\u0600"<=c<="\u06ff")

def _parse_pages(spec, n):
    """'1-3,5' → [0,1,2,4] (0-based، محصور بعدد الصفحات). فارغ=الكل."""
    if not spec or not str(spec).strip(): return list(range(n))
    out=[]
    for part in str(spec).replace("،",",").split(","):
        part=part.strip()
        if not part: continue
        if "-" in part:
            a,b=part.split("-",1)
            try: a=int(a); b=int(b)
            except: continue
            for i in range(a,b+1):
                if 1<=i<=n: out.append(i-1)
        else:
            try:
                i=int(part)
                if 1<=i<=n: out.append(i-1)
            except: pass
    seen=set(); res=[]
    for i in out:
        if i not in seen: seen.add(i); res.append(i)
    return res or list(range(n))

def ocr_pdf(path, pages=None, dpi=int(os.environ.get("OCR_DPI","300")), min_text_chars=40, progress=None, use_ocr=True, structured=False):
    """يستخرجُ نصَّ PDF بالحركات. الافتراضيّ use_ocr=True: يحوّلُ كلَّ صفحةٍ صورةً
    ويمرّرُها على الـ OCR (QARI) — ترتيبٌ عربيٌّ صحيحٌ + حركات. (طبقةُ نصّ PDF
    الرقميّة تُخرِجُ العربيَّ معكوسًا، لذا نتجاهلُها افتراضيًّا.)"""
    if not path or not os.path.exists(path): return "⚠️ لا ملفّ."
    try:
        import pypdfium2 as pdfium
    except Exception as e:
        return f"⚠️ لا مكتبةَ PDF متاحة: {e}"
    try:
        from PIL import Image
        pdf=pdfium.PdfDocument(path)
        npages=len(pdf)
        idxs=_parse_pages(pages, npages)
        chunks=[]
        for k,pi in enumerate(idxs,1):
            if progress: progress(k,len(idxs))
            page=pdf[pi]
            if not use_ocr:
                try:
                    tp=page.get_textpage(); txt=(tp.get_text_range() or "").strip()
                except Exception: txt=""
                # الطبقةُ السريعةُ تُقبَل فقط إن كانت مشكَّلةً (حركات موجودة)؛ وإلّا OCR
                if _ar_count(txt)>=min_text_chars and _harakat_ratio(txt)>=0.15:
                    chunks.append(_strip_markup(_fix_bidi(txt))); continue   # سريع + حركات + إصلاح العكس
                # نصٌّ بلا حركات ← نكملُ إلى OCR (يلتقط الحركات)
            if not available():
                return "⚠️ OCR غير مُعَدّ. شغّل run_setup_ocr.bat مرّةً."
            bmp=page.render(scale=dpi/72.0)
            img=bmp.to_pil().convert("RGB")
            w,h=img.size; mx=max(w,h)
            if mx>MAX_SIDE:
                r=MAX_SIDE/float(mx); img=img.resize((int(w*r),int(h*r)))
            img=_preprocess(img)
            chunks.append(_ocr_pil(img, structured=structured))
        res="\n\n".join(c for c in chunks if c).strip()
        return res or "⚠️ لم يُستخرَج نصّ."
    except Exception as e:
        return f"⚠️ تعذّر قراءةُ PDF: {e}"

def ocr_any(path, pages=None, fast=False, structured=False):
    """يوجّهُ حسب الامتداد: PDF ← ocr_pdf (fast=طبقةُ النصّ السريعة)، وإلّا ocr_image."""
    if not path: return "⚠️ لا ملفّ."
    if str(path).lower().endswith(".pdf"):
        return ocr_pdf(path, pages=pages, use_ocr=not fast, structured=structured)
    return ocr_image(path, structured=structured)

def unload():
    global _MODEL,_PROC
    _MODEL=None; _PROC=None
    try:
        import gc, torch; gc.collect(); torch.cuda.empty_cache()
    except Exception: pass
