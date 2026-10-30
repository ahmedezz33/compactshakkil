# -*- coding: utf-8 -*-
"""render_more.py — تصييرٌ إضافيٌّ قابلٌ للاستئناف، idempotent تمامًا.
يجمّعُ كاملَ المصدرِ مرّةً (seed ثابت) → عناصرُ بفهارسَ عامّةٍ ثابتة؛
يُصيّرُ شريحةَ [--i0:--i1] بأسماءِ c{idx:06d}_{rep}.jpg؛ يتخطّى الموجود؛
يُعيدُ كتابةَ المانيفستِ من قاموسٍ (اسم→نصّ) فلا تكرارَ أبدًا (ويُنظّفُ أيَّ تكرارٍ سابق).
  python render_more.py --src data/ocr_classical_src.txt --out data/ocr_classical_pages_more --i0 0 --i1 400 --reps 1
"""
import os, sys, random, argparse, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_ocr_data as R

def build_items(src, group, seed):
    lines=[l.strip() for l in open(src,encoding="utf-8") if l.strip()]
    rnd=random.Random(seed); items=[]; i=0
    while i<len(lines):
        g=rnd.randint(1,max(1,group)); items.append(" ".join(lines[i:i+g])); i+=g
    return items

def load_manifest(mf):
    d={}
    if os.path.exists(mf):
        for ln in open(mf,encoding="utf-8"):
            ln=ln.rstrip("\n")
            if "\t" in ln:
                k,v=ln.split("\t",1); d[k]=v
    return d

def save_manifest(mf, d):
    tmp=mf+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        for k in sorted(d): f.write(f"{k}\t{d[k]}\n")
    os.replace(tmp, mf)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--src",required=True); ap.add_argument("--out",required=True)
    ap.add_argument("--i0",type=int,required=True); ap.add_argument("--i1",type=int,required=True)
    ap.add_argument("--reps",type=int,default=1); ap.add_argument("--group",type=int,default=16)
    ap.add_argument("--seed",type=int,default=777); ap.add_argument("--strip-gold-marks",action="store_true")
    a=ap.parse_args()
    fonts=R.load_fonts()
    items=build_items(a.src, a.group, a.seed)
    n=len(items); i1=min(a.i1,n)
    os.makedirs(os.path.join(a.out,"images"),exist_ok=True)
    mf=os.path.join(a.out,"manifest.tsv"); man=load_manifest(mf)
    print(f"عناصرُ المصدرِ كلِّها={n} · أُصيّرُ [{a.i0}:{i1}] · reps={a.reps} · خطوط={len(fonts)}")
    rnd=random.Random(a.seed*1000+a.i0)
    done=0; made=0
    for idx in range(a.i0, i1):
        text=items[idx]
        for rep in range(a.reps):
            name=f"images/c{idx:06d}_{rep}.jpg"
            full=os.path.join(a.out,name)
            gold=R._gold(text, a.strip_gold_marks)
            if os.path.exists(full):
                man[name]=gold; done+=1; continue
            fp=rnd.choice(fonts); size=rnd.randint(28,54)
            max_w=rnd.randint(600,1100); pad=rnd.randint(16,40)
            bg=rnd.choice(R.PALETTE_BG); fg=(rnd.randint(0,40),)*3
            line_sp=rnd.randint(6,int(size*0.6)+6)
            try:
                img=R.render_text(text,fp,size,max_w,pad,bg,fg,line_sp); img=R.augment(img)
                img.convert("RGB").save(full,"JPEG",quality=rnd.randint(70,95))
                man[name]=gold; made+=1
            except Exception as e:
                if made==0 and done==0: print("خطأ تصيير:",repr(e)[:80])
                continue
        if (idx-a.i0+1)%50==0:
            save_manifest(mf,man); print(f"  idx={idx+1} · جديد={made} · موجود={done}",flush=True)
    save_manifest(mf,man)
    print(f"✅ شريحةٌ تمّت [{a.i0}:{i1}] · جديد={made} · تخطّي={done} · المانيفست(فريد)={len(man)}")

if __name__=="__main__": main()
