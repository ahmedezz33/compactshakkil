# -*- coding: utf-8 -*-
"""
ar_stress.py — نبرُ الفصحى على سلسلةِ IPA.

نماذجُ Piper مدرَّبةٌ على مخارجِ eSpeak التي تحملُ علامةَ النبر ˈ؛ فبدونها
يخرجُ الإيقاعُ مسطَّحًا («أعجميًّا»). هذه الوحدةُ تُقطّعُ كلَّ كلمةٍ مقاطعَ،
تزِنُها (خفيف/ثقيل/فائق)، وتُدرِجُ ˈ قبل المقطعِ المنبور وفق قاعدةِ العربيّة:

  • إن كان المقطعُ الأخيرُ فائقَ الثقل (CVVC/CVCC) ← يُنبَر.
  • وإلّا إن كان ما قبل الأخيرِ ثقيلًا (CVV/CVC) ← يُنبَر.
  • وإلّا ← ما قبلَ ما قبلِ الأخير (أو الأوّل في القصير).
"""

_VOWEL_START = set("aiueoɛɔəɐæɪʊ")   # بدايةُ رمٲِ صائت (لدينا a i u؛ والبقيّةُ احتياط)
_LONG = "ː"
_MODS = set("ˤʰʲˠˀ̃")                 # لواحقُ تُلصَقُ بالحرفِ السابق


def _tokenize(word):
    """يقسِمُ كلمةً (سلسلةَ IPA بلا فراغات) إلى وحداتٍ صوتيّة: الطولُ واللواحقُ
    تُلصَقُ بسابقها، فيصيرُ 'sˤ' و'aː' وحدةً واحدة."""
    toks = []
    for ch in word:
        if (ch == _LONG or ch in _MODS) and toks:
            toks[-1] += ch
        else:
            toks.append(ch)
    return toks


def _is_vowel(tok):
    return tok and tok[0] in _VOWEL_START


def _syllabify(toks):
    """يُرجِعُ قائمةَ مقاطع؛ كلُّ مقطعٍ (start_index, [tokens], weight).
    القاعدة: بدايةُ المقطعِ صامتٌ واحدٌ (أقصى بداية)، والصائتُ نواةٌ،
    والصامتُ الزائدُ قبل صائتٍ تالٍ يصيرُ خاتمةً للسابق."""
    # مواضعُ النوى (الصوائت)
    nuclei = [i for i, t in enumerate(toks) if _is_vowel(t)]
    if not nuclei:
        return [{"start": 0, "onset": toks, "nucleus": "", "coda": [],
                 "weight": "light"}]
    # بدايةُ كلِّ مقطع: صامتٌ واحدٌ فقط قبلَ النواة (بدايةُ العربيّةِ أحاديّة)
    starts = []
    for k, nuc in enumerate(nuclei):
        prev_nuc = nuclei[k - 1] if k > 0 else -1
        s = nuc
        if nuc - 1 >= 0 and not _is_vowel(toks[nuc - 1]) and (nuc - 1) > prev_nuc:
            s = nuc - 1
        starts.append(s)
    out = []
    for k, nuc in enumerate(nuclei):
        start = starts[k]
        nxt = starts[k + 1] if k + 1 < len(nuclei) else len(toks)
        onset = toks[start:nuc]
        nucleus = toks[nuc]
        coda = toks[nuc + 1:nxt]          # الصوامتُ حتى بدايةِ المقطعِ التالي
        # الوزن
        long_v = _LONG in nucleus
        if long_v and coda:
            w = "superheavy"   # CVVC
        elif len(coda) >= 2:
            w = "superheavy"   # CVCC
        elif long_v or coda:
            w = "heavy"        # CVV أو CVC
        else:
            w = "light"        # CV
        out.append({"start": start, "onset": onset, "nucleus": nucleus,
                    "coda": coda, "weight": w})
    return out


def _stress_index(sylls):
    """يُرجِعُ فهرسَ المقطعِ المنبور وفق قاعدةِ الفصحى."""
    n = len(sylls)
    if n == 1:
        return 0
    last = n - 1
    if sylls[last]["weight"] == "superheavy":
        return last
    penult = n - 2
    if sylls[penult]["weight"] in ("heavy", "superheavy"):
        return penult
    # وإلّا ما قبلَ ما قبلِ الأخير إن وُجد، وإلّا ما قبلَ الأخير
    return penult - 1 if penult - 1 >= 0 else penult


def stress_word(word):
    if not word:
        return word
    toks = _tokenize(word)
    sylls = _syllabify(toks)
    if len(sylls) <= 1:
        return "ˈ" + word if word else word     # أحاديُّ المقطعِ يُنبَر
    si = _stress_index(sylls)
    start = sylls[si]["start"]
    new = toks[:start] + ["ˈ"] + toks[start:]
    return "".join(new)


def add_stress(ipa):
    """يُدرِجُ النبرَ على كلِّ كلمةٍ في سلسلةِ IPA (مفصولةٍ بفراغات)."""
    return " ".join(stress_word(w) for w in ipa.split(" ") if w != "" ) \
        if ipa else ipa
