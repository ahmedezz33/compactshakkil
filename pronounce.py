# -*- coding: utf-8 -*-

try:
    import num2ar
except Exception:
    num2ar=None
"""
pronounce.py — طبقةُ تصحيحٍ لفظيّ ونطقيّ فوق مخرجات النموذج.

يعالج مشكلتين اشتكى منهما المستخدم في تبويب «النطق»:
  1) لفظُ الجلالة «الله» يُشكَّل ويُنطَق خطأً
     (النموذج الحرفيّ يُخرجه أحيانًا «الَلَهُ» أو «الْلُهُ» لأنّ رسمه شاذّ:
      لامٌ مشدّدةٌ فوقها ألفٌ خنجريّة). نُصحّحه معجميًّا إلى صورته القياسيّة
      «اللَّه» مع إبقاء حركة الإعراب التي تنبّأ بها النموذج.
  2) التوقّف (الوقف): عند القراءة يُسكَّن آخِرُ الكلمة الأخيرة من كلّ سطر/عبارة،
     ويُبدَّل تنوينُ الفتح ألفًا (كتابًا ← كتابا). نوفّر وضعين: «وصلًا» (بالإعراب
     كاملًا للتعليم) و«وقفًا» (طبيعيّ عند التسجيل).

مستقلٌّ عن torch — نصوصٌ فقط، فيمكن اختباره وحده.
"""
import re

# الحركات (يونيكود)
FATHA="َ"; KASRA="ِ"; DAMMA="ُ"; SUKUN="ْ"
FATHATAN="ً"; KASRATAN="ٍ"; DAMMATAN="ٌ"
SHADDA="ّ"; DAGGER_ALIF="ٰ"
TATWEEL="ـ"
HARAKAT=FATHA+KASRA+DAMMA+SUKUN+FATHATAN+KASRATAN+DAMMATAN+SHADDA+DAGGER_ALIF
MARKS=set(HARAKAT)
SHORT={FATHA,KASRA,DAMMA}
TANWIN={FATHATAN,KASRATAN,DAMMATAN}

def strip_marks(w):
    return "".join(c for c in w if c not in MARKS and c!=TATWEEL)

_ALEF_MAP=str.maketrans({"ٱ":"ا","أ":"ا","إ":"ا","آ":"ا","ى":"ي"})
def _sk(w):
    """هيكلٌ للبحث المعجميّ: بلا حركات، مع توحيد صور الألف والمقصورة (ٱلَّذِى ← الذي)."""
    return strip_marks(w).translate(_ALEF_MAP)

def _final_vowel(w):
    """آخِر حركةٍ إعرابيّة في الكلمة (تُطبَّق على الهاء في الجلالة)."""
    i=len(w)-1
    # تخطَّ العلاماتِ لالتقاط آخِرها المعنيّ (نتجاهل الشدّة/الخنجريّة)
    seen=""
    while i>=0 and w[i] in MARKS:
        seen=w[i]+seen; i-=1
    for c in seen[::-1]:
        if c in SHORT or c in TANWIN: return c
    return DAMMA   # افتراض: مرفوع إن لم يتبيّن

# ── لفظ الجلالة وما اتّصل به ──────────────────────────────────────────
# الهيكل المجرّد ← بانِي الصورة القياسيّة (تُلحَق حركةُ الإعراب بالهاء)
_LL=SHADDA+FATHA                       # لامٌ مشدّدةٌ مفتوحة  «لَّ»
def _jalalah_core(final):  return "الل"+_LL+"ه"+final          # اللَّهُ
def _lillah(final):        return "لِل"+_LL+"ه"+final          # لِلَّهِ
def _billah(final):        return "بِالل"+_LL+"ه"+final        # بِاللَّهِ
def _wallah(final):        return "وَالل"+_LL+"ه"+final        # وَاللَّهِ
def _fallah(final):        return "فَالل"+_LL+"ه"+final
def _tallah(final):        return "تَالل"+_LL+"ه"+final
def _allahumma(_):         return "الل"+_LL+"ه"+DAMMA+"م"+_LL     # اللَّهُمَّ (بترتيب موحّد)

JALALAH_MAP={
    "الله":_jalalah_core, "لله":_lillah, "بالله":_billah,
    "والله":_wallah, "فالله":_fallah, "تالله":_tallah,
    "اللهم":_allahumma, "اللّهم":_allahumma,
}

def fix_jalalah_word(w):
    sk=_sk(w)
    b=JALALAH_MAP.get(sk)
    if b is None: return w
    return b(_final_vowel(w))

def fix_jalalah(text):
    """صحّح كلَّ صور لفظ الجلالة في النصّ (للعرض والإعراب والنطق)."""
    return " ".join(fix_jalalah_word(w) if w else w for w in _wsplit(text))

# نحافظ على المسافات/الأسطر: نعالج كلمةً كلمة مع إبقاء الفواصل
def _wsplit(text): return text.split(" ")

def fix_jalalah_lines(text):
    out=[]
    for line in text.split("\n"):
        out.append(" ".join(fix_jalalah_word(w) for w in line.split(" ")))
    return "\n".join(out)

# ── الوقف ─────────────────────────────────────────────────────────────
def waqf_word(w):
    """سكِّن آخِرَ الكلمة للوقف: احذف الحركة القصيرة/التنوين، وأبقِ ألفَ تنوين الفتح."""
    if not w: return w
    # حالة «...ًا/ًى»: تنوينُ الفتح على الحرف قبل الألف ← احذف التنوينَ وأبقِ الألف
    if w.endswith("ا") or w.endswith("ى") or w.endswith("آ"):
        return w[:-1].replace(FATHATAN,"")+w[-1]
    # افصل العلاماتِ اللاحقةَ للحرف الأخير
    i=len(w)-1; tail=""
    while i>=0 and w[i] in MARKS:
        tail=w[i]+tail; i-=1
    stem=w[:i+1]
    if FATHATAN in tail:              # تنوين فتحٍ سافر (نادر) ← ألف مدّ
        keep=SHADDA if SHADDA in tail else ""
        return stem+keep+"ا"
    # احذف الحركاتِ القصيرةَ والتنوينَ (أبقِ الشدّةَ والألفَ الخنجريّة)
    keep="".join(c for c in tail if c in (SHADDA,DAGGER_ALIF))
    return stem+keep

def to_waqf(text):
    """طبِّق الوقفَ على آخِر كلمةٍ من كلّ سطر (طبيعيّ عند القراءة/التسجيل)."""
    out=[]
    for line in text.split("\n"):
        ws=line.split(" ")
        # آخِر كلمةٍ غير فارغة
        j=len(ws)-1
        while j>=0 and not ws[j].strip(): j-=1
        if j>=0: ws[j]=waqf_word(ws[j])
        out.append(" ".join(ws))
    return "\n".join(out)

# ── توحيد علامات الرسم العثمانيّ إلى القياسيّ ──────────────────────────
# مصاحفُ العثمانيّ تستعمل علاماتٍ خاصّةً لا يتعرّفها منطقُ النطق القياسيّ:
# سكونُ الرأس ۡ بدل ْ، وياءٌ/واوٌ صغيرتان، وتنوينٌ مفتوح، ومدّةٌ، وعلاماتُ وقف.
_UTH_MAP=str.maketrans({
    "ۡ":"ْ",   # ۡ رأسُ الخاء الصغير ← سكون
    "ٱ":"ا",   # همزةُ الوصل ← ألفٌ قياسيّة (edge لا يُحسِن «ٱل» فيختلّ إدغامُ اللام)
    "ۥ":"و", "ۦ":"ي",           # واوٌ/ياءٌ صغيرتان ← و/ي
    "ࣰ":"ً", "ࣱ":"ٌ", "ࣲ":"ٍ",  # تنوينٌ مفتوح ← ً ٌ ٍ
})
# علاماتٌ تُحذَف (مدّةٌ، رموزُ وقفٍ وتجويدٍ صغيرة، إلخ) — عدا الحركات والخنجريّة
_HH="ٔ"; _HL="ٕ"; _TW="ـ"
_UTH_STRIP=re.compile(r"[ؐ-ؚٖٓٗۖ-ۭ࣓-࣯ࣳ-ࣿ]")
def normalize_marks(text):
    s=text.translate(_UTH_MAP)
    s=re.sub(_TW+r"([ً-ْٰ]*)["+_HH+_HL+"]", r"ء\1", s)  # همزةٌ على السطر ← ء
    s=s.replace(_TW,"")
    s=(s.replace("ا"+_HH,"أ").replace("و"+_HH,"ؤ").replace("ي"+_HH,"ئ")
         .replace("ى"+_HH,"ئ").replace("ا"+_HL,"إ"))
    s=s.replace(_HH,"ء").replace(_HL,"ء")
    return _UTH_STRIP.sub("", s)

# ── تنظيف النصّ للنطق (أرقام الحواشي، علامات الترقيم غير المنطوقة) ──────
# نُزيل الأرقامَ (عربيّةً ولاتينيّة) وأقواسَها ورموزَ الاقتباس والنجوم ونحوها،
# فلا يقرأ المحرّكُ «١ ٢ ٣» ولا أسماءَ الرموز. نُبقي علاماتِ الوقف الطبيعيّة.
_TTS_DROP=re.compile(r"[0-9٠-٩۰-۹()\[\]{}«»\"“”‹›*_`~|/\\<>=+\-&@#$%^﴾﴿§°•]")
_DASH=re.compile(r"[-‐-―−]+")     # الشرطة/الوصلة بأنواعها
def clean_for_tts(text):
    if num2ar is not None:
        text=num2ar.verbalize(text)     # الأرقام ← كلماتٌ عربيّةٌ منطوقة (قبل الحذف)
    text=normalize_marks(text)          # وحّد الرسمَ العثمانيَّ أوّلًا
    text=_DASH.sub("،", text)           # الشرطة ← فاصلة (وقفة) لئلّا تُقرأ «شَرْطة»
    text=_TTS_DROP.sub(" ", text)
    return "\n".join(" ".join(l.split()) for l in text.split("\n"))

# ── تفعيل التضعيف (الشدّة) في النطق ────────────────────────────────────
def expand_shadda(text):
    """حرفٌ مشدَّد ← حرفان (الأوّل ساكن) لتُلفَظ الشدّةُ مُضعَّفةً: رَبّ ← رَبْب.
    يعتمد على الوحدات (حرف+علاماته) فيعمل مهما كان ترتيبُ الشدّة والحركة."""
    out=[]
    for line in text.split("\n"):
        words=[]
        for w in line.split(" "):
            res=[]
            for L,m in _units(w):
                if SHADDA in m:
                    vowel="".join(c for c in m if c!=SHADDA)   # ما عدا الشدّة
                    res.append(L+SUKUN); res.append(L+vowel)   # نسخةٌ ساكنة ثمّ محرّكة
                else:
                    res.append(L+m)
            words.append("".join(res))
        out.append(" ".join(words))
    return "\n".join(out)

# ── قاموسُ تصحيحِ نطقِ المحرّك (edge) ──────────────────────────────────
# محرّكُ edge العصبيّ يُخطئ في نطقِ كلماتٍ بعينها (تَنظُرون←تنظرين، فَرَقْنا بتشديد).
# نُصلحها بجدولٍ نصّيٍّ محلّيٍّ قابلٍ للتحرير: الكلمةُ الخاطئة ← إملاءٌ بديلٌ ينطقه
# edge صحيحًا. المطابقةُ بالهيكل (بلا حركات) فتلتقط الكلمةَ مهما كان تشكيلُها،
# ويدعم عباراتٍ من عدّة كلمات. «تعديلُ المطلوب فقط» حرفيًّا. يُطبَّق قبل النطق.
import os as _os, json as _json
from pathlib import Path as _Path
_OVR_PATH=str(_Path(__file__).parent/"pronunciation_overrides.json")
_OVR_MAP=str.maketrans({"ة":"ه","ؤ":"و","ئ":"ي"})   # فوق توحيدِ _sk للألف والمقصورة
def _mkey(w):
    """مفتاحُ مطابقةٍ موحَّد: بلا حركاتٍ، مع توحيد صور الألف/المقصورة/التاء/الهمزة."""
    return _sk(w).translate(_OVR_MAP)

_OVR_CACHE=None; _OVR_MTIME=None
_BREAKERS=("،","؛",".","؟","!",":","\n")
def _load_overrides():
    """يحمّل القاموسَ (ويعيد تحميلَه إن عُدِّل الملفُّ) → (مفرد, عبارات, أطولُ عبارة, عزل).
    توجيهٌ خاصٌّ «@عزل»: قائمةُ كلماتٍ يُخطئ فيها edge في السياق فقط (صحيحةٌ منفردة)؛
    نلفّها بفاصلتين لتُنطَق بنبرة الابتداء الصحيحة."""
    global _OVR_CACHE,_OVR_MTIME
    try: mt=_os.path.getmtime(_OVR_PATH)
    except OSError: return {},{},1,set()
    if _OVR_CACHE is not None and mt==_OVR_MTIME: return _OVR_CACHE
    single={}; phrases={}; maxlen=1; isolate=set()
    try:
        raw=_json.load(open(_OVR_PATH,encoding="utf-8"))
        for k,v in raw.items():
            if k in ("@عزل","@isolate") and isinstance(v,list):
                for w in v:
                    if isinstance(w,str) and w.strip(): isolate.add(_mkey(w.strip()))
                continue
            if not k or k.startswith("_") or k.startswith("@") or \
               not isinstance(v,str) or not v.strip():
                continue
            toks=k.split()
            key=" ".join(_mkey(t) for t in toks)
            if len(toks)>=2: phrases[key]=v.strip(); maxlen=max(maxlen,len(toks))
            else: single[_mkey(k)]=v.strip()
    except Exception: pass
    _OVR_CACHE=(single,phrases,maxlen,isolate); _OVR_MTIME=mt
    return _OVR_CACHE

def _split_affix(t):
    """يفصل الزوائدَ غيرَ الحرفيّة (ترقيم) عن قلبِ الكلمة الحرفيّ: («كتابٌ،» ← «كتابٌ»,«،»)."""
    idx=[i for i,ch in enumerate(t) if ("ء"<=ch<="ي") or ch in MARKS or ch in ("ٱ",TATWEEL)]
    if not idx: return t,"",""
    a,b=idx[0],idx[-1]
    return t[:a], t[a:b+1], t[b+1:]

def apply_overrides(text):
    """يستبدل الكلماتِ/العباراتِ المُصحَّحةَ من القاموس (يحافظ على الترقيم المُلاصِق)،
    ويعزل كلماتِ «@عزل» بفاصلتين لتصحيح نطقها في السياق."""
    single,phrases,maxlen,isolate=_load_overrides()
    if not text or (not single and not phrases and not isolate): return text
    out=[]
    for line in text.split("\n"):
        toks=line.split(" ")
        pre=[]; core=[]; suf=[]
        for t in toks:
            p,c,s=_split_affix(t); pre.append(p); core.append(c); suf.append(s)
        keys=[_mkey(c) if c else "" for c in core]
        n=len(core); i=0; res=[]
        while i<n:
            hit=False
            hi=min(maxlen,n-i)
            for L in range(hi,1,-1):                     # جرّب أطولَ عبارةٍ أوّلًا
                if all(keys[i+j] for j in range(L)):
                    key=" ".join(keys[i:i+L])
                    if key in phrases:
                        res.append(pre[i]+phrases[key]+suf[i+L-1]); i+=L; hit=True; break
            if hit: continue
            chosen = pre[i]+single[keys[i]]+suf[i] if (keys[i] and keys[i] in single) else toks[i]
            if keys[i] and keys[i] in isolate:           # كلمةٌ تُخطئ في السياق ← اعزلها بفاصلتين
                if res and not res[-1].rstrip().endswith(_BREAKERS):
                    res[-1]=res[-1].rstrip()+"،"
                if not chosen.rstrip().endswith(_BREAKERS):
                    chosen=chosen.rstrip()+"،"
            res.append(chosen); i+=1
        out.append(" ".join(res))
    return "\n".join(out)

# ── تحضيرٌ خفيفٌ للمحرّكات العصبيّة (edge/gTTS) ────────────────────────
# edge محرّكٌ عصبيٌّ يُتقن الشدّةَ واللامَ الشمسيّة/القمريّة والمدّ من النصّ المشكّل
# القياسيّ؛ فإثقالُه (فكُّ الشدّة، إدغامُ اللام يدويًّا) يُربكه ويُفسد النطق.
# لذا نكتفي بتوحيد علامات الرسم العثمانيّ، وتصحيح صورة لفظ الجلالة، والوقف.
def edge_prepare(text, mode="waqf", drop_sun=False):
    text=clean_for_tts(text)            # توحيدُ علامات العثمانيّ + إزالةُ الأرقام
    text=apply_overrides(text)          # قاموسُ تصحيحِ نطقِ edge (الكلماتُ الخاطئة)
    try:
        import iraab_fix; text=iraab_fix.correct(text)   # نطقٌ: أنّ/إنّ + فعل ← سكون (لا يمسُّ التشكيلَ المحفوظ)
    except Exception as _ie: print("iraab_fix skip:", _ie)
    text=fix_lam(text, drop_sun)
    text=jalalah_edge(text)
    if mode=="waqf":
        text=to_waqf(text)
    return text

# ── تحضيرٌ لـ espeak / Piper (espeak داخليًّا) ──────────
# محرّكُ espeak-ng (وهو ما يُفونِمُ لـ Piper) يُتقِنُ من النصّ المشكّلِ
# القياسيِّ وحدَه: اللامَ الشمسيّةَ (الشمس ← aʃʃams) والقمريّةَ (القمر
# ← alqamar) والسكونَ والشدّةَ (رَبّ ← rabː) والمدَّ ولفظَ الجلالة.
# لذا لا نُمارِسُ أيَّ عبثٍ يدويّ: حذفُ لامِ الشمسيّة (drop_sun) يخلّفُ ألفًا
# عاريةً ← صائتٌ طويلٌ زائف (وَال ← waː)، وحيلةُ الجلالة (jalalah_edge) تُرجِعُ
# صورًا مُجرّدةً (لله) تُقرَأُ بلا حركات (llh)، فتُبلعُ الكلمة. النظيفُ أصحّ.
def _fix_bare_ay(text):
    """«أي/أى» غيرَ المشكّلة يقرؤها espeak «آ» (تسقطُ الياء). نمنحُها
    إملاءً مشكّلًا «أَيْ» فتُنطَقُ ay. لا نمسُّ إلا الشكلَ الأعزلَ تمامًا
    (بلا أيّة علامة)، فلا تتأثّرُ «أَيُّ/أَيْ» المشكّلتان."""
    def one(w):
        if not w: return w
        if any(c in MARKS for c in w): return w   # مشكّلة ← اتركها لـ espeak
        core=w.strip("،.؛:!؟«»\"()")
        if core in ("أي","أى","اي","اى"):
            return w.replace(core, "أَيْ", 1)
        return w
    return "\n".join(" ".join(one(w) for w in ln.split(" ")) for ln in text.split("\n"))


def espeak_prepare(text, mode="waqf"):
    text=clean_for_tts(text)            # توحيدُ الرسمِ العثمانيّ + إزالةُ الأرقام
    text=apply_overrides(text)          # قاموسُ تصحيحِ النطق (بن ← ابن، إلخ)
    try:
        import iraab_fix; text=iraab_fix.correct(text)   # أنّ/إنّ + فعل ← سكون
    except Exception as _ie: print("iraab_fix skip:", _ie)
    text=fix_jalalah_lines(text)        # وحّدْ رسمَ الجلالة الشاذّ ← «اللَّهُ» قياسيّة مشكّلة
    text=_fix_bare_ay(text)             # «أي/أى» العزلاء ← «أَيْ» كي لا تسقطَ الياء
    # لا fix_lam ولا drop_sun ولا jalalah_edge: espeak يتولّاها بنفسه أصحّ.
    if mode=="waqf":
        text=to_waqf(text)
    return text

# ── تحضير نصّ gTTS ────────────────────────────────────────────────────
def tts_prepare(text, mode="waqf", gemination=True):
    """
    mode='wasl'    : بالإعراب كاملًا (تعليم النطق النحويّ).
    mode='waqf'    : يُسكَّن آخِرُ كلّ عبارة (طبيعيّ).
    gemination     : تفعيلُ التضعيف (الشدّة) صراحةً في النطق.
    في الحالتين نُصحّح لفظَ الجلالة واللامَ الشمسيّة/القمريّة.
    """
    text=clean_for_tts(text)            # إزالة الأرقام وعلامات الترقيم غير المنطوقة
    text=apply_overrides(text)          # قاموسُ تصحيحِ النطق (الكلماتُ الخاطئة)
    text=fix_jalalah_lines(text)
    text=fix_lam(text)                  # تصحيح اللام الشمسيّة/القمريّة
    text=_tts_jalalah(text)             # لفظ الجلالة ← الصورة القياسيّة «الله»
    if gemination:
        text=expand_shadda(text)        # الشدّة ← حرفان
    if mode=="waqf":
        text=to_waqf(text)
    return text

# ── اللام الشمسيّة والقمريّة ───────────────────────────────────────────
# الشمسيّة: لامُ «الـ» لا تُلفَظ ويُشدَّد الحرفُ بعدها (الشَّمس ← ash-shams).
# القمريّة: تُلفَظ اللامُ ساكنةً (القَمَر ← al-qamar).
SUN=set("تثدذرزسشصضطظلن")
_LETTERS="ابتةثجحخدذرزسشصضطظعغفقكلمنهوىيءأإآؤئ"
# استثناءات: الأسماء الموصولة (التشديد فيها على اللام لا على ما بعدها)،
# وأفعالُ الافتعال التي تاؤها أصليّةٌ لا لامَ تعريفٍ فيها، ولفظُ الجلالة.
REL={"الذي","التي","الذين","اللذان","اللذين","اللتان","اللتين",
     "اللاتي","اللواتي","اللائي","اللتيا","الالي"}
FORM8={"التقى","التقت","التقوا","التقينا","التقيا","التزم","التزمت","التزموا",
       "التفت","التفتت","التفتوا","التحف","التحق","التحقت","التمس","التمست",
       "التمسوا","التأم","التهب","التهبت","التوى","التوت","الترك","التبس",
       "التقاط","التماس","التزام","التفات","التحاق","التهاب","التواء"}

def _units(w):
    u=[]
    for c in w:
        if c in MARKS:
            if u: u[-1][1]+=c
        else: u.append([c,""])
    return u
def _join(u): return "".join(l+m for l,m in u)

def fix_lam_word(w, drop_sun=False):
    sk=_sk(w)
    # جرّب الهيكلَ كما هو، وبعد نزع سابقٍ واحد (و/ف/ب/ك/ل) لالتقاط «والذي، فالتقى»
    cores={sk}
    if len(sk)>1 and sk[0] in "وفبكل": cores.add(sk[1:])
    if sk.startswith("لل"): cores.add("ال"+sk[2:])   # لِلذين ← الذين
    if cores & (REL|FORM8) or sk in JALALAH_MAP: return w
    u=_units(w); n=len(u)
    if n<3: return w
    lets=[x[0] for x in u]
    # موضعُ لام «الـ»: بداية الكلمة (ال…)، أو بعد سابقٍ (وال/فال/بال/كال)، أو (لل…)
    li=None
    if lets[0]=="ا" and lets[1]=="ل": li=1
    elif n>=4 and lets[0] in "وفبك" and lets[1]=="ا" and lets[2]=="ل": li=2
    elif lets[0]=="ل" and lets[1]=="ل": li=1
    if li is None or li+1>=n: return w
    s=li+1                                  # الحرفُ بعد اللام
    if lets[s] in SUN:
        if SHADDA not in u[s][1]: u[s][1]=SHADDA+u[s][1]
        if drop_sun:
            u.pop(li)                       # احذفِ اللامَ نفسَها (espeak/Piper يلفظُها وإلّا)
        else:
            u[li][1]=""                     # اللامُ لا تُلفَظ (edge يكفيه إسكاتُها)
    else:
        if u[li][1]!=SUKUN: u[li][1]=SUKUN  # لامٌ قمريّةٌ ساكنة
    return _join(u)

def fix_lam(text, drop_sun=False):
    out=[]
    for line in text.split("\n"):
        out.append(" ".join(fix_lam_word(x, drop_sun) for x in line.split(" ")))
    return "\n".join(out)

# ── معالجةٌ خاصّةٌ بالنطق التركيبيّ بالوحدات (concatenative) ──────────────
# لفظُ الجلالة يُكتب صورةً صوتيّةً صريحةً (a-l-laa-h) لتُركَّب وحدةً وحدة،
# بدل الصورة المجرّدة «الله» التي تُتهجّى حروفًا في التركيب.
_JAL_PHON={
 "الله":"أَلْلَاه", "لله":"لِلْلَاه", "بالله":"بِلْلَاه",
 "والله":"وَلْلَاه", "فالله":"فَلْلَاه", "تالله":"تَلْلَاه",
 "اللهم":"أَلْلَاهُمْمَ",
}
def jalalah_phon_word(w):
    """صورةٌ صوتيّةٌ صريحةٌ للفظ الجلالة للتركيب بالوحدات، أو None."""
    sk=_sk(w)
    if sk not in _JAL_PHON: return None
    base=_JAL_PHON[sk]
    if sk=="اللهم": return base
    return base+_final_vowel(w)             # حركةُ الإعراب على الهاء

# ── تفخيم/ترقيق لام الجلالة ────────────────────────────────────────────
# القاعدة: تُفخَّم لامُ «الله» بعد فتحةٍ أو ضمّةٍ أو في الابتداء (قالَ اللهُ، هوَ اللهُ)،
# وتُرقَّق بعد كسرةٍ (بسمِ اللهِ، بِاللهِ، لِلَّهِ). صيغُ «لله/بالله» مرقّقةٌ دائمًا،
# و«والله/تالله/فالله» بعد فتحٍ فمفخّمة. تنطبق على القرآن والكلام العاديّ سواءً.
_LIGHT_JAL={"لله","بالله"}
_HEAVY_JAL={"والله","تالله","فالله","اللهم"}
def _last_short_vowel(w):
    for c in reversed(w or ""):
        if c in SHORT or c in TANWIN: return c
    return ""
def is_jalalah(w):
    return _sk(w) in JALALAH_MAP
def jalalah_weight(word, prev=None):
    """أرجِع 'heavy' (مفخّمة) أو 'light' (مرقّقة) للفظ الجلالة حسب ما قبله."""
    sk=_sk(word)
    if sk in _LIGHT_JAL: return "light"
    if sk in _HEAVY_JAL: return "heavy"
    v=_last_short_vowel(prev)
    return "light" if v in (KASRA,KASRATAN) else "heavy"   # الابتداءُ = تفخيم
def jalalah_fallback(weight):
    """صورةٌ حرفيّةٌ احتياطيّةٌ إن لم تتوفّر وحدةُ الجلالة الكاملةُ (بلا تمييزٍ صوتيٍّ للثقل)."""
    return "أَلْلَاهُ" if weight=="heavy" else "لِلْلَاهِ"

def phonetic_form(text, mode="waqf"):
    """الصورةُ النطقيّةُ الكاملةُ المُوحَّدة (للنقحرة والعرض ولمصدرٍ واحدٍ للقواعد):
    لفظُ الجلالة صوتيًّا (أَلْلَاهُ/لِلْلَاهِ)، الألفُ الخنجريّة مدًّا، اللامُ
    الشمسيّةُ/القمريّة، التضعيفُ مفكوكًا، ثمّ الوقفُ/الوصل. تنطبق على القرآن والكلام."""
    text=clean_for_tts(text)
    text=text.replace("ٱ","ا").replace(DAGGER_ALIF,"ا").replace("آ","ءَا").replace("ؤ","ء").replace("ئ","ء")
    text=text.replace("ة","ه" if mode=="waqf" else "ت")
    def line_jal(line):
        out=[]
        for w in line.split(" "):
            j=jalalah_phon_word(w) if w else None
            out.append(j if j is not None else w)
        return " ".join(out)
    text="\n".join(line_jal(l) for l in text.split("\n"))
    text=fix_lam(text)
    text=expand_shadda(text)
    if mode=="waqf":
        text=to_waqf(text)
    return text

def unit_prepare(text, mode="waqf"):
    """تحضيرُ نصٍّ للنطق التركيبيّ بالوحدات: لفظُ الجلالة صوتيًّا، اللامُ
    الشمسيّةُ/القمريّةُ، التضعيفُ، ثمّ الوقفُ/الوصل. يُكمِّله مُقسِّمُ qaida_voice
    الذي يُسقِط الحروفَ الصامتةَ (لامَ الشمسيّة وألفَ الوصل)."""
    text=clean_for_tts(text)
    # توحيدٌ صوتيٌّ لحروفٍ لا وحداتٍ مفردةٍ لها:
    text=text.replace("ٱ","ا").replace(DAGGER_ALIF,"ا")   # الوصلة ٱ→ا والخنجريّة ٰ→ألفُ مدّ
    text=text.replace("آ","ءَا").replace("ؤ","ء").replace("ئ","ء")   # الهمزةُ الحاملةُ ← همزةٌ مفردة
    text=text.replace("ة","ه" if mode=="waqf" else "ت")  # التاءُ المربوطة: هـ وقفًا/ت وصلًا
    def line_jal(line):
        out=[]; prev=None
        for w in line.split(" "):
            if w and is_jalalah(w):
                wt=jalalah_weight(w, prev)          # تفخيمٌ/ترقيقٌ حسب ما قبله
                out.append("JALH" if wt=="heavy" else "JALL")  # علامةُ وحدةٍ كاملة
            else:
                out.append(w)
            if w: prev=w
        return " ".join(out)
    text="\n".join(line_jal(l) for l in text.split("\n"))
    text=fix_lam(text)                       # شمسيّة: لامٌ مجرّدةٌ صامتة + شدّةٌ بعدها
    text=expand_shadda(text)                 # التضعيف ← حرفان
    if mode=="waqf":
        text=to_waqf(text)
    return text

def _case_tail(w):
    """آخِرُ حركةٍ إعرابيّةٍ (قصيرة/تنوين) في الكلمة، أو '' إن لم توجد."""
    t=""
    for c in reversed(w):
        if c in MARKS: t=c+t
        else: break
    for c in t:
        if c in SHORT or c in TANWIN: return c
    return ""

def _tts_jalalah(text):
    """للنطق: نُعيد لفظَ الجلالة إلى صورته المجرّدة القياسيّة «الله» بلا أيّ حركة.
    قواميسُ المحرّكات (espeak داخل Piper، وedge/gTTS) تعرف الكلمةَ المجرّدةَ بالضبط
    فتنطقها صحيحةً بالتفخيم؛ وإضافةُ حركةِ الإعراب أو التشكيلِ الداخليّ تُفشِل
    التطابقَ فتُقرأ بلامٍ خفيفةٍ خطأً. لا نمسّ إلّا ما هيكلُه لفظُ الجلالة
    (فلا تتأثّر «اللَّهَب» ونحوُها)."""
    def fix(w):
        sk=_sk(w)
        if sk not in JALALAH_MAP: return w
        if sk in ("اللهم","اللّهم"): return "اللهم"
        return sk                          # مجرّدةٌ تمامًا: «الله»، «لله»، «بالله»…
    out=[]
    for line in text.split("\n"):
        out.append(" ".join(fix(w) for w in line.split(" ")))
    return "\n".join(out)


def jalalah_edge(text):
    """صيغةُ لفظ الجلالة لـ edge: تفخيمٌ (F1: اللَّاهُ) بعد فتح/ضمّ، وترقيقٌ (الله) بعد كسر،
    مع حركةِ الإعراب، وصيغةِ الوقف عند نهاية العبارة. يُستدعى بعد fix_lam."""
    TAF={"الله":"اللَّاه","والله":"وَاللَّاه","فالله":"فَاللَّاه","تالله":"تَاللَّاه"}
    TARQIQ={"لله","بالله"}
    def one(toks,i):
        t=toks[i]; sk=_sk(t)
        if sk not in JALALAH_MAP: return t
        if sk in ("اللهم","اللّهم"): return "اللهم"
        cv=_final_vowel(t); cv=cv if cv in (FATHA,DAMMA,KASRA) else ""
        nxt=""
        for j in range(i+1,len(toks)):
            if toks[j].strip(): nxt=toks[j].strip(); break
        waqf=(nxt=="") or (nxt[:1] in "،.؛:!؟")
        if sk in TARQIQ: return sk
        if sk in ("والله","فالله","تالله"):
            b=TAF[sk]; return b if waqf else b+(cv or DAMMA)
        prev=None
        for j in range(i-1,-1,-1):
            w=toks[j]
            if not w.strip(): continue
            for ch in reversed(w):
                if ch in (FATHA,DAMMA,KASRA): prev=ch; break
            break
        if prev==KASRA: return "الله"
        b=TAF["الله"]; return b if waqf else b+(cv or DAMMA)
    out=[]
    for line in text.split("\n"):
        toks=line.split(" ")
        out.append(" ".join(one(toks,i) for i in range(len(toks))))
    return "\n".join(out)
