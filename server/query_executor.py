"""
Laplace — Query Executor

接收 LLM 解析出的 JSON 查询指令，
在预加载的从者数据上执行筛选。
支持效果类型、NP 充能、职阶、稀有度等多条件组合查询。
"""

import json
from pathlib import Path
from server.individuality import filter_by_traits

DATA_PATH = Path(__file__).parent / "data" / "servants_db.json"

# 全局缓存
_servants_db: list[dict] | None = None


def load_database() -> list[dict]:
    """加载从者数据库（带缓存）。"""
    global _servants_db
    if _servants_db is None:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            _servants_db = json.load(f)
        # 统计
        has_effects = sum(1 for s in _servants_db if s.get("skillEffects"))
        print(f"📦 从者数据库已加载: {len(_servants_db)} 条, {has_effects} 个有效果数据")
    return _servants_db


def execute_query(conditions: dict) -> list[dict]:
    """
    根据条件筛选从者。

    Args:
        conditions: LLM 解析出的查询条件
            - npCharge: {"op": "eq"|"gte"|"lte"|"gt", "value": int} | None
            - rarity: {"op": "eq"|"gte"|"lte"|"gt", "value": int} | None
            - className: str | None
            - name: str | None
            - skillEffect: str | None  (单效果筛选)
            - skillEffects: list[str] | None  (多效果 AND 筛选)
            - targetType: str | None  ("self" | "party" | "enemy")
            - traits: list[int] | None  (特性 ID 筛选)
            - excludeTraits: list[int] | None  (排斥特性 ID 筛选)
            - gender: str | None  (male, female, unknown)
            - attribute: str | None  (earth, sky, human, star, beast)
            - cards: dict | None  (如 {"buster": 3})
            - npCard: str | None  (buster, arts, quick)
            - npTarget: str | None  (one, all, support)

    Returns:
        匹配的从者列表
    """
    db = load_database()
    results = []

    for servant in db:
        if not _match_servant(servant, conditions):
            continue
        results.append(servant)

    # 按稀有度降序 → collectionNo 升序排序
    results.sort(key=lambda x: (-x["rarity"], x["collectionNo"]))
    return results


def _match_servant(servant: dict, conditions: dict) -> bool:
    """检查单个从者是否匹配条件。"""

    # NP 充能条件
    np_cond = conditions.get("npCharge")
    if np_cond is not None:
        charge = servant.get("totalSelfCharge", 0)
        if not servant.get("hasNpCharge", False):
            return False
        op = np_cond.get("op", "eq")
        value = np_cond.get("value", 0)
        if op == "eq":
            has_exact = any(
                c["chargePercent"] == value
                for c in servant.get("npCharges", [])
            )
            if not has_exact:
                return False
        elif op == "gte":
            if charge < value:
                return False
        elif op == "gt":
            if charge <= value:
                return False
        elif op == "lte":
            if charge > value:
                return False

    # 稀有度条件
    rarity_cond = conditions.get("rarity")
    if rarity_cond is not None:
        rarity = servant.get("rarity", 0)
        op = rarity_cond.get("op", "eq")
        value = rarity_cond.get("value", 0)
        if not _compare(rarity, op, value):
            return False

    # 职阶条件
    class_name = conditions.get("className")
    if class_name is not None:
        if servant.get("className", "").lower() != class_name.lower():
            return False

    # 名称搜索（支持英文、日文和中文翻译）
    name = conditions.get("name")
    if name is not None and isinstance(name, str) and name.strip():
        query_name = name.strip().lower()
        en_name = servant.get("name", "").lower()
        cn_name = servant.get("aliasCN", "").lower()
        jp_name = servant.get("originalName", "").lower()
        
        if (query_name not in en_name) and (query_name not in cn_name) and (query_name not in jp_name):
            return False

    # 单效果筛选
    skill_effect = conditions.get("skillEffect")
    if skill_effect is not None:
        target_type = conditions.get("targetType")
        if not _match_effect(servant, skill_effect, target_type):
            return False

    # 多效果组合筛选（AND 逻辑）
    skill_effects = conditions.get("skillEffects")
    if skill_effects is not None and isinstance(skill_effects, list):
        target_type = conditions.get("targetType")
        for effect in skill_effects:
            if not _match_effect(servant, effect, target_type):
                return False

    # 特性筛选
    traits = conditions.get("traits")
    exclude_traits = conditions.get("excludeTraits")
    if traits or exclude_traits:
        servant_traits = servant.get("traits", [])
        if not filter_by_traits(servant_traits, traits, exclude_traits):
            return False

    # 性别筛选
    gender = conditions.get("gender")
    if gender is not None:
        if servant.get("gender", "") != gender:
            return False

    # 阵营筛选
    attribute = conditions.get("attribute")
    if attribute is not None:
        if servant.get("attribute", "") != attribute:
            return False

    # 配卡筛选
    cards = conditions.get("cards")
    if cards is not None and isinstance(cards, dict):
        servant_cards = servant.get("cards", {})
        for card_type, count in cards.items():
            if servant_cards.get(card_type, 0) < count:
                return False

    # 宝具颜色筛选
    np_card = conditions.get("npCard")
    if np_card is not None:
        if servant.get("npCard", "") != np_card:
            return False

    # 宝具目标/类型筛选
    np_target = conditions.get("npTarget")
    if np_target is not None:
        if servant.get("npTarget", "") != np_target:
            return False

    return True


def _match_effect(
    servant: dict, effect_name: str, target_type: str | None = None
) -> bool:
    """
    检查从者是否拥有特定效果。

    Args:
        servant: 从者数据
        effect_name: 效果名（如 "invincible"）
        target_type: 目标类型筛选（如 "party"），None 表示不限
    """
    # 快速路径：先检查 skillEffects 集合
    servant_effects = servant.get("skillEffects", [])
    if effect_name not in servant_effects:
        return False

    # 如果需要按目标类型筛选，检查详细数据
    if target_type is not None:
        for skill in servant.get("skillDetails", []):
            for eff in skill.get("effects", []):
                if eff.get("type") == effect_name:
                    if eff.get("targetType") == target_type:
                        return True
        return False

    return True


def _compare(actual: int, op: str, expected: int) -> bool:
    """通用比较操作。"""
    if op == "eq":
        return actual == expected
    elif op == "gte":
        return actual >= expected
    elif op == "gt":
        return actual > expected
    elif op == "lte":
        return actual <= expected
    elif op == "lt":
        return actual < expected
    return False
