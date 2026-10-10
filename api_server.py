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
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).parent
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
    if "diac" not in _ENG:
        from bert_graft_infer import GraftInfer
        _ENG["diac"] = GraftInfer()
    return _ENG["diac"]
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

@app.get("/health")
def health():
    return {"status": "ok", "service": "CompactShakkil API", "version": "1.0"}

@app.post("/v1/diacritize")
def diacritize(inp: TextIn, x_api_key: str = Header(None)):
    text = (inp.text or "").strip()
    if not text: raise HTTPException(400, "النصّ فارغ")
    units = len(text)
    charge_key(x_api_key, units)
    try:
        out = eng_diac().diacritize(text)
    except Exception as e:
        raise HTTPException(500, f"خطأ تشكيل: {e}")
    log_usage(x_api_key, "diacritize", units, {"chars": units})
    return {"input": text, "diacritized": out, "chars": units}

@app.post("/v1/pronounce")
def pronounce(inp: TextIn, x_api_key: str = Header(None)):
    text = (inp.text or "").strip()
    if not text: raise HTTPException(400, "النصّ فارغ")
    units = len(text)
    charge_key(x_api_key, units)
    try:
        ipa, latin = eng_g2p().phonemize(text, inp.mode or "waqf")
    except Exception as e:
        raise HTTPException(500, f"خطأ نطق: {e}")
    log_usage(x_api_key, "pronounce", units, {"chars": units})
    return {"input": text, "ipa": ipa, "latin": latin, "mode": inp.mode}

@app.post("/v1/ocr")
async def ocr(x_api_key: str = Header(None), file: UploadFile = File(...)):
    units = int(os.environ.get("OCR_UNITS_PER_PAGE", "1000"))  # صفحةٌ ضوئيّةٌ أغلى من الحرف
    charge_key(x_api_key, units)
    oe = eng_ocr()
    if not oe.available():
        raise HTTPException(503, "محرّك OCR غير مُعدّ على الخادم")
    data = await file.read()
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
