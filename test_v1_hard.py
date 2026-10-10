"""اختبار V1 على آيات أصعب."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.inference import DiacritizationInference
from data.vocab import strip_diacritics, DIACRITIC_CLASSES

print("🔄 تحميل V1...")
model = DiacritizationInference("compactshakkil_v1_baseline/best_model.pt")
print(f"✅ جاهز على: {model.device}\n")

# آيات أصعب (طويلة، نادرة الاقتباس، أو فيها كلمات نادرة)
verses = [
    # آية الكرسي (طويلة، شهيرة، اختبار الحدّ الأعلى)
    ("اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ", "البقرة:255-جزء"),
    # آية فقهية (نادرة الاقتباس)
    ("وَإِذَا ضَرَبْتُمْ فِي الْأَرْضِ فَلَيْسَ عَلَيْكُمْ جُنَاحٌ", "النساء:101-جزء"),
    # آية فيها أسماء أعلام
    ("وَقُلْنَا يَا آدَمُ اسْكُنْ أَنْتَ وَزَوْجُكَ الْجَنَّةَ", "البقرة:35-جزء"),
    # آية فيها كلمات نادرة
    ("وَاصْطَنَعْتُكَ لِنَفْسِي", "طه:41"),
    # آية سليمان (النمل - فيها بسملة داخلية)
    ("إِنَّهُ مِنْ سُلَيْمَانَ وَإِنَّهُ بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "النمل:30"),
    # آيات من سور طويلة نادرة الاستشهاد بها
    ("وَلَهُ اخْتِلَافُ اللَّيْلِ وَالنَّهَارِ", "المؤمنون:80-جزء"),
    ("فَلَمَّا رَآهَا تَهْتَزُّ كَأَنَّهَا جَانٌّ", "النمل:10-جزء"),
    # حروف مقطّعة (اختبار مهمّ)
    ("الم ذَٰلِكَ الْكِتَابُ لَا رَيْبَ فِيهِ", "البقرة:1-2"),
    ("طه مَا أَنْزَلْنَا عَلَيْكَ الْقُرْآنَ لِتَشْقَىٰ", "طه:1-2"),
    ("يس وَالْقُرْآنِ الْحَكِيمِ", "يس:1-2"),
]

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

def compare(original, predicted):
    orig = extract_pairs(original)
    pred = extract_pairs(predicted)
    correct = 0
    wrong = 0
    errors = []
    for (oc, od), (pc, pd) in zip(orig, pred):
        if oc == pc:
            if od == pd:
                correct += 1
            else:
                wrong += 1
                if len(errors) < 5:
                    errors.append(f"{oc}: {repr(od)} → {repr(pd)}")
    return correct, wrong, errors

total_c, total_w = 0, 0
print("=" * 70)
print("اختبار V1 على آيات أصعب")
print("=" * 70)

for i, (verse, source) in enumerate(verses, 1):
    stripped = strip_diacritics(verse)
    predicted = model.diacritize(stripped)
    c, w, errs = compare(verse, predicted)
    total = c + w
    der = 100 * w / total if total > 0 else 0
    total_c += c
    total_w += w
    
    status = "OK" if der == 0 else ("Fair" if der < 15 else "Poor")
    print(f"\n[{i}] {source} [{status}]")
    print(f"    الأصل:    {verse}")
    print(f"    التنبّؤ:  {predicted}")
    print(f"    {c}/{total} صحيح | DER={der:.1f}%")
    for e in errs[:3]:
        print(f"       ! {e}")

print()
print("=" * 70)
overall = 100 * total_w / (total_c + total_w) if (total_c + total_w) > 0 else 0
print(f"الإجماليّ: {total_c}/{total_c + total_w} | DER = {overall:.2f}%")
print("=" * 70)
