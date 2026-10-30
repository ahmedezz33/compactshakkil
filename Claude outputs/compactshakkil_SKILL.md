---
name: "compactshakkil"
description: "استخدمها عند العمل على مشروع CompactShakkil للتشكيل العربيّ + OCR + تعليم النطق + فيديوهات النطق في F:\\Arabic\\tashkil_project (diacritizer، ocr_engine، g2p، app_teach، مولّد الفيديو، الباتات، التدريب على GPU، والنشر على GitHub)."
---

# CompactShakkil — التشكيل + OCR + تعليم النطق + فيديوهات

تطبيقُ Gradio عربيٌّ (app_teach.py) يشكّلُ النصَّ، ويستخرجُه من الصور/PDF (OCR)، ويعلّمُ النطقَ، ويولّدُ فيديوهاتٍ تعليميّة. المسار: `F:\Arabic\tashkil_project`. جهازُ المالك: Windows + RTX 3070 (8GB). منشورٌ: `github.com/ahmedezz33/compactshakkil` (MIT).

## البيئات — أهمُّ ما يُخطئُ كلَّ مرّة

- **ويندوز (المالك)**: GPU + torch + `venv` (لا `.venv`) → `call venv\Scripts\activate.bat`. transformers 4.51.3. هنا فقط يُدرَّبُ/يُقيَّم. **PIL بلا libraqm** (مهمٌّ للفيديو).
- **جسرُ الجهاز (Linux VM)** عبر `device_bash`: `PIL + raqm` (يصلحُ للتصيير) لكن **لا torch ولا GPU**. عدّلْ في المكان. ينقطعُ كثيرًا؛ اجعلِ السكربتاتِ قابلةً للاستئناف؛ مهلةُ الأمرِ ≤180s؛ لا يحذفُ (rm يفشل) → `mv` إلى `_archive/` أو `_to_delete/`. **لا تستعمل `glob('**/...', recursive=True)` أو `du`/`find` على كلِّ المشروع** (venv/data = آلافُ الملفّات → تجاوزُ المهلة)؛ استعملْ glob سطحيًّا.
- **الحاوية السحابيّة**: **لا torch، لا GPU، PyPI محجوب (403)** → لا تُشغِّل نماذجَ فيها. لمعاينةِ صورة: `device_stage_files` ثم `Read`.

## ⭐ النسخُ المكرّرة وsys.path (درسٌ حاسمٌ تسبّبَ بخطأ صامت)

- `bert_graft_infer.py` كان موجودًا في **الجذرِ (قديمٌ، بلا تقطيع، حدُّ pos-encoding = 512)** وفي **`scripts/` (المعتمدة، مُقطّعةٌ `_apply_chunked` MAXLEN=180)**. الآن **الجذرُ مُزامَنٌ = scripts/** (نسخةٌ واحدةٌ فعليًّا)؛ القديمةُ في `_archive/duplicates_OLD/`.
- **القاعدة**: diac_pipeline يضعُ `scripts/` أوّلاً **فقط إن لم يكن المساران في sys.path أصلاً** (`if _p not in sys.path`). فأيُّ سكربت تقييم/دياغنوست يُضيفُ الجذرَ قبلَ scripts يحصلُ على النسخةِ القديمة → تنهارُ الأسطرُ الطويلة (>512) أو تعود عارية. **في أيّ سكربت: `sys.path.insert(0, BASE); sys.path.insert(0, BASE/'scripts')` (scripts بأولويّة index 0) قبلَ `import diac_pipeline`.**
- التطبيقُ/الـAPI يستوردان diac_pipeline بلا إضافةِ مساراتٍ مسبقة → يأخذان scripts/ الصحيحة (الإنتاجُ سليم).

## الفرز والأرشيف

`_archive/` = **توثيقٌ فقط، لا يُستعمَلُ مستقبلاً**: `duplicates_OLD/` (bert_graft_infer الجذر القديم)، `baks/`، `logs/` (*_output.txt)، `snapshots/` (compactshakkil_v*)، `old_experiments/` (41 سكربتَ تجربةٍ غيرَ مستورَد: jawf_*, resolve_hollow_v3..v10, compare_jalalah2..6, test_*, reverence_test*...). مانيفست: `_archive/README.md`. قبلَ أرشفةِ أيّ سكربت: تأكّدْ أنّ لا باتَ يُشغّلُه ولا ملفَ حيًّا يستوردُه (محلّلُ إغلاقِ الاستيراد وحدَه لا يكفي: يُصنّفُ أدواتٍ تُشغَّلُ يدويًّا كـrender_* خطأً كميتة). **لم تُمَسّ**: كلُّ `outputs_*`، وكلُّ الأدوات (render_*, api_*, build_*, batch_ocr, eval_*...).

## الباتات (gotchas)

- **CRLF** + `pause`. **لا تُعدّلْ باتًا جزئيًّا** (يَخلِطُ نهاياتِ السطر → `'ta]' is not recognized`) → **أعِدْ كتابتَه كاملاً** بـ`"\r\n".join(...)` + `newline=""`.
- داخلَ `( ... )`: `&` غيرَ مهرَّب. **تجنّبِ العربيَّ في `echo`** → لاتينيّةً. PowerShell: `.\name.bat`.
- GPU لا يعمل من الجسر/السحابة؛ التدريبُ/الدفعُ إلى github من ويندوز.

## المنهجيّة (القواعدُ الثابتة)

- **قِسْ كلَّ تغييرٍ قبلَ تفعيله** على نفسِ المجموعةِ الذهبيّةِ وبنفسِ المسطرةِ للطرفين. لا رقمَ = لا اعتماد.
- **تحقّقْ من تناقضِ المقاييس**: إن اختلفَ مقياسان على نفسِ المخرجِ بشدّة (مثل CATT تراث 1.5% مقابل 17%) → خللُ محاذاة/بيانات، لا تحكمْ حتّى تُشخّصَ (انظر أمثلةَ dbg وعدّادَ «متخطّى»).
- التعلّمُ من ذهبيٍّ يتفوّقُ على الترقيع. رُفِضَ بالقياس: voice rule، lexicon guard، fuzzy، restore_quran_strong. احفظْ `.bak_<وسم>` (ثمّ أرشفةً إلى `_archive/baks/`).

## المشكّل (diacritizer) ومقياسُ DER

- BERT-graft، المنشور `outputs_bert_graft/best_model.pt`. مُكيَّفٌ صحفيًّا (adapt_news.py). `GraftInfer` يُقطّعُ (MAXLEN=180؛ pos-encoding 512/مقطع) فيتعاملُ مع >1000. وضعان: `diacritize(text, True)`=جزئيّ (يترك غير المؤكَّد عاريًا؛ = الإنتاج)، `(text, False)`=كامل.
- **مقياسُ DER (مقياسُك — الحَكَم)**: `scripts/eval_graft.py` يقارنُ **فئةَ الحركةِ لكلِّ حرف** عبر `data/vocab_v2.split_letters_and_diacritics` → DER كلّي + بنية + حركةُ الآخِر (إعراب). (~1.7% تراث، ~4–5% أخبار). `der_compare.py` مستقلٌّ خامٌّ أصرم.
- **لمعايرةٍ صحيحةٍ (eval_tashkeel_compare.py)**: (1) `scripts/` أوّلاً في sys.path (وإلا تنهارُ الطويلة)، (2) تشكيلٌ كاملٌ `respect=False`، (3) **طبِّعْ** (أبقِ الحروفَ+الحركاتِ+الفراغَ فقط، أزِلِ الترقيمَ/الأرقام) الذهبيَّ والمخرجَين قبلَ DER. (`diac_pipeline._AYA_SEP` يعامل الأرقامَ كفواصل → أسطرُ الأخبارِ ذاتُ الأرقام تكسرُ المحاذاة بلا تطبيع).

## OCR

- `ocr_engine.py` / `NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct`. التوليد: `repetition_penalty=1.3`+`no_repeat_ngram_size=3`+إيقافٌ عند `<|im_end|>`؛ سقف `OCR_MAX_TOKENS=8192`.
- **مقابضُ مقاسةٌ مُطبَّقة** (61 صفحة، `eval_ocr_app.py`): **معالجة OFF** −7.1 (61.97→54.88)، **MAX_SIDE 1600** −1.48 (→53.39)، برومبت AR أفضل. في الباتات الأربعة: `set OCR_PREPROCESS=0` + `set OCR_MAX_SIDE=1600`. أداة: `run_eval_ocr_res61.bat`.
- مجموعةُ الاختبارِ **مُصيَّرةٌ صناعيًّا** (لا مشكلةَ ترتيب) → الـ~53% خطأُ تمييزٍ → التدريبُ رافعة.
- **توسيعُ البيانات (على الجسر، raqm)**: `render_more.py` (idempotent) → `data/ocr_classical_pages_more` (~5642). `build_unified_tsv.py` يضمّه → `ocr_unified_train.tsv` ~11004 (3:1). `build_balanced_tsv.py` (QREP/CCAP) → `ocr_unified_balanced.tsv` ~13682 (1.55:1).

## تدريبُ OCR (QLoRA) — الدرسُ الحاسم

`train_ocr_qlora.py` (4-bit nf4، LoRA r=16، برجٌ بصريٌ مجمّد، batch-1 accum-16). OCR_LORA/OCR_EPOCHS/OCR_MAXSIDE(896)/OCR_NOLORA/OCR_FRESH/OCR_EVAL_MAXTOK(ارفعها 2048). استئناف: `train_state.json`+`optimizer.pt` داخلَ مجلّدِ المحوّل.

- **من الصفرِ كارثةٌ على القرآن**: outputs_ocr_bal_v2 استرسلَ على القرآن (CER آلاف٪) لأنّه لم يتعلّمِ الإيقاف.
- **الحلّ: دافئٌ من v1**: `run_train_ocr_warm.bat` → `outputs_ocr_bal_v3` (نسخُ v1 + train_state=0)، حِقبةٌ واحدة. يُقيّمُ أساس/v1/v3 على القرآن والتراث. **اعتمدْ v3 فقط إن قلَّ CER على الاثنين مقابلَ v1.** المنشورُ (outputs_ocr_unified/_v1) لا يُمَسّ.

## مقارنةُ نماذجَ أخرى

- **CATT** (`catt-tashkeel` PyPI، **ONNX/CPU**، EO أسرع/ED أدقّ، **حدُّ 1024 محرف** → قسّمْ ~800، **يحذفُ الترقيمَ والأرقامَ ويُشوّهُ الأعلامَ الأجنبيّة**). أداة: `eval_tashkeel_compare.py`+`der_compare.py` (يُخرجُ Word → `reports/`؛ `CUDA_VISIBLE_DEVICES=` للتعايش). الترجيح: نموذجُك أقوى على التراث والإعراب ويُبقي الأرقام/الأعلام؛ CATT أنعمُ على الأخبار القصيرة لكنّه يُسقِطُ محتوى.
- **OCR — Qwen2.5-VL-3B مقابل Qari**: `eval_ocr_qwen25.py`. بدائل: AIN(7B)، absir-arabic-ocr-1.6B، PP-OCRv5-ar، Surya/Kraken.
- **التوليد التخميني**: لا ينطبق على BERT (غير توليديّ)؛ للـOCR سرعةٌ لا دقّة.

## مولّدُ فيديوهاتِ النطق

`make_lesson_video.py` (`generate()`) + `app_lesson.py` (Gradio :7862) + `run_app_lesson.bat`.
- **PIL بلا libraqm على ويندوز** → `arabic_reshaper` (`ArabicReshaper({'delete_harakat': False})`) + `python-bidi` (`get_display`)، ارسمْ **بلا** `direction=`/`language=`.
- **صوتٌ متّصلٌ للجملةِ كاملةً** (تشكيل→`edge_prepare`→`tts_engine.synthesize`)، **لا كلمةً كلمة** (مقطّع). التزامنُ عبر **WordBoundary من edge-tts**. ffmpeg: `venv/Scripts/ffmpeg.exe`. الأصوات: `tts_engine.list_voices()`.

## G2P والأرقام والنشر

- **g2p.py**: `phonemize`→`_romanize_units` (IPA، نقحرة). إصلاحات: همزةُ الوصل «i»؛ لامُ «الـ» لا آخرَ الكلمة. **الأرقام**: `num2ar.py`.
- **GitHub** `ahmedezz33/compactshakkil` (MIT): الأسرارُ محجوبة (admin_token.txt, panel_secret.txt, panel_auth.json, semantic_config.json, api_keys.json)؛ النماذج/البيانات عبر Releases/HF. تنظيفُ سرّ: `git rm --cached` + `commit --amend` + `push --force` (من ويندوز).

## مسارات/نماذج نشطة

نماذج: `outputs_bert_graft/best_model.pt`، `outputs_ocr_unified/`+`_v1/` (منشور — لا يُمَسّ)، `outputs_ocr_bal_v2/` (كارثة)، `outputs_ocr_bal_v3/` (دافئ). باتات: run_app_teach[_quran]، run_api[_service] (OCR_PREPROCESS=0+MAX_SIDE=1600)، run_train_ocr_warm، run_eval_ocr_res61، run_eval_tashkeel_compare، run_eval_ocr_qwen25، run_app_lesson. بيانات: data/fonts (14)، data/news_gold_clean.txt + data/ocr_classical_test_src.txt (ذهبيُّ تشكيل)، data/ocr_*_pages[_test]/، data/ocr_unified_balanced.tsv. سجلّ: ACCURACY_ROADMAP.md.

## عند التعديل

عدّلْ على الجسرِ في المكان، احفظْ .bak، تحقّقْ ast، ثمّ **قِسْ**. الباتاتُ تُكتَبُ كاملةً. الملفاتُ تُعدَّلُ مباشرةً في مشروعِه (لا SendUserFile للمصدر). للصور: stage→Read. وأيُّ سكربت يستوردُ diac_pipeline/bert_graft_infer: `scripts/` أوّلاً في sys.path.
