"""اختبار V1 على القرآن مع تقييم صحيح."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.inference import DiacritizationInference
from data.vocab import strip_diacritics

print("Loading V1...")
model = DiacritizationInference("compactshakkil_v1_baseline/best_model.pt")
print("Ready\n")

# مجموعة كل رموز التشكيل (بما فيها الأليف الصغيرة)
DIAC_ALL = set("\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0670")

def is_arabic_letter_extended(c):
    """حرف عربيّ (يشمل الأليف الصغيرة معالجة خاصّة)."""
    return ("\u0621" <= c <= "\u064A") or c in "ىئءؤإأآة"

def extract_letter_diac_pairs(text):
    """يستخرج (حرف، كل الحركات بعده) — أدقّ من السابق."""
    pairs = []
    i = 0
    while i < len(text):
        c = text[i]
        if is_arabic_letter_extended(c):
            diacs = ""
            j = i + 1
            while j < len(text) and text[j] in DIAC_ALL:
                diacs += text[j]
                j += 1
            pairs.append((c, diacs))
            i = j
        else:
            i += 1
    return pairs

def compare_strict(original, predicted):
    """مقارنة صارمة — تعدّ كل خطأ."""
    orig = extract_letter_diac_pairs(original)
    pred = extract_letter_diac_pairs(predicted)
    
    n = min(len(orig), len(pred))
    correct = 0
    wrong = 0
    error_details = []
    
    for i in range(n):
        oc, od = orig[i]
        pc, pd = pred[i]
        if oc != pc:
            continue  # اختلاف الحرف نفسه (نادر)
        if od == pd:
            correct += 1
        else:
            wrong += 1
            error_details.append(f"{oc}: [{od}] -> [{pd}]")
    
    # فرق العدد
    length_diff = abs(len(orig) - len(pred))
    return correct, wrong, error_details, length_diff

verses = [
    ("اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ", "البقرة:255"),
    ("وَإِذَا ضَرَبْتُمْ فِي الْأَرْضِ فَلَيْسَ عَلَيْكُمْ جُنَاحٌ", "النساء:101"),
    ("وَقُلْنَا يَا آدَمُ اسْكُنْ أَنْتَ وَزَوْجُكَ الْجَنَّةَ", "البقرة:35"),
    ("وَاصْطَنَعْتُكَ لِنَفْسِي", "طه:41"),
    ("إِنَّهُ مِنْ سُلَيْمَانَ وَإِنَّهُ بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "النمل:30"),
    ("وَلَهُ اخْتِلَافُ اللَّيْلِ وَالنَّهَارِ", "المؤمنون:80"),
    ("فَلَمَّا رَآهَا تَهْتَزُّ كَأَنَّهَا جَانٌّ", "النمل:10"),
    ("الم ذَٰلِكَ الْكِتَابُ لَا رَيْبَ فِيهِ", "البقرة:1-2"),
    ("طه مَا أَنْزَلْنَا عَلَيْكَ الْقُرْآنَ لِتَشْقَىٰ", "طه:1-2"),
    ("يس وَالْقُرْآنِ الْحَكِيمِ", "يس:1-2"),
]

total_c, total_w = 0, 0
print("=" * 70)
print("Strict Evaluation of V1 on Quran")
print("=" * 70)

for i, (verse, source) in enumerate(verses, 1):
    stripped = strip_diacritics(verse)
    predicted = model.diacritize(stripped)
    c, w, errs, ldiff = compare_strict(verse, predicted)
    total = c + w
    der = 100 * w / total if total > 0 else 0
    total_c += c
    total_w += w
    
    print(f"\n[{i}] {source}")
    print(f"    Original: {verse}")
    print(f"    Predict:  {predicted}")
    print(f"    Score:    {c}/{total} correct | DER={der:.1f}% | LenDiff={ldiff}")
    for e in errs[:5]:
        print(f"       ! {e}")

print()
print("=" * 70)
overall = 100 * total_w / (total_c + total_w) if (total_c + total_w) > 0 else 0
print(f"TOTAL: {total_c}/{total_c + total_w} correct | Real DER = {overall:.2f}%")
print("=" * 70)
