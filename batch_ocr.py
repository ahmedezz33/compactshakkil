# -*- coding: utf-8 -*-
"""
batch_ocr.py — مسحُ كتابٍ كامل (١٠٠٠ صفحةٍ أو أكثر) بالـ OCR مع التشكيل، دفعةً واحدة.

- يحفظُ كلَّ صفحةٍ فورَ إتمامِها (out/pages/page_XXXX.txt) → **استئنافٌ تلقائيّ** بعد أيِّ توقّف.
- يُخرِجُ في النهاية: كتابًا نصيًّا (book.txt) وملفَّ Word (book.docx) باستردادِ آياتِ القرآن.
- النموذجُ (Qwen2.5-VL) يُنتِجُ التشكيلَ مباشرةً، فالمخرجُ مشكَّل.

الاستعمال:
  python batch_ocr.py "F:\\path\\book.pdf"                 # كلّ الصفحات
  python batch_ocr.py book.pdf --pages 1-1000              # نطاق
  python batch_ocr.py book.pdf --struct                    # فصل الأقسام (عنوان/متن/حواشٍ)
  python batch_ocr.py book.pdf --dpi 300 --out out_book
"""
import os, sys, argparse, time, glob

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="")            # مثل 1-1000 ، فارغ=الكل
    ap.add_argument("--out", default="")
    ap.add_argument("--dpi", type=int, default=int(os.environ.get("OCR_DPI","300")))
    ap.add_argument("--struct", action="store_true")
    ap.add_argument("--no-word", action="store_true")
    a=ap.parse_args()
    if not os.path.exists(a.pdf): print("لا ملفّ:", a.pdf); return
    HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
    import ocr_engine as OE
    import pypdfium2 as pdfium
    base=a.out or (os.path.splitext(os.path.basename(a.pdf))[0]+"_ocr")
    outdir=os.path.join(HERE, base); pdir=os.path.join(outdir,"pages")
    os.makedirs(pdir, exist_ok=True)

    pdf=pdfium.PdfDocument(a.pdf); npages=len(pdf)
    idxs=OE._parse_pages(a.pages, npages)
    print(f"الكتاب: {npages} صفحة | سنعالج: {len(idxs)} | المخرج: {outdir}")
    if not OE.available():
        print("OCR غير مُعَدّ. شغّل run_setup_ocr_big.bat"); return

    done=0; t0=time.time()
    for n,pi in enumerate(idxs,1):
        fp=os.path.join(pdir, f"page_{pi+1:04d}.txt")
        if os.path.exists(fp) and os.path.getsize(fp)>0:    # استئناف: متّ مسبقًا
            done+=1; continue
        try:
            page=pdf[pi]
            bmp=page.render(scale=a.dpi/72.0); img=bmp.to_pil().convert("RGB")
            w,h=img.size; mx=max(w,h)
            if mx>OE.MAX_SIDE:
                r=OE.MAX_SIDE/float(mx); img=img.resize((int(w*r),int(h*r)))
            img=OE._preprocess(img)
            txt=OE._ocr_pil(img, structured=a.struct)
            if a.struct:
                try: txt=OE.format_sections(txt)
                except Exception: pass
            open(fp,"w",encoding="utf-8").write(txt or "")
            done+=1
        except Exception as e:
            open(fp+".err","w",encoding="utf-8").write(str(e))
            print(f"  صفحة {pi+1}: خطأ {e}")
        el=time.time()-t0; rate=done/max(el,1); eta=(len(idxs)-n)/max(rate,1e-6)
        print(f"[{n}/{len(idxs)}] صفحة {pi+1} | {rate*60:.1f} صفحة/د | متبقٍّ ~{eta/60:.0f}د", flush=True)

    # تجميعُ المخرجات
    parts=[]
    for pi in idxs:
        fp=os.path.join(pdir, f"page_{pi+1:04d}.txt")
        if os.path.exists(fp):
            t=open(fp,encoding="utf-8").read().strip()
            if t: parts.append(f"[ص {pi+1}]\n{t}")
    book="\n\n".join(parts)
    btxt=os.path.join(outdir,"book.txt"); open(btxt,"w",encoding="utf-8").write(book)
    print(f"✅ نصّ: {btxt}  ({len(parts)} صفحة)")
    if not a.no_word:
        try:
            import ocr_export
            bdoc=os.path.join(outdir,"book.docx")
            ocr_export.export_docx(book, bdoc, structured=a.struct, quran="strong")
            print(f"✅ Word: {bdoc}")
        except Exception as e:
            print("تعذّر Word:", e, "— ثبّتْ python-docx")
    print(f"تمّ. أُنجزت {done}/{len(idxs)} صفحة.")

if __name__=="__main__":
    main()
