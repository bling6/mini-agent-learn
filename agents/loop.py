# from langchain_openai import ChatOpenAI
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


def agent_loop(messages: list):
    # while True:
    response = client.chat.completions.create(
        model="deepseek-chat", tools=TOOLS, messages=messages, max_tokens=8000
    )
    messages.append(
        {"role": "assistant", "content": response.choices[0].message.content}
    )
    msg = response.choices[0].message
    messages.append({"role": "assistant", "content": msg.content})
    print(msg.content)
    # 如果没有 tool_calls，直接返回内容
    if not msg.tool_calls:
        return
    # 打印工具调用信息，方便我们观察

    for tool_call in msg.tool_calls:
        tool_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        print(f"\n\033[33m🛠️ [调用工具] {tool_name}\033[0m")
        print(
            f"\033[90m   参数: {json.dumps(args, ensure_ascii=False, indent=2)}\033[0m"
        )
        if tool_name not in TOOL_MAPPER:
            result = f"工具 {tool_name} 不存在"
        else:
            result = TOOL_MAPPER[tool_name](**args)
        out = result if len(result) < 500 else result[:500] + "\n... (输出已截断)"
        print(f"\033[32m   工具调用结果: {out}\033[0m")
        messages.append(
            {"role": "tool", "tool_call_id": tool_call.id, "content": result}
        )
