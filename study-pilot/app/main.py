import logging
import time
import uuid

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai.types.beta import responses
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

from fastapi import FastAPI,HTTPException,status

from app.schemas import AgentChatRequest,AgentChatResponse,LearningPlan,LearningTask,PlanRequest,TaskUpdate
from app.services import create_plan

from app.database import  Base,engine
from app import db_models

from app.agent_graph import run_agent_graph

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

from app.db_models import LearningPlanDB,LearningTaskDB

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.llm import generate_learning_plan

logger = logging.getLogger(__name__)

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

@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error":{
                "code":f"HTTP_{exc.status_code}",
                "message":exc.detail,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error":{
                "code":"VALIDATION_ERROR",
                "message":"请求参数校验失败",
                "details":jsonable_encoder(exc.errors()),
            }
        },
    )

@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception):
    logger.exception(
        "未处理异常：method=%s path=%s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error":{
                "code":"INTERNAL_SERVER_ERROR",
                "message":"服务器内部错误",
            }
        },
    )

@app.middleware("http")
async def log_request(request: Request, call_next):
    request_id = request.headers.get(
        "X-Request-ID",
        str(uuid.uuid4()),
    )
    start_time = time.perf_counter()

    response = await call_next(request)

    duration_ms = (
        time.perf_counter() - start_time
    )*1000

    response.headers["X-Request-ID"] = request_id

    logger.info(
        "%s %s -> %s | %.2f ms | request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )

    return response

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
    try:
        generated_plan = generate_learning_plan(request)
    except Exception :
        logger.exception(
            "大模型生成失败，改用本地模板生成学习计划"
        )

        generated_plan = create_plan(
            request=request,
            plan_id=0,
        )
        
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

@app.post(
    "/agent/chat",
    response_model=AgentChatResponse,
)
def chat_with_agent(
        request:AgentChatRequest,
        db:DatabaseSession,
) -> AgentChatResponse:
    """接收自然语言并执行 Agent 工作流。"""

    state = run_agent_graph(
        user_input=request.message,
        plan_id=request.plan_id,
        task_id=request.task_id,
        db=db,
    )

    return AgentChatResponse(
        intent=state["intent"],
        plan_id=state["plan_id"],
        task_id=state["task_id"],
        answer=(
            state["final_answer"]
            or "抱歉，Agent 没有生成有效回答。"
        ),
    )