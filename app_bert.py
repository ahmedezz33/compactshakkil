# -*- coding: utf-8 -*-
"""
app_bert.py — تطبيق CompactShakkil (أقصى دقّة: BERT-graft) + نظام تعليم النطق النحويّ.

- التشكيل: نموذج BERT-graft (DER≈1.3%)؛ القرآن بالاسترداد الموقّر (100%).
- تعليم النطق: لوحة «الإعراب» تُبرز حركة آخِر كلّ كلمة بلونٍ وتشرح نوعها
  (مرفوع/منصوب/مجرور/مبنيّ) — لتعليم النطق النحويّ الصحيح.

التشغيل: python app_bert.py   →  http://127.0.0.1:7860
المتطلّبات: torch + transformers + gradio
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent/"scripts"))
import torch, gradio as gr
from data.vocab_v2 import split_letters_and_diacritics
from bert_graft_infer import GraftInfer, case_label
from reverence_aware_unified import load_quran_index, _norm

QURAN="data/raw/quran/quran-simple.txt"
COLOR={"مرفوع":"#2e7d32","منصوب":"#c0392b","مجرور":"#1f6feb","ساكن/مبنيّ":"#777"}

print("📥 تحميل نموذج BERT-graft ...")
INF=GraftInfer()
print("📖 بناء فهرس القرآن ...")
IDX,_full,_va=load_quran_index(QURAN)
KEYS=sorted(IDX, key=len, reverse=True)

def route(line):
    k=_norm(line)
    if k in IDX: return IDX[k], "استرداد (آية تامّة)"
    for vk in KEYS:
        if len(vk)<8: break
        if vk in k: return IDX[vk], "استرداد (آية مضمّنة)"
    return INF.diacritize(line), "نموذج BERT-graft"

def diacritize(text):
    if not text or not text.strip(): return "", "—"
    outs=[]; routes=[]
    for line in text.split("\n"):
        s=line.strip()
        if not s: outs.append(""); continue
        o,r=route(s); outs.append(o); routes.append(r)
    return "\n".join(outs), " | ".join(dict.fromkeys(routes))

def annotate(word):
    """أرجع (حركة آخِر, وسم) من كلمةٍ مشكّلة."""
    L,C=split_letters_and_diacritics(word)
    if not C: return None,None
    return int(C[-1]), case_label(int(C[-1]))

def teach(text):
    """لوحة إعراب: كلّ كلمةٍ ملوّنةٌ بحركة آخِرها مع وسمها."""
    if not text or not text.strip(): return "<div dir='rtl'>—</div>"
    dia,_=diacritize(text)
    html=["<div dir='rtl' style='font-size:22px;line-height:2.4;font-family:Arial'>"]
    counts={"مرفوع":0,"منصوب":0,"مجرور":0,"ساكن/مبنيّ":0}
    for line in dia.split("\n"):
        for w in line.split():
            _,lab=annotate(w)
            c=COLOR.get(lab,"#333"); counts[lab]=counts.get(lab,0)+1
            html.append(f"<span style='color:{c};border-bottom:2px solid {c};margin:0 4px' "
                        f"title='{lab}'>{w}</span><sub style='font-size:11px;color:{c}'>{lab}</sub>")
        html.append("<br>")
    html.append("</div>")
    legend=(f"<div dir='rtl' style='margin-top:10px;font-size:14px'>"
            f"<b>الإحصاء:</b> "
            f"<span style='color:#2e7d32'>مرفوع {counts['مرفوع']}</span> · "
            f"<span style='color:#c0392b'>منصوب {counts['منصوب']}</span> · "
            f"<span style='color:#1f6feb'>مجرور {counts['مجرور']}</span> · "
            f"<span style='color:#777'>مبنيّ/ساكن {counts['ساكن/مبنيّ']}</span></div>")
    return "".join(html)+legend

TITLE="CompactShakkil — مُشكِّلٌ عالي الدقّة + تعليم النطق النحويّ"
with gr.Blocks(title=TITLE, theme=gr.themes.Soft()) as demo:
    gr.Markdown(f"## {TITLE}\nنموذج BERT-graft (DER≈1.3%) — القرآن بالاسترداد، والعامّ بالنموذج. "
                "لوحة «الإعراب» تُعلّم النطق النحويّ الصحيح بإبراز حركة الآخِر وشرحها.")
    with gr.Tab("التشكيل"):
        with gr.Row():
            inp=gr.Textbox(lines=10,label="النصّ (بلا تشكيل)",rtl=True,placeholder="الصق النصّ...")
            out=gr.Textbox(lines=10,label="المشكَّل",rtl=True,show_copy_button=True)
        route_box=gr.Textbox(label="التوجيه")
        gr.Button("شكِّل",variant="primary").click(diacritize,inp,[out,route_box])
    with gr.Tab("تعليم النطق (الإعراب)"):
        inp2=gr.Textbox(lines=6,label="النصّ (بلا تشكيل)",rtl=True)
        panel=gr.HTML()
        gr.Button("حلّل الإعراب",variant="primary").click(teach,inp2,panel)
        gr.Markdown("الألوان: <span style='color:#2e7d32'>مرفوع (ـُ)</span> · "
                    "<span style='color:#c0392b'>منصوب (ـَ)</span> · "
                    "<span style='color:#1f6feb'>مجرور (ـِ)</span> · "
                    "<span style='color:#777'>مبنيّ/ساكن</span>")
    gr.Examples(["ذهب الطالب الى المدرسة","إن العلم نور","قرأت الكتاب المفيد",
                 "الحمد لله رب العالمين"], inputs=inp)

if __name__=="__main__":
    demo.launch(server_name="127.0.0.1",server_port=7860,inbrowser=True)
