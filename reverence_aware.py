# -*- coding: utf-8 -*-
"""
reverence_aware.py — نظام Reverence-Aware (v2: تطبيع الهمزات + استرداد آمن)

المبدأ: حماية النصّ المقدّس بثلاثة مستويات:
    تطابق تامّ مع آية → استرداد النصّ الأصليّ من المصحف (بلا نموذج — خطأ صفر)
    مقطع قرآنيّ جزئيّ → V3 (المتخصّص القرآنيّ)
    نصّ عامّ          → V2 (العامّ)

التطبيع: أ إ آ ٱ → ا (لتحصين المطابقة ضدّ اختلاف رسم الهمزة).

التشغيل:
    .\\venv\\Scripts\\python.exe reverence_aware.py
"""
import sys
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).parent))
from data.vocab_v2 import (
    VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID,
    split_letters_and_diacritics, merge_letters_and_diacritics,
    strip_diacritics, encode_chars,
)
from models.transformer import CompactShakkilBase

V2_CKPT = "outputs_v2/best_model.pt"
V3_CKPT = "outputs_v3/best_model.pt"
QURAN_PATH = "data/raw/quran/quran-simple.txt"

# تطبيع الرسم للمطابقة فقط (النصّ المخزَّن يبقى بالرسم الصحيح):
#   الهمزات (أ إ آ ٱ) → ا  |  ألف مقصورة ى → ي  |  تاء مربوطة ة → ه
NORM_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"})
SMALL_ALIF = "ٰ"  # الأليف الصغيرة — يعدّها المعجم حرفًا، لكن نزيلها للمطابقة فقط


def _norm(s: str) -> str:
    """تجريد الحركات + الأليف الصغيرة + تطبيع الرسم + توحيد الفراغات — للمطابقة فقط."""
    s = strip_diacritics(s).replace(SMALL_ALIF, "").translate(NORM_MAP)
    return " ".join(s.split())


def load_model(ckpt_path, device):
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    m = ckpt.get("config", {}).get("model", {})
    model = CompactShakkilBase(
        vocab_size=VOCAB_SIZE, num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=m.get("d_model", 256), nhead=m.get("nhead", 8),
        num_encoder_layers=m.get("num_encoder_layers", 4),
        dim_feedforward=m.get("dim_feedforward", 1024),
        dropout=0.0, max_position=m.get("max_position", 512), pad_id=PAD_ID,
    ).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model


@torch.no_grad()
def diacritize(text, model, device):
    letters, _ = split_letters_and_diacritics(strip_diacritics(text))
    if not letters:
        return text
    ids = torch.tensor([encode_chars(letters)], dtype=torch.long, device=device)
    mask = torch.ones_like(ids, dtype=torch.bool)
    classes = model(ids, mask).argmax(dim=-1)[0].tolist()
    return merge_letters_and_diacritics(letters, classes)


BISM_NORM = "بسم الله الرحمن الرحيم"   # البسملة مطبّعة (4 كلمات)


def load_quran_index(path):
    """يبني: {آية مطبّعة → آية أصلية مشكّلة} + النصّ المطبّع الكامل للبحث الجزئيّ.

    إن بدأ سطرٌ بالبسملة (لم تُفصَل)، نفهرس ما بعدها كآية مستقلّة أيضًا —
    لاستعادة تطابق الآية الأولى في السور، وردّ الهمزة الصحيحة بالاسترداد.
    """
    index = {}

    def add(key, orig):
        if key and key not in index:
            index[key] = orig

    for line in Path(path).read_text(encoding="utf-8").splitlines():
        orig = " ".join(line.split())   # توحيد المسافات (يزيل المزدوجة)
        if not orig:
            continue
        key = _norm(orig)
        add(key, orig)                         # السطر كاملًا
        if key.startswith(BISM_NORM + " "):    # بسملة + آية ملتصقتان
            post_key = key[len(BISM_NORM) + 1:]
            post_orig = " ".join(orig.split()[4:])   # إسقاط كلمات البسملة الأربع
            add(post_key, post_orig)           # ما بعد البسملة كآية مستقلّة
    return index, " ".join(index.keys())


class ReverenceAware:
    def __init__(self, v2_ckpt, v3_ckpt, quran_path, device, min_len=12):
        self.device = device
        self.min_len = min_len
        print("📥 تحميل V2 (العامّ)...")
        self.v2 = load_model(v2_ckpt, device)
        print("📥 تحميل V3 (المتخصّص القرآنيّ)...")
        self.v3 = load_model(v3_ckpt, device)
        print("📖 بناء فهرس القرآن...")
        self.index, self.norm_full = load_quran_index(quran_path)
        # مفاتيح مرتّبة تنازليًّا بالطول (لإيجاد أطول آية مطابقة أوّلًا)
        self.keys_by_len = sorted(self.index.keys(), key=len, reverse=True)
        print(f"   {len(self.index):,} آية في الفهرس\n")

    def process(self, text):
        key = _norm(text)
        # المستوى 1: آية تامّة → استرداد النصّ الأصليّ (بلا نموذج)
        if key in self.index:
            return {"route": "استرداد (آية تامّة)", "reason": "تطابق تامّ (خطأ صفر)",
                    "output": self.index[key]}
        # المستوى 2: آية مضمّنة داخل النصّ (سياق استشهاد) → استرداد الآية
        for vk in self.keys_by_len:
            if len(vk) < 8:                # الأقصر لا يُعتمد (تجنّب مطابقة عابرة)
                break
            if vk in key:
                return {"route": "استرداد (آية مضمّنة)", "reason": "آية داخل سياق استشهاد",
                        "output": self.index[vk]}
        # المستوى 3أ: المقطع بداية آية (دقيق، عتبة أدنى) → أوّل k كلمات مشكّلة
        if len(key) >= 8 and len(key.split()) >= 2:
            k = len(key.split())
            best = None
            for vk in self.keys_by_len:          # الأطول أوّلًا → آخر مطابقة = الأقصر
                if vk.startswith(key + " "):
                    best = vk
            if best is not None:
                return {"route": "استرداد (مقطع من آية)", "reason": "بداية آية",
                        "output": " ".join(self.index[best].split()[:k])}
        # المستوى 3ب: المقطع وسط آية (عتبة أعلى) → أقصر آية حاوية (كاملة)
        if len(key) >= self.min_len:
            for vk in reversed(self.keys_by_len):  # الأقصر أوّلًا
                if key in vk:
                    return {"route": "استرداد (مقطع من آية)", "reason": "مقطع وسط آية",
                            "output": self.index[vk]}
        # المستوى 4: محتوى قرآنيّ يعبر حدود الآيات → V3
        if len(key) >= self.min_len and key in self.norm_full:
            return {"route": "V3 (متخصّص قرآنيّ)", "reason": "محتوى قرآنيّ",
                    "output": diacritize(text, self.v3, self.device)}
        # المستوى 5: نصّ عامّ → V2
        return {"route": "V2 (عامّ)", "reason": "نصّ عامّ",
                "output": diacritize(text, self.v2, self.device)}


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️  الجهاز: {device}\n")
    for p in (V2_CKPT, V3_CKPT, QURAN_PATH):
        if not Path(p).exists():
            print(f"❌ ملفّ مفقود: {p}"); sys.exit(1)

    system = ReverenceAware(V2_CKPT, V3_CKPT, QURAN_PATH, device)

    tests = [
        "الحمد لله رب العالمين",              # آية تامّة (رسم مطابق)
        "انا اعطيناك الكوثر",                 # آية لكن بألف مجرّدة (اختبار التطبيع)
        "قل هو الله احد",                     # آية بألف مجرّدة
        "ذهب الطالب الى المدرسة صباحا",        # عامّ
        "قال العلماء ان التشكيل مهم للقراءة",   # عامّ
    ]
    print("=" * 72)
    print("تجربة نظام Reverence-Aware (v2)")
    print("=" * 72)
    for t in tests:
        r = system.process(t)
        print(f"\n▌ المدخل : {t}")
        print(f"  التوجيه: {r['route']}  ({r['reason']})")
        print(f"  المخرج : {r['output']}")


if __name__ == "__main__":
    main()
