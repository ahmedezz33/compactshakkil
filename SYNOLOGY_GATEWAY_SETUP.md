# بوّابةُ السينولوجي لـCompactShakkil API

السينولوجي = الواجهةُ العامّةُ الثابتة (DuckDNS + HTTPS + Reverse Proxy).
الـPC = محرّكُ الـGPU خلفَها، داخليٌّ فقط. النطاق: shakkil.duckdns.org

> استبدلْ: `PC_IP` = عنوانُ الـPC الداخليّ · `NAS_IP` = عنوانُ السينولوجي الداخليّ · `DUCK_TOKEN` = رمزُ DuckDNS.

---

## أ) تحضيرٌ (الراوتر + الـPC) — قبلَ السينولوجي

1. **الراوتر — حجزُ عنوانين ثابتين (DHCP Reservation):**
   - الـPC (MAC C4-75-AB-F6-04-55) → عنوانٌ ثابتٌ `PC_IP` (كي لا يتغيّرَ ويكسرَ التمرير).
   - السينولوجي → عنوانٌ ثابتٌ `NAS_IP`.

2. **الراوتر — تحويلُ المنافذِ العامّةِ إلى السينولوجي (لا الـPC):**
   - أعِدْ توجيهَ 80 و443 الخارجيّين → `NAS_IP` (كانا يشيران للـPC).
   - هذا يجعلُ الـPC **محجوبًا عن الإنترنت**.

3. **الـPC:**
   - تأكّدْ أنّ الـAPI يستمعُ على `0.0.0.0:8000` (هو كذلك).
   - **أوقِفْ Caddy على الـPC** (لم يعُدْ لازمًا — HTTPS ينتقلُ للسينولوجي). أبقِ خدمةَ `CompactShakkilAPI`.
   - جدارُ حمايةِ ويندوز: اسمحْ بالوارد على 8000 من الشبكةِ المحليّةِ فقط (الأفضل: من `NAS_IP` حصرًا).

---

## ب) السينولوجي (DSM)

4. **DuckDNS (تحديثُ العنوان):**
   - Control Panel → External Access → DDNS → Add.
   - إن لم يكنْ DuckDNS جاهزًا: Customize Provider، واجعلِ Query URL:
     `https://www.duckdns.org/update?domains=shakkil&token=DUCK_TOKEN&ip=__MYIP__`
   - Hostname: `shakkil.duckdns.org`.

5. **شهادةُ HTTPS (Let's Encrypt):**
   - Control Panel → Security → Certificate → Add → "Get a certificate from Let's Encrypt".
   - Domain name: `shakkil.duckdns.org` (يتطلّبُ وصولَ 80/443 للسينولوجي — تمّ في خطوة ٢).
   - بعدَ الإصدار: Settings → اربطِ `shakkil.duckdns.org` بهذه الشهادة.

6. **Reverse Proxy:**
   - Control Panel → Login Portal → Advanced → Reverse Proxy → Create.
   - **Source:** Protocol HTTPS · Hostname `shakkil.duckdns.org` · Port 443.
   - **Destination:** Protocol HTTP · Hostname `PC_IP` · Port 8000.
   - **Custom Header → Create → WebSocket** (احتياطًا).
   - تأكّدْ أنّ **X-Forwarded-For** يُمرَّر (السينولوجي يُضيفُه افتراضيًّا) — الـAPI يعتمدُه لحدِّ المعدّلِ وحصّةِ التجربةِ لكلِّ IP. بدونَه يتشاركُ كلُّ الزوّارِ عنوانَ السينولوجي.

7. **اختبار:**
   - من خارجِ الشبكة: `https://shakkil.duckdns.org/health` ← يجبُ أن يُعيدَ حالةَ الـPC.
   - ثمّ `/v1/diacritize` بمفتاحٍ.

---

## ج) تحصينٌ بعدَ النجاح
- احذفْ تمريرَ 80/443 القديمَ إلى الـPC (إن بقيَ).
- قصُرْ 8000 على `NAS_IP` في جدارِ الـPC.
- الشهادةُ تتجدّدُ تلقائيًّا في DSM (لا تدخّل).
- نسخٌ احتياطيّة: `backup.bat` دوريًّا (Task Scheduler على ويندوز).

## ملاحظات
- التشكيلُ يتطلّبُ الـPC مُشغَّلًا؛ إن نامَ الـPC يعودُ الـAPI بخطأ 502/504 من البوّابة (طبيعيّ).
- لا تغييرَ في كودِ المشروع — إعدادُ بنيةٍ فقط.
