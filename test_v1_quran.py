"""اختبار V1 على 10 آيات قرآنية بسيطة."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.inference import DiacritizationInference
from data.vocab import strip_diacritics, DIACRITIC_CLASSES

# تحميل V1
print("🔄 تحميل V1...")
model = DiacritizationInference("compactshakkil_v1_baseline/best_model.pt")
print(f"✅ جاهز على: {model.device}")
print()

# الآيات مع مصادرها
verses = [
    ("الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ", "الفاتحة:2"),
    ("مَالِكِ يَوْمِ الدِّينِ", "الفاتحة:4"),
    ("إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "الفاتحة:5"),
    ("اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ", "الفاتحة:6"),
    ("قُلْ هُوَ اللَّهُ أَحَدٌ", "الإخلاص:1"),
    ("اللَّهُ الصَّمَدُ", "الإخلاص:2"),
    ("لَمْ يَلِدْ وَلَمْ يُولَدْ", "الإخلاص:3"),
    ("وَلَمْ يَكُنْ لَهُ كُفُوًا أَحَدٌ", "الإخلاص:4"),
    ("قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ", "الفلق:1"),
    ("قُلْ أَعُوذُ بِرَبِّ النَّاسِ", "الناس:1"),
]

# دالّة مقارنة حرف بحرف
def compare_diacritization(original, predicted):
    """يقارن التشكيل حرفًا بحرف. يُرجع (صحيح، خطأ، تفصيل)."""
    orig_pairs = []
    pred_pairs = []
    
    # استخراج (حرف، حركة) لكل حرف عربيّ
    def extract_pairs(text):
        pairs = []
        i = 0
        while i < len(text):
            c = text[i]
            if "\u0621" <= c <= "\u064A" or c in "ىئءؤإأآة":
                diac = ""
                j = i + 1
                while j < len(text) and text[j] in DIACRITIC_CLASSES:
                    diac += text[j]
                    j += 1
                pairs.append((c, diac))
                i = j
            else:
                i += 1
        return pairs
    
    orig_pairs = extract_pairs(original)
    pred_pairs = extract_pairs(predicted)
    
    correct = 0
    wrong = 0
    errors = []
    
    for i, ((oc, od), (pc, pd)) in enumerate(zip(orig_pairs, pred_pairs)):
        if oc == pc:
            if od == pd:
                correct += 1
            else:
                wrong += 1
                errors.append(f"{oc}: أصل={repr(od)} vs تنبّؤ={repr(pd)}")
    
    return correct, wrong, errors


# التشغيل
total_correct = 0
total_wrong = 0
all_errors = []

print("═" * 70)
print("اختبار V1 على 10 آيات قرآنية")
print("═" * 70)

for i, (verse_correct, source) in enumerate(verses, 1):
    stripped = strip_diacritics(verse_correct)
    predicted = model.diacritize(stripped)
    
    correct, wrong, errors = compare_diacritization(verse_correct, predicted)
    total = correct + wrong
    der = 100 * wrong / total if total > 0 else 0
    
    total_correct += correct
    total_wrong += wrong
    
    status = "OK" if der == 0 else ("Poor" if der > 30 else "Fair")
    print(f"\n[{i}] {source}")
    print(f"    الأصل:    {verse_correct}")
    print(f"    المُدخَل:  {stripped}")
    print(f"    التنبّؤ:  {predicted}")
    print(f"    الدقّة:   {correct}/{total} صحيح | DER={der:.1f}% [{status}]")
    if errors and len(errors) <= 5:
        for e in errors[:3]:
            print(f"       خطأ: {e}")

print()
print("═" * 70)
overall_total = total_correct + total_wrong
overall_der = 100 * total_wrong / overall_total if overall_total > 0 else 0
print(f"الإجماليّ: {total_correct}/{overall_total} صحيح")
print(f"DER الكلّيّ = {overall_der:.2f}%")
print(f"مقارنة: V1 على Tashkeela test = DER 2.38%")
print("═" * 70)
