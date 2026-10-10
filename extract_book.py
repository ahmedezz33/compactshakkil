# -*- coding: utf-8 -*-
"""
extract_book.py — استخراجُ كتابٍ كاملٍ من مكتبة PDF (شاملة) إلى نصٍّ مشكَّلٍ بالـ OCR.
يعملُ صفحةً صفحة (تقدّمٌ + استئنافٌ + سجلّ)، بدقّةٍ عالية، يتخطّى صفحاتِ الغلاف.

تشغيل:
  python extract_book.py --pdf "F:\\shamela4\\pdf\\...\\book.pdf" [--dpi 300] [--skip 3] [--pages 1-99999]
  python extract_book.py --author "0179 مالك بن أنس" --book "الموطأ" [--all-volumes]
المخرجات: data/shamela_corpus/<اسم>.txt   والسجلّ: extract_log.txt
"""
import os, sys, argparse, glob, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import ocr_engine, shamela_import
OUT=os.path.join("data","shamela_corpus"); os.makedirs(OUT,exist_ok=True)
LOG="extract_log.txt"
def log(m):
    line=time.strftime("%H:%M:%S ")+m
    print(line, flush=True)
    open(LOG,"a",encoding="utf-8").write(line+"\n")

def extract_pdf(path, dpi=300, skip=0, pages=None, harakat_min=0.10):
    import pypdfium2 as pdfium
    from PIL import Image
    name=os.path.splitext(os.path.basename(path))[0]
    dst=os.path.join(OUT, name+".txt")
    done=os.path.join(OUT, name+".done")
    if os.path.exists(done):
        log(f"skip (done): {name}"); return dst
    pdf=pdfium.PdfDocument(path); n=len(pdf)
    if pages:
        idxs=ocr_engine._parse_pages(pages, n)
    else:
        idxs=list(range(skip, n))
    # استئناف: كم صفحةً كُتِبت؟
    written=0
    if os.path.exists(dst):
        written=sum(1 for _ in open(dst,encoding="utf-8") if _.startswith("\f"))
    log(f"START {name}: {len(idxs)} صفحة (dpi={dpi}, تخطّي={skip}), مكتوبٌ سابقًا={written}")
    fh=open(dst,"a",encoding="utf-8")
    for k,pi in enumerate(idxs):
        if k<written: continue
        try:
            pg=pdf[pi]; bmp=pg.render(scale=dpi/72.0); img=bmp.to_pil().convert("RGB")
            w,h=img.size; mx=max(w,h)
            if mx>ocr_engine.MAX_SIDE:
                r=ocr_engine.MAX_SIDE/float(mx); img=img.resize((int(w*r),int(h*r)))
            txt=ocr_engine._ocr_pil(img)
            fh.write("\f"+txt.strip()+"\n"); fh.flush()
            if (k+1)%5==0 or k==0: log(f"  {name}: {k+1}/{len(idxs)} صفحة")
        except Exception as e:
            log(f"  ERR page {pi}: {e}"); fh.write("\f\n"); fh.flush()
    fh.close(); open(done,"w").write("ok")
    log(f"DONE {name} -> {dst}")
    return dst

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--pdf"); ap.add_argument("--author"); ap.add_argument("--book")
    ap.add_argument("--dpi",type=int,default=300); ap.add_argument("--skip",type=int,default=3)
    ap.add_argument("--pages",default=None); ap.add_argument("--all-volumes",action="store_true")
    a=ap.parse_args()
    if not ocr_engine.available():
        log("OCR غير مُعَدّ. شغّل run_setup_ocr.bat أولًا."); sys.exit(1)
    files=[]
    if a.pdf: files=[a.pdf]
    elif a.author and a.book:
        files=shamela_import.pdf_files(a.author, a.book)
        if not a.all_volumes and files: files=files[:1]
    else:
        log("مرّرْ --pdf أو (--author و --book)."); sys.exit(1)
    if not files: log("لا ملفّات PDF."); sys.exit(1)
    for f in files:
        extract_pdf(f, dpi=a.dpi, skip=a.skip, pages=a.pages)
    log("انتهى كلُّ الملفّات.")
