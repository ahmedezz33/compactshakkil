# -*- coding: utf-8 -*-
"""
finetune_f5.py — يجهّز بياناتِ F5 ثمّ يبدأ الصقلَ من النموذج العربيّ (إعداداتُ ٨غ.ب).

يضع البياناتِ حيث يتوقّعها F5 (data/<name>_custom بجوار حزمة f5_tts)، ويُحاذي
المفرداتِ مع النموذج العربيّ، ثمّ يشغّل finetune_cli. قابلٌ للاستئناف (يتخطّى ما أُنجِز).
    python finetune_f5.py
"""
import os, sys, shutil, subprocess

META      = os.path.abspath(os.path.join("train_data","minshawy","metadata.csv"))
AR_CKPT   = os.path.abspath(os.path.join("models","arabic_f5","model_547500_8_18.pt"))
AR_VOCAB  = os.path.abspath(os.path.join("models","arabic_f5","vocab.txt"))
DATASET   = "minshawy"
TOKENIZER = "custom"

def data_root():
    # موقعُ حزمة f5_tts الحقيقيّ (نفسُ ما يحسبه F5 لمجلّد data بعد إضافة __init__.py)
    import importlib.util
    spec = importlib.util.find_spec("f5_tts")
    locs = list(spec.submodule_search_locations or [])
    base = locs[0] if locs else os.path.dirname(spec.origin or "")
    return os.path.abspath(os.path.join(base, "..", "..", "data"))

def main():
    for p in (META, AR_CKPT, AR_VOCAB):
        if not os.path.exists(p):
            print("❌ ناقص:", p, "\nشغّل build_train_dataset.py و setup_f5.py أوّلًا."); return
    out = os.path.join(data_root(), f"{DATASET}_{TOKENIZER}")
    os.makedirs(out, exist_ok=True)
    print("📁 مجلّد بيانات F5:", out)

    # (١) تجهيز البيانات (إن لم يُنجَز)
    if not os.path.exists(os.path.join(out, "raw.arrow")):
        print("① تجهيز البيانات (prepare_csv_wavs) …"); sys.stdout.flush()
        r = subprocess.run([sys.executable, "-X", "utf8", "-m",
                            "f5_tts.train.datasets.prepare_csv_wavs", META, out])
        if r.returncode != 0 or not os.path.exists(os.path.join(out, "raw.arrow")):
            print("❌ فشل تجهيزُ البيانات."); return
    else:
        print("① البيانات مُجهّزةٌ سلفًا (raw.arrow موجود).")

    # (٢) محاذاة المفردات مع النموذج العربيّ (شرطُ صحّةِ التضمينات)
    shutil.copy(AR_VOCAB, os.path.join(out, "vocab.txt"))
    print("② نُسِخت مفرداتُ النموذج العربيّ.")

    # (٢-ب) تجريدُ النقطة: أوزانٌ فقط والعدّاد=٠، لئلّا يظنَّ التدريبَ مكتملًا (٥٤٧٥٠٠)
    pretrain = os.path.join(os.path.dirname(AR_CKPT), "arabic_f5_finetune_init.pt")
    if not os.path.exists(pretrain):
        print("②-ب تجريدُ نقطةِ البداية (عدّاد=٠) …"); sys.stdout.flush()
        import torch
        ck = torch.load(AR_CKPT, map_location="cpu", weights_only=False)
        if isinstance(ck, dict):
            # احذف حالةَ المُحسِّن وعدّاداتِ التقدّم تمامًا: فيعامله F5 كنموذجٍ مُسبَقٍ نقيّ
            # (المسارُ else في load_checkpoint) ويبدأ من update=0 بلا طلبِ optimizer_state_dict
            for k in ("optimizer_state_dict","scheduler_state_dict","scaler_state_dict",
                      "optimizer","scheduler","update","step","global_step","last_update","start_step"):
                ck.pop(k, None)
            # أبقِ ema_model_state_dict (يبني منه F5 الأوزانَ في مسار النموذج المُسبَق)
            if "ema_model_state_dict" not in ck and "model_state_dict" in ck:
                ck["ema_model_state_dict"] = {("ema_model."+k2): v for k2, v in ck["model_state_dict"].items()}
        torch.save(ck, pretrain)
    print("   نقطةُ البداية:", pretrain)

    # (٣) الصقل — إعداداتٌ موفّرةٌ للذاكرة (٨غ.ب)
    bnb = []
    try:
        import bitsandbytes  # noqa
        bnb = ["--bnb_optimizer"]; print("③ 8-bit Adam مُفعّل (موفّرُ ذاكرة).")
    except Exception:
        print("③ ⚠️ bitsandbytes غير متاح — بلا 8-bit Adam (خطرُ نفادِ الذاكرة أعلى).")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"; env["PYTHONIOENCODING"] = "utf-8"
    env["WANDB_DISABLED"] = "true"; env["WANDB_MODE"] = "disabled"

    # يُصلِح نفسَه: عند فشلٍ مبكّرٍ (OOM غالبًا) يُعيد بحجمٍ أصغرَ تلقائيًّا.
    # التدريبُ يستأنف من آخِر نقطة حفظٍ في كلّ محاولة، فلا يضيع تقدّم.
    CANDIDATES = [(1000, 8), (640, 6), (384, 4), (256, 2), (160, 1)]
    for i, (bs, ms) in enumerate(CANDIDATES, 1):
        cmd = [sys.executable, "-X", "utf8", "-m", "f5_tts.train.finetune_cli",
               "--exp_name", "F5TTS_Base", "--finetune",
               "--pretrain", pretrain,
               "--dataset_name", DATASET,
               "--tokenizer", TOKENIZER, "--tokenizer_path", os.path.join(out, "vocab.txt"),
               "--batch_size_type", "frame", "--batch_size_per_gpu", str(bs),
               "--grad_accumulation_steps", "8", "--max_samples", str(ms),
               "--learning_rate", "1e-5", "--epochs", "50",
               "--num_warmup_updates", "1000",
               "--save_per_updates", "1000", "--last_per_updates", "500",
               "--keep_last_n_checkpoints", "3",
               "--logger", "tensorboard"] + bnb
        print(f"④ محاولةُ الصقل #{i}: batch={bs}, max_samples={ms}\n   " + " ".join(cmd))
        sys.stdout.flush()
        rc = subprocess.run(cmd, env=env).returncode
        if rc == 0:
            print("✅ انتهى الصقلُ طبيعيًّا (اكتملت الحِقَب)."); break
        print(f"⚠️ توقّفت المحاولةُ #{i} برمز {rc} — غالبًا نفادُ ذاكرة. "
              f"{'أُعيد بحجمٍ أصغر…' if i < len(CANDIDATES) else 'لا حجمَ أصغر — راجِع السجلّ.'}")
        sys.stdout.flush()
    print("نقاطُ الحفظ في مجلّد ckpts داخل بيئة F5 — أخبِرني لأربطها بالتطبيق.")

if __name__ == "__main__":
    main()
