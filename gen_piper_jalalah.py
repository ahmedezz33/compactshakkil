# -*- coding: utf-8 -*-
"""A/B للفظ الجلالة على Piper الطبيعيّ: «الله» نظيفة مقابل «اللَّاه» (حيلة edge). CPU، لا GPU."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_engine
from pronounce import clean_for_tts, apply_overrides, fix_lam, to_waqf, jalalah_edge, edge_prepare

if not tts_engine.piper_available():
    print("لا صوت Piper — شغّل run_download_piper.bat"); sys.exit(1)

os.makedirs("samples_piper_jalalah", exist_ok=True)
phrases = {
    "ikhlas": "قُلْ هُوَ اللَّهُ أَحَدٌ",       # تفخيم (بعد ضمّ)
    "basmala": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",  # ترقيق (بعد كسر)
}

def variant_clean(t):   # بلا حيلة الجلالة: espeak يتولّى «الله» بنفسه
    x = apply_overrides(clean_for_tts(t))
    x = fix_lam(x, drop_sun=True)
    return to_waqf(x)

def variant_hack(t):    # حيلة edge: «اللَّاه/الله»
    return edge_prepare(t, mode="waqf", drop_sun=True)

for name, t in phrases.items():
    for tag, fn in (("clean", variant_clean), ("hack", variant_hack)):
        spoken = fn(t)
        out = os.path.abspath(f"samples_piper_jalalah/{name}_{tag}.wav")
        try:
            tts_engine._piper_save(spoken, out)   # Piper الطبيعيّ (espeak داخليًّا)
            print(f"OK  {name}_{tag}: {spoken}")
        except Exception as e:
            print(f"FAIL {name}_{tag}: {e}")
print("\nاستمع: samples_piper_jalalah/  — قارن clean مقابل hack في كلٍّ.")
