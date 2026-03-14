# BI 数据看板自动生成工作流 — 需求定稿

> 📌 已整合用户标注 + AI落地方案，作为开发正式需求依据。
> 🦞 本版本已适配 OpenClaw Skill 目录规范。

---

## 一、整体流程（定稿版）

```
Excel文件输入
    ↓
[Skill-1] 数据体检 → 输出"数据体检报告"
    ↓
[AI对话层] 命令行问答式确认需求
    ↓
[Skill-2] 根据配置生成 HTML 数据看板
    ↓
[长期规划] 配置可保存为模板 → 下次一键复用
```

> **架构决策**：拆成 2 个 Skill + AI 对话串联（非单 Skill 一把梭）  
> - Skill-1（数据体检）：确定性脚本，输入Excel → 输出报告  
> - AI对话层（需求确认）：天然适合对话，不做成Skill  
> - Skill-2（看板生成）：确定性脚本，输入配置 → 输出HTML  
> - 配置文件保存后可复用，实现"积累→转化为长期任务"

---

## 二、Skill-1：数据体检

### 2.1 识别规则

| 识别项 | 用户规则 | 落地方案 |
|--------|----------|----------|
| Sheet | 先只支持1个 | 默认第1个Sheet，多Sheet时提示选择 |
| 表头 | 第1行为表头 | `header=0`，第1行全空则尝试第2行 |
| 数据类型 | 自动识别 | `pandas.api.types` + 正则检测日期 |
| 空行处理 | 连续≥5空行=数据结束；<5空行=缺失 | 扫描后截断 + 标记NaN |
| 数据质量 | 同空行兜底 | 缺失率 + 重复行 + IQR异常值检测 |

### 2.2 智能推断

| 推断项 | 方案 |
|--------|------|
| 维度字段 | 文本/类别型（唯一值 < 总行数30%） |
| 度量字段 | 数值型（int/float） |
| 时间字段 | 日期格式列 → 自动标记 |
| 推荐角度 | 维度×度量组合 → 生成2-3条建议 |

### 2.3 输出物示例

```
📊 数据体检报告
━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 文件：销售数据2025.xlsx | Sheet1
📏 规模：1,234行 × 8列

📌 字段分类：
  [维度] 地区、部门、产品类别
  [度量] 销售额、订单量、利润率
  [时间] 月份

⚠️ 质量：缺失23个(1.9%) | 重复0行 | 异常值3个

💡 推荐：
  1. 按"地区"对比"销售额" → 柱状图
  2. 按"月份"看"销售额"趋势 → 折线图
  3. 按"产品类别"看占比 → 饼图
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 三、AI对话层：需求确认

### 3.1 交互方式

> **用户选择**：命令行问答式  
> **用户补充**：先积累，后续可转化为长期任务模板直接产出

**落地方案**：
1. 首次：AI基于体检报告逐步提问（5-6个问题）
2. 回答后生成 `dashboard_config.json` 配置文件
3. 配置文件可保存 → 下次加载跳过问答 → "长期任务模板"

### 3.2 配置文件格式

```json
{
  "source_file": "销售数据2025.xlsx",
  "sheet": 0,
  "title": "2025年销售数据看板",
  "style": "business",
  "charts": [
    {"type": "kpi_card", "measure": "销售额", "agg": "sum", "label": "总销售额"},
    {"type": "bar", "dimension": "地区", "measure": "销售额", "agg": "sum"},
    {"type": "line", "dimension": "月份", "measure": "销售额", "agg": "sum"}
  ],
  "output_format": "html"
}
```

> 积累配置后，可说"用上次配置生成新数据的看板"→ 跳过问答直接出图。

---

## 四、Skill-2：看板生成

### 4.1 支持看板类型（全部✅）

| 类型 | 核心图表 | 场景 |
|------|----------|------|
| 综合总览型 | KPI卡片 + 折线 + 饼图 + TOP表 | 一页看全局 |
| 趋势分析型 | 折线图 + 面积图 + 同比环比 | 看时间变化 |
| 对比分析型 | 分组柱状 + 雷达图 | 多组对比 |
| 占比分析型 | 饼图/环形 + 堆叠柱状 | 看构成 |
| 明细报表型 | 可排序表格 + 条件格式 | 看原始数据 |

### 4.2 通用元素

| 元素 | 状态 |
|------|------|
| 看板标题 | ✅ 必须 |
| 数据更新时间 | ✅ 必须 |
| KPI 卡片区 | 按需 |
| 图表区（1-4个） | ✅ 核心 |
| 数据明细表格 | 按需 |
| 筛选器/下拉 | 按需 |

### 4.3 输出格式

> 主输出：**HTML**（配合pyecharts最自然，可交互可分享）  
> 后续可扩展PNG/PDF导出

---

## 五、开源工具调研（重要！）

> **用户反馈**：数据体检不应做 Skill，应该做 Agent。Skill 工具负责"拆 Excel → 转数据库表"，然后 Agent 根据字段去分析。  
> **结论**：有大量成熟开源工具可以直接用，不用从零造轮子。

### 5.1 核心开源工具对比

| 工具 | GitHub 星数 | 定位 | 能力 | 适合我们哪个环节 |
|------|-------------|------|------|-----------------|
| **PandasAI** | 15k+ | 用自然语言和数据对话 | Excel/CSV/SQL → LLM自动生成pandas代码 → 返回分析结果和图表 | ⭐ **数据体检 + 智能推断**（直接替代 Skill-1 的大部分工作） |
| **Vanna AI** | 12k+ | Text-to-SQL（RAG框架） | 自然语言 → SQL查询，支持SQLite/PG/MySQL | ⭐ **Excel转数据库后做复杂查询**（你说的"转表后按字段分析"） |
| **Chat2DB** | 15k+ | AI数据库管理工具 | 自然语言生成SQL + 自动生成报表，支持多种数据库 | 适合已有数据库的场景，对我们偏重 |
| **PyGWalker** | 13k+ | Python版Tableau | 一行代码把DataFrame变成可拖拽的交互式可视化界面 | ⭐ **看板生成**（直接替代 Skill-2，而且是交互式的！） |
| **Streamlit** | 36k+ | Python快速建Web应用 | 上传Excel → 展示图表/表格/筛选器，部署方便 | ⭐ **整体UI框架**（把所有功能串起来） |

### 5.2 推荐方案：组合使用

```
用户上传 Excel
    ↓
[Skill] pandas + openpyxl 拆 Excel → 转 SQLite 数据库表
    ↓
[Agent] PandasAI / Vanna AI 做数据体检 + 智能推断
    ↓  （Agent 可调用 LLM，理解字段语义，推荐分析角度）
[AI对话层] 与用户确认需求
    ↓
[Skill/工具] PyGWalker 或 pyecharts 生成看板
    ↓
[输出] 交互式 HTML 看板
```

---

## 六、技术选型（更新版）

| 环节 | 选择 | 备选 |
|------|------|------|
| Excel读取 | ✅ pandas + openpyxl | — |
| Excel→数据库 | ✅ pandas → SQLite | — |
| 数据体检Agent | ✅ PandasAI（LLM驱动） | Vanna AI（SQL驱动） |
| 可视化引擎 | ✅ pyecharts（V1） | PyGWalker（V2进阶） |
| 看板布局 | ✅ pyecharts Page + CSS | Streamlit（V2进阶） |
| 输出格式 | ✅ HTML 为主 | — |

---

## 七、最终定稿流程（V3 - 精简版）

> 经过多轮讨论，最终确认：阶段1不需要独立Skill，利用已有的 xlsx Skill + AI对话就能搞定。只需新建**1个Skill（看板生成）**。

### 7.1 四步流程

```
步骤1: 用户上传 Excel
    → [xlsx Skill] 读取文件内容
    ↓
步骤2: AI 整理表头展示给用户确认
    → AI对话天然能力：列出列名、数据类型、样例值
    → 用户确认"我要用A列、C列做看板" ← 不是盲盒！
    ↓
步骤3: 用户明确看板意图
    → "A列做X轴，C列做Y轴，柱状图"
    → "再加一个B列的饼图"
    ↓
步骤4: 生成看板 [dashboard-gen Skill]
    → PyEcharts 生成交互式 HTML 文件
    → 浏览器打开即可查看
```

### 7.2 配置示例

```json
{
  "source_file": "销售数据2025.xlsx",
  "sheet": 0,
  "title": "2025年销售数据看板",
  "style": "business",
  "charts": [
    {"type": "kpi_card", "measure": "销售额", "agg": "sum", "label": "总销售额"},
    {"type": "bar", "dimension": "地区", "measure": "销售额", "agg": "sum"},
    {"type": "line", "dimension": "月份", "measure": "销售额", "agg": "sum"},
    {"type": "pie", "dimension": "产品类别", "measure": "销售额", "agg": "sum"}
  ]
}
```

---

## 八、OpenClaw 部署指南

> 🦞 本项目已适配 OpenClaw Skill 目录规范，可直接作为 Skill 安装使用。

### 8.1 部署方式

**方式一：用户技能目录（全局生效）**

```bash
# 把整个文件夹复制到 OpenClaw 的用户技能目录
cp -r OpenClaw-Dashboard-Skill ~/.openclaw/skills/dashboard-gen

# 安装 Python 依赖
bash ~/.openclaw/skills/dashboard-gen/scripts/setup.sh
```

**方式二：工作区技能目录（项目级）**

```bash
# 在你的 OpenClaw 工作区中创建 skills 目录
cp -r OpenClaw-Dashboard-Skill <你的工作区>/skills/dashboard-gen

# 安装 Python 依赖
bash <你的工作区>/skills/dashboard-gen/scripts/setup.sh
```

### 8.2 使用方式

在 IM 软件（QQ/飞书/Telegram 等）中对 OpenClaw 说：

```
"帮我用 ~/数据/销售报表.xlsx 生成一个数据看板"
```

OpenClaw 会：
1. 匹配到 `dashboard-gen` Skill
2. 先用 `--probe` 模式探查数据结构
3. 和你确认图表需求
4. 调用 `dashboard_generator.py` 生成 HTML
5. 告诉你文件路径，用浏览器打开即可

### 8.3 Skill 优先级

OpenClaw 加载 Skill 的优先级（同名覆盖规则）：

```
<workspace>/skills/  > ~/.openclaw/skills/  > bundled skills
（工作区，最高）       （用户目录，中）        （内置，最低）
```

### 8.4 目录结构

```
dashboard-gen/                  ← OpenClaw Skill 根目录
├── SKILL.md                    # Skill 定义（触发条件、工作流、依赖声明）
├── requirements.txt            # Python 依赖清单
├── scripts/
│   ├── dashboard_generator.py  # 核心引擎（读数据→生成HTML看板）
│   └── setup.sh                # 依赖安装脚本
└── BI数据看板工作流梳理.md      # 完整需求文档（本文件）
```

### 8.5 与原版的区别

| 项目 | 原版 (BI-Dashboard-Generator) | OpenClaw 版 |
|------|-------------------------------|------------|
| 目录结构 | 扁平，py文件在根目录 | 脚本放 `scripts/` 子目录 |
| SKILL.md | CodeBuddy 格式 | 增加 `requirements` 字段 |
| 新增功能 | 无 | `--probe` 数据探查模式 |
| 安装脚本 | 无 | `scripts/setup.sh` 一键安装 |
| 部署位置 | `.codebuddy/skills/` | `~/.openclaw/skills/` |
| 页脚标识 | Powered by PyEcharts | 增加 OpenClaw Skill 标识 |

---

> 🚀 **下一步**：部署到 OpenClaw 后，找一个真实 Excel 文件测试完整流程！
