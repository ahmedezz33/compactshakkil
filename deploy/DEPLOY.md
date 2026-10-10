# نشر CompactShakkil API للبيع (ويندوز + HTTPS)

الهدف: خادمٌ عامٌّ آمنٌ `https://api.YOURNAME.duckdns.org` يستدعيه العملاء.

## 1) نطاق مجّاني (DuckDNS)
- أنشئ نطاقًا على https://www.duckdns.org (مثلًا `yourname.duckdns.org`).
- وجّهه إلى IP الإنترنت العامّ لجهازك (DuckDNS يحدّثه تلقائيًّا ببرنامجه).

## 2) فتح المنافذ
- في الراوتر: Port Forward للمنفذين 80 و443 → IP جهازك المحلّيّ.
- في جدار حماية ويندوز: اسمح لـ Caddy بالمنفذين 80/443 (وارِد).
- **لا تفتح** المنفذ 8000 للإنترنت — يبقى محلّيًّا خلف Caddy فقط.

## 3) تشغيل الـAPI كخدمة دائمة (NSSM)
- نزّل NSSM من https://nssm.cc ، ثم (كمسؤول):
```
nssm install CompactShakkilAPI "F:\Arabic\tashkil_project\run_api.bat"
nssm set CompactShakkilAPI AppDirectory "F:\Arabic\tashkil_project"
nssm set CompactShakkilAPI Start SERVICE_AUTO_START
nssm start CompactShakkilAPI
```
(بديلٌ أبسط: Task Scheduler → مهمّة تشتغل عند الإقلاع تُنفّذ run_api.bat.)

## 4) تشغيل Caddy (HTTPS تلقائيّ)
- نزّل caddy.exe من https://caddyserver.com/download ضعه بجوار deploy/Caddyfile.
- عدّل النطاق في Caddyfile، ثم:
```
caddy run --config deploy\Caddyfile
```
- Caddy يُصدِر شهادة Let's Encrypt تلقائيًّا ويعكس الطلبات إلى 127.0.0.1:8000.
- اجعله خدمةً أيضًا (nssm install CaddyProxy ...).

## 5) اختبار
```
curl https://api.YOURNAME.duckdns.org/health
curl -X POST https://api.YOURNAME.duckdns.org/v1/pronounce ^
  -H "X-API-Key: cs_xxx" -H "Content-Type: application/json" ^
  -d "{\"text\":\"قَهْوَةُ الصَّبَاحِ\"}"
```

## أمان
- HTTPS فقط (Caddy يعيد توجيه HTTP→HTTPS تلقائيًّا).
- `api_keys.json` و`api_usage.log` لا يُرفعان ولا يُكشفان.
- راقِب `access.log` و`api_usage.log`؛ عطّل أيّ مفتاح بوضع `"active": false`.
- خذ نسخةً احتياطيّةً من `api_keys.json` دوريًّا.
