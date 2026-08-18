from fastapi import FastAPI,HTTPException,status

from app.schemas import LearningPlan,LearningTask,PlanRequest,TaskUpdate
from app.services import create_plan

from app.database import  Base,engine
from app import db_models

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

from app.db_models import LearningPlanDB,LearningTaskDB

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.llm import generate_learning_plan

Base.metadata.create_all(bind=engine)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]

app=FastAPI(
    title='StudyPilot API',
    description='AI学习规划与任务执行Agent',
    version='0.2.0',
)

plans: dict[int,LearningPlan] = {}
@app.get("/")
async def home():
    return {"message":"StudyPilot is running"}

@app.post("/plans",response_model=LearningPlan,status_code=status.HTTP_201_CREATED)
def generate_plan(request:PlanRequest,db:DatabaseSession):
    # generated_plan = create_plan(
    #     request=request,
    #     plan_id=0,
    # )

    generated_plan = generate_learning_plan(request)

    db_plan = LearningPlanDB(
        goal=request.goal,
        current_level=request.current_level,
        duration_weeks=request.duration_weeks,
        minutes_per_day=request.minutes_per_day,
        weekly_objectives=generated_plan.weekly_objectives,
    )

    for task in generated_plan.tasks:
        db_task = LearningTaskDB(
            title=task.title,
            description=task.description,
            estimated_minutes=task.estimated_minutes,
            acceptance_criteria=task.acceptance_criteria,
            completed=False,
        )

        db_plan.tasks.append(db_task)

    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)

    return LearningPlan.model_validate(db_plan)

@app.get(
    "/plans",
    response_model=list[LearningPlan],
)
def list_plans(db:DatabaseSession):
    statement = (
        select(LearningPlanDB)
        .options(
            selectinload(LearningPlanDB.tasks),
        )
        .order_by(LearningPlanDB.id)
    )

    db_plans = db.scalars(statement).all()
    return [
        LearningPlan.model_validate(plan)
        for plan in db_plans
    ]

@app.get("/plans/{plan_id}",response_model=LearningPlan)
def get_plan(plan_id:int,db:DatabaseSession):
    statement = (
        select(LearningPlanDB)
        .options(
            selectinload(LearningPlanDB.tasks),
        )
        .where(LearningPlanDB.id == plan_id)
    )

    plan = db.scalar(statement)

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    return LearningPlan.model_validate(plan)

@app.patch(
    "/plans/{plan_id}/tasks/{task_id}",
    response_model=LearningTask,
)
def update_task(
        plan_id:int,
        task_id:int,
        update:TaskUpdate,
        db:DatabaseSession,
):
    plan = db.get(LearningPlanDB, plan_id)

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )
    statement = select(LearningTaskDB).where(
        LearningTaskDB.id == task_id,
        LearningTaskDB.plan_id == plan_id,
    )

    task = db.scalar(statement)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task.completed = update.completed

    db.commit()
    db.refresh(task)

    return LearningTask.model_validate(task)