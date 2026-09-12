#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 Netscape Cookie 文件并保存为 JSON"""

import json
import os
import sys

cookie_file = r"C:\Users\Lenovo\Downloads\a73edff3-acd8-48ee-8fb8-2794327dac34.txt"
cookies = {}

with open(cookie_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            name = parts[5]
            value = parts[6]
            cookies[name] = value

print(f"解析到 {len(cookies)} 个 Cookie:")
for name in sorted(cookies.keys()):
    val = cookies[name]
    display = val[:50] + "..." if len(val) > 50 else val
    print(f"  {name} = {display}")

if "__zp_stoken__" in cookies:
    token_len = len(cookies["__zp_stoken__"])
    print(f"\n✅ 找到 __zp_stoken__（长度: {token_len}）")
else:
    print("\n❌ 未找到 __zp_stoken__")
    sys.exit(1)

save_path = r"C:\Users\Lenovo\.openclaw\workspace\skills\resume-builder\data\boss_cookies.json"
os.makedirs(os.path.dirname(save_path), exist_ok=True)
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(cookies, f, ensure_ascii=False, indent=2)
print(f"\n✅ Cookie 已保存: {save_path}")
