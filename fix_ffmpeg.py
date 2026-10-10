# -*- coding: utf-8 -*-
"""
fix_ffmpeg.py — يوفّر ffmpeg و ffprobe لبيئة المشروع (بلا صلاحيّاتِ مدير).

Gradio/pydub يحتاجان ffprobe لتشغيل mp3 (نطق edge)، وWhisper يحتاج ffmpeg (نسخُ
مرجع F5). نجلب الثنائيّتَين عبر static-ffmpeg وننسخهما إلى venv\\Scripts (على PATH).
    python fix_ffmpeg.py
"""
import sys, os, shutil, subprocess
def pip(*a): subprocess.run([sys.executable,"-m","pip",*a], check=False)

print("① تثبيت static-ffmpeg (يجلب ffmpeg و ffprobe) …")
pip("install","static-ffmpeg")
print("\n② جلبُ الثنائيّتَين …")
try:
    from static_ffmpeg import run as _sf
    ff, fp = _sf.get_or_fetch_platform_executables_else_raise()
except Exception as e:
    print("⚠️ تعذّر عبر static-ffmpeg:", e)
    print("بديل: ثبّت imageio-ffmpeg (ffmpeg فقط) أو نزّل ffmpeg يدويًّا.")
    sys.exit(1)

scripts=os.path.dirname(sys.executable)                      # venv\Scripts
ext=".exe" if os.name=="nt" else ""
for src,name in ((ff,"ffmpeg"),(fp,"ffprobe")):
    dst=os.path.join(scripts, name+ext)
    try:
        shutil.copy(src,dst); print("✅ نُسِخ:", dst)
    except Exception as e:
        print(f"⚠️ تعذّر نسخُ {name}:", e, "\n   المصدر:", src)

print("\n③ التحقّق …")
for name in ("ffmpeg","ffprobe"):
    exe=os.path.join(scripts, name+ext)
    try: subprocess.run([exe,"-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True); print("   ✔", name, "يعمل")
    except Exception as e: print("   ✗", name, e)
print("\n✅ جاهز. أعِد تشغيل التطبيق — ستعمل أصواتُ edge (mp3) وF5 معًا.")
