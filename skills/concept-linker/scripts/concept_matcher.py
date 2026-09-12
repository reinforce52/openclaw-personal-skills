#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
concept_matcher.py - 用核心概念种子全文搜索所有笔记，建立跨主题概念索引
核心概念基于学科知识结构归纳，全文匹配标题+正文+tags
"""
import os, re, json, argparse
from collections import defaultdict
from pathlib import Path

LEARNING_TOPICS = [
    "线性代数", "考研数学", "考研高数", "英语六级", "六级备考技巧",
    "自动控制原理", "土木跨考控制工程", "神经网络基础",
    "berkeley-stat-157_learning_assets", "MiniMind_Learning",
]
EXCLUDE_DIRS = [".obsidian", "视频笔记", "_vault-health", "_概念层", "_templates", "99-教材原文"]

# 核心概念种子：{概念名: [别名/关键词列表]}
# 基于学科知识结构归纳，跨主题价值高的概念
CORE_CONCEPTS = {
    # ===== 线性代数核心 =====
    "矩阵": ["矩阵", "matrix", "Matrix"],
    "行列式": ["行列式", "determinant", "Determinant"],
    "特征值与特征向量": ["特征值", "特征向量", "eigenvalue", "eigenvector", "Eigen"],
    "向量": ["向量", "vector", "Vector"],
    "线性变换": ["线性变换", "linear transformation", "Linear Transform"],
    "线性组合与张成空间": ["线性组合", "张成", "span", "Span", "linear combination"],
    "基与基变换": ["基变换", "基向量", "basis", "Basis", "change of basis"],
    "逆矩阵与秩": ["逆矩阵", "矩阵的秩", "秩", "inverse", "rank", "Rank"],
    "列空间与零空间": ["列空间", "零空间", "column space", "null space", "Column Space"],
    "点积与对偶性": ["点积", "对偶性", "dot product", "dual", "Dot Product"],
    "叉积": ["叉积", "cross product", "Cross Product"],
    "克莱姆法则": ["克莱姆", "Cramer", "cramer"],

    # ===== 高等数学核心 =====
    "极限与连续": ["极限", "连续", "limit", "continuity", "Limit"],
    "导数与微分": ["导数", "微分", "derivative", "differential", "Derivative"],
    "积分": ["积分", "定积分", "不定积分", "integral", "Integral", "integration"],
    "微分方程": ["微分方程", "常微分方程", "differential equation", "ODE", "Differential Equation"],
    "级数": ["级数", "幂级数", "泰勒级数", "series", "Series", "Taylor"],
    "多元函数微积分": ["偏导数", "多元函数", "重积分", "partial derivative", "multiple integral"],
    "拉普拉斯变换": ["拉普拉斯", "拉氏变换", "Laplace", "laplace"],

    # ===== 概率论与数理统计 =====
    "概率论基础": ["概率", "随机变量", "probability", "Probability", "random variable"],
    "数理统计": ["数理统计", "假设检验", "置信区间", "statistical", "hypothesis test", "confidence interval"],
    "分布与期望": ["正态分布", "期望", "方差", "distribution", "expectation", "variance", "Normal Distribution"],

    # ===== 自动控制原理核心 =====
    "传递函数": ["传递函数", "transfer function", "Transfer Function"],
    "状态空间": ["状态空间", "状态方程", "state space", "State Space", "state equation"],
    "根轨迹": ["根轨迹", "root locus", "Root Locus"],
    "PID控制": ["PID", "比例积分微分", "proportion integration differentiation"],
    "频率响应": ["频率响应", "频率特性", "frequency response", "Frequency Response"],
    "稳定性分析": ["稳定性", "稳定判据", "stability", "Stability", "劳斯判据", "奈奎斯特"],
    "伯德图": ["伯德图", "Bode", "bode", "波特图"],
    "奈奎斯特判据": ["奈奎斯特", "Nyquist", "nyquist"],
    "反馈控制": ["反馈", "闭环", "负反馈", "feedback", "Feedback", "closed loop"],

    # ===== 神经网络/机器学习核心 =====
    "神经网络": ["神经网络", "neural network", "Neural Network", "ANN"],
    "梯度下降": ["梯度下降", "gradient descent", "Gradient Descent", "SGD"],
    "反向传播": ["反向传播", "backpropagation", "Backpropagation", "BP算法"],
    "激活函数": ["激活函数", "activation function", "Activation", "ReLU", "sigmoid", "Sigmoid"],
    "损失函数": ["损失函数", "loss function", "Loss Function", "loss"],
    "卷积神经网络": ["卷积", "CNN", "convolutional", "Convolution"],
    "PyTorch": ["PyTorch", "pytorch", "torch"],

    # ===== 英语六级核心 =====
    "英语听力": ["听力", "listening", "Listening"],
    "英语阅读": ["阅读理解", "仔细阅读", "长篇阅读", "reading", "Reading", "阅读"],
    "英语写作": ["写作", "作文", "writing", "Writing", "作文模板"],
    "英语翻译": ["翻译", "translation", "Translation", "汉译英"],
    "英语词汇": ["词汇", "单词", "vocabulary", "Vocabulary"],
    "英语语法": ["语法", "长难句", "grammar", "Grammar"],

    # ===== 跨学科工具 =====
    "机器视觉": ["机器视觉", "computer vision", "Computer Vision", "CV", "图像处理"],
    "线性代数应用": ["PCA", "主成分分析", "SVD", "奇异值分解", "降维"],
}


def extract_frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split('\n'):
        line = line.strip()
        if ':' in line:
            key, val = line.split(':', 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def match_concepts_in_text(text, title, fm):
    """在文本中匹配核心概念，返回匹配到的概念列表"""
    matched = set()
    # 合并标题+frontmatter+正文（标题和tags权重更高，但这里只做匹配）
    search_text = title + " " + fm.get("tags", "") + " " + fm.get("category", "") + " " + text[:3000]
    search_lower = search_text.lower()

    for concept, keywords in CORE_CONCEPTS.items():
        for kw in keywords:
            if kw.lower() in search_lower:
                matched.add(concept)
                break
    return matched


def scan_vault(vault_base):
    """扫描整个 vault，用核心概念种子匹配"""
    concept_locations = defaultdict(list)
    file_count = 0
    topic_files = defaultdict(int)
    concept_topic_count = defaultdict(set)  # 概念 -> 出现的主题集合

    for root, dirs, files in os.walk(vault_base):
        dirs[:] = [d for d in dirs if not any(ex in d for ex in EXCLUDE_DIRS)]

        for fname in files:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, vault_base)
            topic = rel.split(os.sep)[0] if os.sep in rel else rel

            if topic not in LEARNING_TOPICS:
                continue

            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception:
                continue

            file_count += 1
            topic_files[topic] += 1

            fm = extract_frontmatter(text)
            title = fm.get("title", Path(fpath).stem)

            matched = match_concepts_in_text(text, title, fm)
            for concept in matched:
                concept_locations[concept].append({
                    "topic": topic,
                    "file": rel.replace("\\", "/"),
                    "title": title[:80],
                })
                concept_topic_count[concept].add(topic)

    return concept_locations, concept_topic_count, file_count, topic_files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=r"E:\obsidian\rein")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    print(f"扫描 vault: {args.vault}")
    concept_locations, concept_topic_count, file_count, topic_files = scan_vault(args.vault)

    print(f"\n扫描完成: {file_count} 个学习类笔记")
    print(f"涉及主题: {len(topic_files)} 个")

    # 按跨主题数+出现次数排序
    sorted_concepts = sorted(
        concept_locations.items(),
        key=lambda x: (-len(concept_topic_count[x[0]]), -len(x[1]))
    )

    print(f"\n=== 核心概念匹配结果（共{len(sorted_concepts)}个，按跨主题数排序）===")
    for i, (concept, locs) in enumerate(sorted_concepts, 1):
        topics = sorted(concept_topic_count[concept])
        print(f"  {i:2d}. {concept:20s} 出现{len(locs):3d}次  跨{len(topics)}主题: {', '.join(topics)}")

    if args.output:
        output_data = {
            "total_files": file_count,
            "total_concepts": len(sorted_concepts),
            "topics": dict(topic_files),
            "concepts": [
                {
                    "name": c,
                    "count": len(locs),
                    "topic_count": len(concept_topic_count[c]),
                    "topics": sorted(concept_topic_count[c]),
                    "locations": locs,
                }
                for c, locs in sorted_concepts
            ],
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 概念索引已保存: {args.output}")


if __name__ == "__main__":
    main()
