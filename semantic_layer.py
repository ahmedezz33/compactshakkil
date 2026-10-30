# -*- coding: utf-8 -*-
"""semantic_layer.py — الطبقةُ [3] الدلاليّة (اختياريّة). المحرّكُ الافتراضيّ: Ollama محلّيّ.
المعماريّة: CAMeL (محلّلٌ لغويّ) يكشفُ الكلماتِ الملتبسةَ (للفعلِ قراءتان: معلوم/مجهول+)،
ونموذجٌ كبيرٌ محلّيٌّ (عبر Ollama) يحسمُ بالمعنى، فنأخذُ حركتَه لتلك الكلمةِ فقط.
لا يُستدعى LLM إلّا على الملتبسِ الحقيقيّ. خصوصيّةٌ تامّةٌ (لا نصَّ يغادرُ الجهاز).

التفعيل: شغّلْ Ollama واسحبِ النموذجَ (ollama pull qwen2.5:7b)؛ الإعداداتُ في semantic_config.json.
لا يُوصَلُ بالتطبيقِ إلّا بعد قياسِ الأثرِ على مجموعةٍ ذهبيّةٍ خاصّة."""
import os, json, functools, urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_KEY_PATH = os.path.join(_HERE, "semantic_key.txt")
_CFG_PATH = os.path.join(_HERE, "semantic_config.json")
_CACHE = {}

def _cfg():
    cfg = {"endpoint": "http://localhost:11434/v1/chat/completions",
           "model": "qwen2.5:7b", "local": True, "timeout": 30, "max_words_per_text": 12}
    try: cfg.update(json.load(open(_CFG_PATH, encoding="utf-8")))
    except Exception: pass
    return cfg

def _key():
    k = os.environ.get("SEMANTIC_KEY", "").strip()
    if k: return k
    try: return open(_KEY_PATH, encoding="utf-8").read().strip()
    except Exception: return ""

def enabled():
    """محلّيٌّ (Ollama) لا يحتاجُ مفتاحًا؛ السحابيُّ يحتاجُ semantic_key.txt."""
    return bool(_cfg().get("local")) or bool(_key())

_AN = None
def _analyzer():
    global _AN
    if _AN is None:
        from camel_tools.morphology.database import MorphologyDB
        from camel_tools.morphology.analyzer import Analyzer
        _AN = Analyzer(MorphologyDB.builtin_db())
    return _AN

from camel_snap import _norm, _strip

@functools.lru_cache(maxsize=100000)
def _voice_pair(bare):
    """زوجُ (معلوم، مجهول) لنفسِ الجذرِ ونفسِ الرسمِ فقط — التباسُ الصوتِ الحقيقيّ."""
    try: ana = _analyzer().analyze(bare)
    except Exception: return tuple()
    act = {}; pas = {}
    for a in ana:
        if a.get("pos") != "verb" or not a.get("diac"): continue
        d = a["diac"]
        if _strip(d) != bare: continue                 # نفسُ الرسمِ بالضبط
        lex = a.get("lex", ""); vox = a.get("vox")
        if vox == "a": act.setdefault((lex, _norm(d)), d)
        elif vox == "p": pas.setdefault((lex, _norm(d)), d)
    for (la, na), da in act.items():
        for (lp, npv), dp in pas.items():
            if la == lp and na != npv:
                return (da, dp)                          # (معلوم، مجهول)
    return tuple()

def ambiguous(word):
    p = _voice_pair(_strip(word))
    return list(p) if len(p) == 2 else []

def _ask_llm(sentence, word, cands):
    cfg = _cfg()
    opts = "\n".join(f"{i+1}. {c}" for i, c in enumerate(cands))
    sys_p = ("أنت مدقّقٌ لغويٌّ عربيّ. تختارُ التشكيلَ الصحيحَ لكلمةٍ واحدةٍ حسبَ معنى الجملة "
             "(خاصّةً المعلوم/المجهول). أجبْ برقمِ الخيارِ فقط لا غير.")
    usr_p = (f"الجملة: {sentence}\n\nالكلمةُ المقصودة: «{_strip(word)}»\n"
             f"الخيارات:\n{opts}\n\nأيُّها الصحيحُ في هذا السياق؟ أجبْ بالرقمِ فقط.")
    headers = {"Content-Type": "application/json"}
    k = _key()
    if k: headers["Authorization"] = f"Bearer {k}"
    body = json.dumps({"model": cfg["model"], "temperature": 0, "stream": False,
                       "messages": [{"role":"system","content":sys_p},
                                    {"role":"user","content":usr_p}]}).encode("utf-8")
    try:
        req = urllib.request.Request(cfg["endpoint"], data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as r:
            out = json.loads(r.read().decode("utf-8"))
        txt = out["choices"][0]["message"]["content"].strip()
        for ch in txt:
            if ch.isdigit():
                i = int(ch) - 1
                if 0 <= i < len(cands): return cands[i]
    except Exception as e:
        print("semantic LLM skip:", e)
    return None

def disambiguate_word(sentence, word):
    cands = ambiguous(word)
    if len(cands) < 2: return word
    if _norm(word) not in {_norm(c) for c in cands}: return word  # BERT قراءةٌ أخرى ← لا نلمس
    key = (_norm(sentence), _strip(word))
    if key in _CACHE: chosen = _CACHE[key]
    else:
        chosen = _ask_llm(sentence, word, cands); _CACHE[key] = chosen
    return chosen if chosen else word

def apply_line(line):
    if not enabled() or not line.strip(): return line
    ws = line.split(" "); budget = _cfg().get("max_words_per_text", 12)
    for i, w in enumerate(ws):
        if budget <= 0: break
        if len(ambiguous(w)) >= 2:
            nw = disambiguate_word(line, w)
            if nw != w: ws[i] = nw
            budget -= 1
    return " ".join(ws)

def apply_text(text):
    if not enabled(): return text
    return "\n".join(apply_line(ln) for ln in text.split("\n"))
