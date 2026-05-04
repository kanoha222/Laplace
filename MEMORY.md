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

## 已知问题 & 解决方案

- **macOS pip 外部管理**: `pip install` 报错 `externally-managed-environment`，需要使用 `python3 -m venv .venv` 创建虚拟环境

## 项目里程碑

| 日期 | 事件 | 备注 |
| :--- | :--- | :--- |
| 2026-05-05 | 项目初始化 | 创建 OpenClaw 风格的项目骨架 |
| 2026-05-05 | Demo v1 完成 | 30% NP 自充筛选器 (Python + Web) |
| 2026-05-05 | 产品升级 | 从静态 Demo 进化为 AI Native 对话式产品 |

## 技术备忘

- **LLM 意图解析链路**: 用户输入 → LLM 解析为 JSON 指令 → Query Executor 执行 → LLM 格式化结果 → 返回对话框
- **数据精度**: FGO NP 值以 1/10000 为单位存储，`Value=3000` 表示 30%
- **Atlas Academy 批量端点**: `https://api.atlasacademy.io/export/JP/nice_servant_lang_en.json`
