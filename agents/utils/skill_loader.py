from pathlib import Path
import re
import yaml

WORKDIR = Path.cwd()
SKILL_DIR = WORKDIR / "skills"


class SkillLoader:
    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.skills = {}
        self.load_all()
    
    def load_all(self):
        """加载技能"""
        if not self.skill_dir.exists():
            return
        for f in sorted(self.skill_dir.rglob("SKILL.md")):
            text = f.read_text()
            meta, content = self.skill_parse(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {
                "meta": meta,
                "content": content,
            }
       
    def skill_parse(self, text: str):
        """解析技能文本"""
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}, text
        content = match.group(2).strip()
        return meta, content

    def get_descriptions(self):
        """获取技能描述"""
        if not self.skills:
            return "没有技能"
        descriptions = []
        for name, skill in self.skills.items():
            description = skill["meta"].get("description", "")
            if description:
                descriptions.append(f" - {name}: {description}")
        return "\n".join(descriptions)
    
    def get_content(self, name: str):
        """获取技能内容"""
        skill = self.skills.get(name)
        if not skill:
            return f"技能 {name} 不存在。有效技能：{','.join(self.skills.keys())}"
        return f"<skill name=\"{name}\" >\n{skill['content']}\n</skill>"


SKILL_LOADER = SkillLoader(SKILL_DIR)