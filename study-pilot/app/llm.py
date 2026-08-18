import os
import json
from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import response

from pydantic import ValidationError
from app.schemas import GeneratedPlan,PlanRequest

# 加载项目根目录下的 .env；已经存在的系统环境变量不会被覆盖。
load_dotenv()


@lru_cache
def get_llm_client() -> OpenAI:
    """创建并缓存一个大模型客户端。"""
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 LLM_API_KEY，请在 .env 中设置它")

    base_url = os.getenv("LLM_BASE_URL")

    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)

    return OpenAI(api_key=api_key)


def get_llm_model() -> str:
    """读取调用大模型时使用的模型名称。"""
    model = os.getenv("LLM_MODEL")
    if not model:
        raise RuntimeError("未配置 LLM_MODEL，请在 .env 中设置它")

    return model
def generate_text(prompt: str) -> str:
    client = get_llm_client()
    model = get_llm_model()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role":"system",
                "content":"你是一名耐心、专业的学习规划助手。",
            },
            {
                "role":"user",
                "content":prompt,
            },
        ],
    )

    content = response.choices[0].message.content

    if content is None:
        raise RuntimeError("大模型没有返回文本内容")

    return content

def generate_learning_plan(request: PlanRequest) -> GeneratedPlan:
    client = get_llm_client()
    model = get_llm_model()

    json_schema =GeneratedPlan.model_json_schema()

    prompt = f"""
请根据用户信息生成一份学习计划。

用户目标：{request.goal}
当前基础：{request.current_level}
学习周期：{request.duration_weeks} 周
每天学习时间：{request.minutes_per_day} 分钟

要求：

1. weekly_objectives 必须正好有 {request.duration_weeks} 项。
2. 每周至少生成一个学习任务。
3. estimated_minutes 不得超过每天学习时间
   {request.minutes_per_day} 分钟。
4. acceptance_criteria 必须是可以检查的验收标准。
5. 只返回 JSON，不要返回 Markdown，不要使用代码块。
6. 返回的 JSON 必须符合下面的 JSON Schema：

{json.dumps(json_schema, ensure_ascii=False)}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role":"system",
                "content":(
                    "你是一名专业的学习规划助手。"
                    "你必须使用简体中文回答，"
                    "你必须按照用户提供的 JSON Schema 输出合法 JSON。"
                ),
            },
            {
                "role":"user",
                "content":prompt,
            },
        ],
        response_format={
            "type":"json_object",
        },
    )

    content = response.choices[0].message.content

    if content is None:
        raise RuntimeError("大模型没有返回内容")

    try:
        raw_data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"大模型返回的内容不是合法 JSON：{content}"
        ) from exc

    try:
        plan=GeneratedPlan.model_validate(raw_data)
    except ValidationError as exc:
        raise RuntimeError(
            f"大模型返回的数据不符合 Pydantic 模型：{exc}"
        ) from exc

    if len(plan.weekly_objectives) !=request.duration_weeks:
        raise RuntimeError(
            "大模型生成的每周目标数量与学习周期不一致"
        )

    for task in plan.tasks:
        if task.estimated_minutes > request.minutes_per_day:
            raise RuntimeError(
                f"任务“{task.title}”的预计时间超过每天可用时间"
            )
    return plan