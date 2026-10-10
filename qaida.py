# -*- coding: utf-8 -*-
"""
qaida.py — دروسُ القاعدة النورانيّة (مبنيّةٌ محلّيًّا، بلا ملفّاتٍ محفوظة الحقوق).
تسلسلٌ تعليميٌّ معروف: الحروف المفردة، فواتح السور، الحركات، التنوين، المدّ،
اللين، السكون، الشدّة. كلُّ درسٍ قائمةُ عناصرَ تُحلَّل وتُنطَق داخل التطبيق.
"""
from pronounce import FATHA, KASRA, DAMMA, SUKUN, FATHATAN, KASRATAN, DAMMATAN, SHADDA

# الحروف الهجائيّة بترتيب القاعدة النورانيّة (مع تمييز الهمزة والألف و«لا»)
HURUF=["ا","ب","ت","ث","ج","ح","خ","د","ذ","ر","ز","س","ش","ص","ض","ط","ظ",
       "ع","غ","ف","ق","ك","ل","م","ن","هـ","و","لا","ي","ء"]
# حروفٌ صالحةٌ لتوليد المقاطع (نستثني ا، لا، هـ من التوليد الآليّ لاختلاف رسمها)
GEN=["ب","ت","ث","ج","ح","خ","د","ذ","ر","ز","س","ش","ص","ض","ط","ظ",
     "ع","غ","ف","ق","ك","ل","م","ن","ه","و","ي","ء"]

# وحداتٌ مفردةٌ (تُختار وتُسجَّل وتُركَّب وحدةً وحدة)
# الهمزةُ على الألف حرفٌ كاملٌ في كلّ الأقسام (الكسرُ يُكتب «إ»، والمدُّ «آ»).
# لا شدّةَ على الهمزة (لا تُضعَّف)، فتُستثنى من درس الشدّة وحدها.
A="أ"; I="إ"
HAMZA_HAR =[A+FATHA, A+DAMMA, I+KASRA]                 # أَ أُ إِ
HAMZA_TAN =[A+FATHATAN, A+DAMMATAN, I+KASRATAN]        # أً أٌ إٍ
HAMZA_SUK =[A+SUKUN]                                    # أْ
HAMZA_MADD=["آ", A+DAMMA+"و", I+KASRA+"ي"]             # آ أُو إِي
HAMZA_LEEN=[A+FATHA+"و"+SUKUN, A+FATHA+"ي"+SUKUN]     # أَوْ أَيْ

def _flat(fn):
    out=[];
    for c in GEN: out+=fn(c)
    return out
def _harakat(): return HAMZA_HAR  + _flat(lambda c:[c+FATHA, c+DAMMA, c+KASRA])
def _tanwin():  return HAMZA_TAN  + _flat(lambda c:[c+FATHATAN, c+DAMMATAN, c+KASRATAN])
def _madd():    return HAMZA_MADD + _flat(lambda c:[c+FATHA+"ا", c+DAMMA+"و", c+KASRA+"ي"])
def _leen():    return HAMZA_LEEN + _flat(lambda c:[c+FATHA+"وْ", c+FATHA+"يْ"])
def _sukun():   return HAMZA_SUK  + [c+SUKUN for c in GEN]
def _shadda():  return _flat(lambda c:[c+SHADDA+FATHA, c+SHADDA+DAMMA, c+SHADDA+KASRA])
def _shadda_madd():   return _flat(lambda c:[c+SHADDA+FATHA+"ا", c+SHADDA+DAMMA+"و", c+SHADDA+KASRA+"ي"])
def _shadda_tanwin(): return _flat(lambda c:[c+SHADDA+FATHATAN, c+SHADDA+DAMMATAN, c+SHADDA+KASRATAN])
# القلقلة: (قطب جد) ساكنةً. الاستعلاء (التفخيم): خصّ ضغط قظ. الغنّة: نّ مّ.
QALQALA=[c+SUKUN for c in "قطبجد"]
ISTILA =[c+FATHA for c in "خصضغطقظ"]
GHUNNA =[c+SHADDA+v for c in "نم" for v in (FATHA,DAMMA,KASRA)]
# أحكامٌ (أمثلةٌ للقراءة بـ«انطق بالوحدات») — نونٌ ساكنةٌ وتنوينٌ وميمٌ ساكنة
NOON_AHKAM=["مِنْ هَادٍ","يَنْأَوْنَ","مَنْ يَقُولُ","مِنْ وَالٍ","مِنْ بَعْدِ","أَنْبِئْهُمْ",
            "أَنْتُمْ","مِنْ نُورٍ","لَهُمْ مَا","تَرْمِيهِمْ بِ"]
MADD_TYPES=["قَالَ نُوحِيهَا","جَاءَ","فِي أَنْفُسِكُمْ","الْحَاقَّةُ","وَلَا الضَّالِّينَ",
            "نَسْتَعِينُ","الم","ص","ن","كهيعص"]

MUQATTA=["الم","الر","المص","المر","كهيعص","طه","طسم","طس","يس","ص","حم","عسق",
         "ق","ن"]

LESSONS=[
 {"t":"١ — الحروف المفردة","n":"انطق كلَّ حرفٍ باسمه ومخرجه.","items":HURUF},
 {"t":"٢ — الحروف المقطّعة (فواتح السور)","n":"تُنطَق بأسماء حروفها.","items":MUQATTA},
 {"t":"٣ — الحركات (فتحة/ضمّة/كسرة)","n":"الحرفُ مع الحركات الثلاث.","items":_harakat()},
 {"t":"٤ — التنوين","n":"فتحتان/ضمّتان/كسرتان = نونٌ ساكنةٌ لفظًا.","items":_tanwin()},
 {"t":"٥ — المدّ (ا و ي)","n":"إشباعُ الحركة بحرف مدٍّ مجانس.","items":_madd()},
 {"t":"٦ — اللين","n":"واوٌ وياءٌ ساكنتان بعد فتح.","items":_leen()},
 {"t":"٧ — السكون","n":"حرفٌ ساكنٌ لا حركة عليه.","items":_sukun()},
 {"t":"٨ — الشدّة","n":"حرفان: ساكنٌ فمتحرّك (تضعيف).","items":_shadda()},
 {"t":"٩ — الشدّة مع المدّ","n":"تضعيفٌ ثمّ إشباع: بَّا بُّو بِّي.","items":_shadda_madd()},
 {"t":"١٠ — الشدّة مع التنوين","n":"تضعيفٌ في آخِر الكلمة منوَّنًا.","items":_shadda_tanwin()},
 {"t":"١١ — القلقلة","n":"حروف (قطب جد) الساكنة تُقلقَل (اهتزازُ المخرج).","items":QALQALA},
 {"t":"١٢ — التفخيم (حروف الاستعلاء)","n":"خصَّ ضغطٍ قظ تُفخَّم؛ وكذا الراء ولام الجلالة بعد فتحٍ/ضمّ.","items":ISTILA},
 {"t":"١٣ — الغنّة (النون والميم المشدّدتان)","n":"غنّةٌ بمقدار حركتين: نّ مّ.","items":GHUNNA},
 {"t":"١٤ — أحكام النون الساكنة والتنوين","n":"إظهار/إدغام/إقلاب/إخفاء — اقرأ الأمثلة بـ«انطق بالوحدات».","items":NOON_AHKAM},
 {"t":"١٥ — المدود بأنواعها","n":"طبيعيّ/متّصل/منفصل/لازم/عارض — أمثلةٌ للقراءة.","items":MADD_TYPES},
]

def titles(): return [L["t"] for L in LESSONS]
def by_title(t):
    for L in LESSONS:
        if L["t"]==t: return L
    return LESSONS[0]

# ── خطّةُ التسجيل مرتّبةً حسب الأولويّة (تُطابق قائمة التسجيل) ──
def record_plan():
    """أرجِع [(رمز, عنوان, [وحدات], أساسيّ؟)] بترتيب الأولويّة للقراءة."""
    return [
      ("أ","حروف المدّ مفردةً", ["ا","و","ي","آ"], True),
      ("ب","الحركات الثلاث", HAMZA_HAR + [c+v for c in GEN for v in (FATHA,DAMMA,KASRA)], True),
      ("ج","السكون", HAMZA_SUK + [c+SUKUN for c in GEN], True),
      ("د","الشدّة مع الحركة", [c+SHADDA+v for c in GEN for v in (FATHA,DAMMA,KASRA)], True),
      ("هـ","التنوين", HAMZA_TAN + [c+t for c in GEN for t in (FATHATAN,DAMMATAN,KASRATAN)], True),
      ("و","أسماء الحروف مفردةً (اختياريّ)", list(GEN), False),
    ]
