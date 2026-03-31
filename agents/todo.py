class TodoManager:
    def __init__(self):
        self.items = []
    # 更新任务列表
    def update(self, items: list) -> str:
        if len(items) > 20:
            raise ValueError("最多只能更新20个任务")
        validated = []
        in_progress_count = 0
        for i, item in enumerate(items):
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).strip()
            item_id = str(item.get("id", str(i + 1)))
            if not text:
                raise ValueError(f"任务 {item_id} 文本不能为空")
            if status not in ["pending", "in_progress", "completed"]:
                raise ValueError(f"任务 {item_id} 无效状态:{status}")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item_id, "text": text, "status": status})
        if in_progress_count > 1:
            raise ValueError("最多只能有一个任务在进行中")
        self.items = validated
        return self.render()
    # 渲染任务列表
    def render(self) -> str:
        if not self.items:
            return "当前没有任务"
        lines = []
        for item in self.items:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[✅]"}[item["status"]]
            line = f"{marker} {item['id']}: {item['text']}"
            lines.append(line)
        done_count = sum(1 for item in self.items if item["status"] == "completed")
        lines.append(f"已完成 {done_count}/{len(self.items)} 个任务")
        # 所有任务都已完成，清空列表
        if done_count == len(self.items):
            self.items = []
        return "\n".join(lines)

todoList = TodoManager()