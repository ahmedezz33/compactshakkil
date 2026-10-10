# -*- coding: utf-8 -*-
"""
build_qaida_voices.py — يملأ مكتبةَ وحدات القاعدة النورانيّة آليًّا (مجّانًا) بمحرّك edge.

كلُّ «وحدة» = حرفٌ بحركته (بَ، بُ، آ، أً…). تُولَّد مرّةً واحدةً بصوتٍ عصبيٍّ
مجّانيٍّ وتُحفَظ WAV في recordings/units/ بنفس مفتاح المركّب، فتعمل فورًا في
«انطق بالوحدات». الوحدةُ المفردةُ ينطقها المحرّكُ صحيحةً لأنّها معزولة.

يحترم تسجيلاتِك: لا يمسُّ وحدةً سجّلتَها بصوتك (إلّا مع --force).
يميّز المولَّدَ آليًّا في recordings/units_source.json، فتقدر تعيد توليد
المولَّد فقط بـ --refresh-tts دون المساس بصوتك.

التشغيل:
    pip install edge-tts imageio-ffmpeg
    python build_qaida_voices.py                # يملأ الناقصَ فقط
    python build_qaida_voices.py --refresh-tts  # يعيد توليد المولَّد آليًّا فقط
    python build_qaida_voices.py --force         # يعيد توليد كلّ شيء (يشمل صوتك!)
    python build_qaida_voices.py --dry           # عرضٌ فقط بلا توليد
    python build_qaida_voices.py --voice ar-EG-ShakirNeural   # صوتٌ آخَر
"""
import os, sys, json, hashlib, subprocess, tempfile, wave
try: import audioop
except Exception: audioop = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qaida, qaida_voice as qv
from pronounce import _units
import tts_engine

def _trim_wav(path, pad_ms=25, win_ms=5, thresh_ratio=0.06, floor=250):
    """يقصُّ الصمتَ من طرفَي ملفّ WAV (مونو 16-بت) مع هامشٍ صغير — لنطقٍ متّصل."""
    if audioop is None: return
    try:
        with wave.open(path, "rb") as w:
            nch, sw, fr, nf = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            data = w.readframes(nf)
    except Exception:
        return
    if sw != 2 or nch != 1 or not data:
        return
    try: peak = audioop.max(data, 2)
    except Exception: return
    thr = max(floor, int(peak * thresh_ratio))
    win = max(1, int(fr * win_ms / 1000)) * 2      # بايتات لكلّ نافذة
    s = 0
    while s < len(data):
        c = data[s:s+win]
        if not c or audioop.max(c, 2) > thr: break
        s += win
    e = len(data)
    while e > s:
        c = data[max(s, e-win):e]
        if not c or audioop.max(c, 2) > thr: break
        e -= win
    if e <= s: return                               # كلُّه صمت → أبقِه
    pad = int(fr * pad_ms / 1000) * 2
    s = max(0, s - pad); e = min(len(data), e + pad)
    out = data[s:e]
    if len(out) < int(fr * 0.05) * 2: return        # قصيرٌ جدًّا → أبقِ الأصل
    try:
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr); w.writeframes(out)
    except Exception:
        pass

RATE = qv.RATE
DIR  = qv.DIR
SRC  = os.path.join("recordings", "units_source.json")

# أسماءُ الحروف (لوحدات القسم الاختياريّ: حرفٌ مفردٌ بلا حركة يُنطَق باسمه)
NAMES = {"ب":"باء","ت":"تاء","ث":"ثاء","ج":"جيم","ح":"حاء","خ":"خاء","د":"دال",
 "ذ":"ذال","ر":"راء","ز":"زاي","س":"سين","ش":"شين","ص":"صاد","ض":"ضاد","ط":"طاء",
 "ظ":"ظاء","ع":"عين","غ":"غين","ف":"فاء","ق":"قاف","ك":"كاف","ل":"لام","م":"ميم",
 "ن":"نون","ه":"هاء","ء":"همزة"}
# حروفُ المدّ المفردة: تُنطَق مدًّا خالصًا لا اسمًا (وإلّا فسدت القراءة)
MADD_TEXT = {"ا":"آ", "آ":"آ", "و":"أوو", "ي":"إيي"}
# وحداتٌ يُنصَح بمراجعتها سمعيًّا (المدُّ المفردُ قد يحتاج إعادةَ تسجيلٍ بصوتك)
VERIFY = set(MADD_TEXT)

def _text_for(disp, key):
    """النصُّ الذي يُنطَق لتوليد هذه الوحدة."""
    if key in MADD_TEXT:            # المدُّ أوّلًا (يغلب اسمَ الحرف لـ و/ي)
        return MADD_TEXT[key]
    if disp in MADD_TEXT:
        return MADD_TEXT[disp]
    if disp in NAMES:              # حرفٌ مفردٌ بلا حركة → اسمُه
        return NAMES[disp]
    return disp                     # حرفٌ بحركةٍ/سكونٍ/شدّةٍ/تنوين → كما هو

def _ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        import shutil
        return shutil.which("ffmpeg")

def _to_wav(mp3, wav, ff):
    subprocess.run([ff, "-y", "-i", mp3, "-ac", "1", "-ar", str(RATE),
                    "-sample_fmt", "s16", wav], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _plan_units():
    """كلُّ الوحدات الفريدة (مفتاح → نصُّ العرض) بترتيب الخطّة."""
    seen = {}
    for tag, title, items, ess in qaida.record_plan():
        for disp in items:
            u = _units(disp)
            if not u:
                continue
            k = qv.unit_key(*u[0])
            if k not in seen:
                seen[k] = disp
    return seen

def generate(voice=None, refresh_tts=False, force=False, log=print):
    """ولّد الوحداتِ الناقصةَ (أو المولَّدةَ آليًّا مع refresh_tts). يحترم صوتَك.
    يُرجِع dict إحصاءات. log: دالّةُ طباعةٍ اختياريّة (للتطبيق)."""
    voice = voice or tts_engine.default_voice()
    units = _plan_units(); total = len(units)
    idx = qv._load()
    try: src = json.load(open(SRC, encoding="utf-8"))
    except Exception: src = {}
    ff = _ffmpeg()
    if not ff:
        return {"error": "لا يوجد ffmpeg. شغّل run_build_qaida_voices.bat مرّةً (يثبّت imageio-ffmpeg).",
                "made": 0, "total": total}
    os.makedirs(DIR, exist_ok=True)
    made = skip_user = skip_have = fail = 0; verify_made = []
    log(f"⏳ التوليد بدأ… ({total} وحدةٍ مفردة + مقاطع مركّبة). قد يأخذ دقائقَ عبر الإنترنت.")
    _done=0
    for k, disp in units.items():
        _done+=1
        if _done % 25 == 0:
            log(f"   … {_done}/{total} (وُلِّد {made})"); sys.stdout.flush()
        have = k in idx and os.path.exists(os.path.join(DIR, idx[k]))
        is_user = have and src.get(k) != "tts"
        if have and not force:
            if is_user: skip_user += 1; continue        # لا نمسُّ صوتَك أبدًا
            if not refresh_tts: skip_have += 1; continue # مولَّدٌ سابقًا وموجود
        text = _text_for(disp, k)
        mp3 = os.path.join(tempfile.gettempdir(), "qaida_unit.mp3")
        try:
            tts_engine._edge_save(text, voice, "-20%", "+0Hz", mp3)
        except Exception:
            try: tts_engine._gtts_save(text, mp3)
            except Exception as e2:
                log(f"تخطّي {disp}: {e2}"); fail += 1; continue
        fn = hashlib.md5(k.encode("utf-8")).hexdigest()[:12] + ".wav"
        dst = os.path.join(DIR, fn)
        try:
            _to_wav(mp3, dst, ff)
        except Exception as e:
            log(f"فشل التحويل {disp}: {e}"); fail += 1; continue
        _trim_wav(dst)                               # قصُّ الصمت لنطقٍ متّصل
        idx[k] = fn; src[k] = "tts"; made += 1
        if k in VERIFY: verify_made.append(disp)

    # وحداتٌ مركّبةٌ للمدّ (مقاطعُ القاعدة الكاملة بَا/بُو/بِي) — ينطقها edge نظيفةً
    from pronounce import FATHA as _F, DAMMA as _D, KASRA as _K
    comps=[]
    for c in qaida.GEN: comps += [c+_F+"ا", c+_D+"و", c+_K+"ي"]
    log(f"⏳ مقاطع المدّ المركّبة ({len(comps)})…"); sys.stdout.flush()
    _c=0
    for disp in comps:
        _c+=1
        if _c % 20 == 0: log(f"   … مركّب {_c}/{len(comps)}"); sys.stdout.flush()
        key=qv.ukey(disp)
        have=key in idx and os.path.exists(os.path.join(DIR, idx[key]))
        is_user=have and src.get(key)!="tts"
        if have and not force and (is_user or not refresh_tts):
            continue
        mp3=os.path.join(tempfile.gettempdir(),"qaida_comp.mp3")
        try:
            tts_engine._edge_save(disp, voice, "-20%", "+0Hz", mp3)
        except Exception:
            try: tts_engine._gtts_save(disp, mp3)
            except Exception as e2: log(f"مركّب {disp}: {e2}"); fail+=1; continue
        fn=hashlib.md5(key.encode("utf-8")).hexdigest()[:12]+".wav"
        try:
            _to_wav(mp3, os.path.join(DIR,fn), ff); _trim_wav(os.path.join(DIR,fn))
            idx[key]=fn; src[key]="tts"; made+=1
        except Exception as e: log(f"مركّب {disp}: {e}"); fail+=1

    # وحدتا لفظ الجلالة الكاملتان: مفخّمة «اللهُ» ومرقّقة «لِلَّهِ» (تفخيم/ترقيق اللام)
    JAL={"§jalalah_heavy":"اللَّهُ", "§jalalah_light":"لِلَّهِ"}
    for key,txt in JAL.items():
        have = key in idx and os.path.exists(os.path.join(DIR, idx[key]))
        is_user = have and src.get(key) != "tts"
        if have and not force and (is_user or not refresh_tts): continue
        mp3=os.path.join(tempfile.gettempdir(),"qaida_jal.mp3")
        try:
            tts_engine._edge_save(txt, voice, "-15%", "+0Hz", mp3)
        except Exception:
            try: tts_engine._gtts_save(txt, mp3)
            except Exception as e2: log(f"جلالة {key}: {e2}"); fail+=1; continue
        wav=os.path.join(tempfile.gettempdir(),"qaida_jal.wav")
        try:
            _to_wav(mp3, wav, ff); _trim_wav(wav)
            fn=hashlib.md5(key.encode("utf-8")).hexdigest()[:12]+".wav"
            import shutil as _sh; _sh.copyfile(wav, os.path.join(DIR, fn))
            idx[key]=fn; src[key]="tts"; made+=1        # حدِّث الفهرسَ في الذاكرة
        except Exception as e:
            log(f"جلالة {key}: {e}"); fail+=1

    qv._save(idx)
    json.dump(src, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {"made": made, "skip_user": skip_user, "skip_have": skip_have,
            "fail": fail, "total": total, "verify": verify_made, "error": None}

def main():
    a = sys.argv[1:]
    dry     = "--dry" in a
    force   = "--force" in a
    refresh = "--refresh-tts" in a
    voice = tts_engine.default_voice()
    if "--voice" in a:
        try: voice = a[a.index("--voice")+1]
        except Exception: pass

    if "--rebuild" in a:
        # إعادةُ بناءٍ كاملة: يُزيل كلَّ الوحدات (بما فيها تسجيلاتُك الشخصيّة) ثمّ
        # يولّد الحروفَ كاملةً بمحرّك edge من جديد.
        qv._save({})
        try: open(SRC,"w",encoding="utf-8").write("{}")
        except Exception: pass
        print("♻️ أُزيلت كلُّ الوحدات (والتسجيلاتُ الشخصيّة). سيُعاد التوليدُ كاملًا...")
        # يتابع التوليدَ العاديّ (الفهرسُ فارغٌ ⇒ يُولَّد كلُّ شيء)

    if "--trim-existing" in a:
        idx = qv._load()
        try: src = json.load(open(SRC, encoding="utf-8"))
        except Exception: src = {}
        cnt = 0
        for k, fn in idx.items():
            if src.get(k) != "tts":            # لا نمسُّ تسجيلاتِك
                continue
            p = os.path.join(DIR, fn)
            if os.path.exists(p):
                _trim_wav(p); cnt += 1
        print(f"✂️ قُصَّ الصمتُ من {cnt} وحدةً مولَّدة. أعِد تشغيلَ التطبيق.")
        return

    if dry:
        units = _plan_units(); idx = qv._load()
        try: src = json.load(open(SRC, encoding="utf-8"))
        except Exception: src = {}
        print(f"# الخطّة: {len(units)} وحدة — الصوت: {voice}")
        for k, disp in units.items():
            print(f"{disp}\t(مفتاح {k})\t→ نصُّ التوليد: {_text_for(disp,k)}")
        n_user = sum(1 for k in idx if src.get(k) != "tts")
        print(f"\nموجودٌ الآن: {len(idx)} (منها بصوتك ~{n_user}).")
        return

    r = generate(voice=voice, refresh_tts=refresh, force=force)
    if r.get("error"):
        print("⚠️", r["error"]); return
    print(f"✅ وُلِّد {r['made']} وحدة | حُفِظ صوتُك دون مساس: {r['skip_user']} | "
          f"موجودٌ سلفًا: {r['skip_have']} | إخفاقات: {r['fail']} | المجموع: {r['total']}")
    if r["verify"]:
        print("🔎 راجِع سمعيًّا وحداتِ المدّ (أعِد تسجيلَها بصوتك إن لزم): "
              + " ".join(r["verify"]))
    print("أعِد تشغيلَ التطبيق ثمّ جرّب «انطق بالوحدات».")

if __name__ == "__main__":
    main()
