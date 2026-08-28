from typing import cast

from langgraph.graph import END,START,StateGraph
from sqlalchemy.orm import Session

from app.agent import (
    AgentState,
    create_initial_state,
    execute_tool,
    generate_final_answer,
    recognize_intent,
)


def build_agent_graph(db: Session):
    """根据数据库会话构建并编译 Agent 状态图"""

    def recognize_intent_node(
            state: AgentState,
    )->dict:
        updated_state = recognize_intent(state)

        return {
            "intent":updated_state["intent"],
            "plan_id":updated_state["plan_id"],
            "task_id":updated_state["task_id"],
        }

    def execute_tool_node(
            state: AgentState,
    ) -> dict:
        updated_state = execute_tool(state,db)

        return {
            "tool_result":updated_state["tool_result"],
        }
    def generate_final_answer_node(
            state: AgentState,
    )->dict:
        updated_state = generate_final_answer(state)

        return {
            "final_answer":updated_state["final_answer"],
        }

    builder = StateGraph(AgentState)

    builder.add_node(
        "recognize_intent",
        recognize_intent_node,
    )
    builder.add_node(
        "execute_tool",
        execute_tool_node,
    )
    builder.add_node(
        "generate_final_answer",
        generate_final_answer_node,
    )

    builder.add_edge(
        START,
        "recognize_intent",
    )
    builder.add_edge(
        "recognize_intent",
        "execute_tool",
    )
    builder.add_edge(
        "execute_tool",
        "generate_final_answer",
    )
    builder.add_edge(
        "generate_final_answer",
        END,
    )

    return builder.compile()


def run_agent_graph(
        user_input:str,
        db: Session,
        plan_id: int | None = None,
        task_id: int | None = None,
) -> AgentState:
    """通过 LangGraph 执行一次完整的 Agent 工作流。"""

    initial_state = create_initial_state(
        user_input=user_input,
        plan_id=plan_id,
        task_id=task_id,
    )

    graph = build_agent_graph(db)
    result = graph.invoke(initial_state)

    return cast(AgentState, result)
