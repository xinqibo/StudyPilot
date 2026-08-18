from app.llm import generate_learning_plan
from app.schemas import PlanRequest


def main() -> None:
    request = PlanRequest(
        goal="学习 LangGraph",
        current_level="了解 Python 和 FastAPI",
        duration_weeks=4,
        minutes_per_day=90,
    )

    plan = generate_learning_plan(request)

    print("对象类型：")
    print(type(plan))

    print("\n学习计划")
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()