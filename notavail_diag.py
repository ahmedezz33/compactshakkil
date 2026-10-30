# -*- coding: utf-8 -*-
"""تشريحُ فئةِ «الصوابُ غيرُ متاحٍ في CAMeL»: إلى ماذا تؤولُ فعلًا؟
لكلِّ خطأٍ من هذه الفئةِ نُصنّفُه إلى:
  1) ترقيم/رمز (تقطيع)        — كلمةٌ فيها محرفٌ غيرُ عربيّ (نقطة/نقطتان/قوس/رقم/لاتينيّ)
  2) مجهولةٌ لـCAMeL (علمٌ/أجنبيّ) — المحلّلُ لا يعرفُ الكلمةَ أصلًا (صفرُ تحليلات)
  3) ذهبيٌّ ناقصُ التشكيل       — الذهبيُّ نفسُه فيه حرفٌ داخليٌّ عارٍ (ليس خطأَ BERT)
  4) اصطلاح (تنوين/شدّة/سكون)   — نفسُ الرسمِ، ويتطابقان بعدَ إسقاطِ التنوين/الشدّة/السكون
  5) خلافٌ حقيقيّ (نفسُ الرسم) — نفسُ الرسمِ لكنْ حركةٌ مختلفةٌ فعلًا (خطأٌ محتملٌ حقيقيّ)
  6) رسمٌ مختلف               — رسمٌ مختلفٌ وCAMeL يعرفُه (علمٌ/تقطيع/صورةٌ أخرى)
"""
import sys, os, random, re
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
N=int(os.environ.get("BENCH_N","400"))
print(f"… تحميل النموذج + محلّل CAMeL (عيّنة={N})")
import app_teach as A
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_snap import _norm, _strip
from data.vocab_v2 import strip_diacritics, split_letters_and_diacritics
an=Analyzer(MorphologyDB.builtin_db())

_DIAC=set("ًٌٍَُِّْٰ")
_TST=set("ًٌٍّْٰ")              # تنوين+شدّة+سكون+خنجريّة
def _letters(s): return "".join(c for c in s if c not in _DIAC)
def _rasm(s): return _norm(_letters(s))                 # هيكلُ الحروفِ المطبَّع
def _novowel_conv(s): return _norm("".join(c for c in s if c not in _TST))  # يُبقي الحركاتِ القصيرة
def _has_nonarabic(s): return bool(re.search(r"[^؀-ۿ]", s))
def _gold_internally_bare(g):
    try: L,D=split_letters_and_diacritics(g)
    except Exception: return False
    return any(D[i]==0 for i in range(max(len(D)-1,0)))

lines=[l.strip() for l in open("data/processed/test.txt",encoding="utf-8") if l.strip()]
random.Random(13).shuffle(lines); lines=lines[:N]

buckets={"ترقيم/رمز (تقطيع)":[], "مجهولةٌ لـCAMeL (علم/أجنبيّ)":[],
         "ذهبيٌّ ناقصُ التشكيل":[], "اصطلاح (تنوين/شدّة/سكون)":[],
         "خلافٌ حقيقيّ (نفسُ الرسم)":[], "رسمٌ مختلف (علم/تقطيع)":[]}
err=0; notavail=0
for gold in lines:
    pb=A.INF.diacritize(strip_diacritics(gold))
    gws=gold.split(" "); pws=pb.split(" ")
    if len(gws)!=len(pws): continue
    for gw,pw in zip(gws,pws):
        if _norm(gw)==_norm(pw): continue
        err+=1
        try: analyses=an.analyze(_strip(pw))
        except Exception: analyses=[]
        norms={_norm(a.get('diac','')) for a in analyses}
        if _norm(gw) in norms:      # صوابُه متاحٌ → ليس من فئتِنا
            continue
        notavail+=1
        # تصنيف (بأولويّة)
        if _has_nonarabic(gw) or _has_nonarabic(pw):
            k="ترقيم/رمز (تقطيع)"
        elif not analyses:
            k="مجهولةٌ لـCAMeL (علم/أجنبيّ)"
        elif _gold_internally_bare(gw):
            k="ذهبيٌّ ناقصُ التشكيل"
        elif _rasm(gw)==_rasm(pw):
            k="اصطلاح (تنوين/شدّة/سكون)" if _novowel_conv(gw)==_novowel_conv(pw) else "خلافٌ حقيقيّ (نفسُ الرسم)"
        else:
            k="رسمٌ مختلف (علم/تقطيع)"
        buckets[k].append((gw,pw))

print("="*64)
print(f"إجماليّ أخطاء BERT: {err}   |   منها «غيرُ متاحٍ في CAMeL»: {notavail}")
print("="*64)
for k,v in sorted(buckets.items(), key=lambda kv:-len(kv[1])):
    pc_err  = 100*len(v)/max(err,1)
    pc_na   = 100*len(v)/max(notavail,1)
    print(f"\n▸ {k}: {len(v)}  ({pc_na:.1f}% من غير المتاح · {pc_err:.1f}% من كلّ الأخطاء)")
    for gw,pw in v[:9]:
        print(f"      ذهبيّ: {gw:<18} | BERT: {pw}")
print("\n"+"="*64)
# ملخّصٌ: كم منها خطأٌ حقيقيٌّ فعلًا؟
real = len(buckets["خلافٌ حقيقيّ (نفسُ الرسم)"]) + len(buckets["مجهولةٌ لـCAMeL (علم/أجنبيّ)"]) + len(buckets["رسمٌ مختلف (علم/تقطيع)"])
noise= len(buckets["ترقيم/رمز (تقطيع)"]) + len(buckets["ذهبيٌّ ناقصُ التشكيل"]) + len(buckets["اصطلاح (تنوين/شدّة/سكون)"])
print(f"ضجيجٌ (اصطلاح/ذهبيّ ناقص/ترقيم): {noise}  ({100*noise/max(notavail,1):.1f}% من غير المتاح)")
print(f"خطأٌ حقيقيٌّ محتمل (رسم مختلف/مجهولة/خلاف حقيقيّ): {real}  ({100*real/max(notavail,1):.1f}% من غير المتاح · {100*real/max(err,1):.1f}% من كلّ الأخطاء)")
print("="*64)
