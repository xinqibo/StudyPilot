from pydantic import  BaseModel,Field
from pydantic import BaseModel,ConfigDict

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
