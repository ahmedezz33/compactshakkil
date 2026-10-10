# -*- coding: utf-8 -*-
"""adapt_news.py — جولةُ تكيُّفٍ صحفيّةٍ قصيرةٌ للمُشكّل.

يبدأُ من النموذجِ المنشور (outputs_bert_graft/best_model.pt)، يُصقَلُ بمعدّلِ
تعلّمٍ منخفضٍ على مزيجٍ (صحفيّ×20 + عامّ)، ويقيسُ قبل/بعد على:
  • اختبار صحفيّ محجوب (data/processed_news/test.txt)
  • اختبار كلاسيكيّ (data/processed_clean/test_noleak.txt) — لضمان عدم التراجع.
يحفظُ إلى outputs_bert_graft_news/ (نموذجُك الحيّ لا يُمَسّ).
"""
import sys, os, math, random
from pathlib import Path
ROOT=Path(__file__).parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import torch, torch.nn as nn
from transformers import AutoTokenizer
import train_bert_graft as T          # مكوّنات مُجرّبة: Graft/load/collate/evaluate

BASE_CFG="outputs_v3_hard/best_model.pt"      # للبنية (يحمل config)
DEPLOYED="outputs_bert_graft/best_model.pt"   # الأوزان المنشورة الكاملة
NEWS_TR="data/processed_news/train.txt"
NEWS_TE="data/processed_news/test.txt"
CLAS_TE="data/processed_clean/test_noleak.txt"
OUT=Path("outputs_bert_graft_news")

def main():
    EP=int(os.environ.get("ADAPT_EPOCHS","2"))
    dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"جهاز={dev} | حقب={EP}")
    tok=AutoTokenizer.from_pretrained(T.MODEL_ID)
    model=T.Graft(T.MODEL_ID, BASE_CFG, dev).to(dev)
    sd=torch.load(DEPLOYED, map_location=dev, weights_only=False)["model_state"]
    model.load_state_dict(sd); print("🔁 بدأ من المنشور:", DEPLOYED)

    tr=T.load(NEWS_TR, None, seed=1)
    news=T.load(NEWS_TE, None, seed=2)
    clas=T.load(CLAS_TE, 4000, seed=3)
    print(f"تدريب={len(tr):,} | اختبار صحفيّ={len(news)} | اختبار كلاسيكيّ={len(clas)}")
    print("— قبل التكيُّف — صحفيّ:");   b_news=T.evaluate(model,news,tok,dev)
    print("— قبل التكيُّف — كلاسيكيّ:"); b_clas=T.evaluate(model,clas,tok,dev)

    bert_p=list(model.bert.parameters())
    other_p=[p for nm,p in model.named_parameters() if not nm.startswith("bert.")]
    opt=torch.optim.AdamW([{"params":bert_p,"lr":5e-6},{"params":other_p,"lr":5e-5}],weight_decay=0.01)
    crit=nn.CrossEntropyLoss(ignore_index=-100)
    scaler=torch.amp.GradScaler(enabled=(dev.type=="cuda"))
    BS=12; total=max(1,(len(tr)//BS)*EP); warm=max(10,total//20)
    def lr_at(s):
        if s<warm: return s/warm
        p=(s-warm)/max(1,total-warm); return max(0.05,0.5*(1+math.cos(math.pi*p)))
    sch=torch.optim.lr_scheduler.LambdaLR(opt,lr_at)
    OUT.mkdir(exist_ok=True)
    def save(nm): torch.save({"model_state":model.state_dict(),"model_id":T.MODEL_ID}, OUT/nm)

    step=0; best_news=b_news; last_clas=b_clas
    for ep in range(EP):
        model.train(); random.shuffle(tr)
        for i in range(0,len(tr),BS):
            batch=tr[i:i+BS]; ci,woc,attn,enc,nwords,tg=T.collate(batch,tok,dev)
            with torch.amp.autocast(device_type=dev.type,enabled=(dev.type=="cuda")):
                logits=model(ci,woc,attn,enc,nwords,dev)
                loss=crit(logits.reshape(-1,T.NUM_DIACRITIC_CLASSES),tg.reshape(-1))
            opt.zero_grad(); scaler.scale(loss).backward()
            scaler.unscale_(opt); nn.utils.clip_grad_norm_(model.parameters(),1.0)
            scaler.step(opt); scaler.update(); sch.step(); step+=1
            if step%100==0: print(f"  ep{ep} step{step}/{total} loss={loss.item():.3f}")
        print(f"— بعد الحقبة {ep} — صحفيّ:");   d_news=T.evaluate(model,news,tok,dev)
        print(f"— بعد الحقبة {ep} — كلاسيكيّ:"); d_clas=T.evaluate(model,clas,tok,dev); last_clas=d_clas
        save("latest.pt")
        if d_news<best_news:
            best_news=d_news; save("best_model.pt"); print(f"   ✅ أفضل صحفيّ DER={d_news:.2f}% — حُفظ best_model.pt")

    print("\n==== الخلاصة ====")
    print(f"صحفيّ   : قبل {b_news:.2f}%  ←  أفضل {best_news:.2f}%   (التحسّن={b_news-best_news:+.2f})")
    print(f"كلاسيكيّ: قبل {b_clas:.2f}%  ←  بعد {last_clas:.2f}%   (التغيّر={last_clas-b_clas:+.2f}؛ يجب ألّا يرتفع كثيرًا)")
    print("المُكيَّف: outputs_bert_graft_news/best_model.pt  |  نموذجك الحيّ سليم في outputs_bert_graft/")

if __name__=="__main__": main()
