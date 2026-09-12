#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
link_projects_to_concepts.py - 将项目档案与概念层关联
在每个概念页里添加"💼 相关项目"部分，标注哪些项目用到了这个概念。
用法:
  python link_projects_to_concepts.py --apply
  python link_projects_to_concepts.py --dry-run
"""
import os, re, argparse
from pathlib import Path

VAULT_BASE = r"E:\obsidian\rein"
CONCEPT_DIR = os.path.join(VAULT_BASE, "_概念层", "concepts")
PROJECT_DIR = os.path.join(VAULT_BASE, "03-项目库")

# 概念 → 相关项目映射（基于项目内容分析）
# 格式: {概念名: [(项目文件名, 项目显示名, 应用说明), ...]}
CONCEPT_PROJECT_MAP = {
    # === 线性代数相关 ===
    "矩阵": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "旋转矩阵实现局部坐标→大地坐标转换"),
        ("pandas数据处理基础应用.md", "pandas数据处理", "DataFrame底层矩阵运算，批量数据处理"),
    ],
    "向量": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "方位角向量、坐标向量运算"),
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "图像像素向量、特征向量"),
    ],
    "行列式": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "坐标变换中的行列式（面积缩放因子）"),
    ],
    "逆矩阵与秩": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "坐标反算中的逆矩阵应用"),
    ],
    "线性变换": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "局部坐标系到测量坐标系的线性变换"),
        ("Revit-BIM建模入门.md", "Revit/BIM", "三维建模中的坐标变换与线性变换"),
    ],
    "特征值与特征向量": [
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "PCA降维（特征值分解）、纹理分析"),
        ("Khoj本地部署-Agent定制.md", "Khoj本地部署", "嵌入向量的特征分解与降维"),
    ],
    "基与基变换": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "局部基→标准基的坐标变换"),
    ],
    "线性组合与张成空间": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "坐标的线性组合表示"),
    ],
    "列空间与零空间": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "坐标变换矩阵的列空间理解"),
    ],
    "叉积": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "向量叉积判断左偏/右偏、面积计算"),
    ],
    "点积与对偶性": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "向量点积计算夹角、投影"),
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "模板匹配中的点积/相关运算"),
    ],
    "克莱姆法则": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "线性方程组求解（坐标反算）"),
    ],
    "线性代数应用": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "线性代数在工程测量中的完整应用"),
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "线性代数在图像处理中的应用"),
    ],

    # === 高等数学相关 ===
    "极限与连续": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "缓和曲线极限性质、连续函数建模"),
    ],
    "导数与微分": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "缓和曲线参数方程求导、曲率计算"),
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "Canny边缘检测中的梯度（导数）"),
    ],
    "积分": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "曲线长度积分、弧长计算"),
    ],
    "多元函数微积分": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "二元函数坐标变换、偏导数"),
    ],
    "微分方程": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "缓和曲线微分方程（曲率线性变化）"),
    ],
    "级数": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "缓和曲线参数方程的级数展开"),
    ],

    # === 概率论与统计相关 ===
    "概率论基础": [
        ("学术数据面板-教务成绩可视化.md", "学术数据面板", "成绩概率分布、统计推断"),
        ("pandas数据处理基础应用.md", "pandas数据处理", "概率统计函数、数据分布分析"),
    ],
    "分布与期望": [
        ("学术数据面板-教务成绩可视化.md", "学术数据面板", "成绩分布直方图、期望/方差计算"),
        ("pandas数据处理基础应用.md", "pandas数据处理", "describe()统计量、分布分析"),
    ],
    "数理统计": [
        ("学术数据面板-教务成绩可视化.md", "学术数据面板", "成绩统计分析、排名计算、学分加权"),
        ("pandas数据处理基础应用.md", "pandas数据处理", "groupby聚合、统计检验、数据透视"),
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "检测准确率统计、误检率分析"),
    ],

    # === 自动控制相关 ===
    "传递函数": [],
    "状态空间": [],
    "PID控制": [],
    "反馈控制": [],
    "稳定性分析": [
        ("测设计算程序-curve_calc.md", "测设计算程序", "数值计算稳定性分析（迭代收敛性）"),
    ],
    "根轨迹": [],
    "伯德图": [],
    "奈奎斯特判据": [],
    "频率响应": [],
    "拉普拉斯变换": [],

    # === 神经网络/AI相关 ===
    "神经网络": [
        ("Khoj本地部署-Agent定制.md", "Khoj本地部署", "AI Agent底层神经网络模型、接入本地模型"),
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "后续方向：YOLOv8/U-Net深度学习检测"),
    ],
    "反向传播": [
        ("Khoj本地部署-Agent定制.md", "Khoj本地部署", "模型训练原理、微调理解"),
    ],
    "激活函数": [
        ("Khoj本地部署-Agent定制.md", "Khoj本地部署", "神经网络激活函数理解"),
    ],
    "损失函数": [
        ("Khoj本地部署-Agent定制.md", "Khoj本地部署", "模型训练损失函数理解"),
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "后续深度学习：检测损失函数（CIoU等）"),
    ],
    "梯度下降": [
        ("Khoj本地部署-Agent定制.md", "Khoj本地部署", "优化算法理解、模型训练"),
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "后续深度学习：梯度下降优化"),
    ],
    "卷积神经网络": [
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "后续方向：CNN/YOLO/U-Net深度学习检测"),
        ("Khoj本地部署-Agent定制.md", "Khoj本地部署", "多模态理解（图像输入）"),
    ],
    "PyTorch": [
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "后续方向：PyTorch实现YOLOv8/U-Net"),
    ],

    # === 跨学科 ===
    "机器视觉": [
        ("混凝土裂缝检测-crack-detection.md", "混凝土裂缝检测", "核心应用：传统CV方法实现裂缝自动化检测"),
        ("测设计算程序-curve_calc.md", "测设计算程序", "摄影测量与计算机视觉交叉（后续方向）"),
    ],

    # === 英语六级相关（项目不直接涉及，跳过）===
}

# 项目显示名映射（用于链接显示）
PROJECT_DISPLAY = {
    "测设计算程序-curve_calc.md": "测设计算程序",
    "混凝土裂缝检测-crack-detection.md": "混凝土裂缝检测",
    "学术数据面板-教务成绩可视化.md": "学术数据面板",
    "Khoj本地部署-Agent定制.md": "Khoj本地部署",
    "Revit-BIM建模入门.md": "Revit/BIM建模",
    "pandas数据处理基础应用.md": "pandas数据处理",
    "工程测量实习经历总结.md": "工程测量实习",
}


def build_project_section(concept_name):
    """构建"相关项目"部分的Markdown内容"""
    projects = CONCEPT_PROJECT_MAP.get(concept_name, [])
    if not projects:
        return None

    lines = []
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 💼 六、相关项目（哪些项目用到了这个概念）")
    lines.append("")
    lines.append(f"> 以下项目实际应用了「{concept_name}」这个概念，点击可跳转项目档案。")
    lines.append("")

    for proj_file, proj_name, usage in projects:
        display = PROJECT_DISPLAY.get(proj_file, proj_name)
        lines.append(f"### [[03-项目库/{proj_file}|{display}]]")
        lines.append(f"- **应用方式**：{usage}")
        lines.append("")

    return "\n".join(lines)


def add_project_section(content, concept_name):
    """在概念页中添加/更新"相关项目"部分"""
    section = build_project_section(concept_name)
    if section is None:
        return content, False

    # 检查是否已存在"相关项目"部分
    if "## 💼 六、相关项目" in content or "## 💼 相关项目" in content:
        # 替换已有部分
        pattern = r'\n---\n\n## 💼.*?相关项目.*?(?=\n---\n|\Z)'
        new_content = re.sub(pattern, section, content, flags=re.DOTALL)
        return new_content, True

    # 在"掌握检验"部分之后插入（在末尾的注释之前）
    marker = "## ✅ 五、掌握检验"
    if marker in content:
        # 找到掌握检验部分的结束位置（下一个 --- 或文件末尾）
        idx = content.find(marker)
        # 找到掌握检验部分之后的第一个 ---
        after = content[idx:]
        sep_match = re.search(r'\n---\n', after)
        if sep_match:
            insert_pos = idx + sep_match.start()
            new_content = content[:insert_pos] + section + content[insert_pos:]
            return new_content, True

    # 如果找不到标记，直接在末尾添加（在最后一行注释之前）
    if "> 📌 本概念页由 concept-linker skill 自动生成" in content:
        idx = content.find("> 📌 本概念页由 concept-linker skill 自动生成")
        new_content = content[:idx] + section + "\n\n" + content[idx:]
        return new_content, True

    # 兜底：直接追加到末尾
    return content + section, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not args.dry_run and not args.apply:
        print("请指定 --dry-run 或 --apply")
        return

    mode = "预览" if args.dry_run else "执行"
    print(f"{'='*60}")
    print(f"💼 项目-概念关联 [{mode}]")
    print(f"{'='*60}")

    # 统计
    total_concepts = 0
    concepts_with_projects = 0
    total_links = 0
    modified = 0
    skipped = 0

    for concept_file in sorted(os.listdir(CONCEPT_DIR)):
        if not concept_file.endswith('.md'):
            continue
        total_concepts += 1
        concept_name = concept_file[:-3]

        projects = CONCEPT_PROJECT_MAP.get(concept_name, [])
        if not projects:
            skipped += 1
            continue

        concepts_with_projects += 1
        total_links += len(projects)

        filepath = os.path.join(CONCEPT_DIR, concept_file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content, changed = add_project_section(content, concept_name)

        if args.apply and changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            modified += 1
            print(f"  ✅ {concept_name}（{len(projects)}个项目）")
        elif args.dry_run:
            print(f"  📋 {concept_name}（{len(projects)}个项目）: {', '.join(p[1] for p in projects)}")

    print(f"\n{'='*60}")
    print(f"📊 统计")
    print(f"  概念总数: {total_concepts}")
    print(f"  有关联项目的概念: {concepts_with_projects}")
    print(f"  关联总数: {total_links}")
    print(f"  无项目关联的概念: {skipped}（多为考研方向/英语，当前项目暂未涉及）")
    if args.apply:
        print(f"  已修改文件: {modified}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
