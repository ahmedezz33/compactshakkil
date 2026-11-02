# -*- coding: utf-8 -*-
"""فحصٌ سريعٌ للاسترجاع القرآنيّ على عيّنةٍ (~٢٥٠ آية) — يؤكّدُ الاسترجاعَ وحفظَ الخنجريّة.
يُدخِلُ كلَّ آيةٍ بالرسمِ العاديِّ (بلا حركاتٍ ولا خنجريّة) عبرَ المسارِ الإنتاجيّ،
ثمّ يقيسُ: نسبةَ الاسترجاع، التطابقَ التامَّ مع الرسمِ المصحفيّ، وفقدَ الخنجريّة."""
import sys, os
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE); sys.path.insert(0, os.path.join(BASE, "scripts"))
import diac_pipeline as dp

SMALL_ALIF = "ٰ"; TATWEEL = "ـ"
HARAKAT = set("ًٌٍَُِّْ") | {SMALL_ALIF, TATWEEL}
def bare(s):   return "".join(c for c in s if c not in HARAKAT)
def ndag(s):   return s.count(SMALL_ALIF)

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "data", "quran_retr_sample.txt")
gold = [l.rstrip("\n") for l in open(path, encoding="utf-8") if l.strip()]
N = len(gold)
retr = exact = dg_gold = dg_out = dg_lost = 0
fails = []
nonr = []
for g in gold:
    out, tag = dp.route(bare(g), True)
    if "استرداد" in tag: retr += 1   # "استرداد"
    if out == g: exact += 1
    dg, do = ndag(g), ndag(out)
    dg_gold += dg; dg_out += do
    if dg > do: dg_lost += (dg - do)
    if out != g: fails.append((g, out, tag))
    if "\u0627\u0633\u062a\u0631\u062f\u0627\u062f" not in tag: nonr.append((g, out, tag))

print("="*60)
print(f"N = {N}  (منها خنجريّة في {sum(1 for g in gold if ndag(g))} آية)")
print(f"استرجاع (route=استرداد):      {retr}/{N} = {100*retr/N:.1f}%")
print(f"تطابق تامّ مع الرسم المصحفيّ: {exact}/{N} = {100*exact/N:.1f}%")
print(f"الخنجريّة:  ذهبيّ={dg_gold} · ناتج={dg_out} · مفقود={dg_lost}")
print("="*60)
if fails:
    print(f"--- عيّناتُ عدمِ التطابق ({min(8,len(fails))} من {len(fails)}) ---")
    for g, o, t in fails[:8]:
        print("IN  :", bare(g)); print("GOLD:", g); print("OUT :", o, "  [", t, "]"); print()
else:
    print("لا عيّناتِ اختلاف — تطابقٌ تامّ ١٠٠٪.")

print("="*60)
print(f"الأسطرُ التي لم تُحسَبْ استرجاعًا: {len(nonr)}")
for g,o,t in nonr:
    print("IN  :", bare(g)); print("GOLD:", g); print("OUT :", o, "  [وسم:", t, "]")
    print("  مطابقٌ تامّ؟", o==g, "· خنجريّة ذهبيّ=%d ناتج=%d"%(ndag(g),ndag(o))); print()
