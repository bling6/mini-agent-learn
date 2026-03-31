from agents.todo import todoList
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from agents.tools import TOOLS, TOOL_MAPPER

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


class Agent:
    def __init__(self, messages: list):
        self.rounds_since_todo = 0
        self.messages = messages

    def agent_loop(self):
        self.rounds_since_todo = 0
        while True:
            print("\033[92m思考中...\033[0m")
            response = client.chat.completions.create(
                model="deepseek-chat",
                tools=TOOLS,
                messages=self.messages,
                max_tokens=8000,
                stream=True,
            )

            content_chunks = []
            tool_calls_chunks = {}
            tool_call_printed = set()

            for chunk in response:
                delta = chunk.choices[0].delta

                if delta.content:
                    print(delta.content, end="", flush=True)
                    content_chunks.append(delta.content)

                if delta.tool_calls:
                    self.deal_tool_chunk(delta, tool_calls_chunks, tool_call_printed)
            print()

            full_content = "".join(content_chunks) if content_chunks else None

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
                return

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
            if tool_name == "todo":
                used_todo = True
            args = json.loads(tool_call["function"]["arguments"])
            tool_call_id = tool_call["id"]
            if tool_name not in TOOL_MAPPER:
                result = f"工具 {tool_name} 不存在"
            else:
                result = TOOL_MAPPER[tool_name](**args)
            out = result if len(result) < 500 else result[:500] + "\n... (输出已截断)"
            print("\033[32m 执行结果:\033[0m")
            print(f"\033[32m {out}\033[0m")
            self.messages.append(
                {"role": "tool", "tool_call_id": tool_call_id, "content": result}
            )
        if todoList.items:
            self.rounds_since_todo = 0 if used_todo else self.rounds_since_todo + 1
        # 超过三次未更新任务，需要提醒
        if self.rounds_since_todo >= 3:
            self.messages.append({"role": "user", "content": "记得更新任务列表"})
