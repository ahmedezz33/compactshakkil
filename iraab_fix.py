# -*- coding: utf-8 -*-
"""
iraab_fix.py — deterministic grammar fix for anna/an and inna/in particles.
Rule: masdariyya an / conditional in are followed by a VERB (sukun, no shadda);
the emphatic anna/inna are followed by a NOUN/pronoun (shadda + fatha). We tell
verb from noun via the lexicon POS, and only correct clear cases.
"""
import os, re, sqlite3, glob, functools, json

_HARAKAT = "ًٌٍَُِّْٰ"
_STRIP = str.maketrans("", "", _HARAKAT)


def _bare(w):
    return w.translate(_STRIP)


_LIGHT = {"أن": "أَنْ", "وأن": "وَأَنْ", "فأن": "فَأَنْ",
          "إن": "إِنْ", "وإن": "وَإِنْ", "فإن": "فَإِنْ"}
_HEAVY = {"أن": "أَنَّ", "وأن": "وَأَنَّ", "فأن": "فَأَنَّ",
          "إن": "إِنَّ", "وإن": "وَإِنَّ", "فإن": "فَإِنَّ"}
_TARGETS = set(_LIGHT)


def _db_path():
    for c in ["lexicon/arabic_lexicon.db", "arabic_lexicon.db"]:
        if os.path.exists(c):
            return c
    g = glob.glob("**/arabic_lexicon.db", recursive=True)
    return g[0] if g else None


_CON = None
def _con():
    global _CON
    if _CON is None:
        p = _db_path()
        if not p:
            raise RuntimeError("no arabic_lexicon.db")
        _CON = sqlite3.connect(p, check_same_thread=False)
    return _CON


@functools.lru_cache(maxsize=20000)
def _pos_of(bare):
    try:
        cur = _con().execute("SELECT analyses_json FROM words WHERE word=? LIMIT 1", (bare,))
        row = cur.fetchone()
    except Exception:
        return frozenset()
    if not row or not row[0]:
        return frozenset()
    try:
        return frozenset(a.get("pos", "") for a in json.loads(row[0]))
    except Exception:
        return frozenset()


_NOMINAL = {"noun", "noun_prop", "adj", "pron", "pron_rel", "pron_dem"}
_VERBAL = {"verb", "verb_pseudo"}


def _cands(bare):
    """مرشّحاتُ الصيغةِ للبحث: كما هي، وبلا ألفِ التنوين المنصوب."""
    c = {bare}
    if len(bare) > 2 and bare.endswith("ا"):
        c.add(bare[:-1])            # زيدًا → زيد
    if len(bare) > 2 and bare.endswith("ة"):
        c.add(bare[:-1] + "ه")
    return c


def _pos_all(bare):
    p = set()
    for c in _cands(bare):
        p |= set(_pos_of(c))
    return p


def _is_pure_verb(bare):
    p = _pos_all(bare)
    return bool(p) and bool(p & _VERBAL) and not (p & _NOMINAL)


def _is_pure_nominal(bare):
    p = _pos_all(bare)
    return bool(p) and bool(p & _NOMINAL) and not (p & _VERBAL)


_PRE_VERB_PARTICLE = {"لا", "لم", "لن"}   # «ما» مُلتبسة (موصولة/نافية) ← أُزيلت


def fix_anna(text):
    """أنّ/إنّ + فعل ← أنْ/إنْ. جراحيّ: يمسُّ الشدّةَ على النونِ فقط ويُبقي الهمزةَ
    كما كتبها النموذج (انحدارٌ ~0.003% على نصٍّ ذهبيّ). لا يفرضُ الاتّجاهَ العكسيّ."""
    if not text:
        return text
    _final_nun = re.compile(r"\u0646[\u064b-\u0652]*$")   # نون آخِرُها بكلِّ حركاتها
    out = []
    for line in text.split("\n"):
        toks = line.split(" ")
        for i, tok in enumerate(toks):
            if _bare(tok) not in _TARGETS:
                continue
            if "\u0651" not in tok:                 # لا شدّةَ ← خفيفةٌ أصلًا
                continue
            j = i + 1
            while j < len(toks) and not toks[j].strip():
                j += 1
            if j >= len(toks):
                continue
            nxt = _bare(toks[j].strip(" \u060c.:؛!؟"))
            if nxt in _PRE_VERB_PARTICLE and j + 1 < len(toks):
                nxt = _bare(toks[j + 1].strip(" \u060c.:؛!؟"))
            if nxt and _is_pure_verb(nxt):
                toks[i] = _final_nun.sub("\u0646\u0652", tok)   # ...ن(بأيِّ حركة) → نْ
        out.append(" ".join(toks))
    return "\n".join(out)


# ═══ القواعدُ المغلقةُ المؤكَّدة: الكلماتُ المبنيّةُ ذاتُ التشكيلِ الثابت ═══
# تُصحَّحُ يقينًا لأنّ صيغتَها لا تتغيّرُ بموقعِها. استُبعِدتِ المتشابهاتُ الملتبسة:
# «من» (مِنْ/مَنْ)، «لكن» (لكنْ/لكنَّ)، «لما» (لَمّا/لِمَا)، «أنت» (أنتَ/أنتِ)،
# «عند/بين/بعد/قبل/كل/بعض» (تتغيّرُ حركةُ آخِرها بالإعراب).
_FIXED_RAW = {
    # ضمائرُ الرفعِ المنفصلة
    "هو": "هُوَ", "هي": "هِيَ", "هم": "هُمْ", "هن": "هُنَّ", "هما": "هُمَا",
    "نحن": "نَحْنُ", "انتم": "أَنْتُمْ", "انتما": "أَنْتُمَا",   # «انا» مُلتبسة (أَنا/إنّا) ← تُركت للنموذج
    "انتن": "أَنْتُنَّ",
    # أسماءُ الإشارة
    "هذا": "هَذَا", "هذه": "هَذِهِ", "هذان": "هَذَانِ", "هذين": "هَذَيْنِ",
    "هؤلاء": "هَؤُلَاءِ", "ذلك": "ذَلِكَ", "ذلكم": "ذَلِكُمْ", "تلك": "تِلْكَ",
    "اولئك": "أُولَئِكَ", "هنا": "هُنَا", "هناك": "هُنَاكَ", "هنالك": "هُنَالِكَ",
    # الأسماءُ الموصولة
    "الذي": "الَّذِي", "التي": "الَّتِي", "الذين": "الَّذِينَ",
    "اللذان": "اللَّذَانِ", "اللتان": "اللَّتَانِ", "اللذين": "اللَّذَيْنِ",
    "اللاتي": "اللَّاتِي", "اللواتي": "اللَّوَاتِي", "اللائي": "اللَّائِي",
    # حروفُ الجرّ (غيرُ الملتبسة)
    "عن": "عَنْ", "في": "فِي", "الى": "إِلَى", "على": "عَلَى",
    # حروفٌ وأدواتٌ مبنيّةٌ ثابتة
    "قد": "قَدْ", "لن": "لَنْ", "لم": "لَمْ", "كي": "كَيْ", "لو": "لَوْ",
    "لولا": "لَوْلَا", "حتى": "حَتَّى", "ثم": "ثُمَّ", "بل": "بَلْ",
    "اذ": "إِذْ", "اذا": "إِذَا", "نعم": "نَعَمْ", "بلى": "بَلَى",
    "كلا": "كَلَّا", "انما": "إِنَّمَا", "ليت": "لَيْتَ", "لعل": "لَعَلَّ",
    "كأن": "كَأَنَّ", "ما": "مَا",
    # ظروفٌ مبنيّة
    "حيث": "حَيْثُ", "الان": "الْآنَ", "امس": "أَمْسِ",
}
_PREFIX = {"و": "وَ", "ف": "فَ"}


def _norm_hamza(w):
    return (w.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
             .replace("ٱ", "ا"))


# مفتاحُ البحث: مجرّدٌ + موحَّدُ الهمزة
_FIXED = {_norm_hamza(k): v for k, v in _FIXED_RAW.items()}


def fix_mabni(text):
    """يفرضُ التشكيلَ الثابتَ للكلماتِ المبنيّة (يقينيّ، مع بادئتَي و/ف)."""
    if not text:
        return text
    out_lines = []
    for line in text.split("\n"):
        toks = line.split(" ")
        for i, tok in enumerate(toks):
            if not tok:
                continue
            b = _norm_hamza(_bare(tok))
            if b in _FIXED:
                toks[i] = _FIXED[b]
            elif len(b) > 1 and b[0] in _PREFIX and b[1:] in _FIXED:
                toks[i] = _PREFIX[b[0]] + _FIXED[b[1:]]
        out_lines.append(" ".join(toks))
    return "\n".join(out_lines)


def correct(text):
    """تصحيحٌ نحويٌّ للنطقِ والعرض: «أنْ/أنَّ + فعل» فقط (جراحيٌّ محايدٌ للدقّة).
    fix_jarr و fix_inna_ism و fix_mabni و الجزمُ و كانَ عُطِّلت جميعًا: القياسُ
    الصارمُ (صافي الأثرِ على مخرجِ النموذج) أظهرَ أنّها تُنقِصُ الدقّةَ — النموذجُ
    المصقولُ أدقُّ منها في السياق. تبقى الدوالُّ معرّفةً للرجوعِ إليها مستقبلًا."""
    # القياسُ الصارمُ (صافي الأثرِ على مخرجِ النموذج مقابلَ الذهبيّ) أثبتَ أنّ
    # fix_jarr و fix_inna_ism يضرّانِ الدقّةَ (النموذجُ أذكى في السياق)، فعُطِّلتا.
    # fix_anna محايدةٌ/نافعةٌ (سكونُ الفعل بعد أنْ) فتبقى وحدَها.
    return fix_anna(text)


# ══════════════════════════════════════════════════════════════════════
#  قواعدُ الإعرابِ الحتميّةُ الآمنة (مُختبَرةٌ على نصٍّ ذهبيّ ≤ 0.002٪ انحدار)
#  الجرُّ بالكسرة (بعد حرفِ جرّ، للمعرّفِ بـ«ال») ونصبُ اسمِ «إنَّ» وأخواتِها.
#  المبنيُّ والمقصورُ وجمعُ المذكّر/المثنّى (بالياء) والضمائرُ المتّصلة ← تُتخطّى.
# ══════════════════════════════════════════════════════════════════════
_ALEF2 = str.maketrans({"ٱ": "ا", "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"})
def _sk2(w): return _bare(w).translate(_ALEF2)

_FATHA = "َ"; _KASRA = "ِ"; _DAMMA = "ُ"; _SUKUN = "ْ"
_FATHATAN = "ً"; _KASRATAN = "ٍ"; _DAMMATAN = "ٌ"; _SHADDA = "ّ"; _DAGGER = "ٰ"
_SHORT = {_FATHA, _KASRA, _DAMMA}; _TANWIN = {_FATHATAN, _KASRATAN, _DAMMATAN}
_MARKSET = set(_HARAKAT)

def _units2(w):
    u = []
    for c in w:
        if c in _MARKSET:
            if u: u[-1][1] += c
        else: u.append([c, ""])
    return u
def _join2(u): return "".join(l + m for l, m in u)

_MABNI_POS = {"pron", "pron_rel", "pron_dem", "pron_interrog"}
_NOM_STRICT = {"noun", "noun_prop", "adj"}
def _is_mabni(b):
    p = _pos_all(b)
    return bool(p) and bool(p & _MABNI_POS) and not (p & _NOM_STRICT)

_ENCL = ["هما", "كما", "هم", "هن", "كم", "كن", "نا", "ني", "ها", "ه", "ك"]
def _encl_idx(u):
    letsn = "".join(l for l, _ in u).translate(_ALEF2)
    for e in _ENCL:
        if letsn.endswith(e) and len(u) - len(e) >= 1:
            return len(u) - len(e) - 1
    return len(u) - 1
def _muqaddar(u):
    return bool(u) and u[-1][0] in ("ى", "ا", "ي", "و")   # مقصور/منقوص/متكلّم ← إعرابٌ مقدّر
def _yaa_sign(letsn):
    return (letsn.endswith("ين") or letsn.endswith("ون")
            or letsn.endswith("ان") or letsn.endswith("وا"))   # جمعٌ سالمٌ/مثنّى (بالحرف)
def _set_case(u, i, target):
    m = u[i][1]
    tan = bool(set(m) & _TANWIN)
    nm = {_FATHA: _FATHATAN, _KASRA: _KASRATAN, _DAMMA: _DAMMATAN}[target] if tan else target
    keep = "".join(c for c in m if c in (_SHADDA, _DAGGER))
    u[i][1] = keep + nm
    return u

_PREP_WORDS = {_sk2(w) for w in ("من","إلى","عن","على","في","حتى","منذ","مذ","رب")}
_STRIPPUNC = " ،.:؛!؟«»()"

def _apply_case_next(text, trigger_ok, target, require_al, skip_jar=False):
    if not text: return text
    out = []
    for line in text.split("\n"):
        toks = line.split(" ")
        for k, t in enumerate(toks):
            if not t or not trigger_ok(t): continue
            j = k + 1
            while j < len(toks) and not toks[j].strip(): j += 1
            if j >= len(toks): continue
            nt = toks[j]; nb = _sk2(nt.strip(_STRIPPUNC))
            if not _is_pure_nominal(nb): continue
            if require_al and not nb.startswith("ال"): continue
            if skip_jar and _starts_jar(nb): continue      # خبرٌ مقدّمٌ مجرور، ليس اسمَ إنّ
            if _is_mabni(nb): continue
            u = _units2(nt)
            if not u or _muqaddar(u): continue
            letsn = "".join(l for l, _ in u).translate(_ALEF2)
            if _yaa_sign(letsn): continue
            i = _encl_idx(u)
            if i < 0: continue
            _set_case(u, i, target)
            toks[j] = _join2(u)
        out.append(" ".join(toks))
    return "\n".join(out)

def fix_jarr(text):
    """الاسمُ المعرّفُ بـ«ال» التالي مباشرةً لحرفِ جرٍّ ← مجرورٌ بالكسرة.
    محافِظ: «ال» فقط (يتفادى الممنوعَ من الصرف)، ويتخطّى المبنيَّ والمقصورَ
    وجمعَ المذكّر/المثنّى (بالياء) والضمائرَ المتّصلة. انحدارٌ ≈0.0018٪."""
    return _apply_case_next(text, lambda t: _sk2(t) in _PREP_WORDS, _KASRA, True)

_INNA_TRIG = {_sk2(w) for w in ("إن","أن","كأن","لكن","ليت","لعل","وإن","فإن","وأن","فأن")}
_JAR_PROCL = ("ب", "ل", "ك")
def _starts_jar(nb):
    """هل الكلمةُ شبهُ جملةٍ مجرورةٌ ببائِها/لامِها/كافِها الجارّة؟ (خبرٌ مقدّمٌ بعد إنّ)."""
    if not nb or nb[0] not in _JAR_PROCL:
        return False
    if nb[:2] == "لل":                 # لِلـمسجد
        return True
    rest = nb[1:]
    if rest.startswith("ال"):          # بالـ/كالـ
        return True
    return _is_pure_nominal(rest)      # بـ + اسمٍ منكّر (بتصحيحٍ)


def fix_inna_ism(text):
    """الاسمُ الظاهرُ التالي مباشرةً لـ«إنَّ» وأخواتِها المشدّدة ← منصوبٌ بالفتحة.
    محافِظ (اسمٌ خالصٌ غيرُ مبنيٍّ ولا مقصور). انحدارٌ ≈0.0002٪."""
    return _apply_case_next(text, lambda t: _sk2(t) in _INNA_TRIG and _SHADDA in t, _FATHA, False, skip_jar=True)
