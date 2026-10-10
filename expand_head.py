# -*- coding: utf-8 -*-
"""
expand_head.py — توسيع رأس تصنيف V1-noLS من 15 إلى 19 فئة (إضافة الخنجريّة).

نُبقي الأوزان الـ15 المُتعلَّمة كما هي، ونهيّئ الصفوف الأربعة الجديدة (15–18)
بقيم صغيرة، فتبدأ نادرة التنبّؤ حتى يضبطها الصقل. لا نمسّ المُشفّر ولا التضمين.

يُشغّل من جذر المشروع (venv):
    python expand_head.py
المخرَج: compactshakkil_v1_nols/expanded_19.pt (نقطة انطلاق للصقل النظيف)
"""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import torch

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "compactshakkil_v1_nols" / "best_model.pt"
if not SRC.exists():
    SRC = ROOT / "outputs_v1_nols" / "latest.pt"
OUT = ROOT / "compactshakkil_v1_nols" / "expanded_19.pt"
OLD, NEW = 15, 19

def main():
    print(f"تحميل: {SRC}")
    ck = torch.load(str(SRC), map_location="cpu", weights_only=False)
    sd = ck["model_state"] if isinstance(ck, dict) and "model_state" in ck else ck
    w = sd["classifier.3.weight"]   # [15,256]
    b = sd["classifier.3.bias"]     # [15]
    assert w.shape[0] == OLD, f"عدد الفئات الحاليّ {w.shape[0]} ≠ {OLD}"
    d = w.shape[1]
    torch.manual_seed(42)
    nw = torch.empty(NEW, d); nw[:OLD] = w; nw[OLD:].normal_(0.0, 0.02)
    nb = torch.zeros(NEW); nb[:OLD] = b   # الصفوف الجديدة تبدأ بانحياز 0
    sd["classifier.3.weight"] = nw
    sd["classifier.3.bias"] = nb
    out = {"model_state": sd, "config": ck.get("config") if isinstance(ck, dict) else None,
           "note": "expanded 15->19 (dagger classes) from V1-noLS"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    torch.save(out, str(OUT))
    print(f"✅ رأس موسّع {OLD}→{NEW} محفوظ: {OUT}")
    print(f"   classifier.3.weight: {tuple(nw.shape)}  bias: {tuple(nb.shape)}")
    print("   المُشفّر والتضمين بلا تغيير. جاهز للصقل النظيف.")

if __name__ == "__main__":
    main()
