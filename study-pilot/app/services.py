from app.schemas import LearningPlan,LearningTask,PlanRequest

def create_plan(
        request:PlanRequest,
        plan_id:int,
)-> LearningPlan:
    weekly_objectives :list[str] = []
    tasks: list[LearningTask] = []
    for week in range(1,request.duration_weeks+1):
        weekly_objectives.append(
            f"第{week}周：学习并实践 {request.goal}"
        )
        tasks.append(LearningTask(
            id=week,
            title=f"第{week}周学习任务",
            description=(
                f"根据“{request.current_level}”的基础，"
                f"继续学习{request.goal}"
            ),
            estimated_minutes=request.minutes_per_day,
            acceptance_criteria=[
                "完成本周学习任务",
                "整理一篇学习笔记",
                "完成至少一个代码练习",
            ],
        )
    )
    return LearningPlan(
        id=plan_id,
        goal=request.goal,
        current_level=request.current_level,
        duration_weeks=request.duration_weeks,
        minutes_per_day=request.minutes_per_day,
        weekly_objectives=weekly_objectives,
        tasks=tasks,
    )