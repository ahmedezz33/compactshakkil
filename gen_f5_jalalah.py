# -*- coding: utf-8 -*-
"""يولّد عيّناتِ A/B للفظ الجلالة بصوت F5 (المنشاويّ). شغّله في venv ويندوز على GPU."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f5_engine
from pronounce import edge_prepare, clean_for_tts, to_waqf

os.makedirs("samples_f5", exist_ok=True)
phrases = {
    "ikhlas_heavy": "قُلْ هُوَ اللَّهُ أَحَدٌ",       # بعد ضمّة ← يجب تفخيم
    "basmala_light": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",  # بعد كسرة ← يجب ترقيق
}
if not f5_engine.available():
    print("F5 غير متاح — شغّل setup_f5.py أولًا."); sys.exit(1)

for name, txt in phrases.items():
    ruled = edge_prepare(txt, mode="waqf")               # مع قاعدة الجلالة (اللَّاه/الله)
    plain = to_waqf(clean_for_tts(txt))                  # خام (بلا قاعدة)
    for tag, spoken in (("ruled", ruled), ("plain", plain)):
        out = os.path.abspath(f"samples_f5/{name}_{tag}.wav")
        try:
            p = f5_engine.synth(spoken, out=out)
            print(f"OK  {name}_{tag}: {spoken}  ->  {p}")
        except Exception as e:
            print(f"FAIL {name}_{tag}: {e}")
print("\nتمّ. استمع لملفّات samples_f5/ وقارن ruled (بالقاعدة) مقابل plain (خام).")
