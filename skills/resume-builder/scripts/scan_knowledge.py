#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库扫描模块 - 扫描 Obsidian 学习库/项目库，提取项目经历、技术栈、成果
输出结构化 JSON，供简历生成使用
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime


def load_config(config_path: str = None) -> dict:
    """加载扫描配置"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "scan_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_frontmatter(content: str) -> tuple:
    """解析 Markdown 的 YAML frontmatter，返回 (metadata_dict, body_text)"""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1].strip()
    body = parts[2].strip()

    metadata = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # 处理列表
            if value.startswith("[") and value.endswith("]"):
                value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
            metadata[key] = value

    return metadata, body


def extract_skills_from_text(text: str) -> list:
    """从文本中提取技术栈/技能关键词"""
    skills = set()

    # 常见技术栈模式
    tech_patterns = [
        r'\b(Python|Java|C\+\+|C#|JavaScript|TypeScript|Go|Rust|MATLAB|SQL)\b',
        r'\b(PyTorch|TensorFlow|Keras|OpenCV|Pandas|NumPy|Scikit-learn|matplotlib)\b',
        r'\b(YOLO|CNN|RNN|LSTM|Transformer|BERT|GAN|ResNet)\b',
        r'\b(Git|Docker|Linux|ROS|CMake|VSCode|Visual Studio)\b',
        r'\b(MySQL|PostgreSQL|MongoDB|Redis)\b',
        r'\b(Flask|Django|FastAPI|Spring|React|Vue)\b',
        r'\b(深度学习|机器学习|计算机视觉|自然语言处理|机器视觉|图像处理)\b',
        r'\b(神经网络|强化学习|迁移学习|目标检测|图像分割|特征提取)\b',
        r'\b(结构力学|材料力学|土力学|混凝土结构|钢结构|工程测量)\b',
        r'\b(AutoCAD|Revit|BIM|ANSYS|ABAQUS|SAP2000)\b',
        r'\b(RTK|GPS|全站仪|水准仪|经纬仪|Pix4D)\b',
    ]

    for pattern in tech_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            skills.add(m)

    # 从 frontmatter 的 tags 提取
    return sorted(list(skills))


def extract_project_info(filepath: str, content: str, metadata: dict) -> dict:
    """从单个文件中提取项目信息"""
    project = {
        "file": filepath,
        "name": metadata.get("project_name", "") or metadata.get("title", "") or os.path.basename(filepath).replace(".md", ""),
        "tags": metadata.get("tags", []),
        "status": metadata.get("status", ""),
        "tech_stack": [],
        "description": "",
        "achievements": [],
        "key_learnings": [],
        "raw_content_length": len(content),
    }

    # 提取技术栈
    project["tech_stack"] = extract_skills_from_text(content)

    # 从正文中提取各部分
    sections = re.split(r'^#{1,3}\s+', content, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section:
            continue

        first_line = section.split("\n")[0].strip()
        body = "\n".join(section.split("\n")[1:]).strip()

        # 项目简介
        if any(kw in first_line for kw in ["项目简介", "简介", "description", "项目描述"]):
            project["description"] = body[:500]

        # 成果/产出
        elif any(kw in first_line for kw in ["项目产出", "成果", "简历可用", "亮点", "产出", "achievement"]):
            # 提取列表项
            items = re.findall(r'^[-*]\s+(.+)$', body, re.MULTILINE)
            project["achievements"] = items if items else [body[:300]]

        # 技术点/学到什么
        elif any(kw in first_line for kw in ["核心技术", "学到什么", "技术点", "key", "技术栈"]):
            items = re.findall(r'^[-*]\s+(.+)$', body, re.MULTILINE)
            if items:
                project["key_learnings"] = items

    # 如果没有提取到描述，用正文前 300 字
    if not project["description"]:
        clean_text = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        clean_text = re.sub(r'---.*?---', '', clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        project["description"] = clean_text[:300]

    return project


def scan_vault(vault_path: str, config: dict) -> list:
    """扫描单个 vault，返回项目列表"""
    projects = []
    exclude = config.get("exclude_patterns", [])
    max_size = config.get("max_file_size_kb", 200) * 1024

    if not os.path.exists(vault_path):
        print(f"[扫描] 目录不存在，跳过: {vault_path}")
        return []

    for root, dirs, files in os.walk(vault_path):
        # 跳过排除目录
        dirs[:] = [d for d in dirs if not any(p in d for p in exclude)]

        for filename in files:
            if not filename.endswith(".md"):
                continue
            if any(p in filename for p in exclude):
                continue

            filepath = os.path.join(root, filename)

            # 跳过过大的文件
            if os.path.getsize(filepath) > max_size:
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                print(f"[扫描] 读取失败 {filepath}: {e}")
                continue

            metadata, body = parse_frontmatter(content)

            # 判断是否是项目笔记（有 project_name 或 tags 包含项目相关）
            tags = metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]

            is_project = (
                metadata.get("project_name") or
                any("项目" in str(t) for t in tags) or
                any("土木视觉" in str(t) for t in tags) or
                "项目库" in vault_path
            )

            if is_project or "项目库" in vault_path or "简历" in vault_path:
                project = extract_project_info(filepath, content, metadata)
                project["vault"] = os.path.basename(vault_path)
                projects.append(project)

    return projects


def scan_all(config_path: str = None) -> dict:
    """扫描所有配置的 vault，汇总结果"""
    config = load_config(config_path)
    base = config["obsidian_base"]
    vaults = config["scan_vaults"]

    all_projects = []
    all_skills = set()

    print(f"[扫描] 开始扫描 {len(vaults)} 个 vault...")
    for vault in vaults:
        vault_path = os.path.join(base, vault)
        print(f"[扫描] 扫描: {vault}")
        projects = scan_vault(vault_path, config)
        print(f"  → 找到 {len(projects)} 个项目/笔记")
        for p in projects:
            all_projects.append(p)
            for skill in p.get("tech_stack", []):
                all_skills.add(skill)

    # 汇总
    result = {
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "vaults_scanned": vaults,
        "total_projects": len(all_projects),
        "all_skills": sorted(list(all_skills)),
        "projects": all_projects,
    }

    print(f"\n[扫描] 完成！共 {len(all_projects)} 个项目，{len(all_skills)} 个技能关键词")
    return result


def main():
    parser = argparse.ArgumentParser(description="Obsidian 知识库扫描器")
    parser.add_argument("--config", "-c", help="配置文件路径", default=None)
    parser.add_argument("--output", "-o", help="输出 JSON 文件路径", default=None)
    parser.add_argument("--json", action="store_true", help="输出 JSON 到 stdout")
    args = parser.parse_args()

    result = scan_all(args.config)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[扫描] 结果已保存: {args.output}")

    if args.json or not args.output:
        # 输出精简版（不输出完整 projects）
        summary = {
            "scan_time": result["scan_time"],
            "total_projects": result["total_projects"],
            "all_skills": result["all_skills"],
            "projects": [{"name": p["name"], "tech_stack": p["tech_stack"][:10], "achievements_count": len(p["achievements"])} for p in result["projects"]],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
