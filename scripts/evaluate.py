"""
سكربت التقييم: يحسب المقاييس القياسية للتشكيل.

المقاييس:
    - DER  (Diacritic Error Rate)   — معدّل خطأ الحركة على مستوى الحرف
    - WER  (Word Error Rate)         — معدّل خطأ الحركة على مستوى الكلمة
    - DER-CE (بلا آخر الكلمة)         — يستبعد الحركة الإعرابية النهائية
    - WER-CE (بلا آخر الكلمة)         — نفس الفكرة على مستوى الكلمة

الاستخدام:
    python scripts/evaluate.py --checkpoint outputs/best_model.pt
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Tuple

import torch
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab import VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID, is_arabic_letter, ID_TO_CHAR
from data.dataset import get_dataloaders
from models.transformer import CompactShakkilBase


@torch.no_grad()
def compute_der_wer(model, loader, device) -> dict:
    """
    يحسب DER و WER.

    - DER: نسبة الحروف العربية التي أخطأ في تشكيلها النموذج
    - WER: نسبة الكلمات التي أخطأ في أي من حركاتها
    - DER-CE / WER-CE: نفس المقياس مع استبعاد الحركة الأخيرة (الإعراب)
    """
    model.eval()

    total_letters = 0
    letter_errors = 0
    letter_errors_ce = 0     # بلا آخر حرف من الكلمة

    total_words = 0
    word_errors = 0
    word_errors_ce = 0

    for batch in tqdm(loader, desc="تقييم"):
        input_ids = batch["input_ids"].to(device)
        target_ids = batch["target_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)

        logits = model(input_ids, attention_mask)
        preds = logits.argmax(dim=-1)  # [B, T]

        # نمرّ على كل عيّنة في الدفعة
        for i in range(input_ids.size(0)):
            inp = input_ids[i].cpu().tolist()
            tgt = target_ids[i].cpu().tolist()
            prd = preds[i].cpu().tolist()

            # نجمّع الكلمات (فصل عند المسافة)
            word_correct = True
            word_correct_ce = True
            word_has_letters = False
            last_letter_idx = -1

            # اعثر على مواقع الحروف داخل الكلمة الحالية
            positions_in_word = []

            for j, (ch_id, t, p) in enumerate(zip(inp, tgt, prd)):
                if t == -100:  # padding
                    continue
                ch = ID_TO_CHAR.get(ch_id, "")

                # نهاية كلمة (مسافة) أو نهاية العيّنة
                is_space = (ch == " ")

                if is_space:
                    if word_has_letters:
                        total_words += 1
                        if not word_correct:
                            word_errors += 1
                        if not word_correct_ce:
                            word_errors_ce += 1
                    word_correct = True
                    word_correct_ce = True
                    word_has_letters = False
                    positions_in_word = []
                    continue

                if not is_arabic_letter(ch):
                    continue

                # حرف عربي — احسبه
                word_has_letters = True
                positions_in_word.append(j)
                total_letters += 1
                if t != p:
                    letter_errors += 1
                    word_correct = False

            # الكلمة الأخيرة (لم تنتهِ بمسافة)
            if word_has_letters:
                total_words += 1
                if not word_correct:
                    word_errors += 1
                if not word_correct_ce:
                    word_errors_ce += 1

        # المرور الثاني لحساب CE: نستبعد آخر حرف من كل كلمة
        for i in range(input_ids.size(0)):
            inp = input_ids[i].cpu().tolist()
            tgt = target_ids[i].cpu().tolist()
            prd = preds[i].cpu().tolist()

            # اعثر على مواقع الحروف الأخيرة في كل كلمة
            last_positions = set()
            current_word_positions = []
            for j, (ch_id, t) in enumerate(zip(inp, tgt)):
                if t == -100:
                    if current_word_positions:
                        last_positions.add(current_word_positions[-1])
                        current_word_positions = []
                    continue
                ch = ID_TO_CHAR.get(ch_id, "")
                if ch == " ":
                    if current_word_positions:
                        last_positions.add(current_word_positions[-1])
                    current_word_positions = []
                elif is_arabic_letter(ch):
                    current_word_positions.append(j)
            if current_word_positions:
                last_positions.add(current_word_positions[-1])

            # الآن احسب الأخطاء مع استبعاد المواقع الأخيرة
            for j, (ch_id, t, p) in enumerate(zip(inp, tgt, prd)):
                if t == -100 or j in last_positions:
                    continue
                ch = ID_TO_CHAR.get(ch_id, "")
                if is_arabic_letter(ch) and t != p:
                    letter_errors_ce += 1

    return {
        "DER":     letter_errors / max(1, total_letters),
        "DER_CE":  letter_errors_ce / max(1, total_letters),
        "WER":     word_errors / max(1, total_words),
        "WER_CE":  word_errors_ce / max(1, total_words),
        "total_letters": total_letters,
        "total_words": total_words,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="ملف .pt")
    parser.add_argument("--data_dir", default="data/processed")
    parser.add_argument("--split", default="test", choices=["val", "test"])
    parser.add_argument("--batch_size", type=int, default=32)
    args = parser.parse_args()

    ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    config = ckpt["config"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️  الجهاز: {device}")

    # النموذج
    model = CompactShakkilBase(
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
    model.load_state_dict(ckpt["model_state"])
    model.to(device)

    # البيانات
    loaders = get_dataloaders(
        data_dir=args.data_dir,
        batch_size=args.batch_size,
        max_length=config["data"]["max_seq_length"],
        num_workers=2,
    )
    loader = loaders[args.split]

    # التقييم
    metrics = compute_der_wer(model, loader, device)

    # طباعة تقرير
    print(f"\n{'═' * 50}")
    print(f"📊 نتائج التقييم على {args.split}")
    print(f"{'═' * 50}")
    print(f"إجمالي الحروف: {metrics['total_letters']:,}")
    print(f"إجمالي الكلمات: {metrics['total_words']:,}\n")
    print(f"DER     (Diacritic Error Rate):        {metrics['DER']*100:.2f}%")
    print(f"DER-CE  (بلا الحركة الإعرابية):        {metrics['DER_CE']*100:.2f}%")
    print(f"WER     (Word Error Rate):             {metrics['WER']*100:.2f}%")
    print(f"WER-CE  (بلا الحركة الإعرابية):        {metrics['WER_CE']*100:.2f}%")
    print(f"{'═' * 50}\n")

    # للمقارنة مع الأدبيات
    print("💡 للمقارنة مع الأدبيات:")
    print("   Shakkelha (Fadel 2019):  DER ~ 3.73%,  WER ~ 11.19%")
    print("   Farasa (Darwish 2017):   DER ~ 4.10%,  WER ~ 12.76%")
    print("   Multi-Level (Abbad 2020): DER ~ 3.00%,  WER ~ 8.90%")


if __name__ == "__main__":
    main()
