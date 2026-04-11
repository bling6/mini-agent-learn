"""联网工具：搜索和抓取网页内容"""

import httpx
import html2text
from ddgs import DDGS


def web_search(query: str, max_results: int = 8) -> str:
    """使用 DuckDuckGo 搜索互联网，返回格式化结果。

    Args:
        query: 搜索关键词。
        max_results: 返回结果数量，默认8，最大15。

    Returns:
        格式化的搜索结果字符串（标题、URL、摘要）。
    """
    max_results = min(max(1, max_results), 15)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        return f"搜索失败: {e}"

    if not results:
        return "未找到相关结果"

    formatted = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "无标题")
        href = r.get("href", "")
        body = r.get("body", "")
        formatted.append(f"{i}. {title}\n   URL: {href}\n   {body}")

    return "\n\n".join(formatted)


def web_fetch(url: str, max_length: int = 8000) -> str:
    """获取指定 URL 的网页内容，转换为 Markdown 格式。

    Args:
        url: 要获取的网页 URL。
        max_length: 返回内容的最大长度，默认8000。

    Returns:
        网页内容（Markdown 或纯文本）。
    """
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AI-Coding-Assistant/1.0)",
                "Accept": "text/html,application/xhtml+xml,text/plain",
            },
        ) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException:
        return "请求超时 (30s)"
    except httpx.HTTPStatusError as e:
        return f"HTTP 错误: {e.response.status_code}"
    except Exception as e:
        return f"请求失败: {e}"

    content_type = response.headers.get("content-type", "")
    raw = response.text

    # 纯文本或 Markdown 直接返回
    if "text/plain" in content_type or "markdown" in content_type:
        return raw[:max_length]

    # HTML 转为 Markdown
    if "text/html" in content_type or raw.strip().startswith("<"):
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        h.ignore_emphasis = True
        h.skip_internal_links = True
        result = h.handle(raw)
        # 清理多余空白
        result = _clean_text(result)
        return result[:max_length]

    # 其他格式直接截断返回
    return raw[:max_length]


def _clean_text(text: str) -> str:
    """清理文本中的多余空白和换行"""
    lines = text.splitlines()
    # print(lines)
    cleaned = []
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            cleaned.append("")
        else:
            cleaned.append(stripped)
    result = " ".join(cleaned).strip()
    # 合并多余空格
    import re

    result = re.sub(r"[ \t]+", " ", result)
    return result
