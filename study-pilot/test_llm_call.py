from app.llm import generate_text

def main() -> None:
    answer = generate_text(
        "请用三句话介绍学习 FastAPI 的好处"
    )
    print("大模型返回结果：")
    print(answer)

if __name__ == "__main__":
    main()