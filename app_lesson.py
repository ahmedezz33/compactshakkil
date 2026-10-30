# -*- coding: utf-8 -*-
"""app_lesson.py — واجهةٌ رسوميّةٌ (Gradio) لمولّدِ فيديوهاتِ النطقِ التعليميّة.
اختَرِ النصَّ والصوتَ والخطَّ والأبعادَ والفجوةَ ثمّ «توليد» — ويُعرَضُ الفيديو ويُنزَّل.
تشغيل: run_app_lesson.bat
"""
import os, sys, glob, time, traceback
BASE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE,"scripts")); sys.path.insert(0, BASE)
import gradio as gr
import make_lesson_video as MLV
import tts_engine

# الأصواتُ (حيّةٌ من edge-tts + احتياطيّ)
try: VOICES=tts_engine.list_voices()            # [(تسمية, معرّف)]
except Exception: VOICES=[("Edge — Hamed (ذكر)","ar-SA-HamedNeural"),("gTTS (احتياطيّ)","__gtts__")]
V_LABELS=[v[0] for v in VOICES]; V_MAP=dict(VOICES)
_defid=tts_engine.default_voice()
V_DEFAULT=next((lbl for lbl,i in VOICES if i==_defid), V_LABELS[0])

# الخطوط
FONTS=sorted(glob.glob(os.path.join(BASE,"data","fonts","*.ttf")))
F_MAP={os.path.basename(p):p for p in FONTS}
F_LABELS=list(F_MAP.keys())
F_DEFAULT=next((n for n in F_LABELS if "Amiri-Bold" in n), (F_LABELS[0] if F_LABELS else ""))

ASPECTS={"أفقي 1280×720 (يوتيوب)":(1280,720),
         "عمودي 1080×1920 (ريلز/شورتس)":(1080,1920),
         "مربّع 1080×1080 (إنستغرام)":(1080,1080)}

OUTDIR=os.path.join(BASE,"lessons"); os.makedirs(OUTDIR, exist_ok=True)

def make(text, voice_label, font_label, aspect, rate, intro, show_latin):
    logs=[]
    def log(m): logs.append(str(m)); print(m)
    try:
        if not (text or "").strip(): return None, "أدخِلْ نصًّا أوّلاً."
        w,h=ASPECTS.get(aspect,(1280,720))
        voice=V_MAP.get(voice_label); font=F_MAP.get(font_label)
        out=os.path.join(OUTDIR, f"lesson_{int(time.time())}.mp4")
        path=MLV.generate(text, out=out, font=font, voice=voice, w=w, h=h,
                          rate_pct=int(rate), intro=float(intro), show_latin=bool(show_latin), log=log)
        return path, "\n".join(logs[-14:])
    except Exception as e:
        return None, "خطأ:\n"+ "".join(traceback.format_exception_only(type(e), e)) + "\n".join(logs[-10:])

with gr.Blocks(title="مولّد فيديوهات النطق") as demo:
    gr.Markdown("## 🎬 مولّد فيديوهات النطق التعليميّة — CompactShakkil\nاكتبِ النصّ، اختَرِ الخيارات، ثمّ «توليد».")
    with gr.Row():
        with gr.Column(scale=3):
            text=gr.Textbox(label="النصّ (يُشكَّلُ تلقائيًّا)", lines=4,
                            value="ذهب الطالب إلى المدرسة وقرأ الدرس")
            with gr.Row():
                voice=gr.Dropdown(V_LABELS, value=V_DEFAULT, label="الصوت")
                font=gr.Dropdown(F_LABELS, value=F_DEFAULT, label="الخطّ")
            with gr.Row():
                aspect=gr.Dropdown(list(ASPECTS.keys()), value="أفقي 1280×720 (يوتيوب)", label="الأبعاد")
                show_latin=gr.Checkbox(value=True, label="إظهار النقحرة اللاتينيّة")
            with gr.Row():
                rate=gr.Slider(-40,40,value=0,step=5,label="سرعة القراءة (%)")
                intro=gr.Slider(0.0,6.0,value=3.0,step=0.5,label="مدّة المقدّمة (ث)")
            btn=gr.Button("🎬 توليد الفيديو", variant="primary")
        with gr.Column(scale=2):
            video=gr.Video(label="النتيجة", autoplay=True)
            status=gr.Textbox(label="السجلّ", lines=8)
    btn.click(make, [text,voice,font,aspect,rate,intro,show_latin], [video,status])

if __name__=="__main__":
    port=int(os.environ.get("LESSON_PORT","7862"))
    demo.launch(server_name="127.0.0.1", server_port=port, inbrowser=True)
