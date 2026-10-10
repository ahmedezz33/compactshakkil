# -*- coding: utf-8 -*-
"""
app.py — تطبيق CompactShakkil للتشكيل (واجهة ويب محلّيّة).
النظام الثابت: القرآن بالاسترداد الموقّر (100%)، والعامّ بنموذج v3-hard،
مع تعليم الكلمات المشكوكة (ثقة<0.90) للمراجعة البشريّة.

التشغيل:  python app.py     ثمّ افتح الرابط المحلّيّ (http://127.0.0.1:7860)
المتطلّبات: torch (مثبّت) + gradio  →  pip install gradio
"""
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import torch
import gradio as gr
from data.vocab_v2 import (split_letters_and_diacritics, merge_letters_and_diacritics,
                           strip_diacritics, encode_chars)
from reverence_aware_unified import ReverenceAwareUnified

CKPT   = "outputs_v3_hard/best_model.pt"          # النموذج المعتمد
QURAN  = "data/raw/quran/quran-simple.txt"
REVIEW_TH = 0.90

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("تحميل النظام...")
SYS = ReverenceAwareUnified(CKPT, QURAN, device)

def _word_spans(L):
    sp=[];st=None
    for i,ch in enumerate(L):
        if ch==" ":
            if st is not None: sp.append((st,i)); st=None
        else:
            if st is None: st=i
    if st is not None: sp.append((st,len(L)))
    return sp

@torch.no_grad()
def _neural_conf_words(text):
    """يُرجع قائمة الكلمات المشكوكة (فيها موضعٌ ثقته<العتبة) في مخرجٍ عصبيّ."""
    letters,_=split_letters_and_diacritics(strip_diacritics(text))
    if not letters: return []
    ids=torch.tensor([encode_chars(letters)],dtype=torch.long,device=device)
    mask=torch.ones_like(ids,dtype=torch.bool)
    logits=SYS.model(ids,mask)[0]
    p=torch.softmax(logits,-1); conf,pred=p.max(-1)
    conf=conf.tolist(); pred=pred.tolist()
    flagged=[]
    for a,b in _word_spans(letters):
        if any(conf[i]<REVIEW_TH for i in range(a,b)):
            flagged.append(merge_letters_and_diacritics(letters[a:b],[int(pred[i]) for i in range(a,b)]))
    return flagged

def diacritize(text):
    if not text or not text.strip():
        return "", "—", ""
    out_lines=[]; routes=[]; review=[]
    for line in text.split("\n"):
        s=line.strip()
        if not s: out_lines.append(""); continue
        r=SYS.process(s)
        out_lines.append(r["output"]); routes.append(r["route"])
        if r["route"].startswith("V3"):          # مخرجٌ عصبيّ → افحص المشكوك
            review += _neural_conf_words(s)
    route_summary=" | ".join(dict.fromkeys(routes))
    review_txt = ("، ".join(review)) if review else "لا مواضع مشكوكة (كلّها فوق العتبة أو مستردّة)"
    return "\n".join(out_lines), route_summary, review_txt

TITLE = "CompactShakkil — مُشكِّل عربيّ مُدمَج"
DESC = ("نموذجٌ مُدمَج (v3-hard) مع استرداد موقّر للقرآن. "
        "الآيات تُستردّ من المصحف (دقّة 100%)، والنصّ العامّ يُشكّله النموذج (DER≈2%). "
        "الكلمات المشكوكة (ثقة<0.90) تُعرَض للمراجعة.")

with gr.Blocks(title=TITLE, theme=gr.themes.Soft()) as demo:
    gr.Markdown(f"## {TITLE}\n{DESC}")
    with gr.Row():
        inp=gr.Textbox(lines=10, label="النصّ (بلا تشكيل — سطرٌ لكلّ جملة)",
                       placeholder="اكتب أو الصق النصّ العربيّ هنا...", rtl=True)
        out=gr.Textbox(lines=10, label="النصّ المُشكَّل", rtl=True, show_copy_button=True)
    with gr.Row():
        route=gr.Textbox(label="التوجيه (استرداد / نموذج)")
        rev=gr.Textbox(label="كلماتٌ للمراجعة", rtl=True)
    btn=gr.Button("شكِّل", variant="primary")
    btn.click(diacritize, inputs=inp, outputs=[out, route, rev])
    gr.Examples(
        examples=["الحمد لله رب العالمين",
                  "قل هو الله احد",
                  "ذهب الطالب الى المدرسة صباحا",
                  "قال العلماء ان التشكيل مهم في فهم النصوص"],
        inputs=inp)

if __name__=="__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
