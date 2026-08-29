from pydantic import  BaseModel,Field
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal


class PlanRequest(BaseModel):
        goal: str=Field(min_length=2,max_length=100)
        current_level: str=Field(min_length=2,max_length=200)
        duration_weeks: int = Field(ge=1,le=24)
        minutes_per_day: int = Field(ge=15,le=480)

class TaskUpdate(BaseModel):
    completed:bool

class LearningTask(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    title: str
    description: str
    estimated_minutes: int =Field(gt=0,le=480)
    acceptance_criteria: list[str]
    completed:bool = False

class LearningPlan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    goal:str
    current_level:str
    duration_weeks:int
    minutes_per_day: int
    weekly_objectives: list[str]
    tasks: list[LearningTask]

class GeneratedTask(BaseModel):
    title: str = Field(min_length=2,max_length=100)
    description: str = Field(min_length=2,max_length=500)
    estimated_minutes: int = Field(gt=15,le=480)
    acceptance_criteria: list[str]= Field(min_length=1)


class GeneratedPlan(BaseModel):
    weekly_objectives: list[str]= Field(min_length=1)
    tasks: list[GeneratedTask] = Field(min_length=1)

class AgentChatRequest(BaseModel):
    """Agent 对话请求"""

    message: str = Field(min_length=1,max_length=500)

    #可选：文本没有包含 ID 时可以手动提供
    plan_id: int| None =Field(
        default=None,
        ge=1,
    )

    task_id : int | None = Field(
        default=None,
        ge=1,
    )

class AgentChatResponse(BaseModel):
    """Agent 对话响应。"""

    intent :Literal[
        "get_plan",
        "get_pending_tasks",
        "complete_task",
        "unknown",
    ]

    plan_id: int | None
    task_id: int | None
    answer: str