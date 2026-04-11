# from agents.loop import agent_loop
from agents.agent import Agent
from agents.utils.watch_skill import run_watch_skill, stop_watch_skill
from agents.utils.Permission import PermissionManager
from agents.utils.Memory import memory_manager
from agents.utils.transcript import transcript_manager


import os
import sys

INIT_PROMPT = """Please analyze this codebase and create a CLAUDE.md file, which will be given to future instances of Claude Code to operate in this repository.\n\nWhat to add:\n1. Commands that will be commonly used, such as how to build, lint, and run tests. Include the necessary commands to develop in this codebase, such as how to run a single test.\n2. High-level code architecture and structure so that future instances can be productive more quickly. Focus on the \"big picture\" architecture that requires reading multiple files to understand.\n\nUsage notes:\n- If there's already a CLAUDE.md, suggest improvements to it.\n- When you make the initial CLAUDE.md, do not repeat yourself and do not include obvious instructions like \"Provide helpful error messages to users\", \"Write unit tests for all new utilities\", \"Never include sensitive information (API keys, tokens) in code or commits\".\n- Avoid listing every component or file structure that can be easily discovered.\n- Don't include generic development practices.\n- If there are Cursor rules (in .cursor/rules/ or .cursorrules) or Copilot rules (in .github/copilot-instructions.md), make sure to include the important parts.\n- If there is a README.md, make sure to include the important parts.\n- Do not make up information such as \"Common Development Tasks\", \"Tips for Development\", \"Support and Documentation\" unless this is expressly included in other files that you read.\n- Be sure to prefix the file with the following text:\n\n```\n# CLAUDE.md\n\nThis file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.\n```"""


def _print_welcome():
    """打印欢迎信息"""
    print("\033[94m" + "=" * 60 + "\033[0m")
    print("\033[92m🤖 AI 程序员助手\033[0m")
    print("\033[90m输入 'exit', 'quit', 'q' 或按 Ctrl+C 退出\033[0m")
    print("\033[90m输入 'clear' 清空对话历史\033[0m")
    print("\033[90m输入 'history' 查看对话历史\033[0m")
    print("\033[90m输入 'memories' 查看记忆历史\033[0m")
    print("\033[90m输入 'restore' 恢复历史对话\033[0m")
    # print("\033[90m输入 '/init' 初始化助手\033[0m")
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


def _restore_session(messages: list) -> list:
    """恢复历史会话，返回恢复后的消息列表"""
    sessions = transcript_manager.list_sessions()
    if not sessions:
        print("\033[93m没有可用的历史对话\033[0m")
        return messages

    print("\033[94m可用的历史会话:\033[0m")
    for i, session in enumerate(sessions, 1):
        agents_str = ", ".join(session["agents"])
        print(
            f"  [{i}] {session['session_id']} - {session['message_count']} 条消息 (agents: {agents_str})"
        )

    try:
        choice = input("\033[90m选择要恢复的会话编号 (按回车取消): \033[0m")
        if not choice.strip():
            return messages

        idx = int(choice) - 1
        if idx < 0 or idx >= len(sessions):
            print("\033[91m❌ 无效的编号\033[0m")
            return messages

        selected = sessions[idx]
        # 优先加载 lead agent 的消息
        lead_file = None
        for f in selected["files"]:
            if f.endswith("_lead") or f == "lead":
                lead_file = f
                break
        file_stem = lead_file or selected["files"][0]
        restored = transcript_manager.load_messages_by_file(file_stem)
        # 开启新 session，避免恢复的历史叠加到旧文件
        transcript_manager.new_session()
        print(
            f"\033[92m✅ 已恢复会话 '{selected['session_id']}' 的 {len(restored)} 条消息\033[0m"
        )
        return restored
    except (ValueError, KeyboardInterrupt):
        print("\033[90m已取消\033[0m")
        return messages


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
            if user_input.lower() == "restore":
                messages = _restore_session(messages)
                continue
            # if user_input.strip() == "/init":
            #     messages.append(
            #         {"role": "user", "content": INIT_PROMPT},
            #     )
            # else:
            messages.append(
                {"role": "user", "content": user_input},
            )
            transcript_manager.save_message("lead", messages[-1])
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
