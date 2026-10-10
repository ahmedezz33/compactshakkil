# -*- coding: utf-8 -*-
"""
reverence_test2.py — تجربة موسّعة أعمق لنظام Reverence-Aware (~300 آية).

ستّة اختبارات تكشف حدود الموجّه الحقيقية:
  1) آيات كاملة (الرسم الأصليّ)      → توقّع: استرداد + مطابقة.
  2) آيات كاملة بألف مجرّدة          → توقّع: استرداد (متانة التطبيع).
  3) تشويش إملائيّ (ة→ه، ى→ي)        → يكشف فجوة التطبيع الحالية.
  4) مقاطع جزئية (نصف الآية)         → توقّع: V3 (لا استرداد كاذب).
  5) آية داخل جملة حاملة             → يكشف حدّ كشف الآيات المضمّنة.
  6) نصوص عامّة                      → توقّع: صفر إنذار كاذب.
"""
import sys
from pathlib import Path
import torch
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import reverence_aware as ra

BARE = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٰ": ""})
ORTHO = str.maketrans({"ة": "ه", "ى": "ي"})   # تشويش شائع


def route_of(system, text):
    r = system.process(text)
    if r["route"].startswith("استرداد"): return "استرداد", r["output"]
    if "V3" in r["route"]: return "V3", r["output"]
    return "V2", r["output"]


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️  الجهاز: {device}\n")
    system = ra.ReverenceAware(ra.V2_CKPT, ra.V3_CKPT, ra.QURAN_PATH, device)
    lines = [l.strip() for l in Path(ra.QURAN_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
    step = max(1, len(lines) // 300)
    sample = [l for l in lines[::step]][:300]
    n = len(sample)
    print(f"عيّنة: {n} آية\n" + "=" * 66)

    def tally(items, transform, label, expect):
        c = {"استرداد": 0, "V3": 0, "V2": 0}
        exact = 0
        for verse in items:
            inp = ra.strip_diacritics(verse)
            inp = transform(inp) if transform else inp
            route, out = route_of(system, inp)
            c[route] += 1
            if route == "استرداد" and out == verse:
                exact += 1
        print(f"── {label}")
        print(f"   استرداد={c['استرداد']}  V3={c['V3']}  V2={c['V2']}  (المتوقّع: {expect})")
        if c["استرداد"]:
            print(f"   مطابقة الأصل: {exact}/{c['استرداد']}")
        print()

    # 1 و 2
    tally(sample, None, "آيات كاملة (رسم أصليّ)", "استرداد=كلّها")
    tally(sample, lambda s: s.translate(BARE), "آيات كاملة بألف مجرّدة", "استرداد=كلّها")
    # 3: تشويش إملائيّ
    tally(sample, lambda s: s.translate(BARE).translate(ORTHO), "تشويش إملائيّ (ة→ه، ى→ي)", "يكشف فجوة التطبيع")
    # 4: مقاطع جزئية (نصف الآية)
    def half(s):
        w = s.split()
        return " ".join(w[:max(3, len(w) // 2)])
    tally(sample, half, "مقاطع جزئية (نصف الآية)", "V3 غالبًا، لا استرداد كاذب")
    # 5: آية داخل جملة حاملة
    tally(sample, lambda s: "قال تعالى " + s + " صدق الله العظيم",
          "آية داخل جملة حاملة", "يكشف حدّ الكشف المضمّن")

    # 6: نصوص عامّة
    general = [
        "ذهب الطالب الى المدرسة صباحا", "اجتمع مجلس الوزراء لمناقشة الميزانية",
        "تطور الذكاء الاصطناعي بسرعة كبيرة", "كتب الباحث مقالة عن اللغة العربية",
        "سافر الفريق الى المؤتمر الدولي", "ارتفعت اسعار النفط هذا الاسبوع",
        "درس الطلاب قواعد النحو والصرف", "افتتح المعرض ابوابه للزوار",
        "اللغة العربية غنية بالمفردات والتراكيب", "الحمد لله على كل حال دائما",
    ]
    fp = sum(1 for g in general if route_of(system, g)[0] == "استرداد")
    print("=" * 66)
    print(f"الإنذارات الكاذبة على {len(general)} نصوص عامّة: {fp} (المثاليّ = 0)")
    print("=" * 66)


if __name__ == "__main__":
    main()
