# Memory — 项目记忆

> 长期知识库，记录关键决策、已知问题和项目演进历史。
> AI 在每次会话开始时应阅读此文件以获取上下文。

## 架构决策记录 (ADR)

### ADR-001: FGO NP 数据精度约定
- **日期**: 2026-05-05
- **状态**: 已采纳
- **背景**: FGO 数据中 NP 值以万分之一为单位存储
- **决策**: `svals[].Value = 3000` 表示 30%，精度 = Value / 100
- **理由**: 与 Atlas Academy API 和 Chaldea 源码保持一致

### ADR-002: 数据获取方式
- **日期**: 2026-05-05
- **状态**: 已采纳
- **背景**: 需要获取全量从者技能数据
- **决策**: 使用 Atlas Academy 的批量导出端点 `nice_servant_lang_en.json`，Python 预处理后生成静态 JSON
- **理由**: 避免前端频繁调 API，数据可离线使用

### ADR-003: AI Native 架构 — LLM 意图解析 + Query Executor
- **日期**: 2026-05-05
- **状态**: 已采纳
- **背景**: 从静态 Demo 升级为 AI Native 对话式产品
- **决策**: LLM 只做意图解析和结果格式化，数据查询由中间层 Query Executor 执行
- **理由**: 分离关注点，LLM 输出的结构化 JSON 指令可预测、可测试，避免 LLM 直接操作数据带来的不可靠性

### ADR-004: Schema Mirror — 知识提取而非代码复制
- **日期**: 2026-05-05
- **状态**: 已采纳
- **背景**: Chaldea 用 Dart 构建了 FGO 最完整的数据类型系统（165+ FuncType、200+ BuffType、40+ SkillEffect 效果分类），需要决定如何利用
- **决策**: 不直接翻译 Dart 代码为 Python，而是提取 Chaldea 的「领域知识」（效果分类体系、枚举映射、数据路径约定）生成 JSON 知识库，注入 LLM System Prompt
- **理由**:
  1. Chaldea Dart 模型高度耦合 Flutter UI（路由、翻译、渲染），直接翻译代价高
  2. 知识提取方式维护成本低，Chaldea 更新时只需重新提取枚举
  3. LLM 具备知识后可自动处理新的查询类型，不需要每种效果都写查询逻辑

## 已知问题 & 解决方案

- **macOS pip 外部管理**: `pip install` 报错 `externally-managed-environment`，需要使用 `python3 -m venv .venv` 创建虚拟环境

## 项目里程碑

| 日期 | 事件 | 备注 |
| :--- | :--- | :--- |
| 2026-05-05 | 项目初始化 | 创建 OpenClaw 风格的项目骨架 |
| 2026-05-05 | Demo v1 完成 | 30% NP 自充筛选器 (Python + Web) |
| 2026-05-05 | AI Native v1 | 对话式查询上线（FastAPI + LLM 意图解析 + 从者卡片） |
| 2026-05-05 | 架构升级 | 确立 Schema Mirror 策略，目标对标 Chaldea 全数据查询 |
| 2026-05-05 | Phase 2 完成 | 实现了 sync_chaldea.py 提取 5 个 Dart 文件的效果知识并与 LLM 集成 |
| 2026-05-05 | Phase 3 完成 | 实现了多语言映射、特性（Trait）匹配算法、宝具与配卡等从者深层属性过滤 |

## 技术备忘

- **LLM 意图解析链路**: 用户输入 → LLM 解析为 JSON 指令 → Query Executor 执行 → LLM 格式化结果 → 返回对话框
- **数据精度**: FGO NP 值以 1/10000 为单位存储，`Value=3000` 表示 30%
- **Atlas Academy 批量端点**: `https://api.atlasacademy.io/export/JP/nice_servant_lang_en.json`
- **Schema Mirror 知识源**: Chaldea `effect.dart` (SkillEffect 40+分类)、`func.dart` (FuncType 165+)、`buff.dart` (BuffType 200+)、`common.dart` (SvtClass 50+)
- **Chaldea 关键数据路径**: `servant.skills[] → skill.functions[] → function.svals[9].Value` (Lv.10数值)
- **效果分类体系**: 攻击(20种) / 防御(11种) / 异常(15种) / 辅助(9种) = 55+ 子分类
