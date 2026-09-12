#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
entity_builder.py - 实体层构建：人物/书籍/工具/组织的跨主题关联页
每个实体一个页面，包含：基本信息 → 跨主题出现位置 → 关联概念 → 学习/使用建议
用法:
  python entity_builder.py --vault "E:\obsidian\rein"
"""
import os, re, json, argparse
from datetime import datetime

VAULT_BASE = r"E:\obsidian\rein"
ENTITY_DIR = os.path.join(VAULT_BASE, "_概念层", "entities")

# 核心实体元数据
ENTITIES = {
    # ===== 人物 =====
    "武忠祥": {
        "type": "人物", "category": "考研数学老师",
        "description": "考研数学辅导名师，主讲高等数学。以严谨细致、重视基础著称，《高等数学辅导讲义》《数学复习全书》作者。",
        "related_concepts": ["极限与连续", "导数与微分", "积分", "微分方程", "级数", "多元函数微积分"],
        "related_entities": ["李永乐", "汤家凤"],
    },
    "李永乐": {
        "type": "人物", "category": "考研线代老师",
        "description": "考研数学辅导名师，主讲线性代数。《线性代数辅导讲义》作者，以条理清晰、重点突出著称。",
        "related_concepts": ["矩阵", "行列式", "向量", "特征值与特征向量", "线性方程组", "二次型"],
        "related_entities": ["武忠祥", "汤家凤"],
    },
    "汤家凤": {
        "type": "人物", "category": "考研数学老师",
        "description": "考研数学辅导名师，主讲高等数学和概率论。《概率论与数理统计辅导讲义》作者。",
        "related_concepts": ["概率论基础", "分布与期望", "数理统计", "极限与连续", "导数与微分"],
        "related_entities": ["武忠祥", "李永乐"],
    },
    "胡寿松": {
        "type": "人物", "category": "控制工程学者",
        "description": "《自动控制原理》教材作者，南京航空航天大学教授。其教材是国内控制工程专业最常用的经典教材之一。",
        "related_concepts": ["传递函数", "状态空间", "根轨迹", "PID控制", "频率响应", "稳定性分析", "伯德图", "奈奎斯特判据", "反馈控制", "拉普拉斯变换"],
        "related_entities": [],
    },
    "3Blue1Brown": {
        "type": "人物", "category": "科普博主",
        "description": "YouTube/B站知名数学科普博主，Grant Sanderson。以动画可视化讲解线性代数、微积分、神经网络等数学概念，《线性代数的本质》《微积分的本质》《神经网络》系列视频作者。",
        "related_concepts": ["向量", "矩阵", "线性变换", "行列式", "特征值与特征向量", "神经网络", "梯度下降", "导数与微分"],
        "related_entities": [],
    },
    "唐昕月": {
        "type": "人物", "category": "英语老师",
        "description": "英语六级词汇辅导老师，主讲六级词汇串讲。",
        "related_concepts": ["英语词汇", "英语阅读", "英语写作"],
        "related_entities": [],
    },

    # ===== 书籍 =====
    "武忠祥高数基础篇": {
        "type": "书籍", "category": "考研教材",
        "description": "武忠祥高等数学辅导讲义（基础篇），考研数学一轮复习核心教材。",
        "related_concepts": ["极限与连续", "导数与微分", "积分", "微分方程", "级数", "多元函数微积分"],
        "location": "考研数学/99-教材原文/武忠祥高数基础篇/",
    },
    "武忠祥高数强化篇": {
        "type": "书籍", "category": "考研教材",
        "description": "武忠祥高等数学辅导讲义（强化篇），考研数学二轮复习核心教材。",
        "related_concepts": ["导数与微分", "积分", "微分方程", "级数", "多元函数微积分"],
        "location": "考研数学/99-教材原文/武忠祥高数强化篇/",
    },
    "李永乐线代辅导讲义": {
        "type": "书籍", "category": "考研教材",
        "description": "李永乐线性代数辅导讲义，考研数学线代部分核心教材。",
        "related_concepts": ["矩阵", "行列式", "向量", "特征值与特征向量", "线性方程组", "二次型", "逆矩阵与秩"],
        "location": "考研数学/99-教材原文/李永乐线代辅导讲义/",
    },
    "汤家凤概率辅导讲义": {
        "type": "书籍", "category": "考研教材",
        "description": "汤家凤概率论与数理统计辅导讲义，考研数学概率部分核心教材。",
        "related_concepts": ["概率论基础", "分布与期望", "数理统计"],
        "location": "考研数学/99-教材原文/汤家凤概率辅导讲义/",
    },
    "胡寿松自动控制原理": {
        "type": "书籍", "category": "控制工程教材",
        "description": "胡寿松《自动控制原理》，国内控制工程专业最常用的经典教材，覆盖经典控制理论和现代控制理论。",
        "related_concepts": ["传递函数", "状态空间", "根轨迹", "PID控制", "频率响应", "稳定性分析", "伯德图", "奈奎斯特判据", "反馈控制"],
        "location": "自动控制原理/",
    },

    # ===== 工具 =====
    "OpenCV": {
        "type": "工具", "category": "计算机视觉库",
        "description": "开源计算机视觉库，支持图像处理、特征检测、目标识别、视频分析等。C++/Python接口，机器视觉方向核心工具。",
        "related_concepts": ["机器视觉", "卷积神经网络", "神经网络"],
        "related_entities": ["PyTorch"],
    },
    "PyTorch": {
        "type": "工具", "category": "深度学习框架",
        "description": "Facebook开源的深度学习框架，动态计算图，Python优先，是目前学术研究和工业界最流行的深度学习框架之一。",
        "related_concepts": ["神经网络", "梯度下降", "反向传播", "激活函数", "损失函数", "卷积神经网络"],
        "related_entities": ["OpenCV"],
    },
    "MATLAB": {
        "type": "工具", "category": "数学计算软件",
        "description": "MathWorks公司的数学计算软件，控制工程仿真核心工具。Simulink支持控制系统建模与仿真，是控制工程专业必备工具。",
        "related_concepts": ["传递函数", "状态空间", "根轨迹", "PID控制", "频率响应", "伯德图"],
        "related_entities": [],
    },
    "Obsidian": {
        "type": "工具", "category": "知识库软件",
        "description": "基于本地Markdown文件的知识库管理软件，支持双向链接、知识图谱、Dataview查询、插件生态。本知识库的核心载体。",
        "related_concepts": [],
        "related_entities": ["OpenClaw"],
    },
    "OpenClaw": {
        "type": "工具", "category": "AI助手",
        "description": "多模型AI助手，支持技能系统、自动化工作流、本地文件操作。本知识库的自动化建库核心工具。",
        "related_concepts": [],
        "related_entities": ["Obsidian"],
    },
    "VSCode": {
        "type": "工具", "category": "代码编辑器",
        "description": "微软开源的代码编辑器，支持丰富插件生态。配合DeepSeek-Harness插件进行编程学习。",
        "related_concepts": [],
        "related_entities": [],
    },

    # ===== 组织 =====
    "中南大学": {
        "type": "组织", "category": "高校",
        "description": "985/211高校，位于湖南长沙。土木工程学科评估A-，控制科学与工程学科评估B+。用户本科就读院校。",
        "related_concepts": ["机器视觉"],
        "related_entities": [],
    },
    "伯克利": {
        "type": "组织", "category": "高校",
        "description": "加州大学伯克利分校（UC Berkeley），世界顶尖公立大学。Stat 157机器学习课程学习资源来源。",
        "related_concepts": ["神经网络", "机器学习"],
        "related_entities": [],
    },
}


def scan_entity_occurrences(entity_name):
    """扫描实体在所有笔记中的出现位置"""
    locations = []
    for root, dirs, files in os.walk(VAULT_BASE):
        # 排除系统目录
        dirs[:] = [d for d in dirs if not d.startswith("_") and d not in [".obsidian", "99-教材原文"]]
        for fname in files:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, VAULT_BASE).replace("\\", "/")
            topic = rel.split("/")[0]
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if entity_name in content:
                    # 提取标题
                    title = fname[:-3]
                    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                    if m:
                        title = m.group(1).strip()[:50]
                    locations.append({"file": rel, "title": title, "topic": topic})
            except Exception:
                pass
    return locations


def build_entity_page(entity_name, entity_data):
    """生成单个实体页"""
    etype = entity_data.get("type", "未分类")
    category = entity_data.get("category", "")
    description = entity_data.get("description", "")
    related_concepts = entity_data.get("related_concepts", [])
    related_entities = entity_data.get("related_entities", [])
    location = entity_data.get("location", "")

    # 扫描出现位置
    locations = scan_entity_occurrences(entity_name)

    # 按主题分组
    topic_groups = {}
    for loc in locations:
        topic = loc["topic"]
        if topic not in topic_groups:
            topic_groups[topic] = []
        topic_groups[topic].append(loc)

    locations_text = ""
    if topic_groups:
        for topic, locs in sorted(topic_groups.items()):
            locations_text += f"### {topic}（{len(locs)}篇）\n"
            for loc in locs[:10]:
                locations_text += f"- [[{loc['file']}|{loc['title']}]]\n"
            if len(locs) > 10:
                locations_text += f"- …等共{len(locs)}篇\n"
            locations_text += "\n"
    else:
        locations_text = "（暂无直接引用，以下为关联内容）\n\n"

    # 关联概念wikilink
    def link_concept(c):
        concept_path = os.path.join(VAULT_BASE, "_概念层", "concepts", c + ".md")
        if os.path.exists(concept_path):
            return f"[[{c}]]"
        return c

    def link_entity(e):
        entity_path = os.path.join(ENTITY_DIR, e + ".md")
        if os.path.exists(entity_path) or e in ENTITIES:
            return f"[[{e}]]"
        return e

    concepts_text = "、".join(link_concept(c) for c in related_concepts) if related_concepts else "—"
    entities_text = "、".join(link_entity(e) for e in related_entities) if related_entities else "—"
    location_text = f"`{location}`" if location else "—"

    page = f"""---
entity: "{entity_name}"
type: "{etype}"
category: "{category}"
occurrence_count: {len(locations)}
created: "{datetime.now().strftime('%Y-%m-%d')}"
tags: ["实体层", "{etype}", "{entity_name}"]
---

# {entity_name}

> **类型**：{etype} | **分类**：{category} | **出现次数**：{len(locations)}篇笔记

---

## 📌 一、基本信息

{description}

**关联位置**：{location_text}

---

## 📚 二、跨主题出现位置

{locations_text}---

## 🔗 三、关联概念

{concepts_text}

## 👥 四、关联实体

{entities_text}

---

> 📌 本实体页由 concept-linker skill 自动生成。实体层用于跨主题的人物/书籍/工具/组织关联。
"""
    return page


def build_entity_index(entities_data):
    """生成实体层总索引"""
    # 按类型分组
    by_type = {}
    for name, data in entities_data.items():
        etype = data.get("type", "未分类")
        if etype not in by_type:
            by_type[etype] = []
        by_type[etype].append(name)

    index = f"""---
type: "entity-index"
tags: ["实体层", "索引"]
created: "{datetime.now().strftime('%Y-%m-%d')}"
---

# 👥 实体层总索引

> 人物/书籍/工具/组织的跨主题关联页。共 {len(entities_data)} 个核心实体。

---

"""
    type_icons = {"人物": "👤", "书籍": "📚", "工具": "🛠️", "组织": "🏛️"}
    for etype in ["人物", "书籍", "工具", "组织"]:
        if etype in by_type:
            icon = type_icons.get(etype, "📌")
            index += f"## {icon} {etype}（{len(by_type[etype])}个）\n\n"
            for name in sorted(by_type[etype]):
                data = entities_data[name]
                cat = data.get("category", "")
                index += f"- [[{name}]] — {cat}\n"
            index += "\n"

    index += """---

## 💡 使用说明

1. 实体页汇总了该实体在所有主题笔记中的出现位置，一键跳转
2. 实体页关联了相关概念和其他实体，形成知识网络
3. 新增实体：编辑 `entity_builder.py` 中的 `ENTITIES` 字典，重新运行
4. 实体层和概念层配合使用：概念层管"知识"，实体层管"人/书/工具/组织"
"""
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=VAULT_BASE)
    args = ap.parse_args()

    os.makedirs(ENTITY_DIR, exist_ok=True)

    print("=" * 50)
    print("👥 实体层构建")
    print(f"  实体数量: {len(ENTITIES)}")
    print("=" * 50)

    for name, data in ENTITIES.items():
        print(f"\n📝 生成实体页: {name}（{data.get('type')}）")
        page = build_entity_page(name, data)
        page_path = os.path.join(ENTITY_DIR, name + ".md")
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(page)
        print(f"  ✅ 已保存: {page_path}")

    # 生成总索引
    print("\n📊 生成实体层总索引...")
    index = build_entity_index(ENTITIES)
    index_path = os.path.join(VAULT_BASE, "_概念层", "_实体层索引.md")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index)
    print(f"  ✅ 已保存: {index_path}")

    print(f"\n{'='*50}")
    print(f"✅ 实体层构建完成！")
    print(f"  实体页: {ENTITY_DIR}")
    print(f"  总索引: {index_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
