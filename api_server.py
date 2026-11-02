# -*- coding: utf-8 -*-
"""
CompactShakkil API — خادمٌ تجاريٌّ يُغلّف محرّكات المشروع:
  • /v1/diacritize  تشكيل النصّ
  • /v1/pronounce   النطق (IPA + نقحرة لاتينيّة) — مناسب لأسماء المنتجات والإعلانات
  • /v1/ocr         استخراج النصّ من صورة
المصادقة: ترويسة  X-API-Key.  الحصّة والفوترة: api_keys.json + api_usage.log.
التشغيل:  run_api.bat   (أو:  uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 1)
"""
import os, json, time, tempfile, threading
try:
    import quran_integrity; quran_integrity.verify()   # حارسُ سلامةِ القرآن
except SystemExit:
    raise
except Exception as _qi:
    print("quran_integrity skip:", _qi)
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

ROOT = Path(__file__).parent
import sys as _sys
for _p in (str(ROOT), str(ROOT / "scripts")):
    if _p not in _sys.path: _sys.path.insert(0, _p)
KEYS_FILE = Path(os.environ.get("API_KEYS_FILE", ROOT / "api_keys.json"))
USAGE_LOG = ROOT / "api_usage.log"
_lock = threading.Lock()

# ───────────────────── المفاتيح والحصّة ─────────────────────
def load_keys():
    if KEYS_FILE.exists():
        try: return json.loads(KEYS_FILE.read_text(encoding="utf-8"))
        except Exception: return {}
    return {}

def save_keys(d):
    tmp = KEYS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(KEYS_FILE)

def charge_key(api_key, units):
    """يتحقّق من المفتاح ويخصم الوحدات (حروف/صفحات). يرفع 401/402 عند الفشل."""
    if not api_key:
        raise HTTPException(401, "أرسل المفتاح في ترويسة X-API-Key")
    with _lock:
        keys = load_keys()
        rec = keys.get(api_key)
        if not rec or not rec.get("active", True):
            raise HTTPException(401, "مفتاح غير صالح أو معطّل")
        limit = rec.get("limit_units")
        used = rec.get("used_units", 0)
        if limit is not None and used + units > limit:
            raise HTTPException(402, "تجاوزت حدّ الاستعمال — جدّد الاشتراك")
        rec["used_units"] = used + units
        keys[api_key] = rec
        save_keys(keys)
        return rec

# ── وضع التجربة المجّانيّة (بلا مفتاح): حدٌّ لكلّ IP وطولٌ محدود ──
_DEMO = {}
DEMO_PER_HOUR = int(os.environ.get("DEMO_PER_HOUR", "40"))
DEMO_MAX_CHARS = int(os.environ.get("DEMO_MAX_CHARS", "200"))
def _client_ip(request):
    xff = request.headers.get("x-forwarded-for", "")
    if xff: return xff.split(",")[0].strip()
    return request.client.host if request.client else "?"
_RL = {}
RL_PER_MIN = int(os.environ.get("RL_PER_MIN", "120"))      # طلبات/دقيقة لكلِّ هويّة
MAX_CHARS  = int(os.environ.get("MAX_CHARS", "20000"))     # سقفُ طولِ النصّ (حمايةٌ من DoS)
def rate_limit(identity):
    now = time.time()
    with _lock:
        q = _RL.setdefault(identity, [])
        cut = now - 60
        while q and q[0] < cut: q.pop(0)
        if len(q) >= RL_PER_MIN:
            raise HTTPException(429, "معدّلُ الطلباتِ مرتفعٌ جدًّا — تمهّلْ لحظةً")
        q.append(now)

def demo_or_charge(request, api_key, text):
    rate_limit(api_key or _client_ip(request))         # حدُّ معدّلٍ لحظيّ (مفتاح أو IP)
    if len(text) > MAX_CHARS:
        raise HTTPException(413, f"النصُّ أطولُ من الحدِّ ({MAX_CHARS} حرفًا)")
    if api_key:
        charge_key(api_key, len(text)); return "paid"
    if len(text) > DEMO_MAX_CHARS:
        raise HTTPException(413, f"\u0627\u0644\u062a\u062c\u0631\u0628\u0629 \u0645\u062d\u062f\u0648\u062f\u0629 \u0628\u0640{DEMO_MAX_CHARS} \u062d\u0631\u0641\u064b\u0627 \u2014 \u0627\u062d\u0635\u0644 \u0639\u0644\u0649 \u0645\u0641\u062a\u0627\u062d \u0644\u0644\u0645\u0632\u064a\u062f")
    ip = _client_ip(request); now = time.time()
    with _lock:
        st = _DEMO.get(ip)
        if not st or now - st[0] > 3600: st = [now, 0]
        if st[1] >= DEMO_PER_HOUR:
            raise HTTPException(429, "\u062a\u062c\u0627\u0648\u0632\u062a \u062d\u062f\u0651 \u0627\u0644\u062a\u062c\u0631\u0628\u0629 \u0644\u0647\u0630\u0647 \u0627\u0644\u0633\u0627\u0639\u0629 \u2014 \u0627\u062d\u0635\u0644 \u0639\u0644\u0649 \u0645\u0641\u062a\u0627\u062d")
        st[1] += 1; _DEMO[ip] = st
    return "demo"

def log_usage(api_key, endpoint, units, meta=None):
    row = {"t": round(time.time()), "key": (api_key or "")[:10],
           "endpoint": endpoint, "units": units}
    if meta: row.update(meta)
    try:
        with open(USAGE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception: pass

# ───────────────────── المحرّكات (تحميلٌ كسول) ─────────────────────
_ENG = {}
def eng_diac():
    import diac_pipeline
    return diac_pipeline._inf()
def eng_g2p():
    if "g2p" not in _ENG:
        import g2p; _ENG["g2p"] = g2p
    return _ENG["g2p"]
def eng_ocr():
    if "ocr" not in _ENG:
        import ocr_engine; _ENG["ocr"] = ocr_engine
    return _ENG["ocr"]

# ───────────────────── التطبيق ─────────────────────
app = FastAPI(title="CompactShakkil API", version="1.0",
              description="تشكيل + نطق + OCR عربيّ")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

class TextIn(BaseModel):
    text: str
    mode: str = "waqf"

_ROOT_HTML = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>CompactShakkil API</title>
<meta name="description" content="واجهة برمجة عربية: تشكيل النص، النطق الصحيح (IPA ونقحرة لاتينية) لأسماء المنتجات، واستخراج النص من الصور (OCR).">
<style>
:root{--bg:#0f1512;--card:#1a211e;--fg:#eef2ee;--mut:#9db0a6;--acc:#49c3a6;--acc2:#0f6f5c;--gold:#d8ad5c;--ln:#2c3531}
*{box-sizing:border-box}body{font-family:system-ui,'Segoe UI',Tahoma,sans-serif;background:var(--bg);color:var(--fg);margin:0;line-height:1.8}
.wrap{max-width:720px;margin:0 auto;padding:40px 18px}
h1{color:var(--acc);font-size:2rem;margin:0 0 4px;text-align:center}
.sub{color:var(--mut);text-align:center;margin:0 0 26px}
.card{background:var(--card);border:1px solid var(--ln);border-radius:16px;padding:20px}
textarea{width:100%;min-height:90px;background:var(--bg);color:var(--fg);border:1px solid var(--ln);border-radius:10px;padding:12px;font:inherit;font-size:1.15rem}
.row{display:flex;gap:10px;margin-top:12px;flex-wrap:wrap}
button{flex:1;min-width:120px;background:var(--acc2);color:#fff;border:0;border-radius:10px;padding:12px;font:inherit;font-weight:600;cursor:pointer}
button:hover{background:var(--acc)}
.out{margin-top:16px;min-height:28px;font-size:1.3rem;color:var(--acc);word-wrap:break-word}
.out .lat{display:block;font-size:1rem;color:var(--gold);margin-top:6px;direction:ltr;text-align:right}
.err{color:#e88}
.links{text-align:center;margin-top:24px;color:var(--mut)}
.links a{color:var(--acc)}
code{background:var(--card);padding:2px 7px;border-radius:5px;color:var(--gold)}
.note{font-size:.82rem;color:var(--mut);text-align:center;margin-top:10px}
</style></head><body><div class="wrap">
<h1>CompactShakkil</h1>
<p class="sub">تشكيل · نطق (IPA/لاتيني) · استخراج نصّ — عربيّ</p>
<div class="card">
<textarea id="t" placeholder="اكتب جملة عربية…">حذرت منظمة الصحة العالمية</textarea>
<div class="row"><button onclick="go('diacritize')">شكّل</button><button onclick="go('pronounce')">انطق</button><button onclick="say()">استمع 🔊</button></div>
<div class="out" id="o"></div>
<div class="note">تجربة مجّانيّة محدودة. للاستعمال الكامل احصل على مفتاح API.</div>
</div>
<div class="links">الأسعار: <a href="/pricing">/pricing</a> · الوثائق: <a href="/docs">/docs</a> · للحصول على مفتاح: <code>ahmedezz3@gmail.com</code></div>
</div>
<script>
async function go(ep){
 var t=document.getElementById('t').value.trim(), o=document.getElementById('o');
 if(!t){o.textContent='اكتب نصًّا أولًا';return}
 o.textContent='…';
 try{
  var r=await fetch('/v1/'+ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});
  var d=await r.json();
  if(!r.ok){o.innerHTML='<span class="err">'+(d.detail||'خطأ')+'</span>';return}
  if(ep==='diacritize')o.textContent=d.diacritized;
  else o.innerHTML=d.latin+'<span class="lat">'+d.ipa+'</span>';
 }catch(e){o.innerHTML='<span class="err">تعذّر الاتصال</span>'}
}

async function say(){
 var t=document.getElementById('t').value.trim(), o=document.getElementById('o');
 if(!t){o.textContent='اكتب نصًّا أولًا';return}
 o.textContent='\u2026 \u062c\u0627\u0631\u064d \u0627\u0644\u062a\u0648\u0644\u064a\u062f';
 try{
  var r=await fetch('/v1/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});
  if(!r.ok){var d=await r.json();o.innerHTML='<span class=\"err\">'+(d.detail||'\u062e\u0637\u0623')+'</span>';return}
  var b=await r.blob(), u=URL.createObjectURL(b);
  o.innerHTML='<audio controls autoplay src=\"'+u+'\"></audio>';
 }catch(e){o.innerHTML='<span class=\"err\">\u062a\u0639\u0630\u0651\u0631 \u0627\u0644\u0627\u062a\u0635\u0627\u0644</span>'}
}
</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
def root():
    return _ROOT_HTML

_PRICING_HTML = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>أسعار CompactShakkil</title>
<meta name="description" content="أسعار واجهة CompactShakkil: تشكيل ونطق واستخراج نص عربي. باقات تجريبية واحترافية ومؤسسات.">
<style>
:root{--bg:#0f1512;--card:#1a211e;--fg:#eef2ee;--mut:#9db0a6;--acc:#49c3a6;--gold:#d8ad5c;--ln:#2c3531}
*{box-sizing:border-box}body{font-family:system-ui,'Segoe UI',Tahoma,sans-serif;background:var(--bg);color:var(--fg);margin:0;line-height:1.8}
.wrap{max-width:960px;margin:0 auto;padding:40px 18px}
h1{color:var(--acc);text-align:center;margin:0 0 4px}.sub{color:var(--mut);text-align:center;margin:0 0 30px}
h2{font-size:1.3rem;margin:34px 0 14px}
.svc,.tiers{display:grid;gap:16px;grid-template-columns:repeat(3,1fr)}
@media(max-width:760px){.svc,.tiers{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--ln);border-radius:14px;padding:20px}
.card h3{color:var(--acc);margin:0 0 6px}.card p{color:var(--mut);margin:0;font-size:.95rem}
.tier{background:var(--card);border:1px solid var(--ln);border-radius:16px;padding:22px;display:flex;flex-direction:column}
.tier.feat{border-color:var(--acc)}.price{font-size:2rem;font-weight:700;margin:8px 0}.price small{font-size:.9rem;color:var(--mut);font-weight:400}
.tier ul{list-style:none;padding:0;margin:12px 0 0;display:flex;flex-direction:column;gap:8px}.tier li::before{content:"\u2713 ";color:var(--acc)}
.unit{color:var(--mut);text-align:center;font-size:.9rem;margin-top:10px}
pre{background:#0b100e;border:1px solid var(--ln);border-radius:12px;padding:16px;overflow-x:auto;direction:ltr;text-align:left;color:#dfe9e4;font-family:ui-monospace,monospace;font-size:.85rem}
.cta{text-align:center;margin-top:30px}code{background:var(--card);padding:2px 7px;border-radius:5px;color:var(--gold)}a{color:var(--acc)}
</style></head><body><div class="wrap">
<h1>CompactShakkil API</h1><p class="sub">تشكيل · نطق (IPA/لاتيني) · استخراج نصّ — عربيّ</p>
<div class="svc">
<div class="card"><h3>التشكيل</h3><p>يعيد النصّ مشكّلًا بالكامل مع ضبط الإعراب.</p></div>
<div class="card"><h3>النطق</h3><p>نطق صحيح لأسماء المنتجات والعلامات والإعلانات.</p></div>
<div class="card"><h3>استخراج النصّ</h3><p>يقرأ النصّ العربيّ من صور الصفحات والمستندات.</p></div>
</div>
<h2>الأسعار</h2>
<div class="tiers">
<div class="tier"><h3>تجريبيّ</h3><div class="price">0<small> ر.س</small></div><ul><li>١٠٬٠٠٠ وحدة/شهر</li><li>\u2248 ١٬٦٠٠ كلمة أو ١٠ صفحات OCR</li><li>كل الخدمات</li></ul></div>
<div class="tier feat"><h3>احترافيّ</h3><div class="price">149<small> ر.س/شهر</small></div><ul><li>٥٠٠٬٠٠٠ وحدة/شهر</li><li>أولويّة في المعالجة</li><li>تقرير استعمال شهريّ</li><li>دعم بالبريد</li></ul></div>
<div class="tier"><h3>مؤسّسات</h3><div class="price">حسب الطلب</div><ul><li>وحدات غير محدودة</li><li>نطاق خاصّ واتفاقيّة خدمة</li><li>تشغيل داخليّ ممكن</li></ul></div>
</div>
<p class="unit">الوحدة = حرف واحد (تشكيل/نطق)، والصفحة الضوئيّة (OCR) = ١٠٠٠ وحدة. أسعار استرشاديّة.</p>
<h2>ابدأ في دقائق</h2>
<pre>curl -X POST https://shakkil.duckdns.org/v1/pronounce \\
  -H "X-API-Key: cs_xxx" -H "Content-Type: application/json" \\
  -d '{"text":"قَهْوَةُ الصَّبَاحِ"}'</pre>
<div class="cta">جرّب الآن: <a href="/">الرئيسيّة</a> · الوثائق: <a href="/docs">/docs</a><br>للحصول على مفتاح: <code>ahmedezz3@gmail.com</code></div>
</div></body></html>"""

@app.get("/pricing", response_class=HTMLResponse)
def pricing():
    return _PRICING_HTML


@app.get("/health")
def health():
    return {"status": "ok", "service": "CompactShakkil API", "version": "1.0"}

@app.post("/v1/diacritize")
def diacritize(inp: TextIn, request: Request, x_api_key: str = Header(None)):
    text = (inp.text or "").strip()
    if not text: raise HTTPException(400, "النصّ فارغ")
    auth = demo_or_charge(request, x_api_key, text)
    try:
        import diac_pipeline
        out = diac_pipeline.diacritize(text, True)[0]
    except Exception as e:
        raise HTTPException(500, f"خطأ تشكيل: {e}")
    log_usage(x_api_key or "demo", "diacritize", len(text), {"chars": len(text), "auth": auth})
    return {"input": text, "diacritized": out, "chars": len(text), "auth": auth}

@app.post("/v1/pronounce")
def pronounce(inp: TextIn, request: Request, x_api_key: str = Header(None)):
    text = (inp.text or "").strip()
    if not text: raise HTTPException(400, "النصّ فارغ")
    auth = demo_or_charge(request, x_api_key, text)
    try:
        import diac_pipeline
        dia = diac_pipeline.diacritize(text, True)[0] or text   # شكّلْ أوّلًا (كالتطبيق) ثمّ انقحِرْ
        ipa, latin = eng_g2p().phonemize(dia, inp.mode or "waqf")
    except Exception as e:
        raise HTTPException(500, f"خطأ نطق: {e}")
    log_usage(x_api_key or "demo", "pronounce", len(text), {"chars": len(text), "auth": auth})
    return {"input": text, "diacritized": dia, "ipa": ipa, "latin": latin, "mode": inp.mode, "auth": auth}

def _render_mixed_api(spans, mode):
    """يدمجُ نصًّا مختلطًا: القرآنُ تلاوةٌ حقيقيّة، والعاديُّ بـ edge — مطابقةً لتطبيقِ app_teach._render_mixed."""
    import os, tempfile
    import numpy as np, soundfile as sf
    import quran_audio, tts_engine, diac_pipeline
    from pronounce import edge_prepare
    try:
        from lafz_splice import _read_any as _read
    except Exception:
        def _read(path, sr):
            import subprocess, shutil
            ff = shutil.which("ffmpeg") or os.path.join(os.getcwd(), "venv", "Scripts", "ffmpeg.exe")
            tmp = tempfile.mktemp(suffix=".wav")
            subprocess.run([ff, "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(sr), tmp], check=True)
            x, _ = sf.read(tmp, dtype="float32")
            try: os.remove(tmp)
            except Exception: pass
            return x
    SR = 24000; pieces = []; gap = np.zeros(int(SR * 0.12), dtype="float32")
    for sp in spans:
        wp = None
        try:
            if sp["type"] == "quran":
                wp = quran_audio._concat_codes(sp["codes"])
            else:
                txt = sp.get("text", "").strip()
                if not txt: continue
                dia = diac_pipeline.diacritize(txt, True)[0]
                try:
                    import lafz_splice
                    if lafz_splice.available():
                        wp = lafz_splice.read_with_lafz(dia, mode=mode)
                except Exception: wp = None
                if not wp:
                    spoken = edge_prepare(dia, mode=mode)
                    wp, _ = tts_engine.synthesize(spoken, voice=tts_engine.default_voice(), rate_pct=0, word_gap=0)
            if not wp: continue
            x = _read(wp, SR)
            if len(x): pieces.append(x); pieces.append(gap)
        except Exception as e:
            print("mixed seg err:", e)
    if not pieces: return None
    out = np.concatenate(pieces).astype("float32")
    op = os.path.join(tempfile.gettempdir(), "mixed_read.wav")
    sf.write(op, out, SR, subtype="PCM_16")
    return op

@app.post("/v1/speak")
def speak(inp: TextIn, request: Request, x_api_key: str = Header(None)):
    text = (inp.text or "").strip()
    if not text: raise HTTPException(400, "النصّ فارغ")
    auth = demo_or_charge(request, x_api_key, text)
    import tempfile, tts_engine
    mode = "waqf"
    # مطابقةُ التطبيق: تلاوةُ القارئِ الحقيقيّةُ للقرآن (آيةً أو مقطعًا)، ثمّ المختلط
    try:
        import quran_audio as _qa
        ap = _qa.audio_path(text)
        if ap and os.path.exists(ap):
            _d = open(ap, "rb").read()
            _mt = "audio/wav" if ap.lower().endswith(".wav") else "audio/mpeg"
            log_usage(x_api_key or "demo", "speak", len(text), {"chars": len(text), "auth": auth, "quran": True})
            return Response(content=_d, media_type=_mt)
        _spans = _qa.split_quran_spans(text)
        if len(_spans) > 1 and any(sp.get("type") == "quran" for sp in _spans):
            _mp = _render_mixed_api(_spans, mode)
            if _mp and os.path.exists(_mp):
                _d = open(_mp, "rb").read()
                log_usage(x_api_key or "demo", "speak", len(text), {"chars": len(text), "auth": auth, "mixed": True})
                return Response(content=_d, media_type="audio/wav")
    except Exception as _qe:
        print("quran audio:", _qe)
    try:
        import diac_pipeline
        dia = diac_pipeline.diacritize(text, True)[0]
    except Exception:
        dia = text
    # مطابقةُ التطبيق: سبكُ لفظِ الجلالةِ الحقيقيّ (تلاوةُ قارئ) للأصواتِ العصبيّة إن توفّر
    try:
        import lafz_splice
        if lafz_splice.available():
            lp = lafz_splice.read_with_lafz(dia, mode="waqf", voice=tts_engine.default_voice(), rate_pct=0)
            if lp and os.path.exists(lp):
                _d = open(lp, "rb").read()
                _mt = "audio/wav" if lp.lower().endswith(".wav") else "audio/mpeg"
                log_usage(x_api_key or "demo", "speak", len(text), {"chars": len(text), "auth": auth, "lafz": True})
                return Response(content=_d, media_type=_mt)
    except Exception as _le:
        print("lafz:", _le)
    try:
        from pronounce import edge_prepare
        spoken = edge_prepare(dia, mode="waqf")
    except Exception:
        spoken = dia
    out = tempfile.mktemp(suffix=".mp3")
    try:
        tts_engine._edge_save(spoken, tts_engine.default_voice(), "+0%", "+0Hz", out)
    except Exception:
        try: tts_engine._gtts_save(spoken, out)
        except Exception as e: raise HTTPException(500, f"خطأ صوت: {e}")
    try:
        data = open(out, "rb").read()
    finally:
        try: os.unlink(out)
        except Exception: pass
    log_usage(x_api_key or "demo", "speak", len(text), {"chars": len(text), "auth": auth})
    return Response(content=data, media_type="audio/mpeg")

@app.post("/v1/ocr")
async def ocr(x_api_key: str = Header(None), file: UploadFile = File(...)):
    units = int(os.environ.get("OCR_UNITS_PER_PAGE", "1000"))  # صفحةٌ ضوئيّةٌ أغلى من الحرف
    rate_limit(x_api_key or "ocr_anon")                        # حدُّ معدّلٍ لحظيّ
    charge_key(x_api_key, units)
    oe = eng_ocr()
    if not oe.available():
        raise HTTPException(503, "محرّك OCR غير مُعدّ على الخادم")
    data = await file.read()
    _mb = int(os.environ.get("OCR_MAX_MB", "10"))
    if len(data) > _mb * 1024 * 1024:
        raise HTTPException(413, f"حجمُ الملفِّ أكبرُ من {_mb}MB")
    suffix = Path(file.filename or "img.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
        tf.write(data); tmp = tf.name
    try:
        text = oe.ocr_any(tmp)
    except Exception as e:
        raise HTTPException(500, f"خطأ OCR: {e}")
    finally:
        try: os.unlink(tmp)
        except Exception: pass
    log_usage(x_api_key, "ocr", units, {"file": file.filename, "pages": 1})
    return {"text": text}

@app.post("/admin/reload")
def admin_reload(x_admin_token: str = Header(None)):
    """يعيدُ تحميلَ منطقِ المعالجةِ من الملفّاتِ دونَ إيقافِ الخدمةِ ولا صلاحيّةِ مسؤول.
    محميٌّ برمزٍ في admin_token.txt. الاستدعاء: POST /admin/reload مع ترويسة X-Admin-Token."""
    try:
        tok = open(ROOT / "admin_token.txt", encoding="utf-8").read().strip()
    except Exception:
        raise HTTPException(503, "لا رمزَ مشرفٍ مضبوط")
    if not tok or x_admin_token != tok:
        raise HTTPException(403, "ممنوع")
    import importlib, sys as _s
    saved_inf = None
    try:
        import diac_pipeline as _dp
        saved_inf = _dp._STATE.get("inf")        # احفظِ النموذجَ المحمَّلَ لئلّا يُعادَ تحميلُه
    except Exception:
        pass
    reloaded = []
    for name in ["num2ar", "iraab_fix", "qaida_voice", "g2p", "quran_audio", "pronounce", "diac_pipeline", "ocr_engine"]:
        m = _s.modules.get(name)
        if m is not None:
            try:
                importlib.reload(m); reloaded.append(name)
            except Exception as e:
                print("reload", name, ":", e)
    try:
        import diac_pipeline as _dp2
        if saved_inf is not None:
            _dp2._STATE["inf"] = saved_inf       # أعِدْ ربطَ النموذج
    except Exception:
        pass
    _ENG.clear()                                  # محرّكاتُ api_server الكسولةُ تُعادُ عندَ الطلب
    return {"ok": True, "reloaded": reloaded}

@app.get("/v1/usage")
def usage(x_api_key: str = Header(None)):
    if not x_api_key: raise HTTPException(401, "X-API-Key مطلوب")
    rec = load_keys().get(x_api_key)
    if not rec: raise HTTPException(401, "مفتاح غير صالح")
    return {"name": rec.get("name"), "used_units": rec.get("used_units", 0),
            "limit_units": rec.get("limit_units"), "active": rec.get("active", True)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("API_HOST", "0.0.0.0"),
                port=int(os.environ.get("API_PORT", "8000")))
