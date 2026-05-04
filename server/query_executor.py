"""
Laplace — Query Executor

接收 LLM 解析出的 JSON 查询指令，
在预加载的从者数据上执行筛选。
"""

import json
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "servants_db.json"

# 全局缓存
_servants_db: list[dict] | None = None


def load_database() -> list[dict]:
    """加载从者数据库（带缓存）。"""
    global _servants_db
    if _servants_db is None:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            _servants_db = json.load(f)
        print(f"📦 从者数据库已加载: {len(_servants_db)} 条")
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
        # 使用 maxSelfCharge（最大自充值，包含 self 类型）
        # 以及 maxPartyCharge（全体充能值）
        # 总可用自充 = max(自充) + max(全体充)
        charge = servant.get("totalSelfCharge", 0)
        # 如果没有充能能力，直接不匹配
        if not servant.get("hasNpCharge", False):
            return False
        # 对于精确匹配，检查是否有任何一个技能的充能等于目标值
        op = np_cond.get("op", "eq")
        value = np_cond.get("value", 0)
        if op == "eq":
            # 精确匹配：检查是否有任何一个技能充能等于目标值
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

    # 名称搜索
    name = conditions.get("name")
    if name is not None:
        if name.lower() not in servant.get("name", "").lower():
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
