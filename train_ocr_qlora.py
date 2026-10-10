# -*- coding: utf-8 -*-
"""train_ocr_qlora.py — صقل QLoRA لنموذج Qari (Qwen2-VL-2B) على بيانات OCR صناعيّة.

4-bit + LoRA على طبقات اللغة (برج الرؤية مُجمَّد) ليسع كرت 8GB.
يتعلّم خرائط (صورة ← نصّ مشكَّل). يحفظ المحوِّلات في outputs_ocr_lora/.

  تدريب:  python train_ocr_qlora.py train --manifest data/ocr_quran/manifest.tsv --root data/ocr_quran
  تقييم:  python train_ocr_qlora.py eval  --manifest data/ocr_quran_test/manifest.tsv --root data/ocr_quran_test
المتغيّرات: OCR_EPOCHS(1) OCR_LIMIT(0=الكل) OCR_MAXSIDE(768) OCR_LORA(outputs_ocr_lora)
"""
import os, sys, argparse, random, math
os.environ.setdefault("OCR_MODEL","NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct")
import torch
from PIL import Image

BASE=os.environ.get("OCR_MODEL")
PROMPT="انسخ النص العربي في الصورة كما هو بكل الحركات، سطرًا بسطر."
LORA_DIR=os.environ.get("OCR_LORA","outputs_ocr_lora")
MAXSIDE=int(os.environ.get("OCR_MAXSIDE","768"))

def load_manifest(mf, root, limit=0):
    rows=[]
    for ln in open(mf,encoding="utf-8"):
        if "\t" not in ln: continue
        img,txt=ln.rstrip("\n").split("\t",1)
        rows.append((os.path.join(root,img), txt))
    random.shuffle(rows)
    return rows[:limit] if limit else rows

def open_img(path):
    im=Image.open(path).convert("RGB")
    w,h=im.size; m=max(w,h)
    if m>MAXSIDE:
        r=MAXSIDE/m; im=im.resize((max(8,int(w*r)),max(8,int(h*r))))
    return im

def build(proc, img, gold=None):
    from qwen_vl_utils import process_vision_info
    um=[{"role":"user","content":[{"type":"image","image":img},{"type":"text","text":PROMPT}]}]
    if gold is None:
        txt=proc.apply_chat_template(um,tokenize=False,add_generation_prompt=True)
        ii,_=process_vision_info(um)
        return proc(text=[txt],images=ii,return_tensors="pt")
    fm=um+[{"role":"assistant","content":[{"type":"text","text":gold}]}]
    ptxt=proc.apply_chat_template(um,tokenize=False,add_generation_prompt=True)
    ftxt=proc.apply_chat_template(fm,tokenize=False)
    ii,_=process_vision_info(fm)
    full=proc(text=[ftxt],images=ii,return_tensors="pt")
    plen=proc(text=[ptxt],images=ii,return_tensors="pt").input_ids.shape[1]
    labels=full.input_ids.clone(); labels[:,:plen]=-100
    labels[full.attention_mask==0]=-100
    full["labels"]=labels
    return full

def load_model(four_bit=True, train=True):
    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration, BitsAndBytesConfig
    proc=AutoProcessor.from_pretrained(BASE)
    kw=dict(device_map={"":0}, torch_dtype=torch.float16)
    if four_bit:
        kw["quantization_config"]=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16)
    model=Qwen2VLForConditionalGeneration.from_pretrained(BASE,**kw)
    return proc, model

def do_train(a):
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, PeftModel
    proc,model=load_model(four_bit=True, train=True)
    model=prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.enable_input_require_grads()
    _STATE=os.path.join(LORA_DIR,"train_state.json")
    _FRESH=os.environ.get("OCR_FRESH","0")=="1"
    resume = (not _FRESH) and os.path.exists(_STATE) and os.path.exists(os.path.join(LORA_DIR,"adapter_config.json"))
    if resume:
        model=PeftModel.from_pretrained(model, LORA_DIR, is_trainable=True)   # متابعة
        print("\U0001F501 متابعة من المحوّلات المحفوظة:", LORA_DIR)
    else:
        lc=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
            target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
            task_type="CAUSAL_LM")
        model=get_peft_model(model, lc)                                       # جديد
    model.print_trainable_parameters()
    rows=load_manifest(a.manifest, a.root, int(os.environ.get("OCR_LIMIT","0")))
    EP=int(os.environ.get("OCR_EPOCHS","1")); ACC=16
    import json as _json
    _OPT=os.path.join(LORA_DIR,"optimizer.pt")
    SAVE_EVERY=int(os.environ.get("OCR_SAVE_EVERY","50")); SEED=int(os.environ.get("OCR_SEED","1234"))
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
    N=len(rows); done_global=0
    if resume and os.path.exists(_STATE):
        try:
            st=_json.load(open(_STATE,encoding="utf-8")); done_global=int(st.get("global_sample",0))
            if os.path.exists(_OPT): opt.load_state_dict(torch.load(_OPT,map_location="cpu"))
            print(f"\U0001F501 استئناف من العيّنة {done_global}/{EP*N}")
        except Exception as e: print("تعذّر الاستئناف الدقيق:",e)
    def _save(gs):
        os.makedirs(LORA_DIR,exist_ok=True)
        model.save_pretrained(LORA_DIR); proc.save_pretrained(LORA_DIR)
        try: torch.save(opt.state_dict(), _OPT)
        except Exception: pass
        _json.dump({"global_sample":int(gs),"epochs":EP,"rows":N}, open(_STATE,"w",encoding="utf-8"))
    model.train(); step=0; dev=model.device; gidx=max(0,done_global-1)
    try:
        for ep in range(EP):
            rr=list(rows); random.Random(SEED+ep).shuffle(rr); opt.zero_grad()
            for i,(path,gold) in enumerate(rr):
                gidx=ep*N+i
                if gidx < done_global: continue          # تخطّي ما أُنجز (استئناف)
                try:
                    enc=build(proc, open_img(path), gold).to(dev)
                    out=model(**enc); loss=out.loss/ACC
                    loss.backward()
                except Exception as e:
                    if i<3: print("تخطّي عيّنة:",e)
                    continue
                if (i+1)%ACC==0:
                    torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1.0)
                    opt.step(); opt.zero_grad(); step+=1
                    if step%20==0: print(f"ep{ep} step{step} loss={out.loss.item():.3f}")
                    if step%SAVE_EVERY==0:
                        _save(gidx+1); print(f"\U0001F4BE حُفظ عند {gidx+1}/{EP*N}")
            _save((ep+1)*N); print(f"— انتهت الحقبة {ep} (حُفظ) —")
    except KeyboardInterrupt:
        _save(gidx+1); print(f"\n\u23F8 أُوقِف — حُفظ عند {gidx+1}. أعِد تشغيل البات للاستكمال.")
        return
    print(f"\u2705 اكتمل التدريب وحُفظت المحوِّلات: {LORA_DIR}")

def _cer(ref,hyp):
    # مسافة ليفنشتاين على الأحرف
    r,h=list(ref),list(hyp); n,m=len(r),len(h)
    if n==0: return 0.0 if m==0 else 1.0
    dp=list(range(m+1))
    for i in range(1,n+1):
        prev=dp[0]; dp[0]=i
        for j in range(1,m+1):
            cur=dp[j]
            dp[j]=min(dp[j]+1, dp[j-1]+1, prev+(r[i-1]!=h[j-1])); prev=cur
    return dp[m]/n

def do_eval(a):
    use_lora=(os.environ.get("OCR_NOLORA","0")!="1") and os.path.exists(LORA_DIR) and os.path.exists(os.path.join(LORA_DIR,"adapter_config.json"))
    proc,model=load_model(four_bit=True, train=False)
    tag="Qari الأساس"
    if use_lora:
        from peft import PeftModel
        model=PeftModel.from_pretrained(model, LORA_DIR); tag=f"Qari+LoRA ({LORA_DIR})"
    model.eval()
    rows=load_manifest(a.manifest, a.root, int(os.environ.get("OCR_LIMIT","0")))
    _eos=[]
    try:
        if proc.tokenizer.eos_token_id is not None: _eos.append(proc.tokenizer.eos_token_id)
        _im=proc.tokenizer.convert_tokens_to_ids("<|im_end|>")
        if isinstance(_im,int) and _im>=0 and _im not in _eos: _eos.append(_im)
    except Exception: pass
    _pad=getattr(proc.tokenizer,"pad_token_id",None) or (_eos[0] if _eos else None)
    tot=0.0; exact=0; n=0; dev=model.device
    import unicodedata
    for path,gold in rows:
        try:
            enc=build(proc, open_img(path)).to(dev)
            with torch.inference_mode():
                g=model.generate(**enc, max_new_tokens=int(os.environ.get("OCR_EVAL_MAXTOK","1024")), do_sample=False,
                                 repetition_penalty=1.2, no_repeat_ngram_size=4,
                                 eos_token_id=(_eos or None), pad_token_id=_pad)
            out=proc.batch_decode([g[0][enc.input_ids.shape[1]:]],skip_special_tokens=True)[0].strip()
        except Exception as e:
            continue
        c=_cer(gold.strip(), out); tot+=c; exact+=int(out==gold.strip()); n+=1
    print(f"[{tag}] عيّنات={n}  CER={100*tot/max(1,n):.2f}%  مطابقة تامّة={100*exact/max(1,n):.1f}%")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("mode",choices=["train","eval"])
    ap.add_argument("--manifest",required=True); ap.add_argument("--root",required=True)
    a=ap.parse_args()
    (do_train if a.mode=="train" else do_eval)(a)

if __name__=="__main__": main()
