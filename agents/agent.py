from email import message
from agents.todo import todoList
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from agents.tools import PARENT_TOOLS, TOOL_MAPPER
from agents.utils.context_compression import tools_msg_compression, auto_compression
from agents.utils.Permission import PermissionManager
from agents.prompt import build_system_prompt
from agents.background_task import bgManager
from agents.utils.transcript import transcript_manager
from .teams import messageBus


load_dotenv()

# 压缩阈值，超过此长度压缩为摘要
THRESHOLD = 5000

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("BASE_URL"),
)


class Agent:
    def __init__(
        self,
        messages: list,
        permission: PermissionManager = None,
        tools: list = PARENT_TOOLS,
        isSubAgent: bool = False,
        system_prompt: str = "",
        teammateName: str = "",
    ):
        self.rounds_since_todo = 0
        self.messages = messages
        self.tools = tools
        self.permission = permission
        self.isSubAgent = isSubAgent
        self.system_prompt = system_prompt
        self.teammateName = teammateName
        self.agent_name = teammateName if teammateName else "lead"

    def run(self):
        return self.agent_loop()

    def save_all_messages(self):
        """保存消息到 transcript，只保存本轮新增的"""
        if not self.messages:
            return

        file_path = transcript_manager._get_file_path(self.agent_name)
        # 计算已有行数，只追加新增的消息
        existing = 0
        if file_path.exists():
            existing = len(file_path.read_text(encoding="utf-8").strip().splitlines())

        for msg in self.messages[existing:]:
            transcript_manager.save_message(self.agent_name, msg)

    def deal_inbox(self):
        inbox = messageBus.read_inbox(self.teammateName or "lead")
        if inbox:
            if self.teammateName:
                self.messages.append(
                    {
                        "role": "user",
                        "content": json.dumps(inbox, indent=2, ensure_ascii=False),
                    }
                )
            else:
                self.messages.append(
                    {
                        "role": "user",
                        "content": f"<inbox>{json.dumps(inbox, indent=2, ensure_ascii=False)}</inbox>",
                    }
                )
        elif self.teammateName:
            self.messages.append(
                {
                    "role": "user",
                    "content": "[]",
                }
            )

    def agent_loop(self):
        self.rounds_since_todo = 0
        try:
            while True:
                system_prompt = build_system_prompt(prefix=self.system_prompt)
                self.messages[0]["content"] = system_prompt
                notify_text = self.check_background()
                if notify_text:
                    self.messages.append(
                        {
                            "role": "user",
                            "content": f"<background-results>\n{notify_text}\n</background-results>",
                        }
                    )
                self.deal_inbox()
                print(
                    f"\033[92m思考中...{f'({self.teammateName})' if self.teammateName else ''}\033[0m"
                )
                # 压缩工具调用结果消息
                tools_msg_compression(self.messages)
                # 自动压缩消息
                if len(self.messages) > THRESHOLD:
                    self.messages[:] = auto_compression(self.messages)
                response = client.chat.completions.create(
                    model=os.getenv("MODEL"),
                    tools=self.tools,
                    messages=self.messages,
                    max_tokens=8000,
                )
                msg = response.choices[0].message
                if msg.reasoning_content:
                    print("\033[94m思考内容: \033[0m")
                    print(f"\033[90m {msg.reasoning_content}\033[0m")
                tool_calls = None
                if msg.tool_calls:
                    tool_calls = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                assistant_msg = {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": tool_calls,
                }
                self.messages.append(assistant_msg)
                full_content = msg.content
                if not msg.tool_calls:
                    print(full_content)
                    return full_content
                self.tool_execute(msg.tool_calls)

                print()
        finally:
            self.save_all_messages()

    def deal_tool_chunk(self, delta, tool_calls_chunks, tool_call_printed):
        for tool_call_delta in delta.tool_calls:
            index = tool_call_delta.index
            if index not in tool_calls_chunks:
                tool_calls_chunks[index] = {
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                }
            if tool_call_delta.id:
                tool_calls_chunks[index]["id"] = tool_call_delta.id
            if tool_call_delta.function:
                if tool_call_delta.function.name:
                    tool_calls_chunks[index]["function"]["name"] = (
                        tool_call_delta.function.name
                    )
                    if index not in tool_call_printed:
                        print(
                            f"\n\033[33m{self.teammateName}🛠️ [调用工具] {tool_call_delta.function.name}\033[0m"
                        )
                        print("\033[90m   参数: \033[0m", end="", flush=True)
                        tool_call_printed.add(index)
                if tool_call_delta.function.arguments:
                    tool_calls_chunks[index]["function"]["arguments"] += (
                        tool_call_delta.function.arguments
                    )
                    print(
                        tool_call_delta.function.arguments,
                        end="",
                        flush=True,
                    )

    def tool_execute(self, tool_calls: list):
        used_todo = False
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_call_id = tool_call.id
            args = json.loads(tool_call.function.arguments)
            print(f"\n\033[33m{self.teammateName}🛠️ [调用工具] {tool_name}\033[0m")
            print(f"\033[90m   参数:  \033[0m{args}")
            # 检查权限
            permission = self.check_permission(tool_name, args)
            if permission["result"] == "deny":
                print("\033[32m 执行结果:\033[0m")
                print(f"\033[32m{permission['reason']}\033[0m")
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": permission["reason"],
                    }
                )
                continue
            result = permission["result"]

            if tool_name == "todo":
                used_todo = True
            # subagent 调用
            if tool_name == "spawn_agent":
                from agents.sub_agent import run_subagent

                result = run_subagent(args["prompt"])
            elif tool_name == "compression":
                print("手动压缩")
                self.messages[:] = auto_compression(self.messages)
                result = "已压缩完成"
            elif tool_name == "send_message" and self.teammateName:
                result = messageBus.send(
                    self.teammateName,
                    args["to"],
                    args["content"],
                    args.get("msg_type", "message"),
                )
            elif tool_name == "read_inbox" and self.teammateName:
                result = json.dumps(
                    messageBus.read_inbox(self.teammateName),
                    indent=2,
                    ensure_ascii=False,
                )
            elif tool_name not in TOOL_MAPPER:
                result = f"工具 {tool_name} 不存在"
            else:
                result = TOOL_MAPPER[tool_name](**args)
            out = result if len(result) < 500 else result[:500] + "\n... (输出已截断)"
            print("\033[32m 执行结果:\033[0m")
            print(f"\033[32m{out}\033[0m")
            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result[:8000],
                }
            )
        if todoList.items:
            self.rounds_since_todo = 0 if used_todo else self.rounds_since_todo + 1
        # 超过三次未更新任务，需要提醒
        if self.rounds_since_todo >= 3:
            self.messages.append({"role": "user", "content": "记得更新任务列表"})

    def check_permission(self, tool_name: str, args: dict):
        if not self.permission:
            return {
                "result": "allow",
            }
        decision = self.permission.check(tool_name, args)
        if decision["behavior"] == "deny":
            return {
                "result": "deny",
                "reason": f"[拒绝执行] {decision['reason']}",
            }
        elif decision["behavior"] == "ask":
            if not self.permission.ask_user(tool_name, args):
                return {
                    "result": "deny",
                    "reason": "用户拒绝",
                }
        return {
            "result": "allow",
        }

    def check_background(self):
        notifies = bgManager.drain_notifications()
        if notifies and self.messages:
            notify_text = "\n".join(
                f"[bg:{n['task_id']}] {n['status']}: {n['preview']} "
                f"(output_file={n['output_file']})"
                for n in notifies
            )
            return notify_text
        return None

    def stream_response(self, response: str):
        content_chunks = []
        tool_calls_chunks = {}
        tool_call_printed = set()

        for chunk in response:
            # print(chunk)
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    print(delta.content, end="", flush=True)
                    content_chunks.append(delta.content)
                if delta.tool_calls:
                    self.deal_tool_chunk(delta, tool_calls_chunks, tool_call_printed)
        print()

        full_content = "".join(content_chunks) if content_chunks else ""

        tool_calls = None
        if tool_calls_chunks:
            tool_calls = []
            for index in sorted(tool_calls_chunks.keys()):
                chunk = tool_calls_chunks[index]
                tool_calls.append(
                    {
                        "id": chunk["id"],
                        "type": chunk["type"],
                        "function": {
                            "name": chunk["function"]["name"],
                            "arguments": chunk["function"]["arguments"],
                        },
                    }
                )

            self.messages.append(
                {
                    "role": "assistant",
                    "content": full_content,
                    "tool_calls": tool_calls,
                }
            )

        return {
            "content": full_content,
            "tool_calls": tool_calls,
        }
