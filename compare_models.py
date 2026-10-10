"""
compare_models.py — مقارنة بصرية بين V3-unified و Syn variant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

الاستخدام:
    (venv) PS F:\Arabic\tashkil_project> python compare_models.py

يعرض تشكيل كل نموذج لعدد من الجمل الاختبارية جنباً إلى جنب.
"""
import sys
from pathlib import Path

# ── تعديل المسارات حسب مشروعك ────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── استيراد النماذج ──────────────────────────────────────────
# (عدّل هذه السطور حسب أسماء ملفاتك الفعلية)
try:
    from tashkil.model import load_model  # عدّل حسب مشروعك
except ImportError as e:
    print(f"❌ خطأ في الاستيراد: {e}")
    print("💡 عدّل import statements حسب هيكل مشروعك")
    sys.exit(1)

# ── مسارات النماذج (عدّلها حسب checkpoints عندك) ─────────────
V3_CHECKPOINT = "checkpoints/v3_unified/best.pt"
SYN_CHECKPOINT = "checkpoints/syn/best.pt"

# ── جمل الاختبار ─────────────────────────────────────────────
TEST_SENTENCES = [
    "ذهب الطالب إلى المدرسة",
    "كتب المهندس التقرير في المكتب",
    "استقبل المدير الضيوف بحفاوة",
    "قرأت الطالبة الكتاب في المكتبة",
    "يعمل الأب في الشركة منذ سنوات",
    "أعجبني حديث العلماء عن الفلك",
]

def compare(v3_model, syn_model, sentences):
    """طبع جدول مقارنة"""
    print("\n" + "═" * 90)
    print(f"{'الجملة':^40} | {'V3-unified':^25} | {'Syn':^25}")
    print("═" * 90)
    
    for s in sentences:
        pred_v3 = v3_model.predict(s)
        pred_syn = syn_model.predict(s)
        # طبع كل واحدة
        print(f"\n📝 الأصل    : {s}")
        print(f"✅ V3       : {pred_v3}")
        print(f"⚠  Syn      : {pred_syn}")
        print("─" * 90)

def main():
    print("🔄 تحميل النموذجين...")
    v3 = load_model(V3_CHECKPOINT)
    syn = load_model(SYN_CHECKPOINT)
    print(f"✓ V3 loaded from  : {V3_CHECKPOINT}")
    print(f"✓ Syn loaded from : {SYN_CHECKPOINT}")
    
    compare(v3, syn, TEST_SENTENCES)
    
    print("\n" + "═" * 90)
    print("💡 لاحظ الفرق في: البنية الصرفية vs حركة الآخِر")
    print("═" * 90)

if __name__ == "__main__":
    main()
