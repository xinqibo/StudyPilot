# StudyPilot

StudyPilot 是一个基于 FastAPI、LangGraph 和大语言模型的智能学习计划 Agent。它可以根据用户的学习目标生成结构化计划，并通过自然语言查询计划、查看未完成任务以及标记任务完成。

## 项目亮点

- 使用大语言模型生成符合 Pydantic Schema 的结构化学习计划
- 使用 LangGraph `StateGraph` 编排意图识别、工具执行和回答生成
- 支持从中文自然语言中提取 `plan_id` 和 `task_id`
- 使用 SQLAlchemy 和 SQLite 持久化计划与任务
- 提供统一的异常响应、请求日志、耗时统计和 `request_id`
- 使用 Pytest 覆盖 API、Agent、异常分支和数据库操作
- 提供独立 Agent 评测集，覆盖正常请求、缺少 ID、资源不存在和模糊表达
- 支持 Docker Compose 一键部署和 SQLite 数据卷持久化

## 技术栈

- Python 3.13
- FastAPI、Uvicorn
- Pydantic
- LangGraph
- SQLAlchemy、SQLite
- OpenAI 兼容 SDK（可接入 DeepSeek 等兼容服务）
- Pytest、HTTPX
- Docker、Docker Compose

## 系统架构

```mermaid
flowchart LR
    U[用户 / Swagger] --> API[FastAPI]
    API --> G[LangGraph StateGraph]
    G --> I[意图识别与 ID 提取]
    I --> T[Agent 工具]
    T --> DB[(SQLAlchemy / SQLite)]
    API --> LLM[大语言模型]
    LLM --> API
    G --> A[最终回答]
    A --> U
```

Agent 工作流：

```mermaid
flowchart TD
    S([START]) --> I[recognize_intent]
    I --> T[execute_tool]
    T --> A[generate_final_answer]
    A --> E([END])
```

## 支持的 Agent 意图

| 意图 | 示例 | 所需参数 |
| --- | --- | --- |
| `get_plan` | `查看计划1的完整内容` | `plan_id` |
| `get_pending_tasks` | `查看计划1中未完成的任务` | `plan_id` |
| `complete_task` | `把计划1中的任务2标记为完成` | `plan_id`、`task_id` |
| `unknown` | `今天天气怎么样` | 无 |

## 目录结构

```text
study-pilot/
├── app/
│   ├── main.py              # FastAPI 应用与路由
│   ├── schemas.py           # Pydantic 请求、响应模型
│   ├── database.py          # 数据库连接与会话
│   ├── db_models.py         # SQLAlchemy ORM 模型
│   ├── llm.py               # 大语言模型调用
│   ├── agent.py             # Agent 状态与核心节点逻辑
│   ├── agent_graph.py       # LangGraph StateGraph
│   ├── agent_tools.py       # 查询计划、任务和完成任务工具
│   └── logging_config.py    # 日志配置
├── evals/
│   ├── agent_cases.json     # Agent 评测数据集
│   └── run_agent_evals.py   # 评测运行器
├── tests/                   # Pytest 自动化测试
├── .env.example             # 环境变量示例
├── Dockerfile
├── compose.yaml
└── requirements.txt
```

## 环境变量

复制示例配置：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`：

```dotenv
LLM_API_KEY=your_api_key_here
LLM_MODEL=your_model_name
LLM_BASE_URL=https://example.com/v1
```

使用 OpenAI 官方接口时，可以删除或留空 `LLM_BASE_URL`。不要把包含真实密钥的 `.env` 提交到 Git。

## Docker 快速启动（推荐）

确保 Docker Desktop 已经启动，然后执行：

```powershell
docker compose up --build -d
docker compose ps
```

打开 Swagger UI：

```powershell
Start-Process "http://127.0.0.1:8000/docs"
```

查看日志：

```powershell
docker compose logs -f api
```

停止容器但保留 SQLite 数据：

```powershell
docker compose down
```

> `docker compose down -v` 会同时删除 SQLite 数据卷，请谨慎使用。

## 本地启动

### 1. 创建虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

### 3. 配置环境变量并启动

```powershell
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

服务地址：

- API：<http://127.0.0.1:8000>
- Swagger UI：<http://127.0.0.1:8000/docs>
- OpenAPI：<http://127.0.0.1:8000/openapi.json>

## API 示例

### 创建学习计划

```http
POST /plans
Content-Type: application/json

{
  "goal": "学习 LangGraph 并完成一个学习规划 Agent",
  "current_level": "了解 Python、FastAPI 和基础 SQL",
  "duration_weeks": 4,
  "minutes_per_day": 90
}
```

### 查询计划

```http
GET /plans/1
```

### 标记任务完成

```http
PATCH /plans/1/tasks/1
Content-Type: application/json

{
  "completed": true
}
```

### 与 Agent 对话

```http
POST /agent/chat
Content-Type: application/json

{
  "message": "把计划1中的任务1标记为完成"
}
```

也可以在文本没有 ID 时显式传入参数：

```json
{
  "message": "把这个任务标记为完成",
  "plan_id": 1,
  "task_id": 1
}
```

## 统一错误响应

资源不存在时返回统一结构：

```json
{
  "error": {
    "code": "HTTP_404",
    "message": "Plan not found"
  }
}
```

每个请求的日志包含请求方法、路径、状态码、耗时和 `request_id`，便于排查问题。

## 自动化测试

```powershell
python -m pytest -v
```

当前测试覆盖：

- 学习计划创建、列表和详情查询
- 任务完成和资源不存在
- 请求参数校验和 LLM 失败回退
- Agent 意图识别与 ID 提取
- Agent 工具调用及对话 API

## Agent 评测

```powershell
python -m evals.run_agent_evals
```

评测数据位于 `evals/agent_cases.json`，覆盖：

- 正常请求
- 缺少计划 ID 或任务 ID
- 计划或任务不存在
- 无关问题和模糊表达

## 后续规划

- 使用 LLM 结构化输出增强复杂意图识别
- 增加 LangGraph Checkpointer，实现多轮对话记忆
- 将 SQLite 替换为 PostgreSQL
- 增加 GitHub Actions 持续集成
- 增加用户认证、限流和可观测性

## License

本项目用于学习、作品展示和技术实践。
