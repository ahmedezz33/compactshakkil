# -*- coding: utf-8 -*-
"""
morph_features.py — إشارة نحويّة صريحة: وسمُ كلّ حرفٍ بوسم كلمته الصرفيّ (POS).

المبدأ: النموذج بصريّ حرفيّ لا يرى النحو. نُغذّيه إشارةً نحويّة واضحة (POS من
CAMeL Tools) لتساعده على حركة الآخِر (الإعراب) تحديدًا — الاسمُ يُعرَب، الفعلُ
يُبنى/يُعرَب، الحرفُ مبنيّ. لا نُسرّب حركة الآخِر نفسها (cas)؛ نعطي البنية فقط.

عقد المحاذاة (حاسم):
  pos_ids  ┈┈  محاذٍ 1:1 مع split_letters_and_diacritics(line)[0]
  • كلّ حرفٍ في كلمة يأخذ وسم كلمته.
  • المسافة تأخذ SPACE_ID.
  • عدد الكلمات المُمرّرة للواسِم = عدد الأوسمة المُعادة (محاذاة مضمونة).

الواسِم قابلٌ للاستبدال: CamelTagger (على جهازك) أو MockTagger (للتحقّق هنا).
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data.vocab_v2 import split_letters_and_diacritics, strip_diacritics

# ── مجموعة أوسمة CAMeL الأساسيّة (ثابتة) ──────────────────────────────
_POS = [
    "noun","noun_prop","noun_num","noun_quant","adj","adj_comp","adj_num",
    "adv","adv_interrog","adv_rel","pron","pron_dem","pron_exclam",
    "pron_interrog","pron_rel","verb","verb_pseudo","part","part_dem",
    "part_det","part_focus","part_fut","part_interrog","part_neg",
    "part_restrict","part_verb","part_voc","prep","abbrev","conj",
    "conj_sub","interj","digit","latin","punc",
]
PAD_POS_ID  = 0            # حشو
SPACE_ID    = 1            # المسافة
OTHER_ID    = 2            # وسمٌ غير معروف
_BASE       = 3            # بداية الأوسمة الحقيقيّة
POS2ID = {p: _BASE + i for i, p in enumerate(_POS)}
NUM_POS = _BASE + len(_POS)   # حجم مفردات الأوسمة (يكفي لأيّ ميزة أصغر)

def pos_to_id(pos: str) -> int:
    return POS2ID.get(pos, OTHER_ID)

# ── ميزة الحالة الإعرابيّة (cas) — لتجربة السقف الأعلى (oracle) ──────────
# تُخزَّن بنفس صيغة .pos وتُدرَّب بنفس الأنبوب؛ تُبقي PAD/SPACE/OTHER كما هي.
CASE2ID = {"n": 3, "a": 4, "g": 5}    # اسميّ / نصبيّ / جرّيّ
def case_to_id(cas: str) -> int:
    return CASE2ID.get(cas, OTHER_ID)   # u/na/None → OTHER(2)

# ── الأوسمة ──────────────────────────────────────────────────────────
class MockTagger:
    """واسِمٌ حتميّ للتحقّق من المحاذاة فقط (بلا لغويّات حقيقيّة)."""
    def tag(self, words, feat="pos"):
        out = []
        for w in words:
            wl = strip_diacritics(w)
            if feat == "cas":
                out.append("n" if len(wl) >= 4 else "u"); continue
            if not wl: out.append("part")
            elif wl[0] in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي" and len(wl) >= 4:
                out.append("verb" if wl.startswith("ي") or wl.startswith("ت") else "noun")
            else:
                out.append("part")
        return out

class CamelTagger:
    """الواسِم الحقيقيّ (على جهازك، داخل venv فيه camel_tools). feat=pos أو cas."""
    def __init__(self, db="calima-msa-r13"):
        from camel_tools.disambig.mle import MLEDisambiguator
        self._d = MLEDisambiguator.pretrained(db)
    def tag(self, words, feat="pos"):
        disamb = self._d.disambiguate(words)   # كلماتنا كتوكِنات → محاذاة 1:1
        out = []
        for dw in disamb:
            a = dw.analyses[0].analysis if dw.analyses else {}
            if feat == "cas":
                out.append(a.get("cas") or "u")
            else:
                out.append(a.get("pos") or "noun")
        return out

# ── المحاذاة الأساسيّة ────────────────────────────────────────────────
def _word_spans(L):
    """أرجع (بداية, نهاية) لكلّ كلمة (تتابع غير مسافة) في قائمة الحروف L."""
    spans=[]; st=None
    for i,ch in enumerate(L):
        if ch==" ":
            if st is not None: spans.append((st,i)); st=None
        else:
            if st is None: st=i
    if st is not None: spans.append((st,len(L)))
    return spans

def line_to_pos_ids(line: str, tagger, feat="pos") -> list:
    """أرجع معرّفات الميزة محاذيةً 1:1 مع أحرف السطر (feat=pos أو cas)."""
    L,_ = split_letters_and_diacritics(line)
    spans = _word_spans(L)
    words = ["".join(L[a:b]) for a,b in spans]         # هياكل الكلمات (بلا حركات أصلًا)
    tags  = tagger.tag(words, feat) if words else []
    assert len(tags)==len(words), "الواسِم أخلّ بالمحاذاة 1:1"
    to_id = case_to_id if feat=="cas" else pos_to_id
    ids = [SPACE_ID]*len(L)
    for (a,b),t in zip(spans,tags):
        pid = to_id(t)
        for i in range(a,b): ids[i]=pid
    return ids, L

# ── التحقّق الذاتيّ (يُشغَّل هنا بالـ MockTagger) ───────────────────────
def _selfcheck(path, n=500):
    tg=MockTagger(); bad_len=bad_space=bad_word=0; seen=0
    for line in open(path,encoding="utf-8"):
        s=line.strip()
        if not s: continue
        seen+=1
        if seen>n: break
        ids,L = line_to_pos_ids(s,tg)
        if len(ids)!=len(L): bad_len+=1; continue
        for i,ch in enumerate(L):
            if ch==" " and ids[i]!=SPACE_ID: bad_space+=1
            if ch!=" " and ids[i]==SPACE_ID: bad_word+=1
        # كلّ كلمة: وسمٌ واحد لكلّ أحرفها
        for a,b in _word_spans(L):
            if len(set(ids[a:b]))!=1: bad_word+=1
    print(f"فُحص {seen-1 if seen>n else seen} سطرًا")
    print(f"  اختلال طول (يجب=0):        {bad_len}")
    print(f"  مسافة بوسم خاطئ (يجب=0):   {bad_space}")
    print(f"  حرف/كلمة بوسم خاطئ (يجب=0):{bad_word}")
    print(f"  |مفردات الأوسمة| = {NUM_POS}")

if __name__=="__main__":
    import sys
    p = sys.argv[1] if len(sys.argv)>1 else "data/processed_clean/val.txt"
    _selfcheck(p)
