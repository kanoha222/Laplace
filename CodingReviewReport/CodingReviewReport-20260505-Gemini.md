这是一份为你量身定制的 **Laplace 项目 Code Review 报告**。这份报告采用了高度结构化的 Markdown 格式，专门针对“AI Agent (Claude) 协同开发”的上下文进行了优化。

你可以直接将这份报告的全文（或特定模块）复制并喂给 Claude，它能够清晰地理解问题背景、当前的架构痛点以及具体的重构目标。

---

# 📝 Laplace 项目 Code Review 与架构治理报告

**审查对象**: Laplace (AI Native FGO 对话式数据助手)
**当前阶段**: Phase 4 已完成，准备向 Phase 5 (多语言与扩展数据域) 演进
**核心协同工具**: Claude (Vibe Coding)

## 💡 一、 架构执行摘要 (Executive Summary)

目前 Laplace 的架构展现了极高的领域驱动设计（DDD）素养。特别是 **“意图解析与执行分离 (Intent-to-Execution)”** 的决策，将 LLM 限制在 DSL (JSON) 生成的边界内，交由 `query_executor.py` 执行确定性检索，完美规避了大模型的数值计算幻觉。同时，`main.py` 中的 **Data Pre-digestion (后端预消化)** 机制有效解决了 RAG 阶段的术语翻译问题。

然而，为了支撑 Phase 5 的复杂需求，当前代码库在 **LLM 交互稳定性、异步 I/O 阻塞、以及条件过滤器的可扩展性** 上存在技术债，需要优先治理。

---

## 🛠 二、 核心重构建议 (Actionable Code Review)

### 🔴 优先级 P0：系统稳定性与并发安全

#### 1. LLM 客户端 JSON 解析的脆弱性
*   **目标文件**: `server/llm_client.py`
*   **问题描述**: 目前解析大模型返回的 JSON 依赖于手动切割字符串（查找 ` ```json ` 标记并截取）。这种方式在主模型 (Claude-Sonnet) 表现尚可，但在触发 Fallback 机制调用较小模型（如 Deepseek-Flash）时，极易因为模型漏写逗号或未转义换行符导致 `json.loads()` 崩溃，直接返回 `{"intent": "unknown"}`。
*   **治理方案**:
    1.  **废弃 Prompt 约束**: 升级 API 调用方式，强制使用兼容 OpenAI 的 **Tool Calling (Function Calling)** 或 **Structured Outputs** (`response_format={ "type": "json_schema" }`)，在 API 层面确保输出结构绝对合法。
    2.  **引入容错机制**: 即使使用了结构化输出，也建议引入 `json_repair` 库作为最后的反序列化兜底，替代原生 `json.loads()`。

#### 2. FastAPI 异步事件循环阻塞 (Async Blocking)
*   **目标文件**: `server/logger.py` & `server/main.py`
*   **问题描述**: `server/logger.py` 使用的是标准的 `logging.FileHandler`，这是一个**同步且阻塞**的磁盘 I/O 操作。而在 `server/main.py` 中，`/api/chat` 是一个 `async def` 路由。在高并发下，同步写日志会阻塞 FastAPI 的 Event Loop，导致整个服务卡顿。
*   **治理方案**:
    1.  **方案 A (推荐)**: 使用 FastAPI 原生的 `BackgroundTasks`。在 `chat` 接口返回前，将 `log_chat_trace` 加入后台任务队列，让接口瞬间返回。
    2.  **方案 B**: 将 `logger.py` 的文件写入改造为使用 `aiofiles` 的纯异步写入。

---

### 🟡 优先级 P1：代码可维护性与扩展性

#### 3. Query Executor 的“If-Else 嵌套地狱”
*   **目标文件**: `server/query_executor.py` (`_match_servant` 函数)
*   **问题描述**: 当前 `_match_servant` 是一个巨型的顺序 `if` 判断流。随着 Phase 5 将引入“宝具 NP 回收率”、“指令卡 Hit 数”、“活动加成”等新维度，该函数将迅速膨胀，面临极高的圈复杂度（Cyclomatic Complexity），且容易发生条件间的逻辑干扰。
*   **治理方案**:
    *   **引入过滤器链模式 (Filter Chain / Strategy Pattern)**。将每个过滤维度（NP、职阶、特性、配卡）抽离为独立的校验函数。
    *   **预期形态**:
        ```python
        # 伪代码结构目标
        FILTERS = {
            "npCharge": check_np_charge,
            "traits": check_traits,
            # ...
        }
        def _match_servant(servant, conditions):
            return all(
                FILTERS[key](servant, value, conditions) 
                for key, value in conditions.items() 
                if value is not None and key in FILTERS
            )
        ```

#### 4. 数据管道 (Data Loader) 职责过载
*   **目标文件**: `server/data_loader.py` (`refine_card_effects` 函数)
*   **问题描述**: `data_loader.py` 目前不仅负责合并 Atlas API 和 Chaldea Schema，还在进行复杂的业务清洗（例如通过硬匹配 `buff.get("name").lower()` 来反向纠正卡色污染）。如果 Atlas 更改了英文文本描述，该逻辑将静默失效。
*   **治理方案**:
    *   剥离职责。将单纯的数据合并逻辑，与针对 Laplace 查询优化的二次清洗逻辑（如预计算 `hasNpCharge`, `totalSelfCharge`, `精炼卡色`）从代码层面拆分为明确的两个 Pipeline 步骤（Extract -> Transform）。

---

## 📋 三、 给 Claude 的执行指令清单 (Vibe Coding Prompts)

你可以直接复制以下指令片段，逐个发送给 Claude 进行重构落地：

### 任务 1: 重构 LLM 客户端
> **Prompt for Claude:**
> "Claude，请审查 `server/llm_client.py`。目前的 JSON 解析依赖字符串切割，存在不稳定性。请帮我重构 `chat_completion` 及相关内部函数：
> 1. 移除手动截取 ` ```json ` 的逻辑。
> 2. 将调用方式改为使用 OpenAI 标准的 Tool Calling (或者 Structured Outputs)，在 API 请求中强制约束模型返回我们需要的 intent 和 conditions 格式。
> 3. 请确保兼容现有的 `PRIMARY_MODEL` 和 `FALLBACK_MODELS` 轮询逻辑。"

### 任务 2: 修复异步日志阻塞
> **Prompt for Claude:**
> "Claude，请审查 `server/main.py` 中的 `/api/chat` 路由和 `server/logger.py`。目前的 `log_chat_trace` 是同步的文件 I/O，会阻塞 FastAPI 的 async 路由。
> 请帮我利用 FastAPI 的 `BackgroundTasks` 重构日志记录逻辑。要求：接口完成 LLM 响应后立刻返回结果，将日志写入动作扔到后台任务中异步执行，不阻塞主线程。"

### 任务 3: 优化查询执行器架构
> **Prompt for Claude:**
> "Claude，请审查 `server/query_executor.py` 中的 `_match_servant` 函数。它目前使用了大量的 if-else 判断。为了迎接 Phase 5 的更多查询维度，我们需要降低圈复杂度。
> 请使用策略模式（Strategy Pattern）或过滤器链（Filter Chain）对 `_match_servant` 进行解耦重构。将现有的各种判断（npCharge, className, traits, cards 等）拆分为独立的小函数，并在 `_match_servant` 中统一遍历执行。"
```