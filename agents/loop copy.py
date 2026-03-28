from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.moonshot.cn/v1",
)

SYSTEM = f"你是 {os.getcwd()} 的一名编码代理。可以使用 bash 命令。"

agent = create_agent(
    model="kimi-k2.5",
    tools=[],
    system_prompt=SYSTEM,
)


def agent_loop(messages: list):
    # while True:
    response = agent.invoke({
        messages
    })
    messages.append(
        {"role": "assistant", "content": response.content}
    )
    print(response.content)
