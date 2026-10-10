# مشروع التشكيل التلقائي للنصوص العربية
# CompactShakkil: Arabic Automatic Diacritization

**المرحلة الأولى (Phase 1):** نموذج تشكيل عربي خفيف عالي الأداء
**المدة المستهدفة:** 6-8 أسابيع
**الهدف النهائي:** DER < 3.5% بأقلّ من 100M معامل

---

## 📁 هيكل المشروع

```
tashkil_project/
├── README.md              # هذا الملف
├── requirements.txt       # التبعيات
├── configs/
│   └── base_config.yaml   # إعدادات النموذج والتدريب
├── data/
│   ├── __init__.py
│   ├── download.py        # تحميل Tashkeela من HuggingFace
│   ├── preprocess.py      # فصل الحروف عن الحركات
│   ├── vocab.py           # مفردات الحروف والحركات
│   └── dataset.py         # PyTorch Dataset
├── models/
│   ├── __init__.py
│   └── transformer.py     # النموذج الأساسي (Character-level Transformer)
├── scripts/
│   ├── train.py           # تدريب النموذج
│   ├── evaluate.py        # حساب DER, WER
│   └── inference.py       # التشكيل التلقائي لنصّ جديد
└── notebooks/
    └── 01_data_exploration.ipynb  # استكشاف البيانات
```

---

## 🚀 خطوات البدء السريع

### 1. إنشاء بيئة بايثون معزولة

```bash
cd tashkil_project
python -m venv venv
source venv/bin/activate       # على Linux/Mac
# venv\Scripts\activate         # على Windows
pip install -r requirements.txt
```

### 2. التحقق من دعم CUDA على جهازك

```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

يجب أن تشاهد اسم بطاقة RTX 3090/4090.

### 3. تحميل بيانات Tashkeela

```bash
python data/download.py
```

سيتمّ التحميل إلى `data/raw/tashkeela/` (حوالي 700MB).

### 4. المعالجة الأولية

```bash
python data/preprocess.py
```

يُنتج ملفات مُعالَجة في `data/processed/` (train/val/test splits).

### 5. تدريب النموذج الأساسي

```bash
python scripts/train.py --config configs/base_config.yaml
```

الوقت المتوقّع على RTX 4090: **8-12 ساعة** للنموذج الأساسي (10 epochs).

### 6. التقييم

```bash
python scripts/evaluate.py --checkpoint outputs/best_model.pt
```

يخرج تقرير DER و WER على مجموعة الاختبار.

### 7. التشكيل التفاعلي

```bash
python scripts/inference.py --text "الحمد لله رب العالمين"
# → الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ
```

---

## 📊 الجدول الزمني للمرحلة الأولى

| الأسبوع | المهمّة | المخرج |
|---|---|---|
| 1 | إعداد البيئة، تحميل البيانات، استكشاف | Notebook استكشافي، إحصاءات Tashkeela |
| 2 | معالجة أولية، بناء dataset، vocab | ملفات مُعالجة، Dataset class |
| 3-4 | تدريب Baseline (Transformer صغير) | نموذج أساسي، DER ~ 5-6% |
| 5-6 | تحسينات (BERT contextual embeddings، Curriculum learning) | نموذج محسّن، DER ~ 3-4% |
| 7 | تقييم شامل ومقارنة مع Shakkelha و Farasa | جداول نتائج |
| 8 | مسودّة workshop paper | ورقة 4 صفحات |

---

## 📚 المراجع الأساسية

- **Zerrouki & Balla (2017).** Tashkeela: Novel corpus of Arabic vocalized texts. *Data in Brief*, 11, 147-151.
- **Fadel et al. (2019).** Arabic Text Diacritization Using Deep Neural Networks. *ICCAIS 2019*. [Shakkelha]
- **Abbad & Xiong (2020).** Multi-components System for Automatic Arabic Diacritization. *ECIR 2020*.
- **Abandah et al. (2015).** Automatic diacritization of Arabic text using recurrent neural networks. *IJDAR*.
- **Darwish et al. (2017).** Arabic Diacritization: Stats, Rules, and Hacks. *WANLP 2017*. [Farasa]

---

## ⚙️ متطلبات النظام

- Python 3.10 أو أحدث
- GPU: NVIDIA بذاكرة 12GB+ (RTX 3090/4090 مثالي)
- مساحة قرص: 5GB (بيانات + نماذج + logs)
- ذاكرة RAM: 16GB+

---

## 🧭 المرحلة الثانية (لاحقًا)

بعد إتمام هذه المرحلة بنجاح، ننتقل إلى:

**Phase 2: إضافة رأس تقييم الجودة (Quality Head)**
- Multi-task learning: تشكيل + جودة
- بيانات إضافية من QALB
- ورقة كاملة لمؤتمر ACL/EMNLP

---

## 📞 الدعم والتطوير

هذا مشروع بحثي شخصي — للأسئلة أو المساهمة، راجع ملف `CONTRIBUTING.md` (سيُضاف لاحقًا).
