from sqlalchemy.orm import Session

from app.agent_graph import run_agent_graph
from app.db_models import LearningPlanDB, LearningTaskDB


def create_test_plan(db: Session) -> tuple[int, list[int]]:
    """创建一条计划和两条测试任务。"""

    plan = LearningPlanDB(
        goal="学习 LangGraph",
        current_level="了解 Python 和 FastAPI",
        duration_weeks=2,
        minutes_per_day=90,
        weekly_objectives=[
            "掌握 StateGraph",
            "完成 Agent 工具调用",
        ],
    )

    plan.tasks = [
        LearningTaskDB(
            title="学习 StateGraph",
            description="理解节点、边和状态",
            estimated_minutes=60,
            acceptance_criteria=[
                "能够创建 StateGraph",
                "能够解释节点和边",
            ],
            completed=False,
        ),
        LearningTaskDB(
            title="实现工具调用",
            description="让 Agent 调用数据库工具",
            estimated_minutes=90,
            acceptance_criteria=[
                "能够查询任务",
                "能够修改任务状态",
            ],
            completed=False,
        ),
    ]

    db.add(plan)
    db.commit()
    db.refresh(plan)

    task_ids = [task.id for task in plan.tasks]

    return plan.id, task_ids


def test_agent_get_plan(db_session: Session):
    """Agent 应该能够查询完整计划。"""

    plan_id, task_ids = create_test_plan(db_session)

    state = run_agent_graph(
        user_input="查询学习计划的完整内容",
        plan_id=plan_id,
        db=db_session,
    )

    assert state["intent"] == "get_plan"
    assert state["final_answer"] is not None
    assert "学习 LangGraph" in state["final_answer"]
    assert "学习 StateGraph" in state["final_answer"]
    assert "实现工具调用" in state["final_answer"]


def test_agent_get_pending_tasks(db_session: Session):
    """Agent 应该能够查询未完成任务。"""

    plan_id, task_ids = create_test_plan(db_session)

    state = run_agent_graph(
        user_input="查询这个计划中未完成的任务",
        plan_id=plan_id,
        db=db_session,
    )

    assert state["intent"] == "get_pending_tasks"
    assert state["final_answer"] is not None
    assert "学习 StateGraph" in state["final_answer"]
    assert "实现工具调用" in state["final_answer"]


def test_agent_complete_task(db_session: Session):
    """Agent 应该能够把任务状态保存为已完成。"""

    plan_id, task_ids = create_test_plan(db_session)
    task_id = task_ids[0]

    state = run_agent_graph(
        user_input="把这个任务标记完成",
        plan_id=plan_id,
        task_id=task_id,
        db=db_session,
    )

    assert state["intent"] == "complete_task"
    assert state["final_answer"] is not None
    assert "已标记为完成" in state["final_answer"]

    # 重新从数据库读取，确认并非只修改了内存
    db_session.expire_all()
    saved_task = db_session.get(LearningTaskDB, task_id)

    assert saved_task is not None
    assert saved_task.completed is True


def test_completed_task_not_in_pending_tasks(
    db_session: Session,
):
    """已经完成的任务不应该继续出现在未完成任务列表中。"""

    plan_id, task_ids = create_test_plan(db_session)
    completed_task_id = task_ids[0]

    run_agent_graph(
        user_input="把这个任务标记完成",
        plan_id=plan_id,
        task_id=completed_task_id,
        db=db_session,
    )

    state = run_agent_graph(
        user_input="查询计划中未完成的任务",
        plan_id=plan_id,
        db=db_session,
    )

    assert state["final_answer"] is not None
    assert "学习 StateGraph" not in state["final_answer"]
    assert "实现工具调用" in state["final_answer"]


def test_agent_plan_not_found(db_session: Session):
    """计划不存在时，Agent 应该返回友好提示。"""

    state = run_agent_graph(
        user_input="查询计划的完整内容",
        plan_id=999,
        db=db_session,
    )

    assert state["intent"] == "get_plan"
    assert state["final_answer"] is not None
    assert "没有找到 ID 为 999 的学习计划" in state["final_answer"]


def test_agent_task_not_found(db_session: Session):
    """任务不存在时，Agent 应该返回友好提示。"""

    plan_id, task_ids = create_test_plan(db_session)

    state = run_agent_graph(
        user_input="把这个任务标记完成",
        plan_id=plan_id,
        task_id=999,
        db=db_session,
    )

    assert state["intent"] == "complete_task"
    assert state["final_answer"] is not None
    assert "没有找到 ID 为 999 的任务" in state["final_answer"]


def test_agent_unknown_intent(db_session: Session):
    """无法识别意图时，Agent 应该返回提示。"""

    state = run_agent_graph(
        user_input="今天天气怎么样",
        db=db_session,
    )

    assert state["intent"] == "unknown"
    assert state["final_answer"] == "抱歉，我暂时无法理解你的请求。"