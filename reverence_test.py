# -*- coding: utf-8 -*-
"""
reverence_test.py — تجربة موسّعة لنظام Reverence-Aware على ~300 آية.

يقيس:
  1) تغطية الاسترداد: كم آية تُوجَّه إلى "استرداد المصحف".
  2) دقّة الاسترداد: هل المخرَج = الآية الأصلية حرفيًّا.
  3) متانة التطبيع: نفس الآيات بألف مجرّدة (أ إ آ → ا) — هل تُسترَدّ.
  4) الإنذارات الكاذبة: نصوص عامّة — هل تُوجَّه خطأً للقرآن.
"""
import sys
from pathlib import Path
import torch

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import reverence_aware as ra   # نعيد استخدام الموجّه المُصحَّح

BARE = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٰ": ""})


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️  الجهاز: {device}\n")
    system = ra.ReverenceAware(ra.V2_CKPT, ra.V3_CKPT, ra.QURAN_PATH, device)

    lines = [l.strip() for l in Path(ra.QURAN_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
    step = max(1, len(lines) // 300)
    sample = lines[::step][:300]
    print(f"عيّنة الاختبار: {len(sample)} سطرًا (كل {step} سطر)\n")

    def run(transform, title):
        retr = exact = v3 = v2 = 0
        mismatches = []
        for verse in sample:
            inp = ra.strip_diacritics(verse)
            if transform:
                inp = inp.translate(BARE)
            r = system.process(inp)
            if r["route"].startswith("استرداد"):
                retr += 1
                if r["output"] == verse:
                    exact += 1
                else:
                    mismatches.append((verse, r["output"]))
            elif "V3" in r["route"]:
                v3 += 1
            else:
                v2 += 1
        n = len(sample)
        print(f"── {title} ──")
        print(f"   استرداد: {retr}/{n} ({100*retr//n}%)  |  V3: {v3}  |  V2: {v2}")
        print(f"   مطابقة الأصل حرفيًّا: {exact}/{retr} من المستردّة")
        if mismatches:
            print(f"   ⚠️ عدم تطابق ({len(mismatches)}): مثال:")
            for o, g in mismatches[:2]:
                print(f"       أصل : {o[:60]}")
                print(f"       ناتج: {g[:60]}")
        print()

    print("=" * 70)
    print("اختبار التغطية على ~300 آية")
    print("=" * 70 + "\n")
    run(False, "المدخل بالرسم الأصليّ (بعد تجريد الحركات)")
    run(True,  "المدخل بألف مجرّدة (اختبار التطبيع)")

    # الإنذارات الكاذبة
    general = [
        "ذهب الطالب الى المدرسة صباحا",
        "اجتمع مجلس الوزراء لمناقشة الميزانية",
        "تطور الذكاء الاصطناعي بسرعة كبيرة",
        "كتب الباحث مقالة عن اللغة العربية",
        "سافر الفريق الى المؤتمر الدولي",
        "ارتفعت اسعار النفط هذا الاسبوع",
        "درس الطلاب قواعد النحو والصرف",
        "افتتح المعرض ابوابه للزوار",
    ]
    fp = sum(1 for g in general if system.process(g)["route"].startswith("استرداد"))
    print("=" * 70)
    print(f"الإنذارات الكاذبة على {len(general)} نصوص عامّة: {fp} (المثاليّ = 0)")
    print("=" * 70)


if __name__ == "__main__":
    main()
