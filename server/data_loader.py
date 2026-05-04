#!/usr/bin/env python3
"""
Laplace — 通用从者数据加载器

从 Atlas Academy API 拉取全量从者数据，
提取所有技能中的 NP 充能信息（不限定阈值），
生成通用数据库供 Query Executor 使用。
"""

import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("请先安装依赖: pip install requests", file=sys.stderr)
    sys.exit(1)

API_BASE = "https://api.atlasacademy.io"
NICE_SERVANT_URL = f"{API_BASE}/export/JP/nice_servant_lang_en.json"
OUTPUT_DIR = Path(__file__).parent / "data"

# NP 充能相关的 funcType
GAIN_NP_FUNC_TYPES = {"gainNp"}

# 自充目标类型
SELF_TARGET_TYPES = {"self"}
# 全体充能目标类型（包含自身）
PARTY_TARGET_TYPES = {"ptAll"}
# 所有包含自身的目标类型
ALL_SELF_TARGETS = SELF_TARGET_TYPES | PARTY_TARGET_TYPES

SKILL_LV10_INDEX = 9


def fetch_servants() -> list[dict]:
    """从 Atlas Academy API 拉取全量从者数据。"""
    print("📡 正在从 Atlas Academy API 拉取从者数据...")
    resp = requests.get(NICE_SERVANT_URL, timeout=120)
    resp.raise_for_status()
    servants = resp.json()
    normal = [
        s for s in servants
        if s.get("type") == "normal" and s.get("collectionNo", 0) > 0
    ]
    print(f"   ✅ 获取到 {len(normal)} 个从者")
    return normal


def get_face_url(servant: dict) -> str:
    """获取从者头像 URL（优先最终再临）。"""
    faces = servant.get("extraAssets", {}).get("faces", {}).get("ascension", {})
    if faces:
        return faces.get("4") or faces.get("3") or faces.get("2") or faces.get("1", "")
    return ""


def extract_np_charges(servant: dict) -> list[dict]:
    """提取从者所有技能中的 NP 充能效果。"""
    charges = []
    for skill in servant.get("skills", []):
        if skill.get("type") != "active":
            continue
        for func in skill.get("functions", []):
            if func.get("funcType") not in GAIN_NP_FUNC_TYPES:
                continue
            target_type = func.get("funcTargetType", "")
            if target_type not in ALL_SELF_TARGETS:
                continue
            svals = func.get("svals", [])
            if len(svals) < 10:
                continue
            lv10_value = svals[SKILL_LV10_INDEX].get("Value", 0)
            if lv10_value > 0:
                charges.append({
                    "skillName": skill.get("name", ""),
                    "skillNum": skill.get("num", 0),
                    "chargePercent": lv10_value // 100,
                    "chargeValue": lv10_value,
                    "targetType": "self" if target_type in SELF_TARGET_TYPES else "party",
                })
    return charges


def build_database(servants: list[dict]) -> list[dict]:
    """构建通用从者数据库。"""
    db = []
    for svt in servants:
        charges = extract_np_charges(svt)
        # 计算最大自充百分比
        self_charges = [c["chargePercent"] for c in charges if c["targetType"] == "self"]
        party_charges = [c["chargePercent"] for c in charges if c["targetType"] == "party"]
        max_self_charge = max(self_charges) if self_charges else 0
        max_party_charge = max(party_charges) if party_charges else 0
        # 总自充 = 自充 + 全体充（全体充也给自己）
        total_self_charge = sum(self_charges) + sum(party_charges)

        entry = {
            "id": svt["id"],
            "collectionNo": svt.get("collectionNo", 0),
            "name": svt.get("name", "Unknown"),
            "rarity": svt.get("rarity", 0),
            "className": svt.get("className", "unknown"),
            "faceUrl": get_face_url(svt),
            "npCharges": charges,
            "maxSelfCharge": max_self_charge,
            "maxPartyCharge": max_party_charge,
            "totalSelfCharge": total_self_charge,
            "hasNpCharge": len(charges) > 0,
        }
        db.append(entry)

    print(f"   ✅ 构建数据库: {len(db)} 个从者, "
          f"{sum(1 for s in db if s['hasNpCharge'])} 个有自充")
    return db


def main():
    print("=" * 50)
    print("🔮 Laplace — Data Loader")
    print("=" * 50)

    servants = fetch_servants()
    db = build_database(servants)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "servants_db.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\n📄 输出: {output_path}")
    print("✨ 完成!")


if __name__ == "__main__":
    main()
