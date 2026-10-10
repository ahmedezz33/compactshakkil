# -*- coding: utf-8 -*-
"""
remote_panel.py — برنامجُك الخاصُّ للتحكّمِ بالحاسوبِ من الجوّال (بلا تطبيقاتِ طرفٍ ثالث).
المزايا: مهامٌّ (تشغيل/إيقاف) + سجلٌّ حيّ + أمرٌ حرّ + حالةُ GPU + **سطحُ مكتبٍ كامل**
(رؤيةُ الشاشة + نقر/كتابة عبر mss+pyautogui) + **تسجيلُ دخول + HTTPS + قفلٌ بعد محاولات**.

التشغيل:  python remote_panel.py
يتطلّب:   pip install flask mss pyautogui pillow cryptography
الأمان:   HTTPS ذاتيّ (المتصفّح ينبّه مرّةً — تابعْ). غيّرْ بيانات الدخول في panel_auth.json.
"""
import os, sys, io, json, time, secrets, hashlib, subprocess
from functools import wraps

HERE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(HERE, "logs"); os.makedirs(LOGDIR, exist_ok=True)
PORT = int(os.environ.get("PANEL_PORT", "8600"))
IS_WIN = os.name == "nt"

def _sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()

# ── بيانات الدخول (ملفٌّ تُحرّره) ─────────────────────────────
_AUTHF = os.path.join(HERE, "panel_auth.json")
if os.path.exists(_AUTHF):
    _AUTH = json.load(open(_AUTHF, encoding="utf-8"))
else:
    _pw = secrets.token_urlsafe(8)
    _AUTH = {"user": "admin", "pass_sha": _sha(_pw), "_plain_once": _pw}
    json.dump({"user": "admin", "pass_sha": _sha(_pw)}, open(_AUTHF, "w", encoding="utf-8"))
_SECF = os.path.join(HERE, "panel_secret.txt")
if os.path.exists(_SECF): SECRET = open(_SECF).read().strip()
else:
    SECRET = secrets.token_hex(16); open(_SECF, "w").write(SECRET)

# ── المهامّ ──────────────────────────────────────────────────
TASKS = {
    "train_large": ("run_train_large.bat", "تدريب القاعدة الكبيرة"),
    "finetune":    ("run_finetune_diac.bat", "صقل التشكيل"),
    "ensemble":    ("run_ensemble_mixed.bat", "مقارنة/دمج"),
    "clean":       ("run_clean_data.bat", "تنظيف البيانات"),
    "app":         ("run_app_teach.bat", "تطبيق Gradio"),
}
_PROC = {}
def _logp(k): return os.path.join(LOGDIR, k + ".log")
def start_task(k):
    bat,_ = TASKS[k]
    if not os.path.exists(os.path.join(HERE, bat)): return False, f"لا يوجد {bat}"
    f = open(_logp(k), "w", encoding="utf-8", errors="replace")
    cf = 0x00000200 if IS_WIN else 0
    cmd = ["cmd","/c",bat] if IS_WIN else ["bash",bat]
    p = subprocess.Popen(cmd, cwd=HERE, stdout=f, stderr=subprocess.STDOUT, creationflags=cf) if IS_WIN \
        else subprocess.Popen(cmd, cwd=HERE, stdout=f, stderr=subprocess.STDOUT)
    _PROC[k] = {"pid": p.pid, "proc": p}; return True, f"بدأ {k} (pid {p.pid})"
def stop_task(k):
    info = _PROC.get(k)
    if not info: return False, "غير مشتغل"
    try:
        if IS_WIN: subprocess.run(["taskkill","/PID",str(info['pid']),"/T","/F"], capture_output=True)
        else: os.kill(info['pid'], 15)
    except Exception as e: return False, f"تعذّر: {e}"
    _PROC.pop(k, None); return True, f"أُوقِف {k}"
def is_running(k):
    info = _PROC.get(k)
    return bool(info and info.get("proc") and info["proc"].poll() is None)
def tail(path, n=60):
    if not os.path.exists(path): return ""
    try:
        with open(path,"rb") as f:
            f.seek(0,2); sz=f.tell(); f.seek(max(0,sz-9000)); d=f.read().decode("utf-8","replace")
        return "\n".join(d.splitlines()[-n:])
    except Exception as e: return f"(تعذّر: {e})"
def gpu_status():
    try:
        o = subprocess.run(["nvidia-smi","--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=8)
        if o.returncode==0 and o.stdout.strip():
            u,mu,mt,tp=[x.strip() for x in o.stdout.strip().splitlines()[0].split(",")]
            return f"GPU {u}% · ذاكرة {mu}/{mt}MB · {tp}°"
    except Exception: pass
    return "GPU: غير متاح"
def latest_der():
    t = tail(_logp("train_large"),200) + "\n" + tail(_logp("finetune"),200)
    d = [l for l in t.splitlines() if "DER=" in l]
    return d[-1].strip() if d else "—"

# ── سطح المكتب ───────────────────────────────────────────────
_SCT = None
def _screct():
    global _SCT
    if _SCT is None:
        import mss; _SCT = mss.mss()
    return _SCT
def grab_jpeg(maxw=1280, q=55):
    from PIL import Image
    sct = _screct(); mon = sct.monitors[1]
    raw = sct.grab(mon)
    im = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    if im.width > maxw:
        r = maxw/im.width; im = im.resize((maxw, int(im.height*r)))
    b = io.BytesIO(); im.save(b, "JPEG", quality=q); return b.getvalue(), mon["width"], mon["height"]
def _pg():
    import pyautogui; pyautogui.FAILSAFE = False; return pyautogui
def do_input(d):
    pg = _pg(); t = d.get("type")
    if t in ("click","dblclick","rclick","move","scroll"):
        sw,sh = _screct().monitors[1]["width"], _screct().monitors[1]["height"]
        x = int(float(d.get("x",0))*sw); y = int(float(d.get("y",0))*sh)
        if t=="move": pg.moveTo(x,y,duration=0.05)
        elif t=="click": pg.click(x,y)
        elif t=="dblclick": pg.doubleClick(x,y)
        elif t=="rclick": pg.rightClick(x,y)
        elif t=="scroll": pg.scroll(int(d.get("amount",-300)), x=x, y=y)
    elif t=="type": pg.typewrite(d.get("text",""), interval=0.01)
    elif t=="key": pg.press(d.get("key"))
    elif t=="combo": pg.hotkey(*d.get("keys",[]))
    else: return False
    return True

# ── Flask ────────────────────────────────────────────────────
try:
    from flask import Flask, request, jsonify, Response, session, redirect
except Exception:
    print("Flask غير مثبَّت: pip install flask mss pyautogui pillow cryptography"); sys.exit(1)
app = Flask(__name__); app.secret_key = SECRET
_FAIL = {}   # ip -> (count, until)

def require_login(fn):
    @wraps(fn)
    def w(*a,**k):
        if not session.get("ok"):
            if request.path=="/" : return redirect("/login")
            return Response("غير مُصرَّح", status=401)
        return fn(*a,**k)
    return w

LOGIN = """<!doctype html><html lang=ar dir=rtl><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>دخول</title>
<style>body{font-family:system-ui;background:#0f1419;color:#e6edf3;display:grid;place-items:center;height:100vh;margin:0}
form{background:#1a2027;padding:24px;border-radius:14px;width:min(90vw,340px)}
input{width:100%;box-sizing:border-box;font-size:16px;padding:12px;margin:8px 0;border-radius:10px;border:1px solid #2a3340;background:#0b0e12;color:#e6edf3}
button{width:100%;font-size:17px;padding:12px;border:0;border-radius:10px;background:#2d6cdf;color:#fff;margin-top:8px}
.e{color:#f85149;font-size:14px;min-height:18px}</style></head><body>
<form method=post><h2>تحكّم CompactShakkil</h2><div class=e>__ERR__</div>
<input name=user placeholder="المستخدم" autocomplete=username>
<input name=pw type=password placeholder="كلمة المرور" autocomplete=current-password>
<button>دخول</button></form></body></html>"""

@app.route("/login", methods=["GET","POST"])
def login():
    ip = request.remote_addr or "?"
    c,until = _FAIL.get(ip,(0,0))
    if until>time.time():
        return Response(LOGIN.replace("__ERR__", f"مقفلٌ مؤقّتًا، جرّبْ بعد {int(until-time.time())}ث"), mimetype="text/html")
    if request.method=="POST":
        u=request.form.get("user",""); p=request.form.get("pw","")
        if u==_AUTH["user"] and _sha(p)==_AUTH["pass_sha"]:
            session["ok"]=True; _FAIL.pop(ip,None); return redirect("/")
        c+=1; _FAIL[ip]=(c, time.time()+ (120 if c>=5 else 0))
        return Response(LOGIN.replace("__ERR__","بياناتٌ خاطئة"), mimetype="text/html")
    return Response(LOGIN.replace("__ERR__",""), mimetype="text/html")

@app.route("/logout")
def logout(): session.clear(); return redirect("/login")

@app.route("/")
@require_login
def home():
    return Response(PAGE.replace("__TASKS__", json.dumps({k:v[1] for k,v in TASKS.items()}, ensure_ascii=False)), mimetype="text/html")

@app.route("/status")
@require_login
def status(): return jsonify({"gpu":gpu_status(),"der":latest_der(),"running":{k:is_running(k) for k in TASKS}})
@app.route("/tail")
@require_login
def tail_r(): return Response(tail(_logp(request.args.get("key","train_large"))), mimetype="text/plain")
@app.route("/start", methods=["POST"])
@require_login
def start_r():
    k=request.args.get("key"); 
    if k not in TASKS: return Response("مجهول",status=400)
    ok,m=start_task(k); return Response(m, status=200 if ok else 500)
@app.route("/stop", methods=["POST"])
@require_login
def stop_r():
    ok,m=stop_task(request.args.get("key")); return Response(m, status=200 if ok else 500)
@app.route("/run", methods=["POST"])
@require_login
def run_r():
    cmd=(request.get_json(silent=True) or {}).get("cmd","").strip()
    if not cmd: return Response("لا أمر",status=400)
    try:
        r=subprocess.run(cmd,cwd=HERE,shell=True,capture_output=True,text=True,timeout=120)
        return Response((r.stdout or "")+(("\n[stderr]\n"+r.stderr) if r.stderr else ""), mimetype="text/plain")
    except Exception as e: return Response(f"تعذّر: {e}",status=500)
@app.route("/screen.jpg")
@require_login
def screen_r():
    try:
        jpg,_,_=grab_jpeg(); return Response(jpg, mimetype="image/jpeg")
    except Exception as e: return Response(f"شاشة متعذّرة: {e}",status=500)
@app.route("/input", methods=["POST"])
@require_login
def input_r():
    try:
        ok=do_input(request.get_json(force=True) or {}); return Response("ok" if ok else "نوع مجهول", status=200 if ok else 400)
    except Exception as e: return Response(f"تعذّر: {e}",status=500)

PAGE = r"""<!doctype html><html lang=ar dir=rtl><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>تحكّم CompactShakkil</title><style>
 *{box-sizing:border-box}body{font-family:system-ui,Arial;margin:0;background:#0f1419;color:#e6edf3}
 .top{position:sticky;top:0;background:#11161c;padding:8px 10px;display:flex;gap:6px;align-items:center;border-bottom:1px solid #222c38;z-index:9}
 .tabs{display:flex;gap:4px;flex:1}.tab{flex:1;text-align:center;padding:10px;border-radius:10px;background:#1a2027}.tab.on{background:#2d6cdf}
 .wrap{padding:10px}.card{background:#1a2027;border:1px solid #2a3340;border-radius:12px;padding:12px;margin:8px 0}
 button{font-size:15px;padding:11px 13px;margin:3px;border:0;border-radius:10px;background:#2d6cdf;color:#fff}
 button.stop{background:#c0392b}button.sec{background:#3a4654}button.sm{padding:8px 10px;font-size:14px}
 pre{white-space:pre-wrap;background:#0b0e12;padding:10px;border-radius:8px;max-height:46vh;overflow:auto;font-size:13px}
 input,select{font-size:16px;padding:9px;border-radius:9px;border:1px solid #2a3340;background:#0b0e12;color:#e6edf3}
 .row{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.k{color:#8b98a5;font-size:13px}.ok{color:#3fb950}
 #scr{width:100%;border-radius:8px;touch-action:none;background:#000}
 .hide{display:none}.keys button{background:#2a3340}
</style></head><body>
<div class=top><div class=tabs>
 <div class=tab id=t0 onclick=tab(0)>التحكّم</div>
 <div class=tab id=t1 onclick=tab(1)>سطح المكتب</div>
 <div class=tab id=t2 onclick=tab(2)>السجلّ</div></div>
 <button class="sm sec" onclick="location='/logout'">خروج</button></div>

<div class=wrap>
 <div id=p0>
  <div class=card><b id=gpu>…</b><div class=k id=der>…</div></div>
  <div class=card id=tasks></div>
  <div class=card><div class=k>أمرٌ حرّ:</div>
   <div class=row><input id=cmd style=flex:1 placeholder="dir  أو  .\run_ensemble_mixed.bat"><button onclick=runcmd()>تنفيذ</button></div>
   <pre id=cmdout></pre></div>
 </div>

 <div id=p1 class=hide>
  <div class=card>
   <div class=row><label class=k><input type=checkbox id=live checked> بثّ حيّ</label>
    <button class=sm sec onclick=shot()>لقطة</button>
    <button class=sm onclick="send({type:'combo',keys:['win']})">Win</button>
    <button class=sm onclick="send({type:'combo',keys:['alt','tab']})">Alt+Tab</button></div>
   <img id=scr src="" alt="الشاشة">
   <div class=row style=margin-top:6px>
    <input id=txt style=flex:1 placeholder="اكتبْ ثمّ أرسلْ إلى الحاسوب">
    <button class=sm onclick=sendtext()>كتابة</button></div>
   <div class="row keys">
    <button class=sm onclick="send({type:'key',key:'enter'})">Enter</button>
    <button class=sm onclick="send({type:'key',key:'esc'})">Esc</button>
    <button class=sm onclick="send({type:'key',key:'backspace'})">⌫</button>
    <button class=sm onclick="send({type:'combo',keys:['ctrl','c']})">Ctrl+C</button>
    <button class=sm onclick="send({type:'combo',keys:['ctrl','v']})">Ctrl+V</button>
    <button class=sm onclick="send({type:'key',key:'up'})">↑</button>
    <button class=sm onclick="send({type:'key',key:'down'})">↓</button></div>
   <div class=k>انقر على الصورة = نقرٌ في مكانه · نقرتان = دبل · ضغطةٌ مطوّلة = زرّ أيمن</div>
  </div>
 </div>

 <div id=p2 class=hide>
  <div class=card><div class=row><select id=sel style=flex:1></select><button class=sec onclick=refresh()>تحديث</button></div>
   <pre id=log>…</pre></div>
 </div>
</div>
<script>
const TASKS=__TASKS__;
function j(p,o){o=o||{};return fetch(p,o)}
function tab(i){for(let n=0;n<3;n++){document.getElementById('p'+n).classList.toggle('hide',n!=i);document.getElementById('t'+n).classList.toggle('on',n==i)}cur=i;if(i==1)shot()}
let cur=0;
function status(){j('/status').then(r=>r.json()).then(d=>{gpu.textContent=d.gpu;der.textContent='آخر DER: '+d.der;
 let h='';for(const k in TASKS){h+=`<div class=row style="justify-content:space-between;padding:4px 0"><span>${TASKS[k]} ${d.running[k]?'<span class=ok>● يعمل</span>':''}</span><span><button class=sm onclick="act('${k}','start')">تشغيل</button><button class="sm stop" onclick="act('${k}','stop')">إيقاف</button></span></div>`}
 tasks.innerHTML=h;
 if(!sel.dataset.i){for(const k in TASKS)sel.innerHTML+=`<option value=${k}>${TASKS[k]}</option>`;sel.dataset.i=1;sel.onchange=refresh}})}
function act(k,a){j('/'+a+'?key='+k,{method:'POST'}).then(()=>{status();if(a=='start')setTimeout(refresh,900)})}
function refresh(){j('/tail?key='+sel.value).then(r=>r.text()).then(t=>log.textContent=t||'(فارغ)')}
function runcmd(){const c=cmd.value;if(!c)return;cmdout.textContent='…';j('/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cmd:c})}).then(r=>r.text()).then(t=>cmdout.textContent=t)}
// سطح المكتب
function shot(){if(cur!=1)return;scr.src='/screen.jpg?x='+Date.now()}
function send(o){j('/input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)})}
function sendtext(){if(txt.value){send({type:'type',text:txt.value});txt.value=''}}
let pressT=0;
scr.addEventListener('pointerdown',e=>{pressT=Date.now()});
scr.addEventListener('pointerup',e=>{const r=scr.getBoundingClientRect();const x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;
 const long=Date.now()-pressT>500;send({type:long?'rclick':'click',x:x,y:y});setTimeout(shot,250)});
let lastTap=0;scr.addEventListener('dblclick',e=>{const r=scr.getBoundingClientRect();send({type:'dblclick',x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height})});
setInterval(()=>{status();if(cur==2)refresh()},5000);
setInterval(()=>{if(cur==1&&live.checked)shot()},1200);
status();
</script></body></html>"""

if __name__ == "__main__":
    host = os.environ.get("PANEL_HOST","0.0.0.0")
    if "_plain_once" in _AUTH:
        print("="*58); print("  أُنشئت بياناتُ الدخول (غيّرْها في panel_auth.json):")
        print("   المستخدم: admin"); print("   كلمة المرور:", _AUTH["_plain_once"]); print("="*58)
    ssl=None
    try:
        import cryptography  # noqa
        ssl="adhoc"; print("HTTPS ذاتيّ مُفعَّل (المتصفّح ينبّه مرّةً — تابعْ بأمان).")
    except Exception:
        print("⚠️ بلا HTTPS (ثبّتْ cryptography لتفعيله): pip install cryptography")
    print(f"افتحْ من الجوّال:  http{'s' if ssl else ''}://<عنوان الحاسوب>:{PORT}/")
    app.run(host=host, port=PORT, threaded=True, ssl_context=ssl)
