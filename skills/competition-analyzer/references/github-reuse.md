# GitHub 成品级开源项目检索与复用

目标：**优先找到"克隆 + 配置即跑"的成品项目**，让 4 周开发周期从"从零写"变成"集成 + 定制"。

## 一、检索方法

### 1. 检索渠道（按优先级）

- `github-remote` Skill 的 `search_repositories` / `search_code`（运行时可用时优先，支持 `stars:>100 language:python` 等高级语法）
- `general_search` 带 `site:github.com` 或"GitHub 开源"关键词
- GitHub 官方 Topics 页（如 `github.com/topics/embodied-carbon`、`topics/building-energy`）按主题聚合
- 学术项目（arXiv 论文常附代码仓库，权威性高）

### 2. 关键词构造

- 中文 + 英文双通道：`建筑 碳排放 智能体` / `building carbon emission agent`
- 标准名是金钥匙：`GB/T 51366`、`embodied carbon`、`Scope 3`、`LCA`、`EnergyPlus`、`BIM`
- 加限定词缩小：`agent`、`LLM`、`LangChain`、`RAG`、`MCP`
- 按"成品可用"过滤：`stars:>50`、`pushed:>2025-01-01`、`license:mit`

### 3. 四档可用性评估（从高到低）

1. **克隆即跑**：有 README 一键启动、requirements 锁定、含示例数据 → 直接部署
2. **需二开**：功能对路但场景/数据/语言不符 → 评估改造工作量
3. **框架组件**：Agent 框架、UI、计算库 → 自己拼装
4. **思路参考**：读架构文档和代码，从零实现

## 二、许可证速查（决定能不能用）

| 许可证 | 商用/二开 | 说明 |
|---|---|---|
| MIT / Apache-2.0 | ✅ 随便用 | 保留版权声明即可，首选 |
| BSD | ✅ 随便用 | 同 MIT |
| GPL-3.0 | ⚠️ 慎用 | 衍生作品须开源（比赛提交仓库会被要求开源，通常可接受，但企业方可能介意） |
| AGPL | ⚠️ 慎用 | 网络服务也算衍生，比赛场景尽量避开 |
| 无 LICENSE | ❌ 不可商用 | 默认保留所有权利，只能参考思路 |

判断：比赛项目本身要开源提交，GPL 并非绝对禁止，但**优先 MIT/Apache** 以免全国赛企业环节出问题。

## 三、绿色建筑/碳排放方向候选项目清单（2026-09 检索）

### 成品级（克隆即跑 / 计算引擎直接复用）

| 项目 | 链接 | 亮点 | 用途 |
|---|---|---|---|
| **GBT51366 公共建筑碳排放计算报告系统** | https://github.com/kasc0206/GBT51366 | 按 GB/T 51366-2019 拆分 39 个计算单元，MIT | **核心计算引擎首选** |
| **building-carbon-ai 建筑碳管理平台** | https://github.com/c50346867/building-carbon-ai | Scope 1/2/3 计算、预测、企业级 Web，符合 GB/T 51366 | 整站参考/二开 |
| **Building Carbon Quota Engine** | https://github.com/SheltonXiao/Building-carbon-quota-engine | 碳配额/能耗限额引擎，国标/省标/历史数据三种模式，35 省 731 城 | 配额评估场景 |
| **CarboLifeCalc** | https://github.com/DavidVeld/CarboLifeCalc | 开源内含碳计算器，Revit/Grasshopper 兼容 | 建材碳计算 + Revit 联动 |
| **HBERT** | https://github.com/HawkinsbrownArch/HBERT | Revit 插件测模型内含碳 | Revit 方向集成 |
| **AmberGreen 碳足迹计算器** | https://github.com/CrocoDealu/AI-Driven-Carbon-Footprint-Calculator | Ollama Llama3.1 本地推理 + Prophet 预测 | **本地推理 + 预测参考架构** |
| **CarbonTrace AI** | https://github.com/lugasraka/SideProject-Scope3Analytics | Scope 3 估算 + 优化 + 可视化 | 估算方法参考 |

### Agent / 多智能体架构参考（思路级别）

| 项目 | 链接 | 亮点 |
|---|---|---|
| **GAIA 可持续基建自主 Agent** | https://github.com/neural-architect-au/gaia | AWS Hackathon 2025 获奖，建筑能耗优化，实测减排 12%，**多智能体架构范本** |
| **GIS2BEM** | https://github.com/UBEM-MCP/gis2bem-agent | GIS→EnergyPlus 建模，MCP server + ReAct agent，**MCP 工程范式** |
| **Autonomous Building Performance Engineering** | https://github.com/mlsmall/autonomous-building-performance-engineering | 工程计算 + 生成式 AI 多智能体 |
| **ESG Intelligence Agent** | https://github.com/yenlikgaisina/esg-intelligence-agent | 建筑业 ESG 自动分析 + LCA + PDF 简报 |
| **CarbonLens** | https://github.com/RastinAghighi/CarbonLens | 多 agent 解析采购清单算 Scope 3 |
| **MASSE 结构工程多智能体** | https://github.com/DelosLiang/masse | 结构工程多智能体系统（有 arXiv 论文） |
| **BIM AI Agent（Revit × Claude MCP）** | https://github.com/Ziad-Amr1/bim-ai-agent | 自然语言查/改 Revit 模型，AI 生成命令 Revit 执行 |

### 框架/组件（自己拼装用）

- **LangGraph / LangChain**：Agent 编排（有向图、工具调用、状态管理）
- **Dify**：可视化工作流 + 界面，本地 docker 部署
- **CrewAI / AutoGen / MetaGPT**：多智能体协作
- **Ollama + Qwen2.5**：本地推理（RTX 4060 8GB 可行）
- **Gradio / Streamlit**：快速交互界面
- **openLCA**：开源 LCA 软件（GPL），生命周期评估数据与逻辑参考

## 四、复用策略（拿到项目后）

1. **先跑通再改**：README 一键运行 → 确认闭环 → 再做定制
2. **计算内核优先复用**：碳排放计算是"标准实现"，自写易错、评审可验证性差，直接复用 MIT 实现并注明来源
3. **Agent 层自己搭**：用 LangGraph/Dify 搭编排，体现工程能力
4. **数据自造可控**：演示数据用标准参数表 + 脱敏样例，保证可复现
5. **引用规范**：复用开源代码须在申报书/README 标注项目名与许可证（原创审查会查）
