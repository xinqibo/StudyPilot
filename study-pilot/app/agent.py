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
def recognize_intent(state: AgentState) ->AgentState:
    """根据关键词识别用户想要执行的操作"""

    user_input = state["user_input"]

    if "未完成" in user_input or "待完成" in user_input:
            intent : AgentIntent = "get_pending_tasks"
    elif "完成任务" in user_input or "标记完成" in user_input:
        intent = "complete_task"
    elif "计划" in user_input:
        intent = "get_plan"
    else:
        intent = "unknown"

    new_state = state.copy()
    new_state["intent"] = intent

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