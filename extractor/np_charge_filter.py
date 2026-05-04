#!/usr/bin/env python3
"""
Laplace — NP Charge Filter (30% Self-Charge Extractor)

从 Atlas Academy API 拉取全量从者数据，
筛选出在技能 Lv.10 时拥有精确 30% 自充效果的从者。

数据精度说明：
  FGO 内部以万分之一为单位存储 NP 值，
  即 Value=3000 表示 30%。

输出：Strict JSON（符合项目 JSON Only 协议约束）
"""

import json
import sys
import os
from pathlib import Path

try:
    import requests
except ImportError:
    print("请先安装依赖: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

# === Constants ===
API_BASE = "https://api.atlasacademy.io"
NICE_SERVANT_LIST_URL = f"{API_BASE}/export/JP/nice_servant_lang_en.json"
TARGET_CHARGE_VALUE = 3000  # 30% = 3000 (FGO internal precision)
SKILL_LV10_INDEX = 9        # svals[9] = Lv.10

# funcType 标识 NP 充能的类型
GAIN_NP_FUNC_TYPE = "gainNp"

# funcTargetType 标识自身充能
SELF_TARGET_TYPES = {"self", "ptAll"}  # ptAll = 全体充能（包含自身）

OUTPUT_DIR = Path(__file__).parent.parent / "demo" / "data"


def fetch_servants() -> list[dict]:
    """从 Atlas Academy API 拉取全量从者数据（英文版）。"""
    print(f"📡 正在从 Atlas Academy API 拉取从者数据...")
    print(f"   URL: {NICE_SERVANT_LIST_URL}")
    
    resp = requests.get(NICE_SERVANT_LIST_URL, timeout=120)
    resp.raise_for_status()
    
    servants = resp.json()
    # 过滤掉非正式从者（如 enemy-only、Beast 等）
    normal_servants = [
        s for s in servants
        if s.get("type") == "normal" and s.get("collectionNo", 0) > 0
    ]
    print(f"   ✅ 获取到 {len(normal_servants)} 个从者")
    return normal_servants


def extract_np_charge_info(servant: dict, target_value: int) -> list[dict]:
    """
    从单个从者的技能中提取 NP 自充信息。
    
    只检查主动技能（active skills），不包括被动技能和宝具。
    返回所有包含精确 target_value 自充的技能记录。
    """
    results = []
    svt_id = servant["id"]
    collection_no = servant.get("collectionNo", 0)
    name = servant.get("name", "Unknown")
    rarity = servant.get("rarity", 0)
    class_name = servant.get("className", "unknown")
    
    # 获取从者头像 URL
    face_url = ""
    faces = servant.get("extraAssets", {}).get("faces", {}).get("ascension", {})
    if faces:
        # 优先取灵基 4（最终再临）
        face_url = faces.get("4") or faces.get("3") or faces.get("2") or faces.get("1", "")
    
    # 遍历所有技能
    for skill in servant.get("skills", []):
        skill_name = skill.get("name", "")
        skill_num = skill.get("num", 0)
        skill_type = skill.get("type", "")
        
        # 只检查主动技能
        if skill_type != "active":
            continue
        
        for func in skill.get("functions", []):
            func_type = func.get("funcType", "")
            func_target = func.get("funcTargetType", "")
            
            # 检查是否是 NP 充能且目标包含自身
            if func_type != GAIN_NP_FUNC_TYPE:
                continue
            if func_target not in SELF_TARGET_TYPES:
                continue
            
            # 获取 svals（技能各等级的数值）
            svals = func.get("svals", [])
            if len(svals) < 10:
                continue
            
            # 取 Lv.10 的 Value
            lv10_value = svals[SKILL_LV10_INDEX].get("Value", 0)
            
            if lv10_value == target_value:
                results.append({
                    "id": svt_id,
                    "collectionNo": collection_no,
                    "name": name,
                    "rarity": rarity,
                    "className": class_name,
                    "chargePercent": lv10_value // 100,  # 3000 -> 30
                    "skillName": skill_name,
                    "skillNum": skill_num,
                    "targetType": func_target,
                    "faceUrl": face_url,
                })
    
    return results


def main():
    """主流程：拉取 → 筛选 → 输出 JSON。"""
    print("=" * 60)
    print("🔮 Laplace — NP Charge Filter")
    print(f"   目标: 精确 {TARGET_CHARGE_VALUE // 100}% 自充从者")
    print("=" * 60)
    
    # 1. 拉取数据
    servants = fetch_servants()
    
    # 2. 筛选
    print(f"\n🔍 筛选 funcType={GAIN_NP_FUNC_TYPE}, "
          f"targetType={SELF_TARGET_TYPES}, "
          f"svals[{SKILL_LV10_INDEX}].Value={TARGET_CHARGE_VALUE}...")
    
    all_results = []
    seen_ids = set()  # 用于去重（同一从者可能有多个自充技能）
    
    for svt in servants:
        charges = extract_np_charge_info(svt, TARGET_CHARGE_VALUE)
        for charge in charges:
            # 按从者 ID 去重，保留第一个匹配的技能
            if charge["id"] not in seen_ids:
                seen_ids.add(charge["id"])
                all_results.append(charge)
    
    # 按稀有度降序 → collectionNo 升序排列
    all_results.sort(key=lambda x: (-x["rarity"], x["collectionNo"]))
    
    print(f"   ✅ 找到 {len(all_results)} 个从者")
    
    # 3. 输出
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "servants_np_charge.json"
    
    output_data = {
        "query": {
            "type": "QUERY_CHARGE",
            "value": TARGET_CHARGE_VALUE // 100,
            "description": f"精确 {TARGET_CHARGE_VALUE // 100}% 自充从者（技能 Lv.10）",
            "funcType": GAIN_NP_FUNC_TYPE,
            "targetTypes": list(SELF_TARGET_TYPES),
        },
        "count": len(all_results),
        "servants": all_results,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 输出文件: {output_path}")
    print(f"   从者数量: {len(all_results)}")
    
    # 打印前 5 个作为预览
    print("\n📋 预览 (前 5 个):")
    for svt in all_results[:5]:
        print(f"   ★{'★' * (svt['rarity'] - 1)} {svt['name']} "
              f"({svt['className']}) — {svt['skillName']} "
              f"[{svt['chargePercent']}%]")
    
    print("\n✨ 完成!")
    return all_results


if __name__ == "__main__":
    main()
