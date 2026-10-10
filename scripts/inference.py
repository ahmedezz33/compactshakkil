"""
سكربت الاستدلال: تشكيل نصّ عربي غير مشكّل.

الاستخدام:
    # نصّ واحد
    python scripts/inference.py --checkpoint outputs/best_model.pt \
                                --text "الحمد لله رب العالمين"

    # ملفّ كامل
    python scripts/inference.py --checkpoint outputs/best_model.pt \
                                --input_file input.txt \
                                --output_file output.txt
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import List

import torch

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab import (
    VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID,
    strip_diacritics, encode_chars,
    merge_letters_and_diacritics, is_arabic_letter,
    SPACE_TOKEN, CHAR_TO_ID,
)
from models.transformer import CompactShakkilBase


class DiacritizationInference:
    """واجهة تشكيل بسيطة."""

    def __init__(self, checkpoint_path: str, device: str = None):
        ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        config = ckpt["config"]

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)

        self.model = CompactShakkilBase(
            vocab_size=VOCAB_SIZE,
            num_diacritic_classes=NUM_DIACRITIC_CLASSES,
            d_model=config["model"]["d_model"],
            nhead=config["model"]["nhead"],
            num_encoder_layers=config["model"]["num_encoder_layers"],
            dim_feedforward=config["model"]["dim_feedforward"],
            dropout=0.0,
            max_position=config["model"]["max_position"],
            pad_id=PAD_ID,
        )
        self.model.load_state_dict(ckpt["model_state"])
        self.model.to(self.device)
        self.model.eval()
        self.max_length = config["data"]["max_seq_length"]

    @torch.no_grad()
    def diacritize(self, text: str) -> str:
        """يشكّل نصًّا عربيًا واحدًا."""
        text = strip_diacritics(text.strip())
        if not text:
            return ""

        # فصل الحروف مع الاحتفاظ بغير العربية للإعادة لاحقًا
        letters: List[str] = []
        for c in text:
            letters.append(c)  # نُبقي حتى الرموز غير العربية

        # للنموذج: نحتاج فقط الحروف التي في مفرداتنا
        input_chars = [c if c in CHAR_TO_ID else SPACE_TOKEN for c in letters]
        input_ids = encode_chars(input_chars)

        if len(input_ids) > self.max_length:
            # قسّم النصّ ثمّ أعد التجميع
            return " ".join(self.diacritize(chunk)
                            for chunk in self._chunk_text(text, self.max_length - 10))

        input_tensor = torch.tensor([input_ids], dtype=torch.long).to(self.device)
        attention_mask = torch.ones_like(input_tensor, dtype=torch.bool)

        logits = self.model(input_tensor, attention_mask)  # [1, T, C]
        pred_classes = logits.argmax(dim=-1)[0].cpu().tolist()

        # ركّب النصّ المشكّل — فقط للحروف العربية
        result: List[str] = []
        for c, cls in zip(letters, pred_classes):
            if is_arabic_letter(c):
                # دمج الحرف مع الحركة
                from data.vocab import DIACRITIC_CLASSES
                result.append(c)
                if cls > 0:
                    result.append(DIACRITIC_CLASSES[cls])
            else:
                # أعد الرمز غير العربي كما هو (مسافة، ترقيم، إلخ)
                result.append(c)
        return "".join(result)

    def _chunk_text(self, text: str, max_len: int) -> List[str]:
        """يقسّم النصّ الطويل عند المسافات."""
        words = text.split()
        chunks: List[str] = []
        current = ""
        for w in words:
            if len(current) + len(w) + 1 <= max_len:
                current = f"{current} {w}".strip()
            else:
                if current:
                    chunks.append(current)
                current = w
        if current:
            chunks.append(current)
        return chunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="ملف .pt")
    parser.add_argument("--text", help="نصّ للتشكيل")
    parser.add_argument("--input_file", help="ملف نصّي كامل")
    parser.add_argument("--output_file", help="مخرج (لو أردت الحفظ)")
    args = parser.parse_args()

    print("🔄 تحميل النموذج...")
    inferencer = DiacritizationInference(args.checkpoint)
    print(f"✅ جاهز على: {inferencer.device}\n")

    if args.text:
        print(f"📥 المدخل: {args.text}")
        result = inferencer.diacritize(args.text)
        print(f"📤 المخرج: {result}")

    elif args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        results = []
        from tqdm import tqdm
        for line in tqdm(lines, desc="تشكيل"):
            line = line.strip()
            if line:
                results.append(inferencer.diacritize(line))
            else:
                results.append("")

        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                for r in results:
                    f.write(r + "\n")
            print(f"✅ محفوظ في: {args.output_file}")
        else:
            for r in results:
                print(r)

    else:
        # الوضع التفاعلي
        print("💬 وضع تفاعلي — اضغط Ctrl+D للخروج\n")
        try:
            while True:
                text = input(">>> ").strip()
                if not text:
                    continue
                print(inferencer.diacritize(text))
                print()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 وداعًا!")


if __name__ == "__main__":
    main()
