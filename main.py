# from agents.loop import agent_loop
from agents.agent import Agent
from agents.utils.watch_skill import run_watch_skill, stop_watch_skill
from agents.utils.Permission import PermissionManager
from agents.utils.Memory import memory_manager


import os
import sys


def _print_welcome():
    """打印欢迎信息"""
    print("\033[94m" + "=" * 60 + "\033[0m")
    print("\033[92m🤖 AI 程序员助手\033[0m")
    print("\033[90m输入 'exit', 'quit', 'q' 或按 Ctrl+D 退出\033[0m")
    print("\033[90m输入 'clear' 清空对话历史\033[0m")
    print("\033[90m输入 'history' 查看对话历史\033[0m")
    print("\033[90m输入 'memories' 查看记忆历史\033[0m")
    print("\033[94m" + "=" * 60 + "\033[0m")
    print()


def _show_conversation_history(messages: list):
    """显示对话历史"""
    print("\033[94m" + "=" * 60 + "\033[0m")
    print("\033[92m📜 对话历史\033[0m")
    print("\033[94m" + "=" * 60 + "\033[0m")

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "system":
            print(
                f"\033[94m[{i}] 系统: \033[0m{content[:100]}{'...' if len(content) > 100 else ''}"
            )

        if role == "user":
            print(
                f"\033[95m[{i}] 用户: \033[0m{content[:100]}{'...' if len(content) > 100 else ''}"
            )
        elif role == "assistant":
            print(
                f"\033[92m[{i}] 助手: \033[0m{content[:100] if content else '[工具调用]'}{'...' if content and len(content) > 100 else ''}"
            )
        elif role == "tool":
            print(
                f"\033[90m[{i}] 工具: \033[0m{content[:100]}{'...' if len(content) > 100 else ''}"
            )

    print("\033[94m" + "=" * 60 + "\033[0m")
    print()
    print(messages)


def main():
    memory_manager.load_all()
    mem_count = len(memory_manager.memories)
    if mem_count:
        print(f"[{mem_count} 条记忆已加载]")
    messages = [
        {"role": "system", "content": ""},
    ]
    perms = PermissionManager()
    while True:
        try:
            user_input = input(">")
            if user_input.strip().lower() in ["exit", "quit", "q", ""]:
                stop_watch_skill()
                break
            if user_input.lower() == "clear":
                # 保留系统消息，清空其他消息
                messages = [messages[0]]
                print("\033[92m✅ 对话历史已清空\033[0m")
                continue

            if user_input.lower() == "history":
                _show_conversation_history(messages)
                continue
            if user_input.strip() == "memories":
                if memory_manager.memories:
                    for name, mem in memory_manager.memories.items():
                        print(f"  [{mem['type']}] {name}: {mem['description']}")
                else:
                    print("  (no memories)")
                continue

            messages.append(
                {"role": "user", "content": user_input},
            )
            Agent(messages=messages, permission=perms).run()
            # if out:
            #     print(out)
            print()

        except (EOFError, KeyboardInterrupt):
            stop_watch_skill()
            break

        except Exception as e:
            print(f"\033[91m[严重错误] 程序异常退出: {e}\033[0m")
            stop_watch_skill()
            sys.exit(1)
        # print(f"历史记录: {messages}")


if __name__ == "__main__":
    _print_welcome()
    run_watch_skill()
    main()
