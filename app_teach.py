# -*- coding: utf-8 -*-
"""
app_teach.py — نظام تعليم النطق النحويّ (على نموذج BERT-graft عالي الدقّة).
أربعة تبويبات:
  1) التشكيل           : تشكيلٌ دقيق (BERT-graft) + استرداد القرآن.
  2) الإعراب والشرح    : حركة آخِر كلّ كلمة ملوّنة + دورها النحويّ وسببه.
  3) تمارين            : يُخفى التشكيل، يكتب المتعلّم، يصحّح النظام ويُعطي درجة.
  4) النطق             : نطقٌ صوتيّ (espeak أمينٌ للتشكيل / edge-tts طبيعيّ / gTTS) + نقحرة.
واجهة Gradio 6.0. التشغيل: python app_teach.py
"""
import sys, os
# ويندوز: أجبِر مخرجَ التطبيق كلَّه على UTF-8 لئلّا ينهار عند طبع العربيّة (cp1252)،
# وعطّل wandb الذي يلفُّ المخرجَ (جاء مع f5-tts). يجب أن يسبق أيَّ استيرادٍ يطبع/يلفّ.
os.environ.setdefault("WANDB_DISABLED","true"); os.environ.setdefault("WANDB_MODE","disabled")
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent/"scripts"))
import gradio as gr
from data.vocab_v2 import split_letters_and_diacritics, strip_diacritics, merge_letters_and_diacritics
from bert_graft_infer import GraftInfer
from iraab_explain import explain, family, final_class
from reverence_aware_unified import load_quran_index, _norm
from pronounce import fix_jalalah_lines, fix_lam, tts_prepare
import tts_engine, g2p, user_voice, qaida, qaida_voice, quran_audio, shamela_import

QURAN="data/raw/quran/quran-simple.txt"
COLOR={"مرفوع":"#2e7d32","منصوب":"#c0392b","مجرور":"#1f6feb","مبنيّ":"#777","مبنيّ/ساكن":"#777"}

print("📥 تحميل BERT-graft ...");  INF=GraftInfer()
print("📖 فهرس القرآن ...");       IDX,_f,_v=load_quran_index(QURAN)
KEYS=sorted(IDX,key=len,reverse=True)
print("🔊 قائمة الأصوات ...");     VOICES=tts_engine.list_voices()
VOICE_LABELS=[l for l,_ in VOICES]; VOICE_BY_LABEL=dict(VOICES)
DEFAULT_LABEL=next((l for l,v in VOICES if v==tts_engine.default_voice_id()), VOICE_LABELS[0])

# أمثلةٌ تعليميّةٌ تُغطّي أبوابَ الإعراب الشائعة
TOPIC_EX=[
    "ذهب الطالب المجتهد الى المدرسة",   # فاعل + نعت + جار ومجرور
    "إن العلم نور",                       # اسم إنّ + خبر إنّ
    "كان الجو جميلا",                     # اسم كان + خبر كان
    "قرأ محمد الكتاب والمجلة",            # فاعل + مفعول به + معطوف
    "كتاب الطالب جديد",                   # مبتدأ (مضاف) + مضاف إليه + خبر
    "يا محمد اجتهد",                      # منادى
    "جلس التلميذ عند الباب",              # ظرف + مضاف إليه
    "هذا كتاب مفيد",                      # اسم إشارة + خبر + نعت
]
LEGEND=("<div dir='rtl' style='font-size:13px;color:#555;margin-top:10px;line-height:1.9'>"
        "<b>دليلٌ سريع:</b> الألوانُ حسب حركة الآخِر — "
        "<span style='color:#2e7d32'>■ مرفوع</span> (فاعل/مبتدأ/خبر/اسم كان)، "
        "<span style='color:#c0392b'>■ منصوب</span> (مفعول به/خبر كان/اسم إنّ/ظرف)، "
        "<span style='color:#1f6feb'>■ مجرور</span> (بحرف جرّ أو مضاف إليه)، "
        "<span style='color:#777'>■ مبنيّ</span> (حرف/ضمير/اسم إشارة). "
        "الحركةُ يقينيّةٌ من النموذج؛ الدورُ تقديريٌّ بقواعدَ مبسّطة.</div>")

import re as _re
_AYA_SEP=_re.compile(r"[0-9٠-٩۰-۹۝۞]+")   # أرقامُ الآي وعلاماتُ نهايتها فواصلُ

def _retrieve_one(k):
    """استرداد آيةٍ لمفتاحٍ مطبّع: تطابقٌ تامّ ثمّ آيةٌ حاويةٌ (مضمّنة)."""
    if not k: return None
    if k in IDX: return IDX[k]
    for vk in KEYS:
        if len(vk)<8: break
        if vk in k: return IDX[vk]
    return None

def route(line, respect=True):
    k=_norm(line)
    hit=_retrieve_one(k)
    if hit is not None and _norm(hit)==k:      # السطرُ آيةٌ واحدةٌ بالضبط
        return hit,"استرداد (آية)"
    # نصٌّ متعدّدُ الآيات: قطّعْ على أرقام الآي/۝/۞ واسترِدَّ كلَّ آيةٍ على حدة
    segs=[s for s in _AYA_SEP.split(line) if _norm(s)]
    if len(segs)>=2:
        outs=[]; hits=0
        for s in segs:
            h=_retrieve_one(_norm(s))
            if h is not None: outs.append(h); hits+=1
            else: outs.append(INF.diacritize_partial(s) if respect else INF.diacritize(s))
        if hits>=2:                            # مقطعٌ قرآنيٌّ متعدّدُ الآيات
            tag="استرداد (آيات)" if hits==len(segs) else f"استرداد جزئيّ ({hits}/{len(segs)} آية)"
            return "\n".join(outs),tag
    # ملاحظة: الآيةُ المضمّنةُ في سياقٍ لا تحذفُ ما حولَها — نشكّلُ النصَّ كلَّه،
    # ثمّ يستبدلُ restore_quran_tashkeel تشكيلَ الآيةِ (بين ﴿﴾/{}) من المصحفِ في مكانِها.
    # respect: احترم التشكيلَ الموجودَ في الإدخال وأكمِل الناقصَ فقط
    out=INF.diacritize_partial(line) if respect else INF.diacritize(line)
    return out,"BERT-graft"

def diacritize(text, respect=True):
    if not text or not text.strip(): return "","—"
    outs=[];routes=[]
    for line in text.split("\n"):
        s=line.strip()
        if not s: outs.append(""); continue
        o,r=route(s, respect)
        # المستردُّ قرآنيٌّ موثوقُ الرسم فلا يُمَسّ؛ نصحّح مخرجَ النموذج فقط
        if r=="BERT-graft":
            try:
                import iraab_fix; o=iraab_fix.correct(o)   # قواعدُ الإعراب الحتميّةُ الآمنة (جرّ/نصب اسم إنّ/أنْ)
            except Exception as _ie: print("iraab_fix skip:", _ie)
            o=fix_lam(fix_jalalah_lines(o))
        outs.append(o); routes.append(r)
    result="\n".join(outs)
    try:
        result=quran_audio.restore_quran_tashkeel(result)   # آيةٌ بين ﴿﴾/{} ← تشكيلُ المصحفِ الصحيح
    except Exception as _qe: print("quran tashkeel:", _qe)
    return result," | ".join(dict.fromkeys(routes))

# ---------- تبويب الإعراب والشرح ----------
def explain_html(text):
    if not text or not text.strip(): return "<div dir='rtl'>—</div>"
    dia,_=diacritize(text)
    rows=[]; colored=[]
    for line in dia.split("\n"):
        if not line.strip(): continue
        for r in explain(line.split()):
            c=COLOR.get(r["حركة"],"#333")
            colored.append(f"<span style='color:{c};border-bottom:2px solid {c};margin:0 5px'>{r['word']}</span>")
            rows.append(f"<tr><td style='color:{c};font-size:18px'>{r['word']}</td>"
                        f"<td style='color:{c}'>{r['حركة']}</td><td><b>{r['دور']}</b></td>"
                        f"<td style='color:#555'>{r['سبب']}</td></tr>")
        colored.append("<br>")
    html=("<div dir='rtl' style='font-family:Arial'>"
          "<div style='font-size:22px;line-height:2.4'>"+ "".join(colored) +"</div>"
          "<table style='width:100%;border-collapse:collapse;margin-top:12px;font-size:14px' border='1' cellpadding='6'>"
          "<tr style='background:#1F3864;color:#fff'><th>الكلمة</th><th>حركة الآخِر</th><th>الدور (تقديريّ)</th><th>السبب</th></tr>"
          + "".join(rows) + "</table>"
          "<div style='font-size:12px;color:#888;margin-top:6px'>الحركة يقينيّةٌ من النموذج؛ الدور تقديريٌّ بقواعد نحويّة مبسّطة.</div></div>")
    return html

# ---------- تبويب التمارين ----------
def _mask_final(word):
    """يُبقي التشكيلَ الداخليّ ويُخفي حركةَ الآخِر (لمستوى «الآخِر فقط»)."""
    L,C=split_letters_and_diacritics(word)
    if not C: return word
    C=list(C)
    if len(L)>=2 and L[-1] in ("ا","ى") and int(C[-1])==0: C[-2]=0   # ...ًا
    else: C[-1]=0
    return merge_letters_and_diacritics(L,C)

def _well_diacritized(t):
    """هل النصُّ مشكَّلٌ جيّدًا أصلًا؟ (نسبةُ الحركاتِ إلى الحروفِ عالية)."""
    import re as _re
    letters=_re.findall(r"[\u0621-\u064a]", t or "")
    marks=_re.findall(r"[\u064b-\u0652\u0670]", t or "")
    return bool(letters) and (len(marks)/len(letters))>=0.5

def make_exercise(text, level):
    if not text or not text.strip(): return "","",(level or ""),"— أدخِل نصًّا أوّلًا."
    # إن كان الإدخالُ مشكَّلًا أصلًا فهو المرجعُ الصحيح (لا نُعيدُ تشكيلَه بالنموذج فنُدخِلَ اختلافًا)
    if _well_diacritized(text):
        dia=text.strip()
    else:
        dia,_=diacritize(text)
    onlyfinal=(level or "").startswith("الآخِر")
    if onlyfinal:
        pre="\n".join(" ".join(_mask_final(w) for w in ln.split()) for ln in dia.split("\n"))
        hint="🟢 المستوى: الآخِر فقط — التشكيلُ الداخليُّ ظاهر، أكمِل حركةَ آخِرِ كلِّ كلمة، ثمّ «صحِّح»."
    else:
        pre="\n".join(strip_diacritics(ln) for ln in dia.split("\n"))
        hint="🔵 المستوى: كامل — اكتب النصَّ مُشكَّلًا بالكامل، ثمّ «صحِّح»."
    return pre, dia, (level or ""), hint

def _progress_md(st):
    st=st or {}; s=st.get("s",0); wt=st.get("wt",0); wok=st.get("wok",0)
    pct=(100*wok/wt) if wt else 0
    return (f"**تقدّمك في الجلسة** — تمارينُ مصحَّحة: {s} · "
            f"كلماتٌ صحيحة: {wok}/{wt} ({pct:.0f}%)")

def grade(attempt, reference, level, st):
    if not reference: return "<div dir='rtl'>جهّز تمرينًا أوّلًا.</div>", st, _progress_md(st)
    onlyfinal=(level or "").startswith("الآخِر")
    ref_lines=reference.split("\n"); att_lines=attempt.split("\n")
    cells=[]; n=0; ok=0
    for li,rl in enumerate(ref_lines):
        rw=rl.split(); aw=(att_lines[li].split() if li<len(att_lines) else [])
        roles=explain(rw) if onlyfinal else None
        for i,rword in enumerate(rw):
            a=aw[i] if i<len(aw) else ""
            n+=1
            if onlyfinal: good=(final_class(rword)==final_class(a))
            else:
                _,rc=split_letters_and_diacritics(rword); _,ac=split_letters_and_diacritics(a)
                good=(list(rc)==list(ac))
            if good:
                ok+=1; cells.append(f"<span style='color:#2e7d32;margin:0 6px'>{a or rword} ✓</span>")
            else:
                extra=""
                if onlyfinal and roles: extra=f" <sub style='color:#1F3864'>[{roles[i]['حركة']} — {roles[i]['دور']}]</sub>"
                cells.append(f"<span style='color:#c0392b;margin:0 6px'>{a or '—'} ✗ "
                             f"<sub style='color:#2e7d32'>({rword})</sub>{extra}</span>")
        cells.append("<br>")
    st=dict(st or {"s":0,"wt":0,"wok":0})
    st["s"]=st.get("s",0)+1; st["wt"]=st.get("wt",0)+n; st["wok"]=st.get("wok",0)+ok
    score=100*ok/max(1,n)
    html=(f"<div dir='rtl' style='font-family:Arial;font-size:20px;line-height:2.6'>"
          + " ".join(cells) +
          f"<div style='font-size:18px;margin-top:10px'><b>درجةُ هذا التمرين: {ok}/{n} = {score:.0f}%</b></div></div>")
    return html, st, _progress_md(st)

# ---------- تبويب النطق ----------
def speak(text, voice_label, custom_voice, mode_label, rate, pitch, gem, gap):
    if not text or not text.strip(): return None, "لا نصّ."
    rec=user_voice.lookup(text)                 # فضِّل تسجيلَ المستخدم إن وُجد
    if rec: return rec, "🎙️ تسجيلُك المحفوظ (بصوتك)"
    ap=quran_audio.audio_path(text)             # تلاوةٌ حقيقيّةٌ للآية/المقطع إن توفّرت
    if ap: return ap, "🕌 تلاوةٌ حقيقيّةٌ (تسجيل قارئ)"
    mode="waqf" if (mode_label or "").startswith("وقف") else "wasl"
    try:                                        # نصٌّ مختلط: قرآنٌ حقيقيٌّ + عاديّ
        spans=quran_audio.split_quran_spans(text)
        if len(spans)>1 and any(sp["type"]=="quran" for sp in spans):
            mp=_render_mixed(spans, mode)
            if mp: return mp, "🕌 مختلط: قرآنٌ حقيقيٌّ مسترَدّ + قراءةٌ عاديّة"
    except Exception as e:
        print("mixed:", e)
    dia,_=diacritize(text)
    if not dia.strip(): return None, "لا نصّ."
    voice=(custom_voice or "").strip() or VOICE_BY_LABEL.get(voice_label, tts_engine.default_voice())
    if voice not in ("__espeak__","__piper__"):   # سبكُ لفظ الجلالة الحقيقيّ (أصواتٌ عصبيّة)
        try:
            import lafz_splice
            if lafz_splice.available():
                lp=lafz_splice.read_with_lafz(dia, mode=mode, voice=voice, rate_pct=rate)
                if lp: return lp, "🕌 قراءةٌ مع لفظ الجلالة الحقيقيّ (تلاوة قارئ)"
        except Exception as e:
            print("lafz splice:",e)
    # المحرّكات العصبيّة (edge/gTTS) تُتقن التشكيلَ بنفسها ← تحضيرٌ خفيفٌ نظيف؛
    # espeak فقط (تركيبيّ) يحتاج فكَّ الشدّةِ وإدغامَ اللام يدويًّا.
    from pronounce import edge_prepare, espeak_prepare
    if voice in ("__espeak__","__piper__"):
        spoken=espeak_prepare(dia, mode=mode)   # نظيفٌ قياسيّ: espeak يتولّى اللامَ والسكونَ والشدّة
    else:
        spoken=edge_prepare(dia, mode=mode)
    _,lat=g2p.phonemize(dia, mode)                             # نقحرةٌ تعليميّة
    try:
        p,engine=tts_engine.synthesize(spoken, voice=voice, rate_pct=rate,
                                       pitch_hz=pitch, word_gap=int(gap))
        return p, (f"المحرّك: {engine} | الوضع: {'وقف' if mode=='waqf' else 'وصل'}\n"
                   f"النطق (نقحرة): {lat}\nالنصّ المُغذَّى: {spoken}")
    except Exception as e:
        print("TTS خطأ:", e); return None, f"تعذّر النطق: {e}"

# ---------- تبويب الحروف والنطق (تهجئة) ----------
def letters_html(text):
    if not text or not text.strip(): return "<div dir='rtl'>—</div>"
    dia,_=diacritize(text)
    rows=g2p.letters_breakdown(dia)
    trs=[]
    for disp,ln,vn,tr,note,ws in rows:
        if ws and trs:
            trs.append("<tr><td colspan='5' style='background:#eef3ff;height:6px;padding:0'></td></tr>")
        trs.append(f"<tr><td style='font-size:24px;color:#1F3864'>{disp}</td>"
                   f"<td>{ln}</td><td>{vn}</td><td style='direction:ltr'>{tr}</td>"
                   f"<td style='color:#b8860b'>{note}</td></tr>")
    return ("<div dir='rtl' style='font-family:Arial'>"
            "<table style='width:100%;border-collapse:collapse;font-size:15px' border='1' cellpadding='6'>"
            "<tr style='background:#1F3864;color:#fff'><th>الحرف</th><th>اسم الحرف</th>"
            "<th>الحركة</th><th>النطق</th><th>ملاحظة تجويديّة</th></tr>"
            + "".join(trs) + "</table>"
            "<div style='font-size:12px;color:#888;margin-top:6px'>الملاحظاتُ التجويديّةُ مبسّطةٌ للتعليم "
            "(قلقلة، مدّ، تشديد، غنّة).</div></div>")

def speak_letters(text, voice_label, custom_voice, rate):
    dia,_=diacritize(text)
    spell=g2p.spell_text(dia)
    if not spell.strip(): return None,"لا نصّ."
    voice=(custom_voice or "").strip() or VOICE_BY_LABEL.get(voice_label, tts_engine.default_voice_id())
    try:
        p,engine=tts_engine.synthesize(spell, voice=voice, rate_pct=int(rate), word_gap=24)
        return p, f"المحرّك: {engine}\nالتهجئة: {spell}"
    except Exception as e:
        print("TTS خطأ:", e); return None, f"تعذّر النطق: {e}"

# ---------- تبويب القاعدة النورانيّة ----------
def _is_rec(it):
    from pronounce import _units as _u
    uu=_u(it)
    return bool(uu and qaida_voice.get_unit(*uu[0]))

def lesson_grid(title):
    L=qaida.by_title(title); cells=[]
    for it in L["items"]:
        ok=_is_rec(it)
        bg="#e3f2e8" if ok else "#ffffff"; bd="#3a7a5a" if ok else "#cbd5e6"; mk="✅" if ok else "⬜"
        cells.append(f"<span style='display:inline-block;margin:4px;padding:6px 12px;"
                     f"border:1px solid {bd};border-radius:8px;font-size:24px;color:#1F3864;"
                     f"background:{bg}'>{it} <span style='font-size:14px'>{mk}</span></span>")
    d=sum(1 for it in L["items"] if _is_rec(it))
    return (f"<div dir='rtl' style='font-family:Arial'><b style='font-size:18px'>{L['t']}</b>"
            f" — <span style='color:#555'>{L['n']}</span> "
            f"<span style='color:#3a7a5a;font-size:14px'>({d}/{len(L['items'])} مسجَّلة)</span>"
            f"<div style='margin-top:10px;line-height:2.6'>{''.join(cells)}</div></div>")

def qaida_lesson(title):
    L=qaida.by_title(title); items=L["items"]
    return lesson_grid(title), gr.update(choices=items, value=(items[0] if items else None))

def record_progress():
    from pronounce import _units as _u
    total=0; done=0; rows=[]
    for tag,title,items,ess in qaida.record_plan():
        cells=[]; d=0
        for it in items:
            uu=_u(it); ok=bool(uu and qaida_voice.get_unit(*uu[0]))
            total+=1
            if ok: done+=1; d+=1
            bg="#e3f2e8" if ok else "#ffffff"; bd="#3a7a5a" if ok else "#cbd5e6"; mk="✅" if ok else "⬜"
            cells.append(f"<span style='display:inline-block;margin:3px;padding:4px 9px;border:1px solid {bd};"
                         f"border-radius:8px;background:{bg};font-size:20px;color:#1F3864'>{it} <span style='font-size:12px'>{mk}</span></span>")
        badge="أساسيّ" if ess else "اختياريّ"
        rows.append(f"<div style='margin:10px 0'><b>{tag} — {title}</b> "
                    f"<span style='color:#777;font-size:13px'>({d}/{len(items)} · {badge})</span>"
                    f"<div style='line-height:2.4'>{''.join(cells)}</div></div>")
    pct=(100*done/total) if total else 0
    head=(f"<div dir='rtl' style='font-family:Arial'><b style='font-size:16px'>"
          f"التقدّم في التسجيل: {done} / {total} وحدة</b>"
          f"<div style='height:10px;background:#e6ded0;border-radius:6px;margin:6px 0 12px'>"
          f"<div style='height:100%;width:{pct:.0f}%;background:#3a7a5a;border-radius:6px'></div></div>")
    return head+"".join(rows)+"</div>"

def _saved_md():
    return f"الوحدات المسجّلة بصوتك: **{len(qaida_voice.saved_units())}**"

def qaida_refresh(title):
    return lesson_grid(title), record_progress(), _saved_md()

def gen_all_units(title):
    """يولّد الوحداتِ الناقصةَ بمحرّك edge على هذا الجهاز، ثمّ يُنعش اللوحات."""
    try:
        import build_qaida_voices as bqv
        r=bqv.generate()
    except Exception as e:
        return f"⚠️ تعذّر التوليد: {e}", lesson_grid(title), record_progress(), _saved_md()
    if r.get("error"):
        msg="⚠️ "+r["error"]
    else:
        msg=(f"✅ وُلِّد {r['made']} وحدة بمحرّك edge | صوتُك محفوظ: {r['skip_user']} | "
             f"موجودٌ سلفًا: {r['skip_have']} | إخفاقات: {r['fail']} | المجموع: {r['total']}")
        if r.get("verify"): msg+="  🔎 راجِع وحداتِ المدّ سمعيًّا: "+" ".join(r["verify"])
    return msg, lesson_grid(title), record_progress(), _saved_md()

def synth_units(text, mode="وقف (طبيعيّ — يُسكَّن الآخِر)"):
    """انطق أيَّ نصٍّ بأصوات القاعدة — من تسجيلاتك أنت فقط. يستعمل استردادَ القرآن،
    ثمّ يطبّق التصحيحَ الصوتيّ (اللام الشمسيّة/القمريّة، لفظ الجلالة، التضعيف)."""
    if not text or not text.strip(): return None,"أدخِل نصًّا."
    try:
        import ocr_engine as _oe; text=_oe.matn_for_reading(text)
    except Exception: pass
    from pronounce import unit_prepare
    dia,_=diacritize(text)                  # استرداد القرآن الموثوق أو تشكيل النموذج
    m="wasl" if str(mode).startswith("وصل") else "waqf"
    phon=unit_prepare(dia, mode=m)          # جلالةٌ صوتيّة + لام + تضعيف (خاصّ بالوحدات)
    p,rec,tot,missing=qaida_voice.synth_text(phon)
    if not p: return None,"تعذّر التركيب — سجّل أو ولّد وحداتٍ أوّلًا."
    msg=f"النصّ المشكّل: {dia}\nالصورة النطقيّة: {phon}\nوحداتٌ بصوتك: {rec}/{tot}"
    if missing: msg+=f"\nوحداتٌ ناقصة (سُكِت مكانَها): {' '.join(missing[:30])}"
    return p, msg

def synth_edge(text, mode="وقف (طبيعيّ — يُسكَّن الآخِر)"):
    """نطقٌ طبيعيٌّ متّصلٌ بمحرّك edge (موصى به للقراءة): استردادُ القرآن + كلُّ قواعد
    النطق (الشمسيّة/القمريّة، تفخيم الجلالة، الشدّة، المدّ، الهمزة)."""
    if not text or not text.strip(): return None,"أدخِل نصًّا."
    try:
        import ocr_engine as _oe; text=_oe.matn_for_reading(text)
    except Exception: pass
    ap=quran_audio.audio_path(text)               # تلاوةٌ حقيقيّةٌ للآية/المقطع إن توفّرت
    if ap: return ap, "🕌 تلاوةٌ حقيقيّةٌ (تسجيل قارئ)"
    m="wasl" if str(mode).startswith("وصل") else "waqf"
    try:                                          # نصٌّ مختلط: قرآنٌ حقيقيٌّ + عاديّ
        spans=quran_audio.split_quran_spans(text)
        if len(spans)>1 and any(sp["type"]=="quran" for sp in spans):
            mp=_render_mixed(spans, m)
            if mp: return mp, "🕌 مختلط: قرآنٌ حقيقيٌّ مسترَدّ + قراءةٌ عاديّة"
    except Exception as e:
        print("mixed:", e)
    from pronounce import edge_prepare
    dia,r=diacritize(text)
    try:                                  # سبكُ لفظ الجلالة الحقيقيّ في غير القرآن
        import lafz_splice
        if lafz_splice.available():
            lp=lafz_splice.read_with_lafz(dia, mode=m)
            if lp: return lp, f"🕌 قراءةٌ مع لفظ الجلالة الحقيقيّ\nالنصّ المشكّل: {dia}"
    except Exception as e:
        print("lafz splice:",e)
    spoken=edge_prepare(dia, mode=m)     # نصٌّ مشكّلٌ نظيفٌ — edge يتولّى الشدّة واللام والمدّ
    try:
        p,eng=tts_engine.synthesize(spoken, voice=tts_engine.default_voice(),
                                    rate_pct=0, word_gap=0)
        return p, f"المحرّك: {eng} | التوجيه: {r}\nالنصّ المشكّل: {dia}"
    except Exception as e:
        return None, f"تعذّر النطق: {e}"

def synth_f5(text, mode="وقف (طبيعيّ — يُسكَّن الآخِر)"):
    """نطقٌ عصبيٌّ SOTA بـ Arabic F5-TTS (أمينٌ للتشكيل، يحتاج GPU وإعدادًا مرّةً)."""
    if not text or not text.strip(): return None,"أدخِل نصًّا."
    try:
        import ocr_engine as _oe; text=_oe.matn_for_reading(text)
    except Exception: pass
    if not tts_engine.f5_available():
        return None, ("نموذجُ F5 غير مُعَدّ. شغّل مرّةً: .\\run_setup_f5.bat "
                      "(يثبّت f5-tts وينزّل الأوزان)، ثمّ أعِد التشغيل.")
    ap=quran_audio.audio_path(text)
    if ap: return ap, "🕌 تلاوةٌ حقيقيّةٌ (تسجيل قارئ)"
    from pronounce import edge_prepare
    dia,r=diacritize(text)
    m="wasl" if str(mode).startswith("وصل") else "waqf"
    spoken=edge_prepare(dia, mode=m)
    try:
        p,eng=tts_engine.synthesize(spoken, voice="__f5__")
        return p, f"المحرّك: {eng} | التوجيه: {r}\nالنصّ المشكّل: {dia}"
    except Exception as e:
        return None, f"تعذّر نطقُ F5: {e}"

def save_f5_reference(audio_path, ref_text):
    """يحفظ صوتَ المرجع لـ F5 (يحوّله wav أحاديًّا) ويضبط f5_reference.json.
    ref_text: النصُّ المشكّلُ كما نُطِق تمامًا (يُوقِف النسخَ التلقائيّ فيُسرِّع ويُدقِّق)."""
    import json, shutil, os
    if not audio_path or not os.path.exists(audio_path):
        return "⚠️ سجّل الصوتَ أوّلًا."
    if not (ref_text or "").strip():
        return "⚠️ الصِق النصَّ المشكّلَ للجملة كما نطقتَها."
    os.makedirs("voices", exist_ok=True)
    dst=os.path.join("voices","f5_ref.wav")
    try:                                   # حوِّل إلى wav أحاديّ ١٦ك (الأنسب لـ F5)
        import soundfile as sf, numpy as np
        data,sr=sf.read(audio_path)
        if getattr(data,"ndim",1)>1: data=data.mean(axis=1)
        sf.write(dst, data, sr, subtype="PCM_16")
    except Exception:
        try: shutil.copy(audio_path,dst)
        except Exception as e: return f"⚠️ تعذّر حفظُ الصوت: {e}"
    json.dump({"ref_audio":dst.replace("\\","/"),"ref_text":ref_text.strip()},
              open("f5_reference.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    return (f"✅ حُفِظ صوتُ المرجع ({dst}) وضُبِط f5_reference.json.\n"
            "أعِد تشغيلَ التطبيق ثمّ استعمل زرَّ F5 — سيقلّد هذا الصوتَ بلا نسخٍ تلقائيّ.")

def synth_piper(text, mode="وقف (طبيعيّ — يُسكَّن الآخِر)"):
    """نطقٌ عصبيٌّ محلّيٌّ بـ Piper (أمينٌ للتشكيل: سكون/شدّة صحيحة، بلا إنترنت).
    نفسُ تحضيرِ edge لكن بمحرّكٍ لا يختزل السكون."""
    if not text or not text.strip(): return None,"أدخِل نصًّا."
    try:
        import ocr_engine as _oe; text=_oe.matn_for_reading(text)
    except Exception: pass
    if not tts_engine.piper_available():
        return None, ("لا نموذجَ Piper بعد. نزّله مرّةً: .\\run_download_piper.bat "
                      "ثمّ ثبّت: pip install piper-tts، وأعِد التشغيل.")
    ap=quran_audio.audio_path(text)               # تلاوةٌ حقيقيّةٌ للآية إن توفّرت
    if ap: return ap, "🕌 تلاوةٌ حقيقيّةٌ (تسجيل قارئ)"
    from pronounce import edge_prepare, espeak_prepare, clean_for_tts, apply_overrides
    dia,r=diacritize(text)
    m="wasl" if str(mode).startswith("وصل") else "waqf"
    # المسارُ الافتراضيّ: نصّيٌّ عبر eSpeak الداخليّ (توزيعُ تدريبِ النموذج ← أنطقُ وأقربُ للعربيّة).
    # المسارُ الخام (IPA يدويّ بتفخيم اللام) اختياريٌّ عبر PIPER_RAW=1 (قد يبدو أعجميًّا لاختلافِ التوزيع).
    import os as _os2
    _use_raw = _os2.environ.get("PIPER_RAW","0")=="1"
    if _use_raw and tts_engine.piper_raw_available():
        try:
            import g2p, tempfile, os as _os
            prep=apply_overrides(clean_for_tts(dia))
            ipa=g2p.phonemize(prep, mode=m)
            ipa=ipa[0] if isinstance(ipa,tuple) else ipa
            try:
                import ar_stress; ipa=ar_stress.add_stress(ipa)   # نبرُ الفصحى ← يزيلُ الطابعَ الأعجميّ
            except Exception as _se: print("stress skip:", _se)
            outp=_os.path.join(tempfile.gettempdir(), "piper_raw.wav")
            tts_engine.piper_phonemes_save(ipa, outp)
            return outp, ("🧠 Piper (phoneme خام — يحترمُ التفخيم/الترقيق واللامَ الشمسيّة)\n"
                          f"IPA: {ipa}\nالمشكّل: {dia}")
        except Exception as e:
            print("piper raw → رجوعٌ للمسار النصّيّ:", e)
    # الاحتياط: المسارُ النصّيّ عبر espeak الداخليّ
    spoken=espeak_prepare(dia, mode=m)   # espeak يتولّى اللامَ الشمسيّة/القمريّة والسكونَ والشدّةَ بنفسه
    try:
        p,eng=tts_engine.synthesize(spoken, voice="__piper__", rate_pct=0)
        return p, f"المحرّك: {eng} | التوجيه: {r}\nالنصّ المشكّل: {dia}"
    except Exception as e:
        return None, f"تعذّر نطقُ Piper: {e}"

def cache_info():
    """سطرُ حالةِ الذاكرة المحلّيّة للأصوات."""
    n,sz=tts_engine.cache_stats()
    mb=sz/1048576
    return (f"🗄️ الذاكرة المحلّيّة: **{n}** مقطعًا مخزَّنًا ({mb:.1f} م.ب) — "
            "النصوصُ المتكرّرةُ تُشغَّل فورًا وبلا إنترنت.")

def cache_clear():
    n=tts_engine.clear_cache()
    return f"🧹 فُرِّغت الذاكرة ({n} ملفًّا). سيُعاد التوليدُ من الخادم عند الحاجة."

def play_unit(item):
    """انطق الوحدةَ المختارة: صوتُك إن سجّلتَه، وإلّا نطقٌ حيٌّ نظيفٌ بمحرّك edge."""
    if not item or not item.strip(): return None,"اختر وحدةً."
    txt=item.strip()
    if qaida_voice.is_user(txt):                 # تسجيلُك الشخصيّ أوّلًا
        p=qaida_voice.get_unit_text(txt)
        if p: return p,"🎙️ تسجيلُك"
    try:                                          # نطقٌ حيٌّ نظيفٌ (لا الملفّات المولّدة)
        p,eng=tts_engine.synthesize(txt, voice=tts_engine.default_voice(), rate_pct=0)
        return p, f"🔊 {eng}"
    except Exception as e:
        return None, f"تعذّر النطق: {e}"

TITLE="نظام تعليم النطق النحويّ — CompactShakkil (BERT-graft)"
def ocr_run(image_path, file_path=None, pages=None, fast=False, structured=False):
    """استخرج النصَّ من صورة أو PDF. fast=استخراجٌ سريعٌ من طبقة نصّ PDF الرقميّ."""
    src=file_path or image_path
    if not src: return "", "ارفع صورةً أو ملفَّ PDF أولًا."
    try:
        import ocr_engine
    except Exception as e:
        return "", f"OCR غير متاح: {e}"
    txt=ocr_engine.ocr_any(src, pages=pages, fast=bool(fast), structured=bool(structured))
    if structured and isinstance(txt,str) and not txt.startswith('⚠️'):
        txt=ocr_engine.format_sections(txt)
    if isinstance(txt,str) and txt.startswith("⚠️"): return "", txt
    # الاسترجاعُ مُعطَّلٌ افتراضيًّا: نعتمدُ على المحوِّلِ العصبيِّ الموحَّدِ (قرآن+عاديّ) لا الترقيع.
    # لتفعيلِه تجريبيًّا فقط: set OCR_RETRIEVAL=1
    if os.environ.get("OCR_RETRIEVAL","0")=="1":
        try:
            import quran_audio as _q
            txt=_q.restore_quran_partial(txt)   # استرداد جزئيّ: جزءُ الآية ← الآية كاملة
        except Exception as _e:
            pass
    kind="PDF" if str(src).lower().endswith(".pdf") else "صورة"
    how="سريع/بالحركات" if fast and kind=="PDF" else "OCR (بالحركات)"
    return txt, f"✅ استُخرِج {len(txt.split())} كلمة من {kind} — {how}. حرّرْه ثمّ انطقه."

def ocr_save(text):
    """احفظ النصَّ المستخرَجَ لمجموعة تحسين نموذج التشكيل."""
    if not text or not text.strip(): return "لا نصّ لحفظه."
    import os
    os.makedirs("data", exist_ok=True)
    p=os.path.join("data","ocr_corpus.txt")
    with open(p,"a",encoding="utf-8") as fh: fh.write(text.strip()+"\n")
    return f"💾 حُفِظ في {p}"

def ocr_to_word(text, structured=False):
    """يُصدّرُ النصَّ المستخرَجَ إلى ملفّ Word (.docx) عربيٍّ صحيحِ الاتّجاه، مع استردادِ
    تشكيلِ الآياتِ من المصحف. يرجعُ (مسارُ الملفّ أو None, رسالة)."""
    if not text or not text.strip():
        return None, "لا نصّ للتصدير."
    import tempfile, os
    try:
        import ocr_export
    except Exception as e:
        return None, f"تعذّر: {e}"
    out=os.path.join(tempfile.gettempdir(), "ocr_export.docx")
    try:
        ocr_export.export_docx(text, out, structured=bool(structured), quran="strong")
        return out, "✅ جاهزٌ للتنزيل (Word، RTL، آياتٌ مستردَّة)."
    except Exception as e:
        return None, f"تعذّر التصدير: {e} — تأكّدْ: pip install python-docx"

def _render_mixed(spans, mode):
    """يدمجُ مقاطعَ نصٍّ مختلط: القرآن تلاوةٌ حقيقيّة، والعاديُّ بـ edge — بالترتيب."""
    import os, tempfile
    import numpy as np, soundfile as sf
    import quran_audio
    from pronounce import edge_prepare
    try:
        from lafz_splice import _read_any as _read
    except Exception:
        def _read(path, sr):
            import subprocess, shutil
            ff=shutil.which("ffmpeg") or os.path.join(os.getcwd(),"venv","Scripts","ffmpeg.exe")
            tmp=tempfile.mktemp(suffix=".wav")
            subprocess.run([ff,"-y","-loglevel","error","-i",path,"-ac","1","-ar",str(sr),tmp],check=True)
            x,_=sf.read(tmp,dtype="float32")
            try: os.remove(tmp)
            except Exception: pass
            return x
    SR=24000; pieces=[]; gap=np.zeros(int(SR*0.12),dtype="float32")
    for sp in spans:
        wp=None
        try:
            if sp["type"]=="quran":
                wp=quran_audio._concat_codes(sp["codes"])
            else:
                txt=sp.get("text","").strip()
                if not txt: continue
                dia,_=diacritize(txt)
                try:
                    import lafz_splice
                    if lafz_splice.available():
                        wp=lafz_splice.read_with_lafz(dia, mode=mode)
                except Exception: wp=None
                if not wp:
                    spoken=edge_prepare(dia, mode=mode)
                    wp,_=tts_engine.synthesize(spoken, voice=tts_engine.default_voice(),
                                               rate_pct=0, word_gap=0)
            if not wp: continue
            x=_read(wp, SR)
            if len(x): pieces.append(x); pieces.append(gap)
        except Exception as e:
            print("mixed seg err:", e)
    if not pieces: return None
    out=np.concatenate(pieces).astype("float32")
    op=os.path.join(tempfile.gettempdir(), "mixed_read.wav")
    sf.write(op, out, SR, subtype="PCM_16")
    return op

def lib_books(author):
    return gr.update(choices=shamela_import.pdf_books(author), value=None)

def lib_ocr(author, book, pages, fast, structured=True):
    import os as _os
    files=shamela_import.pdf_files(author, book)
    if not files: return "", "لا ملفّ PDF لهذا الكتاب."
    try:
        import ocr_engine
    except Exception as e:
        return "", f"OCR غير متاح: {e}"
    txt=ocr_engine.ocr_pdf(files[0], pages=(pages or "1-3"), use_ocr=not bool(fast), structured=bool(structured))
    if structured and isinstance(txt,str) and not txt.startswith('⚠️'):
        txt=ocr_engine.format_sections(txt)
    if isinstance(txt,str) and txt.startswith("⚠️"): return "", txt
    vols=f" (مجلّد ١ من {len(files)})" if len(files)>1 else ""
    return txt, f"✅ {_os.path.basename(files[0])}{vols} — {len(txt.split())} كلمة بالحركات."

def lib_save(text):
    if not text or not text.strip(): return "لا نصّ."
    import os as _os
    _os.makedirs("data",exist_ok=True)
    p=_os.path.join("data","shamela_corpus.txt")
    with open(p,"a",encoding="utf-8") as fh: fh.write(text.strip()+"\n\n")
    return f"💾 أُضيف إلى {p}"

def lib_import():
    res=shamela_import.import_all()
    msg="\n".join(f"• {n}: {st}" for n,st in res) or "لا ملفّات في مجلّد shamela/ — ضع كتبًا (.txt/.epub/.docx) ثمّ أعِد."
    return gr.update(choices=shamela_import.list_books()), msg

def lib_show(name, idx):
    if not name: return "", "اختر كتابًا أولًا."
    txt,total=shamela_import.page(name, int(idx or 0))
    return txt, f"صفحة {int(idx or 0)+1} من {total}"

def lex_fix(text):
    """تصحيحٌ لُغويٌّ لأخطاء رسم OCR عبر المعجم (يرجعُ الكلماتِ مصحَّحةً مشكَّلة)."""
    try:
        import ocr_correct
        fixed,n=ocr_correct.correct(text or "")
        return fixed, f"🩹 صُحِّحت {n} كلمة (أخطاء رسم)."
    except Exception as e:
        return text, f"تعذّر التصحيح: {e}"

def lib_diac(t):
    try: return diacritize(t)[0]
    except Exception: return t

with gr.Blocks(title=TITLE) as demo:
    gr.Markdown(f"## {TITLE}\n"
                "تشكيلٌ عالي الدقّة — **DER 1.09٪ (دقّة 98.91٪)** على مجموعةٍ خاليةٍ من التسرُّب "
                "(البنية 0.96٪، حركة الآخِر 1.48٪) — لتعليم النطق النحويّ الصحيح: "
                "شرحُ الإعراب، تمارينُ تفاعليّة، ونطقٌ صوتيٌّ أمينٌ للتشكيل.")
    with gr.Tab("① التشكيل"):
        t1=gr.Textbox(lines=8,label="النصّ (بلا تشكيل أو بتشكيلٍ ناقص)",rtl=True)
        respect1=gr.Checkbox(value=True,
            label="احترم التشكيلَ الموجودَ وأكمِل الناقصَ فقط (لا يُغيّر ما شكّلتَه)")
        o1=gr.Textbox(lines=8,label="المُشكَّل",rtl=True)
        r1=gr.Textbox(label="التوجيه")
        gr.Button("شكِّل",variant="primary").click(diacritize,[t1,respect1],[o1,r1])
    with gr.Tab("② الإعراب والشرح"):
        t2=gr.Textbox(lines=5,label="النصّ",rtl=True)
        gr.Examples(TOPIC_EX,inputs=t2,label="أمثلةٌ تعليميّة (اضغط لتجربتها)")
        h2=gr.HTML()
        gr.Button("حلّل واشرح",variant="primary").click(explain_html,t2,h2)
        gr.HTML(LEGEND)
    with gr.Tab("③ تمارين"):
        t3=gr.Textbox(lines=4,label="نصّ التمرين (سيُخفى تشكيله)",rtl=True)
        level=gr.Radio(["الآخِر فقط (سهل)","كامل (متوسّط)"],value="الآخِر فقط (سهل)",
                       label="المستوى")
        hint=gr.Markdown()
        bare=gr.Textbox(label="اكتب تشكيلك هنا",rtl=True,interactive=True)
        ref=gr.State(""); lvl=gr.State(""); stats=gr.State({"s":0,"wt":0,"wok":0})
        gr.Examples(TOPIC_EX,inputs=t3,label="أمثلةٌ للتمرين")
        gr.Button("جهّز تمرينًا").click(make_exercise,[t3,level],[bare,ref,lvl,hint])
        res=gr.HTML()
        prog=gr.Markdown(_progress_md({}))
        gr.Button("صحِّح",variant="primary").click(grade,[bare,ref,lvl,stats],[res,stats,prog])
    with gr.Tab("④ النطق"):
        t4=gr.Textbox(lines=4,label="النصّ",rtl=True)
        with gr.Row():
            voice_dd=gr.Dropdown(VOICE_LABELS,value=DEFAULT_LABEL,label="الصوت")
            mode_dd=gr.Radio(["وقف (طبيعيّ — يُسكَّن الآخِر)","وصل (بالإعراب كاملًا)"],
                             value="وقف (طبيعيّ — يُسكَّن الآخِر)",label="طريقة النطق")
        with gr.Row():
            rate_sl=gr.Slider(-80,40,value=0,step=1,label="السرعة % (0 = طبيعيّ)")
            pitch_sl=gr.Slider(-50,50,value=0,step=1,label="طبقة الصوت (Hz)")
        gap_sl=gr.Slider(0,40,value=0,step=1,label="التمهّل بين الكلمات (0 = طبيعيّ متّصل)")
        gem_st=gr.State(True)                       # التضعيف مُفعَّلٌ دائمًا (أُزيلت الخانة)
        custom=gr.Textbox(label="صوتٌ مخصّص (اختياريّ) — اكتب معرّف edge-tts، مثل ar-EG-SalmaNeural",
                          rtl=False,placeholder="اتركه فارغًا لاستعمال الصوت المختار أعلاه")
        au=gr.Audio(label="النطق",type="filepath")
        info4=gr.Textbox(label="تفاصيل",rtl=True,lines=2)
        gr.Examples(["قل هو الله احد","بسم الله الرحمن الرحيم","إن العلم نور"],inputs=t4,
                    label="أمثلةٌ للنطق")
        gr.Button("انطق",variant="primary").click(
            speak,[t4,voice_dd,custom,mode_dd,rate_sl,pitch_sl,gem_st,gap_sl],[au,info4])
    with gr.Tab("⑤ نطق النصّ / الآية"):
        gr.Markdown("### 🔊 انطق أيَّ نصّ / آية")
        gr.Markdown("قراءةٌ متّصلةٌ تطبّقُ كلَّ القواعد: **استردادُ القرآن الحقيقيّ** (مفرد/متعدّد/مختلط)، "
                    "اللام الشمسيّة/القمريّة، **تفخيم/ترقيق لفظ الجلالة**، والأرقام.")
        synth_tb=gr.Textbox(lines=2,label="النصّ / الآية",rtl=True)
        synth_mode=gr.Radio(["وقف (طبيعيّ — يُسكَّن الآخِر)","وصل (بالإعراب كاملًا)"],
                            value="وقف (طبيعيّ — يُسكَّن الآخِر)",label="طريقة النطق")
        gr.Examples(["قل هو الله احد","بسم الله الرحمن الرحيم","الحمد لله رب العالمين",
                     "الله لا اله الا هو الحي القيوم"],
                    inputs=synth_tb,label="أمثلة")
        synth_audio=gr.Audio(type="filepath",label="النطق")
        synth_info=gr.Textbox(label="تفاصيل",rtl=True,lines=3)
        with gr.Row():
            gr.Button("انطق (edge طبيعيّ)",variant="primary").click(
                synth_edge,[synth_tb,synth_mode],[synth_audio,synth_info])
            gr.Button("انطق (Piper محلّيّ)",variant="secondary").click(
                synth_piper,[synth_tb,synth_mode],[synth_audio,synth_info])
        with gr.Accordion("🎙️ صوتٌ مرجعيّ لـ F5 (اختياريّ)",open=False):
            gr.Markdown("سجّل جملةً واضحةً (٥–١٠ ثوانٍ)، والصِق نصَّها المشكّلَ كما نطقتَها، ثمّ احفظ.")
            f5ref_audio=gr.Audio(sources=["microphone","upload"],type="filepath",
                                 label="سجّل/ارفع صوتَ المرجع (WAV)")
            f5ref_text=gr.Textbox(lines=2,rtl=True,label="نصُّ المرجع (مشكّلٌ بالكامل)")
            f5ref_msg=gr.Textbox(label="الحالة",rtl=True,lines=2,interactive=False)
            gr.Button("💾 احفظ كصوتٍ مرجعيّ لـ F5",variant="primary").click(
                save_f5_reference,[f5ref_audio,f5ref_text],f5ref_msg)
        cache_md=gr.Markdown(cache_info())
        with gr.Row():
            gr.Button("🔄 تحديث حالة الذاكرة").click(cache_info,None,cache_md)
            gr.Button("🧹 تفريغ الذاكرة المحلّيّة").click(cache_clear,None,cache_md)
        demo.load(cache_info, None, cache_md)

    with gr.Tab("⑥ قراءة صورة (OCR)"):
        gr.Markdown("ارفع صورةَ صفحةٍ (مصحف أو مطبوع). يُستخرَجُ النصُّ **بالحركات** "
                    "ثمّ يُنطَق (الآياتُ تُطابَقُ تلقائيًّا ← تلاوةٌ حقيقيّة).")
        ocr_img=gr.Image(type="filepath",label="صورة (رفع/لصق)",sources=["upload","clipboard"])
        ocr_file=gr.File(type="filepath",label="أو ملفّ PDF / صورة",
                         file_types=[".pdf",".png",".jpg",".jpeg",".webp",".tif",".tiff",".bmp"])
        ocr_pages=gr.Textbox(label="صفحات PDF (مثل 1-3,5 — فارغ = كلّ الصفحات)",value="")
        ocr_fast=gr.Checkbox(value=False,label="استخراجٌ سريعٌ للـ PDF الرقميّ: يستعملُ طبقةَ النصّ فقط إن كانت مشكَّلةً (يحافظُ على الحركات)، وإلّا يحوّلُ للـ OCR تلقائيًّا.")
        ocr_struct=gr.Checkbox(value=False,label="افصلِ الأقسام (عنوان/متن/حواشٍ) — للكتب المطبوعة ذات الهوامش؛ عند النطق يُقرَأُ المتنُ فقط. اتركه فارغًا لصفحات المصحف.")
        with gr.Row():
            ocr_btn=gr.Button("استخرج النصّ (بالحركات)",variant="primary")
            ocr_speak_btn=gr.Button("استخرج ثمّ انطق",variant="secondary")
        ocr_out=gr.Textbox(lines=8,label="النصّ المستخرَج (قابلٌ للتحرير)",rtl=True,interactive=True)
        ocr_audio=gr.Audio(type="filepath",label="النطق")
        ocr_info=gr.Textbox(label="تفاصيل",rtl=True,lines=2)
        with gr.Row():
            gr.Button("🩹 صحّح لغويًّا (معجم)").click(lex_fix, ocr_out, [ocr_out, ocr_info])
            ocr_save_btn=gr.Button("💾 احفظ النصّ لمجموعة التحسين")
            ocr_save_msg=gr.Textbox(label="الحفظ",rtl=True,lines=1,interactive=False)
        ocr_btn.click(ocr_run, [ocr_img, ocr_file, ocr_pages, ocr_fast, ocr_struct], [ocr_out, ocr_info])
        ocr_speak_btn.click(ocr_run, [ocr_img, ocr_file, ocr_pages, ocr_fast, ocr_struct], [ocr_out, ocr_info]).then(
            synth_edge, [ocr_out, synth_mode], [ocr_audio, ocr_info])
        ocr_save_btn.click(ocr_save, ocr_out, ocr_save_msg)
        with gr.Row():
            ocr_word_btn=gr.Button("📄 صدّر إلى Word (.docx)", variant="secondary")
            ocr_word_file=gr.File(label="ملفّ Word للتنزيل", interactive=False)
        ocr_word_btn.click(ocr_to_word, [ocr_out, ocr_struct], [ocr_word_file, ocr_info])

    with gr.Tab("⑦ المكتبة الشاملة"):
        gr.Markdown("مكتبةُ الشاملة (PDF مشكَّل) — اختَرِ المؤلّفَ ثمّ الكتابَ، وحدّدِ الصفحاتِ ثمّ استخرجْ بالـ OCR (بالحركات). "
                    "الكتبُ مصوَّرةٌ فتُعالَجُ بالـ OCR؛ ابدأْ بصفحاتٍ قليلةٍ (مثل 1-3) لأنّه يأخذ وقتًا.")
        with gr.Row():
            lib_author=gr.Dropdown(shamela_import.pdf_authors(), label="المؤلّف", filterable=True)
            lib_book=gr.Dropdown([], label="الكتاب", filterable=True)
        with gr.Row():
            lib_pages=gr.Textbox(value="1-20", label="الصفحات (مثل 1-1000 مدعومة — للكتاب كامل استعمل الاستخراج المجمَّع run_extract_book.bat، أسرع وبالخلفيّة)")
            lib_fast=gr.Checkbox(value=False, label="سريع (طبقة نصّ إن كانت مشكَّلة، وإلّا OCR)")
            lib_struct=gr.Checkbox(value=True, label="افصلِ الأقسام (عنوان/متن/حواشٍ) — يُقرَأُ المتنُ فقط عند النطق")
        lib_ocr_btn=gr.Button("📖 استخرج بالـ OCR (بالحركات)", variant="primary")
        lib_pinfo=gr.Textbox(label="الحالة", rtl=True, lines=1)
        lib_text=gr.Textbox(lines=10, label="النصّ المستخرَج (مشكَّل، قابلٌ للتحرير)", rtl=True)
        lib_audio=gr.Audio(type="filepath", label="النطق")
        lib_info=gr.Textbox(label="تفاصيل", rtl=True, lines=2)
        with gr.Row():
            gr.Button("🔊 انطق", variant="primary").click(synth_edge,[lib_text,synth_mode],[lib_audio,lib_info])
            gr.Button("◌ شكّل").click(lib_diac, lib_text, lib_text)
            gr.Button("🩹 صحّح لغويًّا").click(lex_fix, lib_text, [lib_text, lib_pinfo])
            lib_save_btn=gr.Button("💾 احفظ لمجموعة التدريب")
        lib_save_msg=gr.Textbox(label="الحفظ", rtl=True, lines=1, interactive=False)
        lib_author.change(lib_books, lib_author, lib_book)
        lib_ocr_btn.click(lib_ocr, [lib_author, lib_book, lib_pages, lib_fast, lib_struct], [lib_text, lib_pinfo])
        lib_save_btn.click(lib_save, lib_text, lib_save_msg)
        with gr.Accordion("استيرادُ ملفّاتٍ نصّيّة (txt/epub/docx/db) من مجلّد shamela/", open=False):
            lib_import_btn=gr.Button("📥 استورد")
            lib_status=gr.Textbox(label="حالة الاستيراد", rtl=True, lines=2)
            lib_import_btn.click(lib_import, None, [lib_book, lib_status])

    gr.Examples(TOPIC_EX,inputs=t1,label="أمثلةٌ للتشكيل")

if __name__=="__main__":
    demo.launch(server_name="127.0.0.1",server_port=7860,inbrowser=True)
