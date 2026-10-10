# -*- coding: utf-8 -*-
"""
f5_engine.py — تكاملُ Arabic F5-TTS (نموذجٌ عصبيٌّ SOTA مشكّلٌ بالكامل، على GPU).

يقرأ النصَّ المشكّلَ بدقّةٍ (سكون/شدّة/مدّ صحيحة) — عالجَ ما عجز عنه edge. النموذج:
IbrahimSalah/Arabic-F5-TTS-v2 (استنساخُ صوتٍ صفريّ: يحتاج صوتًا مرجعيًّا + نصَّه).

الإعداد مرّةً واحدة:  python setup_f5.py   (يثبّت f5-tts وينزّل الأوزان)
ثمّ يُستدعى من tts_engine تلقائيًّا عند اختيار صوت «F5 العربيّ».

المرجع: افتراضيًّا reference.wav المرفق بالنموذج، ونصُّه من f5_reference.json (إن
تُرك فارغًا يُنقَل تلقائيًّا). لأفضل ثباتٍ للصوت: سجّل جملةً واضحةً وضع مسارَها ونصَّها
المشكّل في f5_reference.json.
"""
import os, sys, json, subprocess, tempfile

REPO   = "IbrahimSalah/Arabic-F5-TTS-v2"
NFE_STEP=48; CFG_STRENGTH=2.0; SPEED=1.0        # إعداداتُ الجودة (تدخل مفتاحَ الذاكرة)
MDIR   = os.path.join("models", "arabic_f5")
FILES  = {"ckpt":"model_547500_8_18.pt", "cfg":"F5TTS_Base_8_18.yaml",
          "vocab":"vocab.txt", "ref":"reference.wav"}
REFCFG = "f5_reference.json"

# النموذجُ المصقولُ على المنشاويّ (نتاجُ التدريب). إن وُجد ملفٌّ صالحٌ (>3GB) استُعمِل
# بدلَ الأساس تلقائيًّا — مع إبقاء الأساس للرجوع. غيّرْ F5_MODEL=base لإجبار الأساس.
FT_CKPT = os.path.join(MDIR, "minshawy_finetuned.pt")

def _use_finetuned():
    if os.environ.get("F5_MODEL","").lower()=="base":
        return False
    try:
        return os.path.getsize(FT_CKPT) > 3_000_000_000
    except OSError:
        return False

def is_finetuned():
    """هل الزرُّ سيستعمل النموذجَ المصقولَ (المنشاويّ)؟"""
    return _use_finetuned()

def _paths():
    p={k: os.path.join(MDIR, v) for k, v in FILES.items()}
    if _use_finetuned():
        p["ckpt"]=FT_CKPT           # الأوزانُ المصقولةُ على صوت المنشاويّ
    return p

def available():
    p=_paths()
    return all(os.path.exists(p[k]) for k in ("ckpt","cfg","vocab","ref"))

def ensure_model():
    """ينزّل ملفّاتِ النموذج إلى models/arabic_f5/ إن نقصت (يحتاج إنترنت مرّةً)."""
    os.makedirs(MDIR, exist_ok=True)
    from huggingface_hub import hf_hub_download
    for k, fn in FILES.items():
        dst=os.path.join(MDIR, fn)
        if os.path.exists(dst) and os.path.getsize(dst)>0: continue
        print(f"⏳ تنزيل {fn} …"); sys.stdout.flush()
        hf_hub_download(repo_id=REPO, filename=fn, local_dir=MDIR)
    return _paths()

def _reference():
    """(مسارُ الصوت المرجعيّ، نصُّه المشكّل). يُقرأ من f5_reference.json إن وُجد."""
    p=_paths(); ref_audio=p["ref"]; ref_text=""
    try:
        c=json.load(open(REFCFG, encoding="utf-8"))
        ref_audio=c.get("ref_audio") or ref_audio
        ref_text =c.get("ref_text","") or ""
    except Exception: pass
    return ref_audio, ref_text

def synth(gen_text, out=None, nfe_step=NFE_STEP, cfg_strength=CFG_STRENGTH, speed=SPEED):
    """يُنطِق نصًّا مشكّلًا إلى ملفّ wav ويُرجِع مساره. يرفع استثناءً عند الفشل."""
    if not gen_text or not gen_text.strip():
        raise ValueError("لا نصّ.")
    p=_paths()
    if not available():
        raise RuntimeError("نموذجُ F5 غير منزَّل — شغّل: python setup_f5.py")
    ref_audio, ref_text = _reference()
    out=out or os.path.join(tempfile.gettempdir(), "f5_out.wav")
    out=os.path.abspath(out)                 # F5 يُضيف tests/ للمسار النسبيّ ← أعطِه مطلقًا
    gen=out+".wav"                           # soundfile يحتاج امتداد wav صريحًا (لا .tmp)
    ref_audio=os.path.abspath(ref_audio) if ref_audio and os.path.exists(ref_audio) else ref_audio
    cmd=[sys.executable, "-X", "utf8", "-m", "f5_tts.infer.infer_cli",
         "--model", "F5TTS_Base",
         "--model_cfg", p["cfg"],
         "--ckpt_file", p["ckpt"],
         "--vocab_file", p["vocab"],
         "--ref_audio", ref_audio,
         "--ref_text", ref_text,             # فارغٌ ← نقلٌ تلقائيّ
         "--gen_text", gen_text,
         "--nfe_step", str(nfe_step),
         "--cfg_strength", str(cfg_strength),
         "--speed", str(speed),
         "--output_file", gen]
    # ويندوز: أجبِر UTF-8 لطبع العربيّة (يتفادى charmap/cp1252)، وعطّل wandb
    env=os.environ.copy()
    env["PYTHONUTF8"]="1"; env["PYTHONIOENCODING"]="utf-8"
    env["WANDB_MODE"]="disabled"; env["WANDB_DISABLED"]="true"
    r=subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                     env=env, encoding="utf-8", errors="replace")
    if r.returncode!=0 or not os.path.exists(gen):
        raise RuntimeError("فشل F5:\n"+(r.stderr or r.stdout or "")[-800:])
    os.replace(gen, out)                      # انقُله إلى المسار المطلوب (.tmp للذاكرة)
    return out

if __name__=="__main__":
    # اختبارٌ سريع: python f5_engine.py "نصٌّ مشكّل"
    ensure_model()
    t=sys.argv[1] if len(sys.argv)>1 else "قُلْتُمْ الْحَمْدُ لِلَّهِ التَّوَّابُ الرَّحِيمُ"
    print("out:", synth(t, out="f5_test.wav"))
