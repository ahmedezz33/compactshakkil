# -*- coding: utf-8 -*-
"""
shamela_import.py — استيرادُ كتب المكتبة الشاملة (وغيرها) للقراءة والنطق والتشكيل.
ضعِ الكتبَ في مجلّد shamela/ بصيغة .txt أو .epub أو .docx، ثمّ استورِدْها.
تُستخرَجُ نصوصًا نظيفةً في data/shamela/. بلا اعتماداتٍ خارجيّة (zip/regex فقط).
"""
import os, re, zipfile, html
BASE=os.path.dirname(os.path.abspath(__file__))
SRC=os.path.join(BASE,"shamela")
OUT=os.path.join(BASE,"data","shamela")
os.makedirs(SRC,exist_ok=True); os.makedirs(OUT,exist_ok=True)

_TAG=re.compile(r"<[^>]+>")
def _strip_html(x):
    x=re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>"," ",x)
    x=re.sub(r"(?i)</p>|<br\s*/?>|</div>|</h[1-6]>","\n",x)
    x=_TAG.sub(" ",x); x=html.unescape(x)
    return "\n".join(" ".join(l.split()) for l in x.split("\n") if l.strip())

def _from_epub(path):
    out=[]
    with zipfile.ZipFile(path) as z:
        for n in sorted(n for n in z.namelist() if n.lower().endswith((".xhtml",".html",".htm"))):
            try: out.append(_strip_html(z.read(n).decode("utf-8","ignore")))
            except Exception: pass
    return "\n".join(out)

def _from_docx(path):
    with zipfile.ZipFile(path) as z:
        xml=z.read("word/document.xml").decode("utf-8","ignore")
    xml=re.sub(r"</w:p>","\n",xml)
    return "\n".join(" ".join(l.split()) for l in _TAG.sub(" ",xml).split("\n") if l.strip())

def _from_txt(path):
    for enc in ("utf-8","utf-8-sig","cp1256"):
        try: return open(path,encoding=enc).read()
        except Exception: continue
    return open(path,encoding="utf-8",errors="ignore").read()


def _from_db(path):
    """يقرأُ كتابَ الشاملة بصيغة SQLite (.db): يكتشفُ الجدولَ والعمودَ النصّيَّ
    (nass/matn/text…) ويرتّبُ بالصفحات، ثمّ يجرّدُ HTML."""
    import sqlite3
    con=sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    cur=con.cursor()
    tables=[r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    TEXTCOLS=("nass","matn","text","content","body","صفحة","النص","nص")
    best=None
    # 1) عمودٌ نصّيٌّ معروفُ الاسم
    for t in tables:
        cols=[c[1] for c in cur.execute(f"PRAGMA table_info('{t}')")]
        for cand in TEXTCOLS:
            if cand in cols: best=(t,cand); break
        if best: break
    # 2) وإلّا: أطولُ عمودٍ نصّيّ
    if not best:
        bestlen=0
        for t in tables:
            for c in cur.execute(f"PRAGMA table_info('{t}')"):
                name=c[1]
                try:
                    v=cur.execute(f"SELECT \"{name}\" FROM \"{t}\" WHERE \"{name}\" IS NOT NULL LIMIT 1").fetchone()
                    if v and isinstance(v[0],str) and len(v[0])>bestlen:
                        bestlen=len(v[0]); best=(t,name)
                except Exception: pass
    if not best: con.close(); return ""
    t,col=best
    tcols=[c[1] for c in cur.execute(f"PRAGMA table_info('{t}')")]
    order=next((f' ORDER BY "{oc}"' for oc in ("page","id","part","rowid") if oc in tcols or oc=="rowid"),"")
    try:
        rows=cur.execute(f'SELECT "{col}" FROM "{t}"{order}').fetchall()
    except Exception:
        rows=cur.execute(f'SELECT "{col}" FROM "{t}"').fetchall()
    con.close()
    raw="\n".join(r[0] for r in rows if r and r[0])
    return _strip_html(raw) if "<" in raw else "\n".join(
        " ".join(l.split()) for l in raw.split("\n") if l.strip())

def import_all(force=False):
    """يستوردُ كلَّ ملفّات shamela/ إلى data/shamela/. يرجع قائمةَ (اسم، حالة)."""
    res=[]
    for fn in sorted(os.listdir(SRC)):
        ext=fn.lower().rsplit(".",1)[-1] if "." in fn else ""
        if ext not in ("txt","epub","docx","db","sqlite"): continue
        name=os.path.splitext(fn)[0]; dst=os.path.join(OUT,name+".txt")
        if os.path.exists(dst) and not force: res.append((name,"موجود ✓")); continue
        try:
            src=os.path.join(SRC,fn)
            t=_from_epub(src) if ext=="epub" else \
              _from_docx(src) if ext=="docx" else \
              _from_db(src) if ext in ("db","sqlite") else \
              _from_txt(src)
            open(dst,"w",encoding="utf-8").write(t)
            res.append((name,f"{len(t.split())} كلمة ✅"))
        except Exception as e:
            res.append((name,f"خطأ: {e}"))
    return res

def list_books():
    try: return [os.path.splitext(f)[0] for f in sorted(os.listdir(OUT)) if f.endswith(".txt")]
    except Exception: return []

def load_book(name):
    p=os.path.join(OUT,(name or "")+".txt")
    return open(p,encoding="utf-8").read() if os.path.exists(p) else ""

def page(name, idx=0, size=1200):
    t=load_book(name)
    if not t: return "", 0
    chunks=[t[i:i+size] for i in range(0,len(t),size)] or [""]
    idx=max(0,min(int(idx),len(chunks)-1))
    return chunks[idx], len(chunks)


# ── مكتبةُ PDF (كتبٌ مصوَّرةٌ مشكَّلة — تُستخرَجُ بالـ OCR) ──────────────────
import glob as _glob
_PDF_ROOTS=[os.environ.get("SHAMELA_PDF",""), r"F:\\shamela4\\pdf",
            os.path.join(BASE,"shamela_pdf"),
            os.path.expanduser("~/mnt/pdf")]
def pdf_root():
    for r in _PDF_ROOTS:
        if r and os.path.isdir(r): return r
    return ""
def pdf_authors():
    r=pdf_root()
    if not r: return []
    return sorted(d for d in os.listdir(r) if os.path.isdir(os.path.join(r,d)))
def pdf_books(author):
    r=pdf_root()
    if not (r and author): return []
    ap=os.path.join(r,author); out=[]
    if os.path.isdir(ap):
        for d in sorted(os.listdir(ap)):
            if os.path.isdir(os.path.join(ap,d)): out.append(d)
        if not out and _glob.glob(os.path.join(ap,"*.pdf")): out=["(كتابٌ مباشر)"]
    return out
def pdf_files(author, book):
    r=pdf_root()
    if not (r and author): return []
    base=os.path.join(r,author) if book in ("(كتابٌ مباشر)","",None) else os.path.join(r,author,book)
    return sorted(_glob.glob(os.path.join(base,"*.pdf")))
