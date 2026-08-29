import json
from collections import defaultdict
from pathlib import Path

from annotated_types.test_cases import cases
from unicodedata import category

from app.agent_graph import run_agent_graph
from app.database import SessionLocal

CASES_PATH = Path(__file__).with_name("agent_cases.json")


def evaluate_case(case: dict,state: dict) -> list[str]:
    errors = []

    if state["intent"] != case["expected_intent"]:
        errors.append(
            f"intent 预期 {case['expected_intent']}，"
            f"实际 {state['intent']}"
        )

    if state["plan_id"] != case["expected_plan_id"]:
        errors.append(
            f"plan_id 预期 {case['expected_plan_id']}，"
            f"实际 {state['plan_id']}"
        )

    if  state["task_id"] != case["expected_task_id"]:
        errors.append(
            f"task_id 预期 {case['expected_task_id']}，"
            f"实际 {state['task_id']}"
        )

    answer = state["final_answer"] or ""

    for keyword in case["expected_keywords"]:
        if keyword not in answer:
            errors.append(f"回答中缺少关键词：{keyword}")
    return errors


def main() -> None:

    cases=json.loads(CASES_PATH.read_text(encoding="utf-8"))

    passed=0
    category_results = defaultdict(lambda:{"passed":0,"total":0,})
    db = SessionLocal()

    try:
        for case in cases :
            state = run_agent_graph(
                user_input=case["message"],
                plan_id=None,
                task_id=None,
                db=db,
             )

            errors = evaluate_case(case, state)
            category = case["category"]
            category_results[category]["total"]+=1

            if not errors:
                passed+=1
                category_results[category]["passed"]+=1
                print(f"PASS {case['name']}")
            else:
                print(f"ERROR {case['name']}")

                for error in errors:
                    print(f"    -{error}")
    finally:
        db.close()

    total = len(cases)
    accuracy = passed / total if total else 0

    print("\n评测结果")
    print(f"总通过率：{passed}/{total} = {accuracy:.1%}")

    for category,result in category_results.items():
        category_accuracy = result["passed"] / result["total"] if result["total"] else 0
        print(
            f"{category}：{result['passed']}/{result['total']}"
            f"= {category_accuracy:.1%}"
        )

if __name__ == "__main__":
    main()
