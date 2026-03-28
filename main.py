from agents.loop import agent_loop
import os

SYSTEM = f"你是 {os.getcwd()} 的一名编码代理。可以使用 bash 命令。"


def main():
    messages = [
        {"role": "system", "content": SYSTEM},
    ]
    while True:
        try:
            user_input = input(">")
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.strip().lower() in ["exit", "quit", "q", ""]:
            break
        messages.append(
            {"role": "user", "content": user_input},
        )
        out = agent_loop(messages)
        if out:
            print(out)
        print()
        # print(f"历史记录: {messages}")


if __name__ == "__main__":
    main()
