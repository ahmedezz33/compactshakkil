from pathlib import Path
import numpy as np

lengths = []
with open('data/processed/train.txt', 'r', encoding='utf-8') as f:
    for line in f:
        lengths.append(len(line.strip()))

print(f'إجمالي الجمل: {len(lengths):,}')
print(f'أقصر جملة: {min(lengths)} حرف')
print(f'أطول جملة: {max(lengths)} حرف')
print(f'المتوسّط: {np.mean(lengths):.0f}')
print(f'الوسيط: {np.median(lengths):.0f}')
print(f'المئين 95: {np.percentile(lengths, 95):.0f}')
print(f'المئين 99: {np.percentile(lengths, 99):.0f}')
print()

for threshold in [100, 150, 200, 250, 300, 400, 500]:
    count = sum(1 for l in lengths if l > threshold)
    pct = 100 * count / len(lengths)
    print(f'جمل أطول من {threshold}: {count:>10,}  ({pct:>5.1f}%)')