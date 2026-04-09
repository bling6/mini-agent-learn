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
    ):
        self.rounds_since_todo = 0
        self.messages = messages
        self.tools = tools
        self.permission = permission
        self.isSubAgent = isSubAgent

    def run(self):
        return self.agent_loop()

    def agent_loop(self):
        self.rounds_since_todo = 0
        while True:
            system_prompt = build_system_prompt()
            self.messages[0]["content"] = system_prompt
            print(f"\033[92m思考中...{'(子agent)' if self.isSubAgent else ''}\033[0m")
            # 压缩工具调用结果消息
            tools_msg_compression(self.messages)
            # 自动压缩消息
            if len(self.messages) > THRESHOLD:
                self.messages[:] = auto_compression(self.messages)
            response = client.chat.completions.create(
                model="glm-5",
                tools=self.tools,
                messages=self.messages,
                max_tokens=8000,
                stream=True,
            )

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
                        self.deal_tool_chunk(
                            delta, tool_calls_chunks, tool_call_printed
                        )
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

            if not tool_calls:
                return full_content

            self.tool_execute(tool_calls)

            print()

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
                            f"\n\033[33m🛠️ [调用工具] {tool_call_delta.function.name}\033[0m"
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
            tool_name = tool_call["function"]["name"]
            tool_call_id = tool_call["id"]
            args = json.loads(tool_call["function"]["arguments"])
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
            if tool_name == "task":
                from agents.sub_agent import run_subagent

                result = run_subagent(args["prompt"])
            elif tool_name == "compression":
                print("手动压缩")
                self.messages[:] = auto_compression(self.messages)
                result = "已压缩完成"
            elif tool_name not in TOOL_MAPPER:
                result = f"工具 {tool_name} 不存在"
            else:
                result = TOOL_MAPPER[tool_name](**args)
            out = result if len(result) < 500 else result[:500] + "\n... (输出已截断)"
            print("\033[32m 执行结果:\033[0m")
            print(f"\033[32m{out}\033[0m")
            self.messages.append(
                {"role": "tool", "tool_call_id": tool_call_id, "content": result[:8000]}
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
