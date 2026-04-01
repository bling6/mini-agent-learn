import json
import sys
from typing import Any
from openai import OpenAI
import os
from dotenv import load_dotenv
# from test_data import messages
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("BASE_URL"),
)

# 保留最近的工具调用结果数量
KEEP_RECENT = 10
# 不压缩结果的工具名称集合
RESERVE_RESULT_TOOLS = {"read_file"}
# 最小内容长度，低于此长度不压缩
MIN_CONTENT_LENGTH = 100

def tools_msg_compression(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    压缩工具调用结果消息，只保留最近的工具调用结果
    """
    # 筛选出所有工具调用结果消息
    tool_results = [msg for msg in messages if msg["role"] == "tool"]
    
    # 如果工具结果数量不超过保留数量，直接返回原消息
    if len(tool_results) <= KEEP_RECENT:
        return messages
    
    # 建立工具调用ID到工具名称的映射
    tool_name_map = {}
    for msg in messages:
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for tool_call in msg["tool_calls"]:
                tool_name_map[tool_call["id"]] = tool_call["function"]["name"]
    
    # 遍历除最近结果外的所有工具结果进行压缩
    for result in tool_results[:-KEEP_RECENT]:
        content = result.get("content", "")
        # 内容过短则跳过压缩
        if len(content) < MIN_CONTENT_LENGTH:
            continue
            
        # 获取工具调用ID对应的工具名称
        tool_id = result["tool_call_id"]
        tool_name = tool_name_map.get(tool_id, "unknown")
        
        # 如果是保留工具，跳过压缩
        if tool_name in RESERVE_RESULT_TOOLS:
            continue
            
        # 将内容压缩为简短描述
        result["content"] = f"[Previous: used {tool_name}]"
    
    return messages


def auto_compression(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    自动压缩消息，将所有消息通过LLM生成摘要进行压缩
    保留system消息
    """
    if len(messages) <= 30:
        return messages
    system_messages = messages[1]
    compact_messages = messages[1:-20]
    last_messages = messages[-20:]
    
    if not compact_messages:
        return messages
    
    conversation_text = json.dumps(compact_messages, default=str)
    
    summary_prompt = f"""请将以下对话历史压缩为简洁的摘要，保留关键信息：
        1. 用户的主要请求和目标
        2. 已完成的重要操作
        3. 当前状态和待处理事项
        4. 重要的上下文信息

        对话历史：
        {conversation_text}"""

    try:
        response = client.chat.completions.create(
            model="glm-5",
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=2000,
        )
        
        summary = response.choices[0].message.content or "对话历史摘要生成失败"
    except Exception as e:
        summary = f"[对话历史摘要生成失败: {str(e)}]"
    
    compressed_messages = [system_messages]
    compressed_messages.append({
        "role": "user",
        "content": f"[对话历史摘要]\n{summary}"
    })
    compressed_messages.extend(last_messages)
    print(compressed_messages)
    return compressed_messages

# auto_compression(messages)
