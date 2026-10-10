# -*- coding: utf-8 -*-
"""
piper_raw.py — نطقُ Piper بإدخالِ phoneme خام.

يمرّرُ الـ IPA الذي يبنيه g2p.py مباشرةً إلى نموذج Piper (ONNX) دون المرورِ
بـ espeak، فيُحترَمُ تفخيمُ لفظِ الجلالة (ɫ) والتفخيمُ (ˤ) واللامُ الشمسيّة
وكلُّ ما رمّزناه — وهو ما لا يفعلُه المسارُ النصّيُّ العاديّ.

الآليّة: IPA (حرفًا حرفًا) → محاذاةٌ لمخزونِ phonemes الصوت (phoneme_id_map)
→ [BOS] + (phoneme + PAD)* + [EOS] → onnxruntime.
"""
import os, json, wave, struct

_BOS, _EOS, _PAD = "^", "$", "_"

# رموزٌ قد تغيبُ عن مخزونِ صوتٍ بعينِه ← أقربُ بديلٍ متاح (يُطبَّقُ فقط إن غاب الأصل)
_FALLBACK = {
    "ɫ": ["l"],        # اللام المفخّمة → لام عاديّة (Piper نادرًا ما يملكُ ɫ)
    "ˤ": [],           # علامةُ التفخيم وحدَها: تُسقَطُ إن لم تكنْ في المخزون (يبقى الحرفُ الأصل)
    "ʔ": ["ʔ", ""],    # الهمزة: إن غابت تُسقَط (وقفةٌ طبيعيّة)
    "ː": ["ː", ""],    # المدّ: إن غاب يُسقَط (يبقى الصائتُ قصيرًا)
    "ɣ": ["ɣ", "x"],
    "θ": ["θ", "t"],
    "ð": ["ð", "d"],
    "ħ": ["ħ", "h"],
    "ʕ": ["ʕ", ""],
    "x": ["x", "k"],
    "q": ["q", "k"],
    "j": ["j", "i"],
}


def config_path(onnx_path):
    for c in (onnx_path + ".json", os.path.splitext(onnx_path)[0] + ".json"):
        if os.path.exists(c):
            return c
    return None


def load_config(onnx_path):
    cp = config_path(onnx_path)
    if not cp:
        raise RuntimeError("لا ملفَّ إعدادٍ (.json) بجوارِ نموذجِ الصوت")
    with open(cp, encoding="utf-8") as f:
        return json.load(f)


def _adapt(ipa, id_map):
    """يحوّلُ سلسلةَ IPA (حرفًا حرفًا) إلى رموزٍ موجودةٍ في مخزونِ الصوت.
    يُرجِعُ (phonemes, missing) حيث missing الرموزُ التي تعذّر تعيينُها."""
    out, missing = [], []
    for ch in ipa:
        if ch == " ":
            if _PAD in id_map:      # الفراغُ = وقفةٌ قصيرة (رمزُ الحشو)
                out.append(_PAD)
            continue
        if ch in id_map:
            out.append(ch); continue
        placed = False
        for alt in _FALLBACK.get(ch, []):
            if alt == "":           # بديلٌ صريحٌ بالإسقاط
                placed = True; break
            if alt in id_map:
                out.append(alt); placed = True; break
        if not placed:
            missing.append(ch)      # لا أصلَ ولا بديلَ → يُسقَطُ ويُسجَّل
    return out, missing


def phonemes_to_ids(phonemes, id_map):
    """بناءُ سلسلةِ المُعرّفات بترتيبِ Piper: BOS ثمّ (phoneme + PAD)* ثمّ EOS."""
    ids = list(id_map.get(_BOS, [0]))
    for p in phonemes:
        if p in id_map:
            ids.extend(id_map[p])
            if p != _PAD and _PAD in id_map:
                ids.extend(id_map[_PAD])
    ids.extend(id_map.get(_EOS, [0]))
    return ids


def ipa_to_ids(ipa, cfg):
    id_map = cfg["phoneme_id_map"]
    phonemes, missing = _adapt(ipa, id_map)
    return phonemes_to_ids(phonemes, id_map), missing


def available():
    try:
        import onnxruntime, numpy      # noqa: F401
        return True
    except Exception:
        return False


def synth(ipa, onnx_path, out, cfg=None):
    """يُخرِجُ ملفَّ WAV من IPA خامٍ عبر نموذجِ Piper مباشرةً."""
    import numpy as np
    import onnxruntime as ort

    cfg = cfg or load_config(onnx_path)
    ids, missing = ipa_to_ids(ipa, cfg)
    if missing:
        print("piper_raw: رموزٌ غيرُ مُعيَّنة (أُسقِطت):", "".join(sorted(set(missing))))

    inf = cfg.get("inference", {})
    scales = np.array([inf.get("noise_scale", 0.667),
                       inf.get("length_scale", 1.0),
                       inf.get("noise_w", 0.8)], dtype=np.float32)
    x = np.array([ids], dtype=np.int64)
    x_len = np.array([x.shape[1]], dtype=np.int64)
    inputs = {"input": x, "input_lengths": x_len, "scales": scales}

    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    # بعضُ النماذج تتطلّبُ sid للمتحدّثين المتعدّدين
    names = {i.name for i in sess.get_inputs()}
    if "sid" in names:
        inputs["sid"] = np.array([0], dtype=np.int64)
    audio = sess.run(None, {k: v for k, v in inputs.items() if k in names})[0]

    audio = audio.squeeze()
    m = float(np.max(np.abs(audio))) or 1.0
    pcm = (audio / m * 32767.0).astype("<i2")
    sr = int(cfg.get("audio", {}).get("sample_rate", 22050))
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(struct.pack("<%dh" % len(pcm), *pcm.tolist()))
    return out
