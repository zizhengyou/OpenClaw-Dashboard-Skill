---
name: dashboard-gen
description: >
  BI数据看板生成Skill。用户上传Excel/CSV数据文件，指定维度、度量和图表类型，
  自动生成交互式HTML数据看板。支持柱状图、折线图、饼图、散点图、KPI卡片和数据表格。
  触发场景：用户说"生成看板"、"做个图表"、"出报表"、"数据可视化"等。
requirements:
  - python3
  - pip install pandas openpyxl pyecharts
---

# dashboard-gen

根据用户指定的Excel/CSV数据字段和图表需求，自动生成交互式HTML数据看板。

## 触发条件

当用户的意图涉及以下关键词或场景时，激活此Skill：
- "生成看板"、"做个看板"、"出看板"
- "做个图表"、"画个图"、"数据可视化"
- "出报表"、"生成报表"
- "分析一下这个Excel"、"帮我看看这个数据"
- 用户已确认要使用哪些字段，并表达了图表需求

## 前置条件

在执行此Skill之前，必须确保：
1. 用户已上传或指定了Excel/CSV文件路径
2. 文件路径在本地可访问（OpenClaw 本地运行，所以可以直接读取）
3. 用户已明确或可推断出图表需求

如果信息不完整，先引导用户补充，不要盲目生成。

## 依赖安装

本Skill需要Python环境和以下库：

```bash
# 方式1：使用安装脚本（推荐）
bash scripts/setup.sh

# 方式2：手动安装
pip install pandas openpyxl pyecharts
```

## 工作流程

### Step 1: 探查数据

先读取Excel文件，获取字段列表和数据概况：

```bash
python scripts/dashboard_generator.py --probe '文件路径.xlsx'
```

输出示例：
```
📁 文件：销售数据.xlsx
📏 规模：1234行 × 8列
📌 字段：地区(文本), 月份(文本), 销售额(数值), 订单量(数值), ...
```

### Step 2: 收集看板配置

根据用户需求，组装配置JSON：

```json
{
  "source_file": "用户的Excel文件路径",
  "sheet": 0,
  "title": "看板标题",
  "style": "business",
  "charts": [
    {
      "type": "bar|line|pie|kpi_card|scatter|table",
      "dimension": "维度字段名（X轴/分类）",
      "measure": "度量字段名（Y轴/数值）",
      "agg": "sum|mean|count|max|min",
      "label": "图表标题（可选）"
    }
  ]
}
```

### Step 3: 执行看板生成

调用脚本生成HTML看板：

```bash
python scripts/dashboard_generator.py --config '配置JSON' --output output.html
```

或用JSON文件传入配置：
```bash
python scripts/dashboard_generator.py --config config.json --output output.html
```

### Step 4: 输出结果

生成完成后：
1. 告知用户HTML文件的保存路径
2. 提示用户用浏览器打开查看（`open output.html`）
3. 询问是否需要调整图表

## 支持的图表类型

| 类型 | type值 | 说明 | 必需字段 |
|------|--------|------|----------|
| 柱状图 | `bar` | 维度对比 | dimension + measure |
| 折线图 | `line` | 趋势变化 | dimension + measure |
| 饼图 | `pie` | 占比分析 | dimension + measure |
| KPI卡片 | `kpi_card` | 核心指标数字 | measure + agg |
| 散点图 | `scatter` | 相关性分析 | dimension + measure |
| 数据表格 | `table` | 明细展示 | 可选columns字段 |

## 聚合方式

| agg值 | 说明 |
|-------|------|
| `sum` | 求和（默认） |
| `mean` | 平均值 |
| `count` | 计数 |
| `max` | 最大值 |
| `min` | 最小值 |

## 输出规范

- 输出格式：单个HTML文件（内嵌CSS + JS + ECharts CDN）
- 文件命名：`{标题}_{日期}.html`
- 看板布局：响应式Grid布局，适配PC和平板
- 必含元素：看板标题、数据更新时间、图表区域
- 配色方案：默认商务蓝（business），支持dark/light主题

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| Excel文件不存在 | 提示用户检查文件路径 |
| 指定列名不存在 | 列出所有可用列名，让用户重新选择 |
| 数据为空 | 提示"该字段无有效数据，建议换一个字段" |
| 依赖未安装 | 提示运行 `bash scripts/setup.sh` 安装依赖 |

## 边界

**做：**
- 根据用户确认的配置生成看板
- 支持多图表组合布局
- 自动处理数据聚合
- 生成可直接浏览器打开的HTML
- 支持 --probe 模式快速探查数据结构

**不做：**
- 不自行推测用户想看什么（那是AI对话层的事）
- 不修改原始Excel文件
- 不启动Web服务（只生成静态HTML）
- 不做数据清洗（假设数据已就绪）
