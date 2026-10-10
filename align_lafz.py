# -*- coding: utf-8 -*-
"""
align_lafz.py — استخراجُ لفظ الجلالة «الله» بتوقيتٍ دقيقٍ من تلاوة المنشاوي
عبر المحاذاة القسريّة (forced alignment) بنموذج wav2vec2 عربيّ.
يُنتج مقطعًا نظيفًا لكلِّ حالةٍ إعرابيّة في recordings/lafz/.
يعمل على الويندوز داخل venv (torch/torchaudio/transformers مثبَّتة).
"""
import os, sys, io, unicodedata
import numpy as np
import torch, torchaudio
import torchaudio.functional as AF
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
ROOT=os.path.dirname(os.path.abspath(__file__))
WAVS=os.path.join(ROOT,"train_data","minshawy","wavs")
OUT =os.path.join(ROOT,"recordings","lafz"); os.makedirs(OUT,exist_ok=True)
MODEL=os.environ.get("ALIGN_MODEL","jonatasgrosman/wav2vec2-large-xlsr-53-arabic")

# (code, transcript, word_index_of_lafz, case_tag)
TASKS=[
 ("112002","الله الصمد",0,"nom"),
 ("002015","الله يستهزئ بهم ويمدهم في طغيانهم",0,"nom2"),
 ("001001","بسم الله الرحمن الرحيم",1,"gen"),
 ("104006","نار الله الموقدة",1,"gen2"),
 ("026108","فاتقوا الله واطيعون",1,"acc"),
 ("026126","فاتقوا الله واطيعون",1,"acc2"),
]

def norm(s):
    s="".join(c for c in s if not unicodedata.combining(c))
    return s.translate(str.maketrans({"ٱ":"ا","أ":"ا","إ":"ا","آ":"ا","ى":"ي"}))

print("torch",torch.__version__,"| torchaudio",torchaudio.__version__)
print("loading model:",MODEL,"(one-time download ~1.2GB)"); sys.stdout.flush()
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

def _ensure_safetensors(repo):
    """ينزّلُ النموذجَ ويحوّلُ pytorch_model.bin ← model.safetensors إن لزم،
    ليتجاوزَ قيدَ transformers (torch<2.6 لا يحمّل pickle)."""
    from huggingface_hub import snapshot_download
    local=snapshot_download(repo)
    import os as _os
    binp=_os.path.join(local,"pytorch_model.bin")
    stp =_os.path.join(local,"model.safetensors")
    if _os.path.exists(stp) or not _os.path.exists(binp):
        return local
    print("  converting .bin -> .safetensors (one-time) ..."); sys.stdout.flush()
    from safetensors.torch import save_file
    sd=torch.load(binp, map_location="cpu", weights_only=True)
    sd={k:v.detach().cpu().contiguous().clone() for k,v in sd.items()
        if hasattr(v,"detach")}
    save_file(sd, stp, metadata={"format":"pt"})
    print("  converted."); sys.stdout.flush()
    return local

_local=_ensure_safetensors(MODEL)
proc=Wav2Vec2Processor.from_pretrained(_local)
model=Wav2Vec2ForCTC.from_pretrained(_local).eval()
vocab=proc.tokenizer.get_vocab()
delim=proc.tokenizer.word_delimiter_token
blank=proc.tokenizer.pad_token_id if proc.tokenizer.pad_token_id is not None else 0
SR=16000

def fade(x,ms,sr):
    n=int(sr*ms/1000); 
    if n>0 and len(x)>2*n:
        x[:n]*=np.linspace(0,1,n); x[-n:]*=np.linspace(1,0,n)
    return x

def extract(code,transcript,widx,tag):
    wav_path=os.path.join(WAVS,code+".wav")
    if not os.path.exists(wav_path): print("  MISS wav",wav_path); return
    wav,sr0=torchaudio.load(wav_path)            # [C,N] native sr (24k)
    wav=wav.mean(0,keepdim=True)                 # mono
    w16=torchaudio.functional.resample(wav,sr0,SR) if sr0!=SR else wav
    with torch.inference_mode():
        logits=model(w16).logits[0]              # [T,C]
    emission=torch.log_softmax(logits,dim=-1).unsqueeze(0)  # [1,T,C]
    words=norm(transcript).split()
    targets=[]; wid=[]
    for i,wd in enumerate(words):
        if i>0 and delim in vocab: targets.append(vocab[delim]); wid.append(-1)
        for c in wd:
            if c in vocab: targets.append(vocab[c]); wid.append(i)
            else: print("   char not in vocab:",repr(c))
    tgt=torch.tensor([targets],dtype=torch.int32)
    aligned,scores=AF.forced_align(emission,tgt,blank=blank)
    spans=AF.merge_tokens(aligned[0],scores[0])   # one span per target token, in order
    if len(spans)!=len(targets):
        print(f"   WARN spans={len(spans)} targets={len(targets)} (proceeding by min len)")
    sel=[sp for sp,wi in zip(spans,wid) if wi==widx]
    if not sel: print("   no spans for word idx",widx); return
    T=emission.shape[1]; ratio=wav.shape[1]/T      # samples per frame (native sr)
    s0=int(sel[0].start*ratio); s1=int(sel[-1].end*ratio)
    padL=int(sr0*0.02); padR=int(sr0*0.03)
    s0=max(0,s0-padL); s1=min(wav.shape[1],s1+padR)
    clip=wav[0,s0:s1].numpy().astype(np.float32)
    clip=fade(clip,12,sr0)
    pk=np.max(np.abs(clip)) or 1.0
    clip=clip/pk*0.89
    outp=os.path.join(OUT,tag+".wav")
    sf.write(outp,clip,sr0,subtype="PCM_16")
    print(f"  OK {tag:5} {code} dur={len(clip)/sr0:.2f}s -> {outp}")

if __name__=="__main__":
    for t in TASKS:
        try: extract(*t)
        except Exception as e:
            import traceback; print("  ERR",t[0],t[3],e); traceback.print_exc()
    print("DONE. clips in",OUT)
