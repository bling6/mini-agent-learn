# from agents.loop import agent_loop
from agents.agent import Agent
from agents.utils.skill_loader import SKILL_LOADER
from agents.utils.watch_skill import run_watch_skill, stop_watch_skill

import os
import sys


# 系统提示词
SYSTEM = f"""你是 {os.getcwd()} 的专业的 AI 程序员助手。

## 规则
你拥有以下可用技能：
{SKILL_LOADER.get_descriptions()}

## 注意事项：
- 你必须**先判断用户问题是否需要技能**：
   - 不需要技能 → 直接正常回答
   - 需要技能 → 必须按固定格式声明“加载技能”，再执行
- 仅查看技能时，不需要加载技能的具体内容，只要告知用户技能description即可，除非用户明确表示某个技能的具体内容
- 加载技能只能使用load_skill工具
- 只能操作当前工作目录下的所有文件和目录，包括子级
- 执行危险命令会被拒绝
- 文件操作支持 UTF-8 编码
- 使用uv包管理工具，如果uv命令不存在，请先安装uv包，需要使用者确认安装
- 回复内容不用过于详细
"""


def _print_welcome():
    """打印欢迎信息"""
    print("\033[94m" + "=" * 60 + "\033[0m")
    print("\033[92m🤖 AI 程序员助手\033[0m")
    print("\033[90m输入 'exit', 'quit', 'q' 或按 Ctrl+D 退出\033[0m")
    print("\033[90m输入 'clear' 清空对话历史\033[0m")
    print("\033[90m输入 'history' 查看对话历史\033[0m")
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
    _print_welcome()
    run_watch_skill()
    messages = [
        {"role": "system", "content": SYSTEM},
    ]
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

            messages.append(
                {"role": "user", "content": user_input},
            )
            Agent(messages).start()
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
    main()
