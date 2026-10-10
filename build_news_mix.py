# -*- coding: utf-8 -*-
"""build_news_mix.py — يُعيد بناء مزيج التكيّف الصحفيّ (قابل للتكرار).
= أخبار×NEWS_REP + تصحيحاتك×CORR_REP + عيّنة عامّة (تمنع النسيان).
التصحيحاتُ حالاتُ الفشلِ بعينِها، فتأخذ ترجيحًا أعلى."""
import random, os
random.seed(7)
NEWS_REP=int(os.environ.get("NEWS_REP","20"))
CORR_REP=int(os.environ.get("CORR_REP","40"))
GEN=int(os.environ.get("GEN_LINES","80000"))
HAR=set("ًٌٍَُِّْٰ")
def readlines(p):
    return [l.strip() for l in open(p,encoding="utf-8")] if os.path.exists(p) else []
def ok(s): return s and any(c in HAR for c in s)
news=[l for l in readlines("data/news_train.txt") if ok(l)]
corr=[l for l in readlines("data/news_corrections.txt") if ok(l)]
gen=[]
with open("data/processed_clean/train.txt",encoding="utf-8") as f:
    for line in f:
        s=line.strip()
        if s: gen.append(s)
        if len(gen)>=GEN: break
mix = news*NEWS_REP + corr*CORR_REP + gen
random.shuffle(mix)
os.makedirs("data/processed_news",exist_ok=True)
open("data/processed_news/train.txt","w",encoding="utf-8").write("\n".join(mix)+"\n")
print(f"أخبار {len(news)}×{NEWS_REP}={len(news)*NEWS_REP} | "
      f"تصحيحات {len(corr)}×{CORR_REP}={len(corr)*CORR_REP} | عامّ {len(gen)} | "
      f"الإجمالي {len(mix):,} سطر")
