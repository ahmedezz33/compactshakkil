# -*- coding: utf-8 -*-
"""num2ar.py — تفقيطُ الأعداد إلى كلماتٍ عربيّةٍ منطوقةٍ مُشكَّلة (للنطق TTS).
مستقلٌّ بلا اعتمادات. يغطّي الأعدادَ الصحيحةَ حتى المليارات، والتواريخَ
(15-4-1448 → مجموعاتٌ مفصولةٌ بوقفة)، والكسورَ العشريّةَ والنِّسَب المئويّة.
الكلماتُ مُشكَّلةٌ كي تُنطَقَ صحيحةً ولا تخرجَ عاريةً في النقحرة/edge.
"""
import re

_ONES=["","وَاحِد","اثْنَان","ثَلَاثَة","أَرْبَعَة","خَمْسَة","سِتَّة","سَبْعَة","ثَمَانِيَة","تِسْعَة",
       "عَشَرَة","أَحَدَ عَشَرَ","اثْنَا عَشَرَ","ثَلَاثَةَ عَشَرَ","أَرْبَعَةَ عَشَرَ","خَمْسَةَ عَشَرَ","سِتَّةَ عَشَرَ",
       "سَبْعَةَ عَشَرَ","ثَمَانِيَةَ عَشَرَ","تِسْعَةَ عَشَرَ"]
_TENS=["","","عِشْرُونَ","ثَلَاثُونَ","أَرْبَعُونَ","خَمْسُونَ","سِتُّونَ","سَبْعُونَ","ثَمَانُونَ","تِسْعُونَ"]
_HUND=["","مِائَة","مِئَتَان","ثَلَاثُمِائَة","أَرْبَعُمِائَة","خَمْسُمِائَة","سِتُّمِائَة","سَبْعُمِائَة","ثَمَانِمِائَة","تِسْعُمِائَة"]
_SCALES=[(10**9,("مِلْيَار","مِلْيَارَان","مِلْيَارَات")),
         (10**6,("مِلْيُون","مِلْيُونَان","مَلَايِين")),
         (10**3,("أَلْف","أَلْفَان","آلَاف"))]

def _below_thousand(n):
    parts=[]
    h=n//100; r=n%100
    if h: parts.append(_HUND[h])
    if r:
        if r<20: parts.append(_ONES[r])
        else:
            o=r%10; t=r//10
            parts.append((_ONES[o]+" وَ"+_TENS[t]) if o else _TENS[t])
    return " وَ".join(parts)

def tafqit(n):
    n=int(n)
    if n==0: return "صِفْر"
    neg=n<0; n=abs(n); chunks=[]
    for value,(sing,dual,plur) in _SCALES:
        if n>=value:
            c=n//value; n%=value
            if c==1: chunks.append(sing)
            elif c==2: chunks.append(dual)
            elif 3<=c<=10: chunks.append(_below_thousand(c)+" "+plur)
            else: chunks.append(_below_thousand(c)+" "+sing)
    if n>0: chunks.append(_below_thousand(n))
    res=" وَ".join(chunks)
    return ("سَالِب "+res) if neg else res

_AR2EN=str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹","01234567890123456789")
_NUMRUN=re.compile(r"\d+")

def verbalize(text):
    """يحوّلُ كلَّ عددٍ في النصّ إلى كلماتٍ عربيّةٍ منطوقةٍ مُشكَّلة."""
    if not text: return text
    t=text.translate(_AR2EN)
    # أزل فاصلةَ الآلاف أوّلًا: 10,000 ← 10000 ، 1,000,000 ← 1000000
    while re.search(r"\d,\d{3}(?!\d)", t): t=re.sub(r"(\d),(\d{3})(?!\d)", r"\1\2", t)
    while re.search(r"\d٬\d{3}(?!\d)", t): t=re.sub(r"(\d)٬(\d{3})(?!\d)", r"\1\2", t)  # ٬
    t=re.sub(r"(?<=\d)\s*%",  " بِالْمِائَة ", t)      # ٪
    t=re.sub(r"(?<=\d)\.(?=\d)", " فَاصِلَة ", t)       # كسر عشريّ
    t=re.sub(r"(?<=\d)\s*[-/]\s*(?=\d)", " ، ", t)     # فواصلُ التاريخ (- /) ← وقفة
    t=_NUMRUN.sub(lambda m: " "+tafqit(m.group())+" ", t)
    return re.sub(r"[ \t]{2,}"," ",t).strip()
