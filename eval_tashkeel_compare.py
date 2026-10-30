# -*- coding: utf-8 -*-
"""مقارنةُ التشكيل: مشكّلُك (BERT-graft) مقابل CATT — بمقياسين للطرفين.
  (أ) مقياسُك: فئةُ الحركةِ لكلِّ حرف (split_letters_and_diacritics) → DER كلّي/بنية/حركةُ آخِر.
  (ب) مستقلّ : der_compare الخامّ (حرفيّ/كلميّ، موحّد/عادل).
يُصفّي أسطرَ الأرقام/اللاتينيِّ (تكسرُ المحاذاة)، يطبعُ المتخطَّى، ويُخرجُ Word.
بيئة: N_NEWS(150) N_CLASS(100) CATT_MODEL=eo|ed CLEAN(1) DEBUG(0) N_DBG(3)."""
import os, sys, time, datetime, re
BASE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE); sys.path.insert(0, os.path.join(BASE,"scripts"))
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
def say(*a): print(*a, flush=True)
import der_compare as D
from data.vocab_v2 import split_letters_and_diacritics as SPLIT
_DIRTY=re.compile(r"[0-9A-Za-z٠-٩۰-۹]")
CLEAN=os.environ.get("CLEAN","0")=="1"
DEBUG=os.environ.get("DEBUG","0")=="1"; N_DBG=int(os.environ.get("N_DBG","3"))
import re as _re3
_KEEPRE=_re3.compile(r"[^\u0620-\u065F\u0670 ]")
def norm(s):
    s=_KEEPRE.sub('', s); return _re3.sub(r'\s+',' ',s).strip()
def bare(s): return "".join(c for c in s if c not in D.HARAKAT)
def chunks(text, maxlen=800):
    ws=text.split(" "); out=[]; cur=""
    for w in ws:
        if len(cur)+len(w)+1>maxlen and cur: out.append(cur); cur=w
        else: cur=(cur+" "+w).strip()
    if cur: out.append(cur)
    return out or [text]
def _spans(L):
    sp=[];st=None
    for i,ch in enumerate(L):
        if ch==" ":
            if st is not None: sp.append((st,i)); st=None
        else:
            if st is None: st=i
    if st is not None: sp.append((st,len(L)))
    return sp
def der_yours(gold_lines, pred_lines):
    tot=err=it=ie=ft=fe=skip=0
    for g,p in zip(gold_lines, pred_lines):
        Lg,Cg=SPLIT(g); Lp,Cp=SPLIT(p or "")
        if len(Lg)!=len(Lp): skip+=1; continue
        fin={b-1 for a,b in _spans(Lg)}
        for i in range(len(Lg)):
            if Lg[i]==" ": continue
            tot+=1; isf=i in fin
            if isf: ft+=1
            else: it+=1
            if int(Cg[i])!=int(Cp[i]):
                err+=1
                if isf: fe+=1
                else: ie+=1
    return dict(tot=tot,err=err,it=it,ie=ie,ft=ft,fe=fe,skip=skip)
def pc(a,b): return 100*a/max(1,b)

SETS=[("أخبار","data/news_gold_clean.txt", int(os.environ.get("N_NEWS","150"))),
      ("تراث","data/ocr_classical_test_src.txt", int(os.environ.get("N_CLASS","100"))),
      ("قرآن","data/quran_gold_sample.txt", int(os.environ.get("N_QURAN","150")))]
say("… تحميلُ مشكّلِك (BERT-graft)"); import diac_pipeline
CATT=None; catt_name=""
try:
    which=os.environ.get("CATT_MODEL","eo").lower()
    from catt_tashkeel import CATTEncoderDecoder, CATTEncoderOnly
    say(f"… تحميلُ CATT ({'ED' if which=='ed' else 'EO'}) — ONNX/CPU")
    CATT=(CATTEncoderDecoder() if which=="ed" else CATTEncoderOnly()); catt_name=f"CATT-{'ED' if which=='ed' else 'EO'}"
    say("✅ CATT جاهز")
except Exception as e:
    say("⚠️ CATT غير متاح:", repr(e)[:160])
def catt_line(text):
    parts=chunks(text,800)
    try: res=list(CATT.do_tashkeel_batch(parts, verbose=False))
    except Exception:
        res=[]
        for p in parts:
            try: res.append(CATT.do_tashkeel(p, verbose=False))
            except Exception: res.append(p)
    return " ".join(res)

rows=[]
for name,path,n in SETS:
    if not os.path.exists(path): say(f"تخطّي {path}"); continue
    gold=[l.strip() for l in open(path,encoding="utf-8") if l.strip()]
    if CLEAN:
        before=len(gold); gold=[g for g in gold if not _DIRTY.search(g)]
        say(f"   تصفية {name}: حُذف {before-len(gold)} سطرًا فيه أرقام/لاتيني")
    gold=gold[:n]; bares=[bare(g) for g in gold]
    say(f"\n===== {name} — {len(gold)} سطر =====")
    bert=[]
    for j,b in enumerate(bares):
        try: bert.append(diac_pipeline.diacritize(b, False)[0] or b)
        except Exception: bert.append(b)
        if (j+1)%50==0: say(f"   BERT {j+1}/{len(bares)}")
    goldN=[norm(x) for x in gold]; bertN=[norm(x) for x in bert]
    Y=der_yours(goldN,bertN); B=D.der(goldN,bertN); rows.append((name,"مشكّلُك (BERT-graft)",Y,B))
    say(f"   [مشكّلُك] مقياسُك DER {pc(Y['err'],Y['tot']):.2f}% (بنية {pc(Y['ie'],Y['it']):.2f}% · آخِر {pc(Y['fe'],Y['ft']):.2f}%) · متخطّى {Y['skip']}  |  مستقلّ عادل حرفيّ {pc(B['lerr_f'],B['letters']):.2f}%")
    if CATT is not None:
        cp=[]
        for j,b in enumerate(bares):
            cp.append(catt_line(b))
            if (j+1)%25==0: say(f"   CATT {j+1}/{len(bares)}")
        cpN=[norm(x) for x in cp]
        Yc=der_yours(goldN,cpN); Bc=D.der(goldN,cpN); rows.append((name,catt_name,Yc,Bc))
        say(f"   [{catt_name}] مقياسُك DER {pc(Yc['err'],Yc['tot']):.2f}% (بنية {pc(Yc['ie'],Yc['it']):.2f}% · آخِر {pc(Yc['fe'],Yc['ft']):.2f}%) · متخطّى {Yc['skip']}  |  مستقلّ عادل حرفيّ {pc(Bc['lerr_f'],Bc['letters']):.2f}%")
        if DEBUG:
            os.makedirs("reports", exist_ok=True)
            with open(f"reports/dbg_{name}.txt","w",encoding="utf-8") as fh:
                for i in range(min(N_DBG,len(gold))):
                    fh.write("GOLD: "+gold[i]+"\n"+"BERT: "+bert[i]+"\n"+"CATT: "+cp[i]+"\n---\n")
            say(f"   (دَبّغ: reports/dbg_{name}.txt)")

try:
    from docx import Document
    doc=Document(); doc.add_heading("مقارنةُ التشكيل: مشكّلُك مقابل CATT — بمقياسين", level=0)
    doc.add_paragraph(f"التاريخ: {datetime.date.today().isoformat()}. كلُّ نموذجٍ قِيسَ بمقياسين على نفسِ الذهبيّ (أُزيلت أسطرُ الأرقام/اللاتينيِّ لأنّها تكسرُ المحاذاة).")
    doc.add_paragraph("• مقياسُك (الأساس): مقارنةُ فئةِ الحركةِ لكلِّ حرفٍ كما في eval_graft.py — DER كلّي، البنيةُ (داخليّ)، حركةُ الآخِر (إعراب).")
    doc.add_paragraph("• مستقلّ: مقارنةُ الحركاتِ خامًّا (der_compare) — أصرمُ، أرقامُه أعلى؛ نفسُ المسطرةِ للطرفين. قد يتأثّرُ باختلافِ صيغةِ الإخراج.")
    for st in [s for s in ["أخبار","تراث"] if any(r[0]==s for r in rows)]:
        doc.add_heading(f"مجموعة: {st}", level=1)
        rr=[r for r in rows if r[0]==st]
        cols=["النموذج","مقياسُك DER","بنية","حركةُ آخِر","مستقلّ حرفيّ موحّد","حرفيّ عادل","كلميّ عادل"]
        tb=doc.add_table(rows=1, cols=len(cols))
        try: tb.style="Light Grid Accent 1"
        except Exception: pass
        for i,h in enumerate(cols): tb.rows[0].cells[i].text=h
        best=min((pc(Y['err'],Y['tot']) for _,_,Y,_ in rr), default=0)
        for _,model,Y,B in rr:
            c=tb.add_row().cells
            vals=[model, f"{pc(Y['err'],Y['tot']):.2f}%", f"{pc(Y['ie'],Y['it']):.2f}%", f"{pc(Y['fe'],Y['ft']):.2f}%",
                  f"{pc(B['lerr_u'],B['letters']):.2f}%", f"{pc(B['lerr_f'],B['letters']):.2f}%", f"{pc(B['werr_f'],B['words']):.2f}%"]
            for i,v in enumerate(vals): c[i].text=v
            if abs(pc(Y['err'],Y['tot'])-best)<1e-9:
                for rn in c[1].paragraphs[0].runs: rn.bold=True
        win=min(rr, key=lambda r: pc(r[2]['err'],r[2]['tot']))
        doc.add_paragraph(f"الأقلُّ DER بمقياسِك على «{st}»: {win[1]}.")
    os.makedirs("reports", exist_ok=True)
    outp=os.path.join("reports", f"tashkeel_compare_{int(time.time())}.docx"); doc.save(outp)
    say(f"\n✅ ملفُّ Word: {os.path.abspath(outp)}")
except Exception as e:
    say(f"\n(تعذّر ملفُّ Word: {repr(e)[:140]})")
