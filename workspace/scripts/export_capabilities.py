#!/usr/bin/env python3
"""
export_capabilities.py — 导出 strong_verified 能力
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import safe_read_json
from utils.paths import CAPABILITIES_JSON

CST = timezone(timedelta(hours=8))


def main():
    if not os.path.exists(CAPABILITIES_JSON):
        print("❌ capabilities.json 不存在")
        return

    data = safe_read_json(CAPABILITIES_JSON)
    capabilities = data.get("capabilities", [])

    exportable = [
        cap for cap in capabilities
        if cap.get("status") == "strong_verified"
    ]

    output = {
        "exported_at": datetime.now(CST).isoformat(),
        "count": len(exportable),
        "capabilities": exportable
    }

    out_path = os.path.join(os.path.dirname(CAPABILITIES_JSON), "capabilities_export.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 导出完成：{len(exportable)} 个 strong_verified 能力 → {out_path}")
    for cap in exportable:
        print(f"  [{cap['capability_id']}] {cap.get('display_name','')} | 复用：{cap.get('reuse_count',0)} | 最近：{cap.get('last_used','')}")


if __name__ == "__main__":
    main()
