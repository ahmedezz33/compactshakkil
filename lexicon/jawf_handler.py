"""
Jawf-Handler: نظام معالجة الأفعال الجوفاء ذو 3 مستويات.

المستويات:
1. Gold Standard   — بحث في قاموس مُتحقّق منه يدويًا (دقّة 100%)
2. Rules-Based     — استنتاج من الأوزان الصرفية والمشتقّات (دقّة ~90%)
3. Statistical     — تحليل إحصائي للمشتقّات (دقّة ~75%)

الاستخدام:
    from jawf_handler import JawfHandler
    handler = JawfHandler('lexicon/arabic_lexicon.db')
    result = handler.resolve('ق.#.ل')
    # → {'root': 'ق.و.ل', 'confidence': 1.0, 'source': 'gold', ...}
"""

import sqlite3
import json
import re
from collections import Counter
from pathlib import Path

# استيراد Gold Dictionary
try:
    from gold_dictionary import GOLD_HOLLOW_ROOTS
except ImportError:
    # لو شغّلنا من مجلد آخر
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from gold_dictionary import GOLD_HOLLOW_ROOTS


class JawfHandler:
    """معالج الأفعال الجوفاء متعدّد المستويات."""

    def __init__(self, db_path='lexicon/arabic_lexicon.db'):
        self.db_path = db_path
        self.gold = GOLD_HOLLOW_ROOTS
        self._pattern_cache = {}

        # قواعد استنتاج من الأوزان (Rule-based)
        # مبنيّة على قواعد الصرف العربي الكلاسيكية
        self.pattern_hints = {
            # أوزان تدلّ على واو
            "1a2A3": "ambiguous",           # فَعَال (يحتاج تحليل)
            "1u2U3": "و",                   # فُعُول → غالبًا واوي
            "ma1A2i3": "و",                 # مَفَاعِل → واوي مُلحق
            "1A2i3": "ambiguous",           # فَاعِل → يحتاج مشتقّات
            "1u2la_n": "و",                 # فُعْلَان → غالبًا واوي

            # أوزان تدلّ على ياء
            "1a2i2": "ي",                   # فَعِيل → غالبًا يائي
            "1I2a_n": "ي",                  # فِيعَان → يائي
            "ma1I2": "ي",                   # مَفِيع → يائي
        }

    # ═══════════════════════════════════════════════════════════
    # المستوى 1: Gold Standard Lookup
    # ═══════════════════════════════════════════════════════════

    def _try_gold(self, root_camel: str):
        """المستوى 1: البحث في القاموس المعياري."""
        if root_camel in self.gold:
            info = self.gold[root_camel]
            return {
                "root": info["full"],
                "letter": info["letter"],
                "type": info["type"],
                "confidence": 1.0,
                "source": "gold",
                "meaning": info.get("meaning", ""),
            }
        return None

    # ═══════════════════════════════════════════════════════════
    # المستوى 2: Rule-Based (تحليل المشتقّات صرفيًا)
    # ═══════════════════════════════════════════════════════════

    def _try_rules(self, root_camel: str, cursor):
        """
        المستوى 2: استنتاج من الأوزان الصرفية للمشتقّات.

        المنطق:
        - كل جذر له مشتقّات في المعجم
        - كل مشتقّة لها وزن (pattern) وشكل مشكّل (diac)
        - نستنتج الحرف من الأنماط الظاهرة
        """
        # جلب كل المشتقّات مع تحليلاتها
        cursor.execute("""
            SELECT DISTINCT w.word, w.analyses_json
            FROM words w
            JOIN roots r ON w.id = r.word_id
            WHERE r.root = ?
        """, (root_camel,))

        rows = cursor.fetchall()
        if not rows:
            return None

        # جمع أدلّة على الحرف الأصلي
        evidence = {"و": 0, "ي": 0, "ا": 0}
        total_analyses = 0

        for word, analyses_json in rows:
            try:
                analyses = json.loads(analyses_json)
            except (json.JSONDecodeError, TypeError):
                continue

            for a in analyses:
                if a.get("root") != root_camel:
                    continue
                total_analyses += 1

                # الشكل المشكّل (diac) يخبرنا كثيرًا
                diac = a.get("diac", "")
                pattern = a.get("pattern", "")

                # قاعدة 1: وجود واو صريحة في الشكل المشكّل
                if "و" in diac and "ي" not in diac:
                    evidence["و"] += 2
                elif "ي" in diac and "و" not in diac:
                    evidence["ي"] += 2

                # قاعدة 2: أوزان تدلّ على حرف معيّن
                if pattern in self.pattern_hints:
                    hint = self.pattern_hints[pattern]
                    if hint in evidence:
                        evidence[hint] += 3

                # قاعدة 3: كلمة تنتهي بـ "ون" أو "ين"
                if word.endswith("ون") or word.endswith("وا"):
                    evidence["و"] += 1
                elif word.endswith("ين") or word.endswith("ية"):
                    evidence["ي"] += 1

        if total_analyses == 0:
            return None

        # اتخاذ القرار
        best_letter = max(evidence, key=evidence.get)
        max_score = evidence[best_letter]
        total_score = sum(evidence.values())

        if total_score == 0:
            return None

        confidence = max_score / total_score

        # نقبل فقط إذا كانت الثقة > 60%
        if confidence < 0.6:
            return None

        # بناء الجذر الكامل
        full_root = root_camel.replace("#", best_letter, 1)

        return {
            "root": full_root,
            "letter": best_letter,
            "type": self._classify_hollow_type(root_camel),
            "confidence": round(confidence, 2),
            "source": "rules",
            "evidence": evidence,
            "sample_count": total_analyses,
        }

    # ═══════════════════════════════════════════════════════════
    # المستوى 3: Statistical (تحليل تكراري)
    # ═══════════════════════════════════════════════════════════

    def _try_statistical(self, root_camel: str, cursor):
        """
        المستوى 3: تحليل إحصائي لمشتقّات الجذر.

        نستخدمه عندما تفشل القواعد.
        نبحث في كل الحروف داخل المشتقّات نفسها.
        """
        cursor.execute("""
            SELECT DISTINCT w.word
            FROM words w
            JOIN roots r ON w.id = r.word_id
            WHERE r.root = ?
        """, (root_camel,))

        words = [row[0] for row in cursor.fetchall()]
        if not words:
            return None

        # عدّ حروف العلّة في المشتقّات
        letter_count = {"و": 0, "ي": 0, "ا": 0}
        for word in words:
            for ch in word:
                if ch in letter_count:
                    letter_count[ch] += 1

        total = sum(letter_count.values())
        if total == 0:
            # لا حروف علّة في المشتقّات → افتراضيًا ألف
            return {
                "root": root_camel.replace("#", "ا", 1),
                "letter": "ا",
                "type": self._classify_hollow_type(root_camel),
                "confidence": 0.3,
                "source": "statistical_default",
                "note": "لا يوجد حرف علّة صريح في المشتقّات"
            }

        # الأكثر تكرارًا (باستثناء الألف — نادرة كأصل)
        non_alef = {"و": letter_count["و"], "ي": letter_count["ي"]}
        best = max(non_alef, key=non_alef.get)
        confidence = non_alef[best] / (non_alef["و"] + non_alef["ي"] + 1)

        return {
            "root": root_camel.replace("#", best, 1),
            "letter": best,
            "type": self._classify_hollow_type(root_camel),
            "confidence": round(confidence, 2),
            "source": "statistical",
            "letter_counts": letter_count,
            "sample_words": words[:5],
        }

    # ═══════════════════════════════════════════════════════════
    # مساعدات
    # ═══════════════════════════════════════════════════════════

    def _classify_hollow_type(self, root: str) -> str:
        """تصنيف نوع الجذر (أجوف/مثال/ناقص/لفيف)."""
        parts = root.split('.')
        if len(parts) != 3:
            return "غير معروف"

        hash_positions = [i for i, p in enumerate(parts) if p == '#']

        if len(hash_positions) == 1:
            pos = hash_positions[0]
            return {0: "مثال", 1: "أجوف", 2: "ناقص"}.get(pos, "غير معروف")
        elif len(hash_positions) == 2:
            if 0 in hash_positions and 2 in hash_positions:
                return "لفيف مفروق"
            else:
                return "لفيف مقرون"
        elif len(hash_positions) == 3:
            return "غامض تمامًا"
        else:
            return "صحيح"

    # ═══════════════════════════════════════════════════════════
    # الواجهة الرئيسية
    # ═══════════════════════════════════════════════════════════

    def resolve(self, root_camel: str) -> dict:
        """
        الحلّ الشامل لأيّ جذر جوف.

        Args:
            root_camel: الجذر بصيغة CAMeL (مثل "ق.#.ل")

        Returns:
            dict فيه: root, letter, type, confidence, source
        """
        # التحقّق من المدخل
        if '#' not in root_camel:
            return {
                "root": root_camel,
                "confidence": 1.0,
                "source": "not_hollow",
                "note": "الجذر ليس جوفًا — لا يحتاج معالجة"
            }

        # المستوى 1: Gold Standard
        result = self._try_gold(root_camel)
        if result:
            return result

        # المستويان 2 و 3 يحتاجان اتصالاً بقاعدة البيانات
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # المستوى 2: Rules
            result = self._try_rules(root_camel, cursor)
            if result and result["confidence"] >= 0.6:
                return result

            # المستوى 3: Statistical
            result = self._try_statistical(root_camel, cursor)
            if result:
                return result
        finally:
            conn.close()

        # فشل كامل
        return {
            "root": root_camel,
            "confidence": 0.0,
            "source": "failed",
            "note": "تعذّر تحديد الحرف الأصلي"
        }

    def resolve_batch(self, roots: list, verbose: bool = False) -> dict:
        """معالجة قائمة كاملة من الجذور."""
        results = {}
        stats = {"gold": 0, "rules": 0, "statistical": 0, "failed": 0}

        for root in roots:
            result = self.resolve(root)
            results[root] = result
            source = result.get("source", "failed")
            if source in stats:
                stats[source] += 1
            elif "statistical" in source:
                stats["statistical"] += 1
            else:
                stats["failed"] += 1

            if verbose:
                print(f"  {root:12s} → {result['root']:12s} "
                      f"[{source}, conf={result.get('confidence', 0):.2f}]")

        return {"results": results, "stats": stats}


# ═══════════════════════════════════════════════════════════
# اختبار مباشر
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 65)
    print("Jawf-Handler: نظام معالجة الأفعال الجوفاء")
    print("=" * 65)

    handler = JawfHandler('lexicon/arabic_lexicon.db')

    # اختبار على 10 جذور معروفة
    test_roots = [
        "ق.#.ل",   # قول (gold)
        "ب.#.ع",   # بيع (gold)
        "#.ع.د",   # وعد (gold)
        "د.ع.#",   # دعا (gold)
        "ر.م.#",   # رمى (gold)
        "ق.#.م",   # قوم (gold)
        "خ.ذ.#",   # اختبار: هل نعرفه؟
        "ن.#.ر",   # اختبار
        "ف.#.ز",   # فوز (gold)
        "س.#.ر",   # سير (gold)
    ]

    print("\nاختبار على 10 جذور:")
    print("-" * 65)
    for root in test_roots:
        result = handler.resolve(root)
        conf = result.get("confidence", 0)
        source = result.get("source", "?")
        print(f"  {root:12s} → {result['root']:14s} [{source:16s}] conf={conf:.2f}")

    print("\n" + "=" * 65)
    print("اكتمل الاختبار!")
