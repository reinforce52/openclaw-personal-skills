#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vault_health.py - 知识库自动体检：死链/重复/孤儿/矛盾四项检测
扫描所有学习类主题 vault，输出体检报告到 _vault-health/
"""
import os, re, json, argparse
from collections import defaultdict
from pathlib import Path
from datetime import datetime

VAULT_BASE = r"E:\obsidian\rein"
HEALTH_DIR = os.path.join(VAULT_BASE, "_vault-health")

# 学习类主题
LEARNING_TOPICS = [
    "线性代数", "考研数学", "考研高数", "英语六级", "六级备考技巧",
    "自动控制原理", "土木跨考控制工程", "神经网络基础",
    "berkeley-stat-157_learning_assets", "MiniMind_Learning",
    "_概念层",
]
# 排除目录
EXCLUDE_DIRS = [".obsidian", "_vault-health", "_templates", "99-教材原文", "images"]


def sanitize(name):
    return re.sub(r'[\\/:*?"<>|#]', '_', name).strip()


def scan_all_md():
    """扫描所有学习类md文件，返回 {rel_path: {title, content, topic, size}}"""
    files = {}
    for root, dirs, fnames in os.walk(VAULT_BASE):
        dirs[:] = [d for d in dirs if not any(ex in d for ex in EXCLUDE_DIRS)]
        for fname in fnames:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, VAULT_BASE).replace("\\", "/")
            topic = rel.split("/")[0]
            if topic not in LEARNING_TOPICS:
                continue
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            # 提取标题
            title = fname[:-3]
            m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if m:
                title = m.group(1).strip()[:80]
            files[rel] = {
                "title": title,
                "content": content,
                "topic": topic,
                "size": len(content),
                "fname": fname[:-3],
            }
    return files


def extract_wikilinks(content):
    """提取所有wikilink目标（不含#锚点和|别名），排除矩阵/纯数字误报"""
    links = set()
    for m in re.finditer(r'\[\[([^\]|#]+)', content):
        target = m.group(1).strip()
        if not target:
            continue
        # 排除矩阵元素/数学表达式误报：短字符串+逗号/数学函数
        if len(target) < 8 and (',' in target or re.match(r'^[\d\s\.\-\+/θπ]+(tan|sin|cos|log)?[\d\s\.\-\+/θπ]*$', target)):
            continue
        # 排除纯数字/符号
        if re.match(r'^[\d\s,\.\-\+/θπtansincolog]+$', target):
            continue
        # 排除太短的（<2个字符，不太可能是笔记名）
        if len(target) < 2:
            continue
        links.add(target)
    return links


def check_dead_links(files):
    """死链检测：wikilink目标在整个vault中不存在"""
    # 建立所有文件名索引（Obsidian全局搜索，所以按文件名匹配）
    all_fnames = {}
    for rel, info in files.items():
        fname = info["fname"]
        if fname not in all_fnames:
            all_fnames[fname] = []
        all_fnames[fname].append(rel)

    # 额外扫描被排除目录的文件名（不读内容，只用于死链检测）
    for root, dirs, fnames in os.walk(VAULT_BASE):
        for fname in fnames:
            if not fname.endswith('.md'):
                continue
            base = fname[:-3]
            if base not in all_fnames:
                rel = os.path.relpath(os.path.join(root, fname), VAULT_BASE).replace("\\", "/")
                all_fnames[base] = [rel]

    dead_links = defaultdict(list)  # 文件 -> [死链目标]
    link_count = 0

    for rel, info in files.items():
        links = extract_wikilinks(info["content"])
        for link in links:
            link_count += 1
            # 去掉末尾的.md后缀（Obsidian wikilink可带可不带.md）
            link_clean = link[:-3] if link.endswith(".md") else link
            # Obsidian全局搜索：按文件名匹配，也支持带路径的
            link_base = os.path.basename(link_clean)
            # 检查1：精确文件名匹配（不带.md）
            if link_base in all_fnames:
                continue
            # 检查2：带路径的，检查路径是否存在
            full_path = os.path.join(VAULT_BASE, link_clean + ".md")
            if os.path.exists(full_path):
                continue
            # 检查3：链接目标包含路径分隔，检查最后一级文件名
            if "/" in link_clean:
                last = link_clean.split("/")[-1]
                if last in all_fnames:
                    continue
            # 都找不到，是死链
            dead_links[rel].append(link)

    return dead_links, link_count, all_fnames


def text_similarity(text1, text2):
    """简单文本相似度：基于字符n-gram重合度"""
    def get_ngrams(text, n=4):
        text = re.sub(r'\s+', '', text)
        return set(text[i:i+n] for i in range(len(text)-n+1))
    g1, g2 = get_ngrams(text1), get_ngrams(text2)
    if not g1 or not g2:
        return 0.0
    return len(g1 & g2) / min(len(g1), len(g2))


def check_duplicates(files):
    """重复笔记检测：标题相似+内容相似，排除同一目录下的笔记"""
    duplicates = []
    file_list = list(files.items())
    checked = set()

    for i, (rel1, info1) in enumerate(file_list):
        dir1 = os.path.dirname(rel1)
        for j, (rel2, info2) in enumerate(file_list):
            if i >= j:
                continue
            # 排除同一目录下的笔记（同一视频/同一章节的笔记结构本来就相似）
            if os.path.dirname(rel2) == dir1:
                continue
            key = (rel1, rel2)
            if key in checked:
                continue
            checked.add(key)

            # 标题相似度
            title_sim = text_similarity(info1["title"], info2["title"])
            # 内容相似度（只比较正文，排除frontmatter和模板字段）
            content1 = re.sub(r'^---.*?---', '', info1["content"], flags=re.DOTALL)[:2000]
            content2 = re.sub(r'^---.*?---', '', info2["content"], flags=re.DOTALL)[:2000]
            content_sim = text_similarity(content1, content2)

            # 标题高度相似 且 内容高度相似（两个条件都满足才判定，减少误报）
            if title_sim >= 0.7 and content_sim >= 0.6:
                duplicates.append({
                    "file1": rel1,
                    "file2": rel2,
                    "title1": info1["title"],
                    "title2": info2["title"],
                    "title_similarity": round(title_sim, 2),
                    "content_similarity": round(content_sim, 2),
                    "size1": info1["size"],
                    "size2": info2["size"],
                })

    # 按相似度排序
    duplicates.sort(key=lambda x: -max(x["title_similarity"], x["content_similarity"]))
    return duplicates


def check_orphans(files):
    """孤儿笔记检测：没有被任何其他笔记wikilink引用的文件"""
    # 统计每个文件被引用的次数
    reference_count = defaultdict(int)
    reference_from = defaultdict(list)

    all_fnames = {}
    for rel, info in files.items():
        all_fnames[info["fname"]] = rel

    for rel, info in files.items():
        links = extract_wikilinks(info["content"])
        for link in links:
            link_clean = link[:-3] if link.endswith(".md") else link
            link_base = os.path.basename(link_clean)
            if link_base in all_fnames:
                target = all_fnames[link_base]
                if target != rel:  # 不算自引用
                    reference_count[target] += 1
                    reference_from[target].append(rel)

    orphans = []
    for rel, info in files.items():
        # 排除导航文件（_开头的索引/总览/图谱文件，这些本来就不该被引用）
        fname = os.path.basename(rel)
        if fname.startswith("_") or "总览" in fname or "索引" in fname or "图谱" in fname:
            continue
        if reference_count[rel] == 0:
            orphans.append({
                "file": rel,
                "title": info["title"],
                "topic": info["topic"],
                "size": info["size"],
            })

    orphans.sort(key=lambda x: (x["topic"], -x["size"]))
    return orphans, reference_count


def check_contradictions(files):
    """矛盾标记（简单版）：同一概念在不同笔记中的定义/描述差异，标注待人工确认
    方法：提取包含'定义''是指''指的是''意味着'等定义性语句的笔记，
    对同一概念在不同笔记中的定义做相似度对比，差异大的标注为潜在矛盾"""
    # 提取定义性语句
    definition_patterns = [
        r'(.{0,20}(?:定义|是指|指的是|意味着|本质是|核心是).{0,80})',
    ]

    concept_definitions = defaultdict(list)  # 概念 -> [(文件, 定义语句)]

    # 用核心概念种子匹配
    CORE_CONCEPTS = [
        "矩阵", "行列式", "特征值", "向量", "线性变换", "导数", "积分",
        "极限", "微分方程", "概率", "传递函数", "状态空间", "稳定性",
        "神经网络", "梯度下降", "卷积", "激活函数", "损失函数",
    ]

    for rel, info in files.items():
        content = info["content"]
        for concept in CORE_CONCEPTS:
            # 找包含该概念的定义性语句
            for pattern in definition_patterns:
                for m in re.finditer(pattern, content):
                    sentence = m.group(1).strip()
                    if concept in sentence and len(sentence) > 10:
                        concept_definitions[concept].append({
                            "file": rel,
                            "sentence": sentence[:120],
                        })
                        break  # 每个概念每文件只取一条

    # 找出同一概念在不同笔记中定义差异大的
    contradictions = []
    for concept, defs in concept_definitions.items():
        if len(defs) < 2:
            continue
        # 两两比较定义相似度
        for i in range(len(defs)):
            for j in range(i+1, len(defs)):
                sim = text_similarity(defs[i]["sentence"], defs[j]["sentence"])
                if 0.1 < sim < 0.4:  # 有一定关联但差异较大
                    contradictions.append({
                        "concept": concept,
                        "file1": defs[i]["file"],
                        "file2": defs[j]["file"],
                        "definition1": defs[i]["sentence"],
                        "definition2": defs[j]["sentence"],
                        "similarity": round(sim, 2),
                    })

    contradictions.sort(key=lambda x: x["similarity"])
    return contradictions[:30]  # 最多30条


def generate_report(files, dead_links, link_count, duplicates, orphans, ref_count, contradictions):
    """生成体检报告"""
    total_files = len(files)
    dead_file_count = len(dead_links)
    dead_link_count = sum(len(v) for v in dead_links.values())
    dup_count = len(duplicates)
    orphan_count = len(orphans)
    contradiction_count = len(contradictions)

    # 健康评分
    score = 100
    score -= min(dead_link_count * 0.5, 20)  # 死链最多扣20分
    score -= min(dup_count * 2, 15)  # 重复最多扣15分
    score -= min(orphan_count * 0.3, 15)  # 孤儿最多扣15分
    score = max(0, round(score))

    if score >= 85:
        grade = "🟢 优秀"
    elif score >= 70:
        grade = "🟡 良好"
    elif score >= 50:
        grade = "🟠 一般"
    else:
        grade = "🔴 需改善"

    report = f"""---
type: vault-health-report
date: "{datetime.now().strftime('%Y-%m-%d %H:%M')}"
total_files: {total_files}
health_score: {score}
grade: "{grade}"
---

# 🏥 知识库体检报告

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

## 📊 总体评分

| 指标 | 数值 | 状态 |
|------|------|------|
| **健康评分** | **{score}/100** | {grade} |
| 扫描文件总数 | {total_files} | — |
| 总链接数 | {link_count} | — |
| 死链数 | {dead_link_count} | {"🔴" if dead_link_count > 20 else "🟡" if dead_link_count > 5 else "🟢"} |
| 含死链的文件 | {dead_file_count} | — |
| 疑似重复笔记 | {dup_count}对 | {"🔴" if dup_count > 10 else "🟡" if dup_count > 3 else "🟢"} |
| 孤儿笔记 | {orphan_count} | {"🟡" if orphan_count > 20 else "🟢"} |
| 潜在矛盾 | {contradiction_count} | — |

---

## 🔗 一、死链检测（{dead_link_count}个）

> wikilink 指向不存在的文件。Obsidian 中显示为灰色链接。

"""
    if dead_links:
        report += "| 文件 | 死链目标 |\n|------|----------|\n"
        for rel, links in sorted(dead_links.items(), key=lambda x: -len(x[1]))[:30]:
            for link in links:
                report += f"| [[{rel}\|{os.path.basename(rel)}]] | `{link}` |\n"
        if dead_file_count > 30:
            report += f"\n> 仅显示前30个含死链的文件，共{dead_file_count}个文件含死链。\n"
    else:
        report += "✅ 未发现死链！\n"

    report += f"""
---

## 📑 二、重复笔记检测（{dup_count}对）

> 标题或内容高度相似的笔记，建议合并。

"""
    if duplicates:
        report += "| # | 文件1 | 文件2 | 标题相似度 | 内容相似度 |\n|---|-------|-------|-----------|-----------|\n"
        for i, dup in enumerate(duplicates[:20], 1):
            report += f"| {i} | [[{dup['file1']}\|{dup['title1'][:30]}]] | [[{dup['file2']}\|{dup['title2'][:30]}]] | {dup['title_similarity']} | {dup['content_similarity']} |\n"
        if dup_count > 20:
            report += f"\n> 仅显示前20对，共{dup_count}对疑似重复。\n"
    else:
        report += "✅ 未发现疑似重复笔记！\n"

    report += f"""
---

## 🏝️ 三、孤儿笔记检测（{orphan_count}个）

> 没有被任何其他笔记 wikilink 引用的笔记（已排除导航文件）。
> 孤儿笔记意味着知识网络中有断点，建议补充关联。

"""
    if orphans:
        # 按主题分组
        by_topic = defaultdict(list)
        for o in orphans:
            by_topic[o["topic"]].append(o)
        for topic, items in sorted(by_topic.items()):
            report += f"### {topic}（{len(items)}个）\n\n"
            for o in items[:15]:
                report += f"- [[{o['file']}\|{o['title'][:50]}]]\n"
            if len(items) > 15:
                report += f"- …等共{len(items)}个\n"
            report += "\n"
    else:
        report += "✅ 未发现孤儿笔记！\n"

    report += f"""
---

## ⚠️ 四、潜在矛盾检测（{contradiction_count}条）

> 同一概念在不同笔记中定义差异较大，建议人工确认是否矛盾。

"""
    if contradictions:
        report += "| # | 概念 | 文件1 | 文件2 | 相似度 |\n|---|------|-------|-------|--------|\n"
        for i, c in enumerate(contradictions[:15], 1):
            report += f"| {i} | {c['concept']} | [[{c['file1']}\|{os.path.basename(c['file1'])[:30]}]] | [[{c['file2']}\|{os.path.basename(c['file2'])[:30]}]] | {c['similarity']} |\n"
        report += "\n> 点击文件查看具体定义，人工判断是否真的矛盾。\n"
    else:
        report += "✅ 未发现明显潜在矛盾！\n"

    report += """
---

## 🛠️ 五、修复建议

### 死链修复
1. 检查死链目标是否拼写错误（Obsidian 全局搜索文件名）
2. 如果目标笔记已删除，移除该 wikilink 或改为纯文本
3. 如果目标笔记在其他目录，补充完整路径

### 重复笔记合并
1. 对比两篇笔记内容，保留更完整的一篇
2. 将另一篇的独有内容合并到保留篇
3. 删除重复篇，更新所有指向它的 wikilink

### 孤儿笔记关联
1. 为孤儿笔记补充 `前置知识`/`关联知识点` 字段
2. 在相关主题的总览/索引页中加入该笔记的 wikilink
3. 检查是否是真正独立的内容（如配置文件、模板），这类可以忽略

### 矛盾确认
1. 打开两篇笔记，对比具体定义
2. 如果确实矛盾，标注哪个更准确，更新另一篇
3. 如果只是表述不同（不矛盾），忽略该条

---

> 📌 本报告由 vault-health 自动生成。建议每月运行一次体检，保持知识库健康。
"""
    return report, score, grade


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=VAULT_BASE)
    ap.add_argument("--output-dir", default=HEALTH_DIR)
    args = ap.parse_args()

    print("扫描知识库...")
    files = scan_all_md()
    print(f"  扫描到 {len(files)} 个学习类笔记")

    print("检测死链...")
    dead_links, link_count, _ = check_dead_links(files)
    print(f"  死链: {sum(len(v) for v in dead_links.values())}个，涉及{len(dead_links)}个文件")

    print("检测重复笔记...")
    duplicates = check_duplicates(files)
    print(f"  疑似重复: {len(duplicates)}对")

    print("检测孤儿笔记...")
    orphans, ref_count = check_orphans(files)
    print(f"  孤儿笔记: {len(orphans)}个")

    print("检测潜在矛盾...")
    contradictions = check_contradictions(files)
    print(f"  潜在矛盾: {len(contradictions)}条")

    print("生成体检报告...")
    report, score, grade = generate_report(
        files, dead_links, link_count, duplicates, orphans, ref_count, contradictions
    )

    os.makedirs(args.output_dir, exist_ok=True)
    report_path = os.path.join(args.output_dir, "体检报告.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # 同时保存详细数据
    data_path = os.path.join(args.output_dir, "health_data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "total_files": len(files),
            "dead_links": {k: v for k, v in dead_links.items()},
            "duplicates": duplicates,
            "orphans": orphans,
            "contradictions": contradictions,
            "score": score,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ 体检完成！健康评分: {score}/100 ({grade})")
    print(f"   报告: {report_path}")
    print(f"   数据: {data_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
