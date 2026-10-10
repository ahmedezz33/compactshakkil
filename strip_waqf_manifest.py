# -*- coding: utf-8 -*-
"""ينسخُ مانيفستًا مع تنظيفِ عمودِ الذهبيِّ من رموزِ الوقف/التجويد (U+06D6..06ED).
الصُّوَرُ لا تُمَسّ (تبقى بالرموز). الاستعمال: python strip_waqf_manifest.py <src.tsv> <dst.tsv>"""
import re, sys
W=re.compile(r"[ۖ-ۭ]")
src,dst=sys.argv[1],sys.argv[2]
R=[]
for ln in open(src,encoding="utf-8").read().splitlines():
    if "\t" in ln:
        a,b=ln.split("\t",1); R.append(a+"\t"+W.sub("",b).strip())
open(dst,"w",encoding="utf-8").write("\n".join(R)+"\n")
print(f"✅ ذهبيّ نظيف: {len(R)} سطرًا → {dst}")
