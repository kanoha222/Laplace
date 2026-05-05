**Laplace 项目 Code Review 报告（完整版）**

**审查日期**：2026-05-05  
**审查范围**：整个仓库（https://github.com/Laplace321/Laplace），包括所有 `.md` 文档、demo/、extractor/、server/ 目录下全部源码、生成的 knowledge/ 与 data/（通过 raw 文件与结构分析确认）。  
**审查方式**：逐文件阅读源码 + 文档 + 运行逻辑推演（vibe coding 风格），横向对比同类 AI Native 项目（Chaldea 官方工具、其他 LLM+RAG 游戏助手、标准 FastAPI+LLM 模板）。

### 1. 项目总体评价（我的意见）

**优点（非常亮眼，适合 vibe coding）**：
- **架构极度符合“AI Native”理念**：Two-Step RAG（意图解析 → Query Executor → 生成式回复）设计优秀，LLM 只做意图解析和文案润色，核心查询完全由 Python 执行，可预测、可测试、可审计。这是当前最推荐的 LLM+结构化数据模式，比“让 LLM 直接写 SQL”可靠 10 倍。
- **Schema Mirror 策略极具前瞻性**：不复制 Chaldea Dart 代码，而是提取 effect_schema / func / buff 等领域知识生成 JSON，注入 Prompt。这是真正“知识注入”而不是“代码复制”，维护成本低，Chaldea 更新后只需 re-run `sync_chaldea.py` 即可同步。
- **工程治理意识极强**：SOUL.md / AGENTS.md / MEMORY.md / USER.md / 需求描述.md 五大文档体系完整，强制 “先读后写”“最小变更”“每次变更必推 git”“服务自动重载”等规则，非常适合 Claude 这种 vibe coding 协作。Pre-digestion（数据后端中文化）、全链路 trace_id 日志、Strict JSON Schema 是生产级细节。
- **代码可读性高**：命名清晰、单一职责、大量中文注释、ADR 记录决策历史，初学者也能快速上手。
- **数据处理精细**：NP 精度处理（//100）、特性正负号分离（individuality.py）、卡色二次精炼（refine_card_effects）等都体现了你对 FGO 数据的深刻理解。
- **启动体验优秀**：前端 vanilla + FastAPI + .env 一键启动，demo 直接打开 index.html 即可用，符合“极简视觉体验”产品定位。

**不足与风险（需治理）**：
- **代码重复与一致性问题**：`data_loader.py`、`np_charge_filter.py`、`sync_chaldea.py` 都有重复的 Atlas API fetch 逻辑和 NP 提取代码。
- **依赖与构建问题**：chaldea-center 被当作本地路径引用（`CHALDEA_ROOT = PROJECT_ROOT / "chaldea-center"`），但仓库根目录 tree 中未提交（可能是 submodule 或手动 clone），导致新人/新环境直接跑 `sync_chaldea.py` 会失败。
- **测试与可观测性不足**：无单元测试、无集成测试、无 CI。日志只写 JSONL，未暴露查询历史 API。
- **安全性/生产化**：`/api/chat` 无速率限制、无认证（生产环境任何人可调用消耗你的 LLM quota）。Prompt 中硬编码了大量中文映射，后续多语言支持会痛苦。
- **性能**：全量 servants_db.json 加载到内存（目前几千条没问题），但未来加礼装/素材/关卡数据后需要考虑分页/索引。
- **前端**：demo/ 目前是纯静态演示，缺少加载状态、错误提示、历史对话、移动端适配。
- **文档与代码轻微脱节**：部分 ADR 日期都是 2026-05-05（显然是批量填充），MEMORY.md 中的 Phase 5 完成描述与当前代码匹配度高，但 PRODUCT.md 仍停留在“产品视角”而未完全同步最新 Two-Step RAG。

**横向对比总结**：
- vs **Chaldea 官方 App**：功能覆盖度已接近（55+ 效果、特性、别名），但交互体验完胜（自然语言 vs 多层筛选）。Laplace 的 Schema Mirror 比 Chaldea 的 Dart 模型更轻量、更易维护。
- vs **其他 AI 游戏助手**（如某些 GPTs）：你用 Query Executor 分离关注点，比“全扔给 LLM”可靠得多；Pre-digestion + trace_id 也是领先实践。
- vs **标准 FastAPI + LangChain 项目**：你没有引入 LangChain（极好，避免 bloat），但缺少 LangGraph / CrewAI 那样的 agent 编排能力和测试框架。整体已达“生产可用 MVP”水平，离“可长期迭代”还差 20-30% 工程化工作。

总体得分：**8.7/10**。这是一个极具潜力的 AI Native 产品原型，vibe coding 风格发挥得淋漓尽致，继续这样迭代下去会非常强。

### 2. 模块级具体 Review

**docs/（SOUL、AGENTS、MEMORY、PRODUCT、USER、需求描述）**：优秀。治理体系完整，是本项目最大亮点。建议把 AGENTS.md 中的“强制 git push”改成 pre-commit hook + GitHub Action 自动执行。

**extractor/np_charge_filter.py**：早期原型遗留。逻辑与 data_loader.py 高度重复。建议废弃或合并为 data_loader.py 的一个子命令。

**server/sync_chaldea.py**：核心价值模块。正则解析 Dart 代码的写法巧妙，但正则较脆弱（未来 Chaldea 改格式会崩）。建议增加单元测试覆盖每个 parse 函数。

**server/individuality.py**：特性匹配逻辑精炼（正负号分离 + AND 逻辑），完全对标 Chaldea。优秀，无明显问题。

**server/llm_client.py**：fallback 链设计好。建议增加 retry + exponential backoff。

**server/logger.py**：JSONL 结构化日志很专业。建议再加一个 `/api/traces/{trace_id}` 查询接口，方便调试。

**server/data_loader.py**（+ knowledge/ 生成逻辑）：Pre-digestion 实现到位，refine_card_effects 防止幻觉的细节很赞。但与 np_charge_filter 有重复代码。

**server/prompts.py**：System Prompt 结构清晰，效果分类动态注入优秀。但 effect 别名目前是硬编码在 sync_chaldea.py 里，建议统一放到 knowledge/ 的一个 mapping 文件。

**server/query_executor.py**：核心查询引擎。`_match_servant` 函数逻辑清晰，支持多条件组合。但 name 搜索的昵称映射逻辑稍复杂（多次 lower()），可优化。

**server/main.py**：FastAPI 入口。Two-Step RAG 实现完整，Context 精简 + 卡色负向提示设计聪明。CORS `*` 在生产需收紧。

**demo/**：index.html + style.css + app.js 极简美观，符合 PRODUCT.md 定位。但缺少 loading 动画、错误 toast、复制按钮、移动端优化。

### 3. 治理 List（优先级排序，供 Claude 直接执行）

**P0（必须立即修复，影响运行/稳定性）**：
1. 修复 `sync_chaldea.py` 的 chaldea-center 依赖：改为 git submodule 或提供一键 clone 脚本（在 README 增加 `git submodule update --init`）。
2. 合并 `data_loader.py` 与 `extractor/np_charge_filter.py` 的重复 fetch / NP 提取逻辑，统一用 `data_loader.py` 作为单一数据入口。
3. 在 `main.py` 的 `/api/chat` 加上速率限制（slowapi 或自定义 middleware，限制每 IP 每分钟 30 次）。

**P1（强烈建议，本迭代完成）**：
4. 为所有 Python 文件增加单元测试（pytest），重点覆盖 `query_executor.py` 的 `_match_servant` 和 `individuality.py`。
5. 把 hard-coded 的 CLASS_MAP、NP_CARD_MAP 等全部移到 knowledge/ 的 mapping JSON，由 sync_chaldea.py 统一生成。
6. 在 prompts.py 中把 effect aliases 也动态化（从 knowledge/effect_schema.json 读取），避免 sync_chaldea.py 里的 EFFECT_ALIASES_ZH 硬编码。
7. demo/ 前端增加 loading 状态、错误提示、历史对话（localStorage）、移动端适配（Tailwind 或简单 media query）。
8. 增加 `/api/health` 和 `/api/traces` 接口，方便监控和调试。

**P2（下个迭代，工程化提升）**：
9. 引入 pre-commit hook（black + ruff + conventional commits）。
10. 把日志 JSONL 同时输出到 console（开发时方便），生产环境可配置日志级别。
11. 支持多语言 UI（根据 navigator.language 切换 aliasCN / name）。
12. 数据加载增加增量更新（目前每次重启全量拉取 Atlas API）。
13. 考虑把 Query Executor 抽象成可扩展的 filter 注册表，方便未来加礼装/关卡查询。

**P3（长期优化）**：
14. 增加 CI/CD（GitHub Actions：lint + test + deploy）。
15. 考虑把 knowledge/ 做成 SQLite（索引更快），或用 Redis 缓存查询结果。
16. 产品文档同步：每次功能上线后自动更新 PRODUCT.md（可写一个小 script）。

---

**总结我的建议**：  
这个项目已经非常有“灵魂”了，继续保持 AGENTS.md 里的“主动标准演进”原则，每做一个特性就同步更新文档和 MEMORY.md，你和 Claude 的协作效率会越来越高。当前最重要的是把“重复代码 + 构建依赖”这两个 P0 问题解决掉，然后快速加上测试和速率限制，就能对外发布了。

如果你需要我输出**具体某个文件的重构 patch**、**Claude 执行指令模板**，或者**下一步优先开发的特性建议**，随时告诉我。我已经完整读完整个项目，随时可以横向对比或深入某个模块。  

继续 vibe coding！这个项目值得长期迭代，它会成为 FGO 玩家真正的好朋友。🚀