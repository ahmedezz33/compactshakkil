# -*- coding: utf-8 -*-
"""
diac_pipeline.py — خطُّ التشكيلِ الكاملُ المشتركُ بين تطبيقِ التعليم (app_teach) والـ API.

يُطابِقُ app_teach.diacritize حرفيًّا حتى يُخرِجَ الـ API نفسَ تشكيلِ التطبيقِ تمامًا:
  استردادُ القرآن (آية/آيات/جزئيّ) → BERT-graft (مع احترامِ تشكيلِ الإدخال) →
  iraab_fix (قواعدُ الإعرابِ الحتميّة) → fix_jalalah_lines → fix_lam →
  restore_quran_tashkeel (إحلالُ تشكيلِ المصحفِ للآياتِ بين ﴿﴾).

مصدرٌ واحدٌ للحقيقة: التطبيقُ والـ API يستوردانِ الدوالَّ نفسَها، فلا ينحرفُ أحدُهما عن الآخَر.
"""
import re as _re
import sys as _sys
from pathlib import Path as _Path

_ROOT = _Path(__file__).parent
for _p in (str(_ROOT), str(_ROOT / "scripts")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from reverence_aware_unified import load_quran_index, _norm   # noqa: E402
from pronounce import fix_jalalah_lines, fix_lam              # noqa: E402
import quran_audio                                            # noqa: E402

QURAN = str(_ROOT / "data" / "raw" / "quran" / "quran-simple.txt")
_AYA_SEP = _re.compile(r"[0-9٠-٩۰-۹۝۞]+")   # أرقامُ الآي وعلاماتُ نهايتها فواصل

_STATE = {}

def _inf():
    """نسخةُ BERT-graft (تحميلٌ كسولٌ، نسخةٌ واحدةٌ مشتركة)."""
    if "inf" not in _STATE:
        from bert_graft_infer import GraftInfer
        _STATE["inf"] = GraftInfer()
    return _STATE["inf"]

def _index():
    if "idx" not in _STATE:
        idx, _f, _v = load_quran_index(QURAN)
        _STATE["idx"] = idx
        _STATE["keys"] = sorted(idx, key=len, reverse=True)
    return _STATE["idx"], _STATE["keys"]

def _retrieve_one(k):
    """استرداد آيةٍ لمفتاحٍ مطبّع: تطابقٌ تامّ ثمّ آيةٌ حاويةٌ (مضمّنة)."""
    if not k:
        return None
    idx, keys = _index()
    if k in idx:
        return idx[k]
    for vk in keys:
        if len(vk) < 8:
            break
        if vk in k:
            return idx[vk]
    return None

def route(line, respect=True):
    INF = _inf()
    k = _norm(line)
    hit = _retrieve_one(k)
    if hit is not None and _norm(hit) == k:          # السطرُ آيةٌ واحدةٌ بالضبط
        return hit, "استرداد (آية)"
    segs = [s for s in _AYA_SEP.split(line) if _norm(s)]
    if len(segs) >= 2:
        outs = []; hits = 0
        for s in segs:
            h = _retrieve_one(_norm(s))
            if h is not None:
                outs.append(h); hits += 1
            else:
                outs.append(INF.diacritize_partial(s) if respect else INF.diacritize(s))
        if hits >= 2:                                # مقطعٌ قرآنيٌّ متعدّدُ الآيات
            tag = "استرداد (آيات)" if hits == len(segs) else f"استرداد جزئيّ ({hits}/{len(segs)} آية)"
            return "\n".join(outs), tag
    out = INF.diacritize_partial(line) if respect else INF.diacritize(line)
    return out, "BERT-graft"

def diacritize(text, respect=True):
    """يُطابِقُ app_teach.diacritize: يُعيدُ (النصَّ المشكَّل، سلسلةَ المسارات)."""
    if not text or not text.strip():
        return "", "—"
    INF = _inf()  # noqa: F841 (يضمنُ تحميلَ النموذجِ قبلَ route)
    outs = []; routes = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            outs.append(""); continue
        o, r = route(s, respect)
        if r == "BERT-graft":                        # المستردُّ القرآنيُّ لا يُمَسّ
            try:
                import iraab_fix; o = iraab_fix.correct(o)
            except Exception as _ie:
                print("iraab_fix skip:", _ie)
            o = fix_lam(fix_jalalah_lines(o))
            try:
                import lex_fix; o = lex_fix.apply_text(o)
            except Exception as _le:
                print("lex_fix skip:", _le)
        outs.append(o); routes.append(r)
    result = "\n".join(outs)
    try:
        result = quran_audio.restore_quran_tashkeel(result)
    except Exception as _qe:
        print("quran tashkeel:", _qe)
    return result, " | ".join(dict.fromkeys(routes))
