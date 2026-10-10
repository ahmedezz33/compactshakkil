# -*- coding: utf-8 -*-
"""render_ocr_data.py — مولّد بيانات OCR صناعيّة من نصّ ذهبيّ.

يصيّر كل سطر نصّ (آية/جملة) صورةً بخطّ وحجم عشوائيّين، يغلّف الأسطر الطويلة
كصفحة، ثمّ يضيف ضجيجًا/طمسًا/ميلًا/آثار ضغط ليشبه المسح الحقيقيّ.
يعتمد PIL+raqm (تشكيل صحيح) + cv2/numpy. يكتب صورًا + manifest (مسار<TAB>نصّ).

  python render_ocr_data.py --src data/raw/quran/quran-simple.txt \
     --out data/ocr_quran --reps 3 --n 0        # n=0 => الكل
"""
import os, sys, random, argparse, io, glob, math
from PIL import Image, ImageFont, ImageDraw, ImageEnhance, ImageFilter, ImageOps
import numpy as np
try: import cv2
except Exception: cv2=None

RAQM = ImageFont.Layout.RAQM
FONT_DIR = "data/fonts"
# خطوط مناسبة للتشكيل (نسخيّة أساسًا + بعض التنوّع)
def load_fonts():
    fs=sorted(glob.glob(os.path.join(FONT_DIR,"*.ttf")))
    if not fs: sys.exit("لا خطوط في data/fonts")
    return fs

def wrap_lines(draw, text, font, max_w):
    words=text.split(" "); lines=[]; cur=""
    for w in words:
        cand=(cur+" "+w).strip()
        bb=draw.textbbox((0,0),cand,font=font,direction="rtl",language="ar")
        if (bb[2]-bb[0])>max_w and cur:
            lines.append(cur); cur=w
        else: cur=cand
    if cur: lines.append(cur)
    return lines

def render_text(text, font_path, size, max_w, pad, bg, fg, line_sp):
    font=ImageFont.truetype(font_path, size, layout_engine=RAQM)
    tmp=ImageDraw.Draw(Image.new("RGB",(10,10)))
    lines=wrap_lines(tmp, text, font, max_w)
    # أبعاد
    widths=[]; heights=[]
    for ln in lines:
        bb=tmp.textbbox((0,0),ln,font=font,direction="rtl",language="ar")
        widths.append(bb[2]-bb[0]); heights.append(bb[3]-bb[1])
    lh=max(heights)+line_sp
    W=max(widths)+2*pad; H=lh*len(lines)+2*pad
    img=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(img)
    y=pad
    for ln in lines:
        d.text((W-pad, y), ln, font=font, fill=fg, direction="rtl",
               language="ar", anchor="ra")       # محاذاة لليمين
        y+=lh
    return img

def augment(img):
    r=random.random
    # خلفية/إضاءة
    if r()<0.6: img=ImageEnhance.Brightness(img).enhance(random.uniform(0.85,1.12))
    if r()<0.6: img=ImageEnhance.Contrast(img).enhance(random.uniform(0.85,1.2))
    # ميل بسيط
    if r()<0.6:
        ang=random.uniform(-2.5,2.5)
        img=img.rotate(ang, expand=True, fillcolor=(random.randint(245,255),)*3,
                       resample=Image.BICUBIC)
    # طمس
    if r()<0.5: img=img.filter(ImageFilter.GaussianBlur(random.uniform(0.3,1.1)))
    arr=np.array(img).astype(np.float32)
    # ضجيج غاوسي
    if r()<0.7:
        arr+=np.random.normal(0, random.uniform(3,14), arr.shape)
    # آثار حبر (تمدّد/تآكل) على الرماديّ
    if cv2 is not None and r()<0.4:
        g=cv2.cvtColor(np.clip(arr,0,255).astype(np.uint8),cv2.COLOR_RGB2GRAY)
        k=np.ones((2,2),np.uint8)
        g=cv2.dilate(g,k) if r()<0.5 else cv2.erode(g,k)
        arr=cv2.cvtColor(g,cv2.COLOR_GRAY2RGB).astype(np.float32)
    arr=np.clip(arr,0,255).astype(np.uint8); img=Image.fromarray(arr)
    # آثار ضغط JPEG
    if r()<0.6:
        b=io.BytesIO(); img.save(b,"JPEG",quality=random.randint(30,80)); b.seek(0)
        img=Image.open(b).convert("RGB")
    # تحجيم طفيف (فقدان تفاصيل كالمسح)
    if r()<0.4:
        w,h=img.size; s=random.uniform(0.75,0.95)
        img=img.resize((max(8,int(w*s)),max(8,int(h*s)))).resize((w,h))
    return img

PALETTE_BG=[(255,255,255),(252,250,244),(248,246,238),(250,250,250),(245,243,235)]
import re as _re
_WAQF=_re.compile(r"[\u06D6-\u06ED]")
def _gold(t, strip):
    return _WAQF.sub("", t) if strip else t

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--src",required=True); ap.add_argument("--out",required=True)
    ap.add_argument("--reps",type=int,default=3); ap.add_argument("--n",type=int,default=0)
    ap.add_argument("--seed",type=int,default=1); ap.add_argument("--start",type=int,default=0); ap.add_argument("--end",type=int,default=0)
    ap.add_argument("--strip-gold-marks",action="store_true",
                    help="يُصيِّرُ النصَّ بالرموز في الصورة، لكن يكتبُ الذهبيَّ بلا رموزِ وقف/تجويد (U+06D6..06ED)")
    ap.add_argument("--group",type=int,default=1,
                    help="عدد الأسطر المصدرية المدموجة في صورة واحدة (تنويع الطول)")
    a=ap.parse_args(); random.seed(a.seed); np.random.seed(a.seed)
    fonts=load_fonts()
    lines=[l.strip() for l in open(a.src,encoding="utf-8") if l.strip()]
    if a.n>0: lines=lines[:a.n]
    if a.end>0: lines=lines[a.start:a.end]
    elif a.start>0: lines=lines[a.start:]
    # دمج أسطر لتنويع الطول
    items=[]
    i=0
    while i<len(lines):
        g=random.randint(1,max(1,a.group))
        items.append(" ".join(lines[i:i+g])); i+=g
    os.makedirs(os.path.join(a.out,"images"),exist_ok=True)
    man=open(os.path.join(a.out,"manifest.tsv"),"a",encoding="utf-8")
    cnt=0
    for idx,text in enumerate(items):
        for rep in range(a.reps):
            fp=random.choice(fonts); size=random.randint(28,54)
            max_w=random.randint(600,1100); pad=random.randint(16,40)
            bg=random.choice(PALETTE_BG); fg=(random.randint(0,40),)*3
            line_sp=random.randint(6,int(size*0.6)+6)
            try:
                img=render_text(text,fp,size,max_w,pad,bg,fg,line_sp)
                img=augment(img)
            except Exception as e:
                if cnt==0: print("خطأ تصيير:",e)
                continue
            name=f"images/q{a.start+idx:06d}_{rep}.jpg"
            if os.path.exists(os.path.join(a.out,name)):
                man.write(f"{name}\t{_gold(text, a.strip_gold_marks)}\n"); cnt+=1; continue
            img.convert("RGB").save(os.path.join(a.out,name),"JPEG",quality=random.randint(70,95))
            man.write(f"{name}\t{_gold(text, a.strip_gold_marks)}\n"); cnt+=1
        if (idx+1)%500==0: print(f"  {idx+1}/{len(items)} عناصر، {cnt} صورة")
    man.close()
    print(f"✅ {cnt} صورة | manifest: {a.out}/manifest.tsv | خطوط={len(fonts)}")

if __name__=="__main__": main()
