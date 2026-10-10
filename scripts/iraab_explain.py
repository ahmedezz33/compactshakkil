# -*- coding: utf-8 -*-
"""
iraab_explain.py — شرحٌ نحويٌّ تقديريّ (النسخة 2، أغنى قواعد).

الحركةُ يقينيّةٌ من النموذج؛ الدورُ تقديريٌّ بقواعدَ نحويّةٍ مبسّطة (يُعرَض بـ«غالبًا»).
يغطّي: الفاعل، المفعول به، المبتدأ والخبر، اسمَ/خبرَ إنّ، اسمَ/خبرَ كان،
الاسمَ المجرور والمضافَ إليه، النعت، المعطوف، المنادى، الظرف، والأسماءَ المبنيّة.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import split_letters_and_diacritics, strip_diacritics

NOM={3,7,11}; ACC={1,5,9}; JAR={2,6,10}
def family(c):
    if c in NOM: return "مرفوع"
    if c in ACC: return "منصوب"
    if c in JAR: return "مجرور"
    return "مبنيّ"

def final_class(word):
    L,C=split_letters_and_diacritics(word)
    if not C: return 0
    c=int(C[-1])
    # «...ًا/ًى»: تنوينُ الفتح على الحرف قبل الألف، فخذْ حركتَه
    if c==0 and len(C)>=2 and L and L[-1] in ("ا","ى"): return int(C[-2])
    return c

# ── مجموعاتٌ نحويّة ──────────────────────────────────────────────────
PREP={"من","إلى","الى","عن","على","علي","في","حتى","منذ","مذ","حاشا","عدا","خلا","رب","كي"}
INNA={"إن","إنّ","ان","أنّ","أن","كأن","كأنّ","لكن","لكنّ","ليت","لعل","لعلّ"}
KANA={"كان","أصبح","اصبح","أمسى","امسى","أضحى","اضحى","ظل","ظلّ","بات","صار","ليس",
      "مازال","مابرح","مافتئ","ماانفك","دام","مادام"}
NASB={"أن","لن","كي","إذن","اذن"}                 # نواصب المضارع
JAZM={"لم","لما","لمّا","لا"}                       # جوازم (تقريبيّ)
ATF={"و","ف","ثم","ثمّ","أو","أم","بل","لكن"}        # حروف العطف (المنفصلة)
NIDA={"يا","أيا","هيا"}
ZARF={"عند","لدى","بعد","قبل","تحت","فوق","بين","أمام","خلف","وراء","حين","يوم",
      "ليلة","صباح","مساء","مع","دون","حول","وسط","إثر","عقب","ساعة","لحظة","نحو","تلقاء"}
DEMON={"هذا","هذه","ذلك","تلك","هؤلاء","أولئك","هذان","هاتان","ذاك"}
RELAT={"الذي","التي","الذين","اللذان","اللتان","اللذين","اللتين","اللاتي","اللواتي","اللائي","ما","من"}
PRON={"هو","هي","هم","هن","هما","أنا","نحن","أنت","أنتم","أنتن","أنتما","إياك","إياه"}
MABNI=DEMON|RELAT|PRON|{"هنا","هناك","هنالك","حيث","الآن","أمس","كيف","متى","أين","كم","أيان","أنى","إذ","إذا","لولا"}

# أفعالٌ ماضيةٌ شائعة (كشفُ الماضي صرفيًّا صعبٌ بلا معجم)
PAST={"قال","كان","ذهب","جاء","رأى","خلق","قرأ","كتب","سمع","علم","عَلِم","وجد","أخذ",
      "فعل","نصر","ضرب","دخل","خرج","جلس","قام","نام","أكل","شرب","فتح","أغلق","بدأ",
      "انتهى","درس","لعب","عمل","صنع","بنى","حمل","رفع","وضع","ترك","طلب","سأل","أجاب",
      "أرسل","بعث","نزل","صعد","مشى","ركب","وصل","رجع","عاد","بقي","مات","عاش","ولد"}

def _sk(w): return strip_diacritics(w)
# كشفُ المضارع: نقصره على بادئة الياء (الأقلّ التباسًا بالأسماء) بطولٍ ≥4 وبلا «ال»،
# مع استثناء أسماءٍ شائعةٍ تبدأ بالياء. هذا يتجنّب عدَّ «نور، تمر، أحمد» أفعالًا.
_Y_NOUNS={"يمين","يسار","يقين","يتيم","يمامة","ياقوت","يانصيب"}
def is_present(sk):
    return sk.startswith("ي") and len(sk)>=4 and not sk.startswith("ال") and sk not in _Y_NOUNS
def is_verb(sk):
    if sk in INNA or sk in KANA or sk in MABNI: return False
    return is_present(sk) or sk in PAST

def explain(words):
    """أرجِع لكلّ كلمة: dict(word, حركة, دور, سبب)."""
    out=[]; prev=None; seen_verb=False; seen_kana=False; seen_inna=False
    last_noun_fam=None
    n=len(words)
    for i,w in enumerate(words):
        sk=_sk(w); pv=_sk(prev) if prev else ""
        fam=family(final_class(w)); role=""; reason=""
        nxt=_sk(words[i+1]) if i+1<n else ""

        # 1) الحروف والأدوات
        if sk in NIDA:
            role="حرف نداء"; reason="أداةُ نداء"
        elif sk in INNA:
            role="حرف ناسخ"; reason="من أخوات «إنّ» (ينصب الاسمَ ويرفع الخبر)"; seen_inna=True
        elif sk in KANA:
            role="فعل ناسخ"; reason="من أخوات «كان» (يرفع الاسمَ وينصب الخبر)"; seen_kana=True
        elif sk in PREP:
            role="حرف جرّ"; reason="يَجُرّ ما بعده"
        elif sk in NASB and not is_present(sk):
            role="حرف نصب"; reason="ينصب الفعلَ المضارع"
        elif sk in JAZM:
            role="حرف جزم/نفي"; reason="أداةٌ جازمة/نافية"
        elif sk in ATF and len(sk)<=3 and fam=="مبنيّ":
            role="حرف عطف"; reason="يَعطِف ما بعده على ما قبله"
        # 2) الأفعال
        elif is_verb(sk):
            seen_verb=True
            role="فعل"; reason=("فعلٌ مضارع" if is_present(sk) else "فعلٌ ماضٍ")+" (غالبًا)"
        # 3) الأسماء المبنيّة
        elif sk in DEMON:
            role="اسم إشارة"; reason="مبنيٌّ في محلّ إعراب"
        elif sk in RELAT and fam=="مبنيّ":
            role="اسم موصول"; reason="مبنيٌّ في محلّ إعراب"
        elif sk in PRON:
            role="ضمير"; reason="مبنيٌّ في محلّ إعراب"
        # 4) الأسماء المُعرَبة — حسب حركة الآخِر والسياق
        elif fam=="مجرور":
            atf=(pv in ATF) or sk[:1] in ("و","ف")     # عطفٌ منفصلٌ أو متّصلٌ بالكلمة
            if pv in PREP: role="اسم مجرور"; reason=f"مسبوقٌ بحرف الجرّ «{prev}»"
            elif atf and last_noun_fam=="مجرور": role="معطوف"; reason="مجرورٌ معطوفٌ على مجرورٍ قبله"
            elif last_noun_fam=="مجرور" and _is_noun(pv): role="نعت"; reason="مجرورٌ يتبع مجرورًا قبله (صفة)"
            else: role="مضاف إليه"; reason="اسمٌ مجرورٌ بعد اسم (إضافة)"
            last_noun_fam="مجرور"
        elif fam=="منصوب":
            atf=(pv in ATF) or sk[:1] in ("و","ف")
            if pv in NIDA: role="منادى"; reason=f"بعد أداة النداء «{prev}»"
            elif pv in INNA: role="اسم إنّ"; reason=f"بعد «{prev}» (اسمها منصوب)"
            elif sk in ZARF: role="ظرف"; reason="مفعولٌ فيه (ظرف زمان/مكان)"
            elif atf and last_noun_fam=="منصوب": role="معطوف"; reason="منصوبٌ معطوفٌ على منصوبٍ قبله"
            elif (pv in KANA) or (seen_kana and last_noun_fam=="مرفوع"): role="خبر كان"; reason="منصوبٌ خبرًا لكان أو أخواتها"
            elif last_noun_fam=="منصوب" and _is_noun(pv): role="نعت"; reason="منصوبٌ يتبع منصوبًا قبله (صفة)"
            elif seen_verb: role="مفعول به"; reason="اسمٌ منصوبٌ بعد فعل"
            else: role="منصوب"; reason="مفعولٌ به/خبرُ كان/اسمُ إنّ (غالبًا)"
            last_noun_fam="منصوب"
        elif fam=="مرفوع":
            atf=(pv in ATF) or sk[:1] in ("و","ف")
            if pv in KANA: role="اسم كان"; reason=f"بعد «{prev}» (اسمها مرفوع)"
            elif seen_inna and last_noun_fam=="منصوب": role="خبر إنّ"; reason="مرفوعٌ خبرًا لإنّ بعد اسمها"
            elif is_verb(pv): role="فاعل"; reason="اسمٌ مرفوعٌ بعد فعل"
            elif atf and last_noun_fam=="مرفوع": role="معطوف"; reason="مرفوعٌ معطوفٌ على مرفوعٍ قبله"
            elif i==0: role="مبتدأ"; reason="اسمٌ مرفوعٌ في بداية الجملة"
            elif last_noun_fam=="مرفوع" and _is_noun(pv): role="نعت/خبر"; reason="مرفوعٌ يتبع مرفوعًا قبله (صفة أو خبر)"
            else: role="مرفوع"; reason="فاعل/مبتدأ/خبر (غالبًا)"
            last_noun_fam="مرفوع"
        else:
            role="مبنيّ/ساكن"; reason="لا إعراب ظاهر (حرف/مبنيّ/وقف)"

        out.append({"word":w,"حركة":fam,"دور":role,"سبب":reason})
        prev=w
    return out

def _is_noun(sk):
    return not (sk in PREP or sk in INNA or sk in KANA or sk in NASB or sk in JAZM
                or sk in ATF or sk in NIDA or is_verb(sk))

if __name__=="__main__":
    tests=[
        "ذهب الطالبُ المجتهدُ إلى المدرسةِ",
        "إنّ العلمَ نورٌ",
        "كان الجوُّ جميلًا",
        "يا محمدُ اجتهدْ",
        "قرأ محمدٌ الكتابَ والمجلةَ",
        "جلس التلميذُ عندَ البابِ",
    ]
    for t in tests:
        print("▌",t)
        for r in explain(t.split()):
            print(f"   {r['word']:12} {r['حركة']:7} {r['دور']:12} — {r['سبب']}")
        print()
