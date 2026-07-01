import os
import yaml
from typing import Optional


class SkillsLoader:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        if content.startswith("---\n"):
            end_index = content.find("\n---\n", 4)
            if end_index != -1:
                yaml_content = content[4:end_index]
                metadata = yaml.safe_load(yaml_content) if yaml_content.strip() else {}
                body = content[end_index + 5:]
                return (metadata, body)
        return ({}, content)

    def build_skills_summary(self) -> str:
        if not os.path.isdir(self.skills_dir):
            return ""
        
        skills_list = []
        for item in os.listdir(self.skills_dir):
            item_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(item_path):
                skill_file = os.path.join(item_path, "SKILL.md")
                if os.path.isfile(skill_file):
                    with open(skill_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    metadata, _ = self._parse_frontmatter(content)
                    name = metadata.get("name", item)
                    description = metadata.get("description", "")
                    rel_path = os.path.join(item, "SKILL.md")
                    skills_list.append(f"- {name} ({rel_path})：{description}")
        
        if not skills_list:
            return ""
        
        header = "**可用技能：**\n"
        return header + "\n".join(skills_list)

    def load_skill(self, name: str) -> Optional[str]:
        skill_dir = os.path.join(self.skills_dir, name)
        if not os.path.isdir(skill_dir):
            return None
        
        skill_file = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_file):
            return None
        
        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        _, body = self._parse_frontmatter(content)
        return body

    def list_skills(self) -> list[dict]:
        skills = []
        if not os.path.isdir(self.skills_dir):
            return skills
        
        for item in os.listdir(self.skills_dir):
            item_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(item_path):
                skill_file = os.path.join(item_path, "SKILL.md")
                if os.path.isfile(skill_file):
                    with open(skill_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    metadata, _ = self._parse_frontmatter(content)
                    skills.append({
                        "name": metadata.get("name", item),
                        "description": metadata.get("description", ""),
                        "path": os.path.join(item, "SKILL.md")
                    })
        
        return skills
