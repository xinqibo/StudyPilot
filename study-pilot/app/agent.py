import re
from typing import Literal,TypedDict

from sqlalchemy.orm import Session

AgentIntent = Literal[
    "get_plan",
    "get_pending_tasks",
    "complete_task",
    "unknown",
]

class AgentState(TypedDict):


    user_input: str
    plan_id: int | None
    task_id: int | None
    intent: AgentIntent
    tool_result: str | None
    final_answer: str | None


def create_initial_state(
    user_input: str,
    plan_id: int | None = None,
    task_id: int | None = None,
) -> AgentState:

    return AgentState(
        user_input=user_input,
        plan_id=plan_id,
        task_id=task_id,
        intent="unknown",
        tool_result=None,
        final_answer=None,
    )
def extract_ids_from_text(
        user_input: str,
) -> tuple[int | None ,int | None]:
    """从用户输入中提取计划 ID 和任务 ID。"""
    plan_match = re.search(
        r"计划\s*(\d+)",
        user_input,
    )
    task_match = re.search(
        r"任务\s*(\d+)",
        user_input,
    )

    plan_id = (
        int(plan_match.group(1))
        if plan_match
        else None
    )

    task_id = (
        int(task_match.group(1))
        if task_match
        else None
    )

    return plan_id, task_id

def recognize_intent(state: AgentState) ->AgentState:
    """根据关键词识别用户想要执行的操作"""

    user_input = state["user_input"]

    #1.识别意图

    if "未完成" in user_input or "待完成" in user_input:
        intent : AgentIntent = "get_pending_tasks"
    elif "完成任务" in user_input or "标记完成" in user_input or "标记为完成" in user_input or "设为完成" in user_input:
        intent = "complete_task"
    elif "计划" in user_input:
        intent = "get_plan"
    else:
        intent = "unknown"

    #2. 从文本中提取 ID
    extracted_plan_id,extracted_task_id= (
        extract_ids_from_text(user_input)
    )

    #3.复制旧状态
    new_state = state.copy()
    new_state["intent"] = intent

    #4.只有没有手动传入ID时，才使用正则提取的 ID
    if new_state["plan_id"] is None:
        new_state["plan_id"] = extracted_plan_id

    if new_state["task_id"] is None:
        new_state["task_id"] = extracted_task_id

    return new_state

def execute_tool(
        state: AgentState,
        db: Session,
) ->AgentState:
    """根据已经识别的意图选择对应工具。"""
    if state["intent"] == "get_plan":
        from app.agent_tools import get_plan_tool

        return get_plan_tool(state,db)

    if state["intent"] == "get_pending_tasks":
        from app.agent_tools import get_pending_tasks_tool

        return get_pending_tasks_tool(state,db)

    if state["intent"] == "complete_task":
        from app.agent_tools import complete_task_tool

        return complete_task_tool(state,db)

    new_state = state.copy()
    new_state["tool_result"] = (
        f"暂时不支持意图：{state['intent']}"
    )

    return new_state

def generate_final_answer(state: AgentState) -> AgentState:
    """根据工具执行结果生成最终回答"""
    new_state = state.copy()
    tool_result = state["tool_result"]

    if tool_result is None:
        new_state["final_answer"] = (
            "抱歉，我暂时无法获得相关信息。"
        )
    elif state["intent"] == "get_pending_tasks":
        new_state["final_answer"] = (
            "以下是当前未完成的学习任务：\n"
            f"{tool_result}"
        )
    elif state["intent"] == "unknown":
        new_state["final_answer"] = (
            "抱歉，我暂时无法理解你的请求。"
        )
    else:
        new_state["final_answer"] = tool_result

    return new_state

def run_agent(
        user_input:str,
        db: Session,
        plan_id: int | None = None,
        task_id: int | None = None,
) -> AgentState:
    """执行一次完整的 Agent 工作流程。"""
    state = create_initial_state(
        user_input=user_input,
        plan_id=plan_id,
        task_id=task_id,
    )

    state = recognize_intent(state)
    state = execute_tool(state,db)
    state = generate_final_answer(state)

    return state