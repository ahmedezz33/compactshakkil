# -*- coding: utf-8 -*-
"""يبني مانيفستًا موحَّدًا (قرآن + تراث/عاديّ) بمسارات جذرِ المشروع، مخلوطًا.
الاستعمال: python build_unified_tsv.py
المدخلات: data/ocr_quran_pages/manifest.tsv , data/ocr_classical_pages/manifest.tsv
المخرج:  data/ocr_unified_train.tsv  (path<TAB>text ، path نسبيٌّ لجذر المشروع)
"""
import os, random, re
random.seed(20)
_WAQF=re.compile(r"[\u06D6-\u06ED]")  # رموزُ وقف/تجويد: في الصورةِ لا في الذهبيّ
SRC=[("data/ocr_quran_pages","قرآن"),("data/ocr_classical_pages","تراث/عاديّ")]
rows=[]
for d,tag in SRC:
    mf=os.path.join(d,"manifest.tsv")
    if not os.path.exists(mf):
        print(f"⚠️ مفقود: {mf} (شغّل التصيير أولًا)"); continue
    n=0
    for ln in open(mf,encoding="utf-8"):
        ln=ln.rstrip("\n")
        if "\t" not in ln: continue
        rel,txt=ln.split("\t",1)
        rel=rel.lstrip("/").replace("\\","/")
        if not rel.startswith("images/"):            # تسامحٌ لو كان المسارُ كاملًا
            rel=rel.split("/images/")[-1]; rel="images/"+rel if not rel.startswith("images/") else rel
        full=f"{d}/{rel}"
        g=_WAQF.sub("", txt).strip()
        if g: rows.append(f"{full}\t{g}"); n+=1
    print(f"  {tag}: {n} صورة من {d}")
random.shuffle(rows)
out="data/ocr_unified_train.tsv"
open(out,"w",encoding="utf-8").write("\n".join(rows)+"\n")
print(f"✅ {len(rows)} سطرًا → {out}")
