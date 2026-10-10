# -*- coding: utf-8 -*-
"""
morph_extract.py — يستخرج أوسمة POS (محاذيةً 1:1) لكلّ سطر ويكتبها ملفًّا موازيًا.

لكلّ <split>.txt يُنتج <split>.pos : سطرٌ لكلّ سطر، أعدادُ POS مفصولةً بمسافات،
بطولٍ = عدد أحرف السطر (بما فيها المسافات) — جاهزةٌ للتدريب مباشرةً.

الاستخدام (على جهازك، داخل venv فيه camel_tools):
  ملف:   python morph_extract.py data\processed_clean\val.txt  val.pos  file
  مجلّد: python morph_extract.py data\processed_clean  data\processed_clean_pos
  تجربة بلا CAMeL:  أضِف  mock  في آخر الأمر (لاختبار الأنابيب فقط)
"""
import sys, os, time
from pathlib import Path
sys.path.insert(0, ".")
from morph_features import line_to_pos_ids, CamelTagger, MockTagger

def get_tagger(use_mock):
    if use_mock: print("⚠️ MockTagger (اختبار الأنابيب فقط)"); return MockTagger()
    print("📥 تحميل CAMeL MLEDisambiguator ..."); t=CamelTagger()
    print("   جاهز."); return t

def process_file(inp, outp, tagger, limit=0, feat="pos"):
    """limit>0: عالِج أوّل limit سطرٍ فقط (للطيّار). المحاذاة تبقى من الأعلى 1:1."""
    n=0; read=0; t0=time.time()
    with open(inp,encoding="utf-8") as f, open(outp,"w",encoding="utf-8") as w:
        for line in f:
            if limit and read>=limit: break
            read+=1
            s=line.strip()
            if not s: w.write("\n"); continue
            ids,_=line_to_pos_ids(s,tagger,feat)
            w.write(" ".join(map(str,ids))+"\n"); n+=1
            if n%2000==0: print(f"   {n:,} سطرًا ({n/(time.time()-t0):.0f}/ث)")
    print(f"✓ {inp} → {outp}  ({n:,} سطرًا، {time.time()-t0:.0f}ث)")

def _limit_of(rest):
    for r in rest:
        if r.startswith("head="):
            try: return int(r.split("=")[1])
            except Exception: return 0
    return 0

def _feat_of(rest):
    for r in rest:
        if r.startswith("feat="): return r.split("=")[1]
    return "pos"

def main():
    a1,a2 = sys.argv[1], sys.argv[2]
    rest = sys.argv[3:]
    mode = "file" if "file" in rest else "dir"
    limit = _limit_of(rest)            # head=N ⇒ يحدّ train فقط
    feat  = _feat_of(rest)             # feat=pos (افتراضيّ) أو feat=cas
    print(f"الميزة: {feat}")
    tagger = get_tagger("mock" in rest)
    if mode=="file":
        process_file(a1,a2,tagger,limit,feat)
    else:
        os.makedirs(a2,exist_ok=True)
        for sp in ["train","val","test"]:
            p=Path(a1)/f"{sp}.txt"
            if not p.exists(): print(f"[{sp}] غير موجود — تجاوز"); continue
            lim = limit if sp=="train" else 0     # الحدّ لـ train فقط؛ val/test كاملان
            process_file(str(p), str(Path(a2)/f"{sp}.pos"), tagger, lim, feat)

if __name__=="__main__":
    main()
