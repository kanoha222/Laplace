# Laplace

> AI Native 对话式 FGO 数据助手 —— 用自然语言查询 Fate/Grand Order 游戏数据

## 项目简介

Laplace 利用大语言模型（LLM）的意图识别能力，将传统的 FGO 工具软件转化为**对话式智能助手**。用户无需学习复杂的筛选 UI，只需用自然语言提问，即可获得精确的游戏数据。

**Old Way**: 打开 App → 选择从者列表 → 点击筛选 → 勾选 NP 充能 → 输入 30

**Laplace**: 输入 "帮我找一下 30 自充的从者有哪些" → AI 直接返回结果

## 功能特性

- [x] 30% NP 自充从者筛选（静态 Demo）
- [ ] 对话框界面 — 自然语言查询
- [ ] LLM 意图解析 — 自然语言 → 结构化查询指令
- [ ] Query Executor — 执行查询，返回结果
- [ ] 从者别名系统 — 支持"呆毛""村正"等非规范术语
- [ ] 多维度查询 — 职阶/稀有度/技能效果组合筛选

## 技术栈

| 类别 | 技术 |
| :--- | :--- |
| 前端 | HTML / CSS / JavaScript |
| 后端 | Python (FastAPI) |
| LLM | OpenAI / Gemini / Claude API |
| 数据源 | Atlas Academy API + Chaldea |
| 协议 | Strict JSON Schema |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js (可选，用于开发)

### 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r extractor/requirements.txt
```

### 运行 Demo (v1 静态版)

```bash
cd demo && python3 -m http.server 8080
# 访问 http://localhost:8080
```

### 更新从者数据

```bash
source .venv/bin/activate
python3 extractor/np_charge_filter.py
```

## 项目结构

```
Laplace/
├── README.md              # 项目说明
├── SOUL.md                # AI 助手人格定义
├── AGENTS.md              # AI 操作指南与全局约束
├── USER.md                # 用户画像
├── MEMORY.md              # 长期记忆与项目知识库
├── 需求描述.md             # 需求文档
├── demo/                  # Web Demo
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── data/              # 预处理数据
├── extractor/             # 数据提取器
│   ├── np_charge_filter.py
│   └── requirements.txt
└── chaldea-center/        # 参考源码 (gitignored)
```

## 合规声明

数据及部分逻辑源自开源项目 [Chaldea](https://github.com/chaldea-center/chaldea)，数据来源 [Atlas Academy](https://atlasacademy.io/)。

## License

CC-BY-NC-SA-4.0
