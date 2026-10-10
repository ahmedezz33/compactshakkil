# -*- coding: utf-8 -*-
"""
g2p.py — محوّلٌ صوتيّ (Grapheme→Phoneme) للعربيّة المشكّلة.

يحوّل النصَّ المشكّلَ إلى تسلسلٍ صوتيٍّ صريح (فونيمات IPA + نقحرةٌ لاتينيّةٌ للتعليم)
يحترم: الحركاتِ القصيرةَ والطويلة، التنوينَ، الشدّةَ (تضعيف)، السكونَ، اللامَ
الشمسيّةَ/القمريّة، لفظَ الجلالة (تفخيم)، التاءَ المربوطة، والوقفَ.

فائدتان: (١) عرضُ «كيف تُنطَق» للمتعلّم صراحةً، (٢) تغذيةُ محرّكٍ صوتيّ
(espeak-ng أو SSML‏ phoneme) بنطقٍ لا يعتمد على تخمين المحرّك.

مستقلٌّ عن torch؛ يعتمد pronounce.py في التصحيحات المشتركة.
"""
from pronounce import (_units, fix_jalalah_lines, fix_lam, to_waqf, _tts_jalalah,
    clean_for_tts, phonetic_form, FATHA, KASRA, DAMMA, SUKUN, FATHATAN, KASRATAN, DAMMATAN,
    SHADDA, DAGGER_ALIF, strip_marks, _sk, JALALAH_MAP)

# صوامتُ العربيّة → IPA / نقحرة
CONS={
 "ء":("ʔ","ʾ"),"ب":("b","b"),"ت":("t","t"),"ث":("θ","th"),"ج":("d͡ʒ","j"),
 "ح":("ħ","ḥ"),"خ":("x","kh"),"د":("d","d"),"ذ":("ð","dh"),"ر":("r","r"),
 "ز":("z","z"),"س":("s","s"),"ش":("ʃ","sh"),"ص":("sˤ","ṣ"),"ض":("dˤ","ḍ"),
 "ط":("tˤ","ṭ"),"ظ":("ðˤ","ẓ"),"ع":("ʕ","ʿ"),"غ":("ɣ","gh"),"ف":("f","f"),
 "ق":("q","q"),"ك":("k","k"),"ل":("l","l"),"م":("m","m"),"ن":("n","n"),
 "ه":("h","h"),"و":("w","w"),"ي":("j","y"),"ى":("j","y"),
 "أ":("ʔ","ʾ"),"إ":("ʔ","ʾ"),"آ":("ʔaː","ʾā"),"ئ":("ʔ","ʾ"),"ؤ":("ʔ","ʾ"),
 "ٱ":("ʔ","ʾ"),"ة":("t","t"),
}
SHORT={FATHA:("a","a"),KASRA:("i","i"),DAMMA:("u","u")}
TANWIN={FATHATAN:("an","an"),KASRATAN:("in","in"),DAMMATAN:("un","un")}
LONG_OF={FATHA:("aː","ā"),KASRA:("iː","ī"),DAMMA:("uː","ū")}
SUN=set("تثدذرزسشصضطظلن")

def _emit_cons(sym, doubled):
    ip,la=sym
    return (ip+"ː" if doubled and not ip.endswith("ː") else (ip*2 if doubled else ip),
            (la+la) if doubled else la)

def _hasV(m): return any(c in SHORT or c in TANWIN for c in m)
def _lengthen_a(ipa,lat):
    if ipa and ipa[-1]=="a": ipa[-1]="aː"; lat[-1]="ā"
    else: ipa.append("aː"); lat.append("ā")

def _word_phon(w, ipa, lat):
    """أضِف فونيماتِ كلمةٍ واحدةٍ إلى القائمتين."""
    u=_units(w); n=len(u)
    if not n: return
    lets=[x[0] for x in u]
    # لام «الـ» الساكنة قبل حرفٍ شمسيّ مشدَّد لا تُلفَظ
    silent=set()
    for i,(L,m) in enumerate(u):
        if L=="ل" and not _hasV(m) and SUKUN not in m and i+1<n \
           and lets[i+1] in SUN and SHADDA in u[i+1][1]:
            silent.add(i)
    i=0
    # همزةُ الوصل/ألفُ «الـ» في أوّل الكلمة: بدايةٌ قصيرة «a»
    if lets[0]=="ا" and not _hasV(u[0][1]):
        ipa.append("a"); lat.append("a"); i=1
    while i<n:
        if i in silent: i+=1; continue
        L,m=u[i]
        # ألفُ المدّ والألفُ الخنجريّة والمقصورة: تُطيلُ الفتحةَ قبلها
        if L=="ا" or L==DAGGER_ALIF or L=="ى" or L=="آ":
            _lengthen_a(ipa,lat); i+=1; continue
        if L in CONS:
            doubled=SHADDA in m
            ci,cl=_emit_cons(CONS[L], doubled)
            # واو/ياء ساكنتان بعد حركةٍ مجانِسة ← مدّ
            if L=="و" and not _hasV(m) and ipa and ipa[-1]=="u":
                ipa[-1]="uː"; lat[-1]="ū"; i+=1; continue
            if L in ("ي",) and not _hasV(m) and ipa and ipa[-1]=="i":
                ipa[-1]="iː"; lat[-1]="ī"; i+=1; continue
            # تاءٌ مربوطةٌ بلا حركة (وقف) ← تُلفَظ هاءً
            if L=="ة" and not _hasV(m):
                ipa.append("h"); lat.append("h"); i+=1; continue
            ipa.append(ci); lat.append(cl)
            for c in m:
                if c in TANWIN: ipa.append(TANWIN[c][0]); lat.append(TANWIN[c][1]); break
                if c in SHORT:  ipa.append(SHORT[c][0]);  lat.append(SHORT[c][1]);  break
            i+=1; continue
        i+=1

def _vowel_in(m): return any(c in SHORT or c in TANWIN for c in m)
# إطالةُ حركةٍ قصيرةٍ في نهاية المقطع (idx 0=IPA, 1=نقحرة)
_LONG={"a":("aː","ā"),"i":("iː","ī"),"u":("uː","ū")}
_LONGSET=set("āīūaːiːuː")|{"ː"}
def _lengthen(seq, idx):
    if seq and seq[-1] and seq[-1][-1]=="ː": return          # طويلٌ سلفًا
    if seq and seq[-1] and seq[-1][-1] in "āīū": return
    if seq and seq[-1] and seq[-1][-1] in "aiu":
        v=seq[-1][-1]; seq[-1]=seq[-1][:-1]+_LONG[v][idx]
    else:
        seq.append(_LONG["a"][idx])

def _romanize_units(units, idx):
    """يُنقحِر قائمةَ وحداتٍ (حرف, علامات) قد حُلّت قواعدُها (لامُ الشمسيّة وألفُ
    الوصل مُسقَطتان سلفًا). idx: 0=IPA، 1=نقحرة لاتينيّة."""
    seq=[]
    for L,m in units:
        if L in ("ا","آ","ى",DAGGER_ALIF):
            # همزةُ الوصل: ألفٌ عاريةٌ بلا حركةٍ بعد ساكنٍ (كلامِ «الـ») لا فتحةَ قبلها
            # تُمَدّ ← تُنطَقُ كسرةَ الوصل «i»، لا مدًّا. مثال: الْاحْتِيَاجَات ← al-iḥtiyājāt
            if L=="ا" and not _vowel_in(m) and seq and seq[-1] and seq[-1][-1] not in "aāː":
                seq.append("i"); continue
            _lengthen(seq, idx); continue
        if L=="و" and not _vowel_in(m) and seq and seq[-1][-1:]=="u":
            seq[-1]=seq[-1][:-1]+_LONG["u"][idx]; continue
        if L=="ي" and not _vowel_in(m) and seq and seq[-1][-1:]=="i":
            seq[-1]=seq[-1][:-1]+_LONG["i"][idx]; continue
        if L not in CONS: continue
        cl=CONS[L][idx]; v=""
        for c in m:
            if c in TANWIN: v=TANWIN[c][idx]; break
            if c in SHORT:  v=SHORT[c][idx];  break
        seq.append(cl+v)
    return "".join(seq)


# ── تفخيم/ترقيق لفظ الجلالة في مخرجات IPA/النقحرة ────────────────────────
def _tafkhim_line(ipa, lat):
    """لامُ لفظ الجلالة: مُطبَقةٌ (ɫ / ḷ) بعد فتح/ضمّ، رقيقةٌ (l) بعد كسر."""
    it=ipa.split(" "); lt=lat.split(" ")
    for k,tok in enumerate(it):
        if "laːh" not in tok: continue                 # ليست لفظَ الجلالة
        tarqiq = tok.startswith(("li","bi"))           # لله/بالله ← كسر ← ترقيق
        if not tarqiq and k>0:
            pv=it[k-1].rstrip("ː")
            tarqiq = pv[-1:] in ("i","")               # ما قبلها كسر ← ترقيق
        if not tarqiq:                                  # تفخيم
            it[k]=tok.replace("l","ɫ")
            if k<len(lt): lt[k]=lt[k].replace("l","ḷ")
    return " ".join(it), " ".join(lt)

def phonemize(text, mode="waqf"):
    """أرجِع (IPA, نقحرة) مشتقَّين من نفس مُقسِّم الوحدات المستعمَل في التركيب الصوتيّ،
    فتُطابق النقحرةُ ما يُنطَق فعلًا (لامُ الشمسيّة محذوفة، ألفُ الوصل، الجلالة…)."""
    from qaida_voice import _word_units
    phon=phonetic_form(text, mode)
    ipa_lines=[]; lat_lines=[]
    for line in phon.split("\n"):
        started=False; wi=[]; wl=[]
        for w in line.split(" "):
            if not w: continue
            units,started=_word_units(w, started)
            wi.append(_romanize_units(units,0)); wl.append(_romanize_units(units,1))
        _ipa=" ".join(x for x in wi if x); _lat=" ".join(x for x in wl if x)
        _ipa,_lat=_tafkhim_line(_ipa,_lat)          # تفخيم/ترقيق لفظ الجلالة
        ipa_lines.append(_ipa); lat_lines.append(_lat)
    return "\n".join(ipa_lines), "\n".join(lat_lines)

def transcription(text, mode="waqf"):
    """نقحرةٌ لاتينيّةٌ للعرض التعليميّ."""
    return phonemize(text, mode)[1]

if __name__=="__main__":
    for t in ["بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
              "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
              "إِنَّ اللَّهَ غَفُورٌ رَحِيمٌ",
              "ذَهَبَ الطَّالِبُ إِلَى الْمَدْرَسَةِ"]:
        ip,la=phonemize(t,"waqf")
        print("النصّ :",t); print("IPA  :",ip); print("نقحرة:",la); print()


# ═══════════════════════════════════════════════════════════
# تحليلٌ حرفًا حرفًا للتعليم: تشكيلُ كلّ حرفٍ ونطقُه وملاحظةٌ تجويديّة
# ═══════════════════════════════════════════════════════════
LETTER_NAME={
 "ا":"ألف","أ":"همزة","إ":"همزة","آ":"ألف ممدودة","ء":"همزة","ٱ":"همزة وصل",
 "ب":"باء","ت":"تاء","ة":"تاء مربوطة","ث":"ثاء","ج":"جيم","ح":"حاء","خ":"خاء",
 "د":"دال","ذ":"ذال","ر":"راء","ز":"زاي","س":"سين","ش":"شين","ص":"صاد","ض":"ضاد",
 "ط":"طاء","ظ":"ظاء","ع":"عين","غ":"غين","ف":"فاء","ق":"قاف","ك":"كاف","ل":"لام",
 "م":"ميم","ن":"نون","ه":"هاء","و":"واو","ي":"ياء","ى":"ألف مقصورة",
 "ؤ":"همزة على واو","ئ":"همزة على ياء",
}
QALQALA=set("قطبجد")
def _vowel_name(m):
    if SHADDA in m and FATHA in m: return "شدّة + فتحة"
    if SHADDA in m and KASRA in m: return "شدّة + كسرة"
    if SHADDA in m and DAMMA in m: return "شدّة + ضمّة"
    if FATHATAN in m: return "تنوين فتح"
    if KASRATAN in m: return "تنوين كسر"
    if DAMMATAN in m: return "تنوين ضمّ"
    if SHADDA in m: return "شدّة"
    if FATHA in m: return "فتحة"
    if KASRA in m: return "كسرة"
    if DAMMA in m: return "ضمّة"
    if SUKUN in m: return "سكون"
    if DAGGER_ALIF in m: return "ألف خنجريّة (مدّ)"
    return "—"

def _unit_translit(L,m,prev_ip):
    """نقحرةٌ تقريبيّةٌ لوحدةِ حرفٍ (حرف + حركته)."""
    doubled=SHADDA in m
    if L in ("ا","آ","ى",DAGGER_ALIF): return "ā"
    if L in CONS:
        _,la=_emit_cons(CONS[L],doubled)
        v=""
        for c in m:
            if c in TANWIN: v=TANWIN[c][1]; break
            if c in SHORT: v=SHORT[c][1]; break
        return la+v
    return ""

def letters_breakdown(text):
    """أرجِع صفوفًا: [(الحرف المشكّل, اسم الحرف, اسم الحركة, النطق, ملاحظة, بدايةُ كلمة)]."""
    text=fix_jalalah_lines(text); text=fix_lam(text)
    rows=[]
    for line in text.split("\n"):
        for w in line.split(" "):
            if not w: continue
            u=_units(w)
            for i,(L,m) in enumerate(u):
                disp=L+m
                lname=LETTER_NAME.get(L,L)
                vname=_vowel_name(m)
                tr=_unit_translit(L,m,"")
                # ملاحظاتٌ تجويديّة مبسّطة
                notes=[]
                if SHADDA in m and L in ("ن","م"): notes.append("غنّة")
                if SHADDA in m and L not in ("ن","م"): notes.append("تشديد")
                if (SUKUN in m or (not _hasV(m) and SUKUN not in m and i>0)) and L in QALQALA:
                    notes.append("قلقلة")
                if L in ("ا","ى","آ",DAGGER_ALIF): notes.append("مدّ")
                if L=="و" and SUKUN in m: notes.append("مدّ/لين")
                if L=="ي" and SUKUN in m: notes.append("مدّ/لين")
                note=" ، ".join(notes) if notes else ""
                rows.append((disp,lname,vname,tr,note,i==0))
    return rows

def spell_text(text):
    """نصٌّ للنطق المقطّع: كلُّ حرفٍ بحركته مفصولٌ بفاصلةٍ ليُلفَظ مستقلًّا."""
    text=fix_jalalah_lines(text); text=fix_lam(text)
    parts=[]
    for line in text.split("\n"):
        for w in line.split(" "):
            if not w: continue
            for L,m in _units(w):
                parts.append(L+m)
    return " ، ".join(parts)
