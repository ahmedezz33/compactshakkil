# -*- coding: utf-8 -*-
"""dedup_against_train.py — يتجاهل ما تدرّب عليه النموذج آليًّا.

يبني بصمةَ n-gram (مرشّح بلوم) من مدوّنة التدريب (train/val/test)، ثم يُسقِط
من أي عيّنة جديدة كلَّ سطرٍ يتداخل معها فوق عتبة — فيحرس ضد التسرّب والتكرار،
ويعمل رغم اختلافات OCR الطفيفة (يطابق جذاذات كلمات لا أسطرًا حرفيّة).

  python dedup_against_train.py build  <fp.blm> <file1> [file2 ...]   # إنشاء/إضافة
  python dedup_against_train.py filter <fp.blm> <candidates> <out> [threshold]
  python dedup_against_train.py selftest <fp.blm> <train_file>
"""
import sys, os, re, zlib, pickle

_HARAKAT="ًٌٍَُِّْٰ"
_STRIP=str.maketrans("","",_HARAKAT)
_ALEF=str.maketrans({"ٱ":"ا","أ":"ا","إ":"ا",
                     "آ":"ا","ى":"ي","ة":"ه",
                     "ؤ":"و","ئ":"ي"})
_TATWEEL="ـ"
_KEEP=re.compile(r"[^ء-ي ]+")
_WS=re.compile(r"\s+")
N=7                                   # حجم الجذاذة (كلمات)

def norm(line):
    t=line.translate(_STRIP).replace(_TATWEEL,"").translate(_ALEF)
    t=_KEEP.sub(" ", t)
    return _WS.sub(" ", t).strip()

class Bloom:
    def __init__(self, bits=(1<<29), k=3):
        self.bits=bits; self.k=k; self.ba=bytearray(bits//8)
    def _pos(self, data):
        b=self.bits
        for i in range(self.k):
            yield zlib.crc32(data, (i*0x9e3779b1) & 0xffffffff) % b
    def add(self, data):
        ba=self.ba
        for p in self._pos(data): ba[p>>3] |= (1<<(p&7))
    def has(self, data):
        ba=self.ba
        return all(ba[p>>3] & (1<<(p&7)) for p in self._pos(data))

def shingles(words, n=N):
    if len(words) < n:
        if words: yield " ".join(words)
        return
    for i in range(len(words)-n+1):
        yield " ".join(words[i:i+n])

def _save(bl, out):
    with open(out,"wb") as fo:
        pickle.dump({"bits":bl.bits,"k":bl.k,"ba":bytes(bl.ba),"n":N}, fo, protocol=4)

def _load(fp):
    d=pickle.load(open(fp,"rb"))
    bl=Bloom(bits=d["bits"],k=d["k"]); bl.ba=bytearray(d["ba"])
    return bl, d.get("n",N)

def build(out, files):
    if os.path.exists(out):
        bl,_=_load(out); print("إضافةٌ لبصمةٍ قائمة:",out)
    else:
        bl=Bloom()
    nl=ng=0
    for f in files:
        if not os.path.exists(f): print("تخطّي (غير موجود):",f); continue
        c=0
        for line in open(f, encoding="utf-8", errors="ignore"):
            t=norm(line)
            if not t: continue
            nl+=1; c+=1
            for sh in shingles(t.split()):
                bl.add(sh.encode("utf-8")); ng+=1
        print(f"  ضُمّ {f}: {c:,} سطر")
    _save(bl, out)
    print(f"✅ {out} | أسطر={nl:,} | جذاذات={ng:,} | حجم={os.path.getsize(out)//(1<<20)}MB")

def filter_file(fp, cand, out, thr=0.5):
    bl,n=_load(fp)
    kept=[]; drop=0; tot=0
    for line in open(cand, encoding="utf-8", errors="ignore"):
        raw=line.rstrip("\n"); t=norm(raw)
        if not t: continue
        tot+=1
        sh=list(shingles(t.split(), n))
        if not sh: continue
        hit=sum(1 for s in sh if bl.has(s.encode("utf-8")))
        if hit/len(sh) >= thr: drop+=1
        else: kept.append(raw)
    with open(out,"w",encoding="utf-8") as fo:
        fo.write("\n".join(kept)+("\n" if kept else ""))
    print(f"المدخل:{tot:,}  أُبقي:{len(kept):,}  أُسقِط(تداخل>={thr}):{drop:,}  ({100*drop/max(1,tot):.1f}%)")
    print("الناتج:",out)

def selftest(fp, train_file):
    bl,n=_load(fp)
    # 1) أسطرٌ من التدريب يجب أن تُكتشف (تداخل عالٍ)
    seen=0; det=0
    for line in open(train_file, encoding="utf-8", errors="ignore"):
        t=norm(line)
        if not t: continue
        sh=list(shingles(t.split(), n))
        if not sh: continue
        seen+=1
        hit=sum(1 for s in sh if bl.has(s.encode("utf-8")))
        if hit/len(sh)>=0.5: det+=1
        if seen>=2000: break
    print(f"كشفُ التدريب (يجب ~100%): {100*det/max(1,seen):.1f}%  ({det}/{seen})")
    # 2) جُمَلٌ صحفيّةٌ جديدة يجب أن تنجو
    news=["أغلقت السلطات الفرنسية نحو أربعمئة مدرسة ثانوية إثر موجة احتجاجات طلابية",
          "أعلن المتحدث باسم الحكومة عن حزمة إجراءات اقتصادية جديدة لدعم الأسر",
          "ارتفعت أسعار النفط اليوم بعد اجتماع منظمة الدول المصدرة للبترول"]
    for s in news:
        sh=list(shingles(norm(s).split(), n))
        hit=sum(1 for x in sh if bl.has(x.encode("utf-8")))
        print(f"  خبر: تداخل={100*hit/max(1,len(sh)):.0f}%  (يجب ~0) :: {s[:40]}...")

def main():
    a=sys.argv
    if len(a)<2: print(__doc__); return
    if a[1]=="build":   build(a[2], a[3:])
    elif a[1]=="filter":filter_file(a[2], a[3], a[4], float(a[5]) if len(a)>5 else 0.5)
    elif a[1]=="selftest": selftest(a[2], a[3])
    else: print(__doc__)

if __name__=="__main__": main()
