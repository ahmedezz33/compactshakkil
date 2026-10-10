# -*- coding: utf-8 -*-
"""api_bill.py — فاتورةٌ شهريّةٌ من api_usage.log لكلّ عميل.
الاستعمال:
  python api_bill.py                              # الشهر الحاليّ
  python api_bill.py --month 2026-10 --price 2.0 --vat 15
  --price: ريال لكلّ 1000 وحدة (افتراضي 2.0)
  --vat:   نسبة ضريبة % (افتراضي 0)
يطبع جدولًا ويكتب bills_<الشهر>.csv
"""
import os, json, argparse, csv, datetime
from collections import defaultdict
from pathlib import Path
LOG = Path("api_usage.log"); KEYS = Path("api_keys.json")

def month_bounds(m):
    y, mo = map(int, m.split("-"))
    start = datetime.datetime(y, mo, 1)
    end = datetime.datetime(y + (mo == 12), (mo % 12) + 1, 1)
    return start.timestamp(), end.timestamp()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default=datetime.date.today().strftime("%Y-%m"))
    ap.add_argument("--price", type=float, default=float(os.environ.get("PRICE_PER_1000", "2.0")))
    ap.add_argument("--vat", type=float, default=float(os.environ.get("VAT_PCT", "0")))
    a = ap.parse_args()
    lo, hi = month_bounds(a.month)
    names = {}
    if KEYS.exists():
        for k, rec in json.loads(KEYS.read_text(encoding="utf-8")).items():
            names[k[:10]] = rec.get("name", k[:10])
    agg = defaultdict(lambda: defaultdict(int))
    if not LOG.exists():
        print("لا يوجد api_usage.log بعد."); return
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception: continue
        if not (lo <= r.get("t", 0) < hi): continue
        agg[r.get("key", "")][r.get("endpoint", "?")] += int(r.get("units", 0))
    if not agg:
        print(f"لا استعمالَ في {a.month}."); return
    print(f"\n=== فاتورة {a.month} | {a.price} ر.س/1000 وحدة | ضريبة {a.vat}% ===\n")
    hdr = f'{"العميل":<20}{"تشكيل":>9}{"نطق":>9}{"OCR":>9}{"إجمالي":>11}{"مبلغ":>10}{"+ضريبة":>11}'
    print(hdr); print("-" * 80)
    rows = []; gtotal = 0.0
    for kp, eps in sorted(agg.items(), key=lambda x: -sum(x[1].values())):
        name = names.get(kp, kp)
        d, p, o = eps.get("diacritize", 0), eps.get("pronounce", 0), eps.get("ocr", 0)
        tot = d + p + o
        amount = tot / 1000.0 * a.price
        withvat = amount * (1 + a.vat / 100.0)
        gtotal += withvat
        print(f'{name:<20}{d:>9,}{p:>9,}{o:>9,}{tot:>11,}{amount:>10.2f}{withvat:>11.2f}')
        rows.append([name, kp, d, p, o, tot, round(amount, 2), round(withvat, 2)])
    print("-" * 80)
    print(f'الإجمالي الكلّيّ (مع الضريبة): {gtotal:.2f} ر.س')
    out = f"bills_{a.month}.csv"
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["العميل", "بادئة المفتاح", "تشكيل", "نطق", "OCR", "إجمالي الوحدات", "المبلغ", "مع الضريبة"])
        w.writerows(rows)
    print(f"✅ حُفظ: {out}")

if __name__ == "__main__": main()
