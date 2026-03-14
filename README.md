# 📊 OpenClaw Dashboard Skill — BI 数据看板自动生成器

> 上传 Excel/CSV → 指定图表需求 → 一键生成交互式 HTML 数据看板

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 这是什么？

这是一个 **OpenClaw Skill**（技能插件），安装后你可以在 IM 聊天中对 OpenClaw 说：

> "帮我用这个 Excel 生成一个数据看板"

OpenClaw 就会自动读取数据、和你确认需求、生成一个可以直接在浏览器打开的交互式 HTML 看板。

**核心能力：**
- 🔍 **数据探查**：自动识别字段类型（维度/度量/时间），给出分析建议
- 📊 **多图表支持**：柱状图、折线图、饼图、散点图、KPI 卡片、数据表格
- 🎨 **主题配色**：商务蓝（默认）、暗色、亮色三种风格
- 📱 **响应式布局**：PC 和平板都能正常查看
- ⚡ **零依赖前端**：生成的 HTML 内嵌所有样式和 ECharts CDN，双击即可打开

---

## 📁 目录结构

```
OpenClaw-Dashboard-Skill/
├── SKILL.md                    # Skill 定义文件（触发条件、工作流、参数说明）
├── requirements.txt            # Python 依赖清单
├── README.md                   # 本文件
├── BI数据看板工作流梳理.md      # 完整需求与设计文档
├── scripts/
│   ├── dashboard_generator.py  # 核心引擎（数据读取 → 图表生成 → HTML 输出）
│   └── setup.sh                # 一键依赖安装脚本
└── .gitignore
```

---

## 🚀 快速安装

### 在 OpenClaw 中安装（推荐）

```bash
# 克隆到 OpenClaw 用户技能目录
git clone https://github.com/zizhengyou/OpenClaw-Dashboard-Skill.git ~/.openclaw/skills/dashboard-gen

# 安装 Python 依赖
bash ~/.openclaw/skills/dashboard-gen/scripts/setup.sh
```

### 手动安装依赖

```bash
pip install pandas openpyxl pyecharts
```

**环境要求：** Python 3.8+

---

## 📖 使用方法

### 方式一：通过 OpenClaw 对话使用

安装完成后，直接跟 OpenClaw 说：

```
"帮我用 ~/数据/销售报表.xlsx 生成一个数据看板"
```

OpenClaw 会自动匹配到本 Skill，引导你完成看板配置。

### 方式二：命令行直接使用

**① 探查数据结构**

```bash
python scripts/dashboard_generator.py --probe '你的文件.xlsx'
```

输出示例：
```
📊 数据探查报告
━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 文件：销售数据.xlsx
📏 规模：1,234行 × 8列

📌 字段详情：
  地区(文本, 5种值) 示例: 华东, 华北, 华南
  月份(文本, 12种值) 示例: 1月, 2月, 3月
  销售额(数值, 892种值) 示例: 12500.0, 8900.5, 23100.0

🎯 自动识别：
  [维度字段] 地区, 月份
  [度量字段] 销售额, 订单量
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**② 生成看板**

```bash
python scripts/dashboard_generator.py \
  --config '{
    "source_file": "销售数据.xlsx",
    "title": "2025年销售数据看板",
    "style": "business",
    "charts": [
      {"type": "kpi_card", "measure": "销售额", "agg": "sum", "label": "总销售额"},
      {"type": "bar", "dimension": "地区", "measure": "销售额", "agg": "sum"},
      {"type": "line", "dimension": "月份", "measure": "销售额", "agg": "sum"},
      {"type": "pie", "dimension": "产品类别", "measure": "销售额", "agg": "sum"}
    ]
  }' \
  --output 我的看板.html
```

**③ 用配置文件生成**

```bash
python scripts/dashboard_generator.py --config config.json --output 我的看板.html
```

### 方式三：Python 代码调用

```python
from scripts.dashboard_generator import generate_dashboard

config = {
    "source_file": "销售数据.xlsx",
    "title": "销售看板",
    "charts": [
        {"type": "bar", "dimension": "地区", "measure": "销售额", "agg": "sum"}
    ]
}

generate_dashboard(config, "output.html")
```

---

## 📊 支持的图表类型

| 类型 | `type` 值 | 适用场景 | 必需字段 |
|------|-----------|----------|----------|
| 柱状图 | `bar` | 维度对比（如各地区销售额） | `dimension` + `measure` |
| 折线图 | `line` | 趋势分析（如按月变化） | `dimension` + `measure` |
| 饼图 | `pie` | 占比分析（如品类构成） | `dimension` + `measure` |
| 散点图 | `scatter` | 相关性分析 | `dimension` + `measure` |
| KPI 卡片 | `kpi_card` | 核心指标展示（如总销售额） | `measure` + `agg` |
| 数据表格 | `table` | 明细数据查看 | 可选 `columns` |

---

## 🔢 聚合方式

| `agg` 值 | 含义 |
|-----------|------|
| `sum` | 求和（默认） |
| `mean` | 平均值 |
| `count` | 计数 |
| `max` | 最大值 |
| `min` | 最小值 |

---

## ⚙️ 配置参数说明

```json
{
  "source_file": "Excel或CSV文件路径（必填）",
  "sheet": 0,
  "title": "看板标题",
  "style": "business | dark | light",
  "charts": [
    {
      "type": "图表类型",
      "dimension": "维度字段名（X轴/分类）",
      "measure": "度量字段名（Y轴/数值）",
      "agg": "聚合方式",
      "label": "图表标题（可选）"
    }
  ]
}
```

---

## 🎨 主题样式

| 主题 | `style` 值 | 说明 |
|------|------------|------|
| 商务蓝 | `business` | 默认主题，专业沉稳 |
| 暗色 | `dark` | 深色背景，适合大屏展示 |
| 亮色 | `light` | 浅色简约风 |

---

## 🛠 技术栈

| 组件 | 用途 |
|------|------|
| [pandas](https://pandas.pydata.org/) | 数据读取与聚合计算 |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel .xlsx 文件解析 |
| [pyecharts](https://pyecharts.org/) | 基于 Apache ECharts 的图表生成 |

---

## 📋 常见问题

**Q: 支持哪些文件格式？**
A: `.xlsx`、`.xls`、`.csv` 三种格式。

**Q: 生成的看板需要联网吗？**
A: 首次打开需要联网加载 ECharts CDN（约 1MB），之后浏览器会缓存。

**Q: 如何修改看板样式？**
A: 修改 `config` 中的 `style` 字段，或直接编辑生成的 HTML 文件中的 CSS。

**Q: 数据量有限制吗？**
A: 理论上无限制，但建议单文件不超过 10 万行以保证生成速度。数据表格默认只展示前 50 行。

---

## 📄 License

MIT License — 随意使用、修改和分发。
