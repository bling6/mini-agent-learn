from .BashSecurityValidator import bash_validator
import json
from fnmatch import fnmatch

MODES = ("default", "plan", "auto")
DEFAULT_RULES = [
    # Always deny dangerous patterns
    {"tool": "bash", "content": "rm -rf /", "behavior": "deny"},
    {"tool": "bash", "content": "sudo *", "behavior": "deny"},
    # Allow reading anything
    {"tool": "read_file", "path": "*", "behavior": "allow"},
    {"tool": "save_memory", "behavior": "allow"},
]


class PermissionManager:
    def __init__(self, mode: str = "default", rules: list = None):
        # if mode not in MODES:
        #     raise ValueError(f"Unknown mode: {mode}. Choose from {MODES}")
        # self.mode = mode
        self.rules = rules or list(DEFAULT_RULES)
        # 请求系统不允许的操作。
        # self.consecutive_denials = 0
        # self.max_consecutive_denials = 3

    def check(self, tool_name: str, tool_input: str):
        if tool_name == "bash":
            command = tool_input.get("command", "")
            failures = bash_validator.validate(command)
            if failures:
                severe_hits = [name for name in failures if name in {"sudo", "rm_rf"}]
                if severe_hits:
                    des = bash_validator.describe_failures(command)
                    return {
                        "behavior": "deny",
                        "reason": f"{des}",
                    }
                desc = bash_validator.describe_failures(command)
                return {"behavior": "allow", "reason": f"{desc}"}
        # 检查规则
        for rule in self.rules:
            match_rule = self._matches(rule, tool_name, tool_input)
            if match_rule:
                if match_rule["behavior"] == "deny":
                    return {"behavior": "deny", "reason": f"deny rule: {match_rule}"}
                if match_rule["behavior"] == "allow":
                    self.consecutive_denials = 0
                    return {"behavior": "allow", "reason": f"allow rule: {match_rule}"}
        return {
            "behavior": "ask",
            "reason": f"未匹配到规则: {tool_name}, 询问用户",
        }

    def ask_user(self, tool_name: str, tool_input: dict) -> bool:
        """询问用户是否允许"""
        preview = json.dumps(tool_input, ensure_ascii=False)[:200]
        print(f"\n  [Permission] {tool_name}: {preview}")
        try:
            answer = input("是否允许？ (y/n/always): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False

        if answer == "always":
            # 为该工具添加永久允许规则
            self.rules.append({"tool": tool_name, "path": "*", "behavior": "allow"})
            return True
        if answer in ("y", "yes"):
            return True

        return False

    def _matches(self, rule: dict, tool_name: str, tool_input: dict) -> dict | None:
        """Check if a rule matches the tool call."""
        # Tool name match
        if rule.get("tool") and rule["tool"] != "*":
            if rule["tool"] != tool_name:
                return None
        # Path pattern match
        if "path" in rule and rule["path"] != "*":
            path = tool_input.get("path", "")
            if not fnmatch(path, rule["path"]):
                return None
        # Content pattern match (for bash commands)
        if "content" in rule:
            command = tool_input.get("command", "")
            if not fnmatch(command, rule["content"]):
                return None
        return rule
