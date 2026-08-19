
from app.schemas import  (
    GeneratedPlan,
    GeneratedTask,
    PlanRequest,
)
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session,sessionmaker
from sqlalchemy.pool import StaticPool


from app import db_models
from app.database import Base,get_db
from app.main import app

test_engine = create_engine(
    "sqlite://",
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)

def override_get_db() -> Generator[Session,None,None]:
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def create_test_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)
@pytest.fixture(autouse=True)
def mock_generate_learning_plan(monkeypatch):

    def fake_generate_learning_plan(
            request: PlanRequest,
    ) -> GeneratedPlan:
        weekly_objectives = [
            f"第{week}周：学习并实践{request.goal}"
            for week in range(1,request.duration_weeks+1)
        ]

        tasks = [
            GeneratedTask(
                title=f"第{week}周学习任务",
                description=(
                    f"根据“{request.current_level}”的基础，"
                    f"继续学习和实践 {request.goal}"
                ),
                estimated_minutes=min(
                    60,
                    request.minutes_per_day,
                ),
                acceptance_criteria=[
                    "完成本周学习任务",
                    "整理一篇学习笔记",
                    "完成至少一个代码练习",
                ],
            )
            for week in range(1,request.duration_weeks+1)
        ]

        return GeneratedPlan(
            weekly_objectives=weekly_objectives,
            tasks=tasks,
        )

    monkeypatch.setattr(
        "app.main.generate_learning_plan",
        fake_generate_learning_plan,
    )