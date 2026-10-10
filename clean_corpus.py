# -*- coding: utf-8 -*-
"""clean_corpus.py — منظِّفُ مدوّنةِ التشكيل (تدريبًا واختبارًا)."""
import sys, re, argparse
_HARAKAT = "ًٌٍَُِّْٰ"; _TAN=set("ًٌٍ"); _SHORT=set("َُِ")
_SUKUN="ْ"; _SHADDA="ّ"; _DAGGER="ٰ"; _MARKS=set(_HARAKAT)
_STRIP=str.maketrans("","",_HARAKAT); _TATWEEL="ـ"
_AR=re.compile(r"[ء-ي]")
_LATIN_DIGIT=re.compile(r"[A-Za-z0-9٠-٩۰-۹]")
_PARTICLES={"من","عن","في","إلى","على","قد","لقد","ثم","بل","هل","لم","لن","لا","ما",
"إن","أن","كي","إذ","إذا","حتى","أو","لكن","بلى","نعم","الذي","التي","الذين","هذا","هذه","ذلك","هؤلاء"}
_ALEF=str.maketrans({"ٱ":"ا","أ":"ا","إ":"ا","آ":"ا","ى":"ي"})
def _bare(w): return w.translate(_STRIP).translate(_ALEF)
def _final_tanwin(w):
    for c in reversed(w):
        if c in _TAN: return True
        if c in _MARKS: continue
        return False
    return False
def _is_def_mudaf(b):
    if b.startswith("ال") or b[:3] in ("وال","فال","بال","كال") or b.startswith("لل"): return True
    for e in ("هما","كما","هم","هن","كم","كن","نا","ها","ه","ك"):
        if b.endswith(e) and len(b)>len(e)+1: return True
    return False
def impossible_tanwin_word(w):
    if not _final_tanwin(w): return False
    b=_bare(w.strip(" ،.:؛!؟«»()[]ـ"))
    if not b: return False
    if _is_def_mudaf(b): return True
    if b in _PARTICLES: return True
    return False
def malformed_marks(w):
    """محافِظٌ جدًّا: حركتان قصيرتان مختلفتان متتاليتان، أو حركةٌ تبدأُ الكلمةَ
    (قبلَ أيِّ حرف). لا نلمسُ الشدّةَ+التنوين (صحيحةٌ: حَقٌّ/نبيًّا)."""
    prev=""; seen=0
    for c in w:
        if c in _MARKS:
            if seen==0: return True
            if prev in _SHORT and c in _SHORT and prev!=c: return True
            prev=c
        else:
            seen+=1; prev=""
    return False


def repair_line(line):
    out=[]
    for w in line.split(" "):
        if w and impossible_tanwin_word(w):
            k=len(w)-1
            while k>=0 and w[k] in _MARKS:
                if w[k] in _TAN: w=w[:k]+w[k+1:]; break
                k-=1
        out.append(w)
    return " ".join(out)
def line_is_dirty(line, allow_repair):
    if _LATIN_DIGIT.search(line): return "latin_digit"
    for w in line.split():
        if malformed_marks(w): return "malformed"
        if not allow_repair and impossible_tanwin_word(w): return "impossible_tanwin"
    return None
def clean_stream(lines, repair=False, out_fh=None):
    st={"in":0,"out":0,"latin_digit":0,"malformed":0,"impossible_tanwin":0,"repaired":0,"empty":0}
    for raw in lines:
        line=raw.replace(_TATWEEL,""); line=re.sub(r"[ \t]{2,}"," ",line).strip()
        if not line: st["empty"]+=1; continue
        st["in"]+=1
        r=line_is_dirty(line, repair)
        if r: st[r]+=1; continue
        if repair:
            rep=repair_line(line)
            if rep!=line: st["repaired"]+=1; line=rep
        if out_fh is not None: out_fh.write(line+"\n")
        st["out"]+=1
    return st
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("inp"); ap.add_argument("out",nargs="?",default="")
    ap.add_argument("--repair",action="store_true"); ap.add_argument("--report",action="store_true")
    a=ap.parse_args()
    out_fh=None
    if a.out and not a.report:
        out_fh=open(a.out,"w",encoding="utf-8")
    with open(a.inp,encoding="utf-8",errors="ignore") as fh:
        st=clean_stream(fh,repair=a.repair,out_fh=out_fh)
    if out_fh: out_fh.close()
    pct=(100*st["out"]/st["in"]) if st["in"] else 0
    print("المدخل:",a.inp)
    print("  أسطرٌ داخلة        :","{:,}".format(st["in"]))
    print("  محذوفٌ لاتينيّ/رقم  :","{:,}".format(st["latin_digit"]))
    print("  محذوفٌ مشوَّه       :","{:,}".format(st["malformed"]))
    if not a.repair: print("  محذوفٌ تنوينٌ مستحيل :","{:,}".format(st["impossible_tanwin"]))
    else: print("  أُصلِح تنوينُه      :","{:,}".format(st["repaired"]))
    print("  الناتج             :","{:,} سطر ({:.1f}%)".format(st["out"],pct))
    if out_fh is not None: print("✅ كُتِب",a.out)
if __name__=="__main__": main()
