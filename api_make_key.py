# -*- coding: utf-8 -*-
"""ينشئ مفتاح API لعميل ويضيفه إلى api_keys.json.
الاستعمال:  python api_make_key.py "اسم العميل" [حدّ_الوحدات]
مثال:       python api_make_key.py "متجر النور" 100000
(بلا حدّ = غير محدود)"""
import sys, json, secrets
from pathlib import Path
F = Path("api_keys.json")
def main():
    if len(sys.argv) < 2:
        print('الاستعمال: python api_make_key.py "اسم العميل" [حدّ_الوحدات]'); return
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    keys = json.loads(F.read_text(encoding="utf-8")) if F.exists() else {}
    key = "cs_" + secrets.token_urlsafe(24)
    keys[key] = {"name": name, "active": True, "used_units": 0, "limit_units": limit}
    F.write_text(json.dumps(keys, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ مفتاح جديد لـ", name)
    print("   KEY =", key)
    print("   الحدّ =", limit if limit else "غير محدود")
if __name__ == "__main__": main()
