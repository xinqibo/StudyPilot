from sqlalchemy import select
from sqlalchemy.orm import Session,selectinload

from app.agent import AgentState
from app.db_models import LearningPlanDB,LearningTaskDB


def get_pending_tasks_tool(
        state: AgentState,
        db: Session,
)->AgentState:
    """查询指定计划中所有未完成的任务"""

    new_state = state.copy()
    plan_id = state["plan_id"]

    if plan_id is None:
        new_state["tool_result"]=(
            "无法查询任务，没有提供计划 ID。"
        )
        return new_state

    plan = db.get(LearningPlanDB, plan_id)

    if plan is None:
        new_state["tool_result"]=(
            f"没有找到 ID 为 {plan_id} 的学习计划。"
        )
        return new_state

    statement = (
        select(LearningTaskDB)
        .where(
            LearningTaskDB.plan_id == plan_id,
            LearningTaskDB.completed.is_(False),
        )
        .order_by(LearningTaskDB.id)
    )

    pending_tasks = db.scalars(statement).all()

    if not pending_tasks:
        new_state["tool_result"]=(
            f"计划 {plan_id} 中没有未完成的任务。"
        )
        return new_state

    task_lines = [
        (
            f"任务 {task.id}：{task.title}，"
            f"预计需要 {task.estimated_minutes} 分钟"
        )
        for task in pending_tasks
    ]

    new_state["tool_result"]="\n".join(task_lines)

    return new_state

def get_plan_tool(
        state: AgentState,
        db: Session,
) -> AgentState:
    """查询指定学习计划及其全部任务"""

    new_state = state.copy()
    plan_id = state["plan_id"]

    if plan_id is None:
        new_state["tool_result"]=(
            "无法查询计划：没有提供计划ID。"
        )
        return new_state

    statement = (
        select(LearningPlanDB)
        .options(
            selectinload(LearningPlanDB.tasks)
        )
        .where(LearningPlanDB.id == plan_id)
    )

    plan = db.scalar(statement)

    if plan is None:
        new_state["tool_result"]=(
            f"没有找到 ID 为 {plan_id} 的学习计划。"
        )
        return new_state

    task_lines = []

    for task in plan.tasks:
        status_text = (
            "已完成"
            if task.completed
            else "未完成"
        )

        task_lines.append(
            (f"任务 {task.id}：{task.title}，"
            f"状态：{status_text}，"
            f"预计需要 {task.estimated_minutes} 分钟"
             )
        )

    if task_lines:
        tasks_text = "\n".join(task_lines)
    else:
        tasks_text = "该计划暂时没有学习任务。"

    new_state["tool_result"] = (
        f"计划 {plan_id}：{plan.goal}\n"
        f"当前基础：{plan.current_level}\n"
        f"学习周期：{plan.duration_weeks}周\n"
        f"每天学习：{plan.minutes_per_day}分钟\n"
        f"任务列表：\n{tasks_text}"
    )
   
    return new_state

def complete_task_tool(
        state: AgentState,
        db: Session,
) -> AgentState:
    """将指定计划中的指定任务标记为完成。"""

    new_state = state.copy()

    plan_id = state["plan_id"]
    task_id = state["task_id"]

    #1.检查参数
    if plan_id is None:
        new_state["tool_result"]=(
            "无法完成任务：没有提供计划ID。"
        )
        return new_state

    if task_id is None:
        new_state["tool_result"]=(
            "无法完成任务：没有提供任务ID。"
        )
        return new_state

    #2.查询任务
    task = db.get(LearningTaskDB, task_id)

    if task is None:
        new_state["tool_result"]=(
            f"没有找到 ID 为 {task_id} 的任务。"
        )
        return new_state

    #3.检查任务是否属于指定计划
    if task.plan_id != plan_id:
        new_state["tool_result"]=(
            f"任务 {task_id} 不属于计划 {plan_id}。"
        )
        return new_state

    #4.防止重复完成
    if task.completed:
        new_state["tool_result"]=(
            f"任务 {task_id}“{task.title}”已经是完成状态。"
        )
        return new_state

    #5.修改并保存到数据库
    task.completed = True

    try:
        db.commit()
        db.refresh(task)
    except Exception:
        db.rollback()
        raise

    #6.返回工具执行结果
    new_state["tool_result"]=(
        f"任务 {task.id}“{task.title}”已标记为完成。"
    )

    return new_state