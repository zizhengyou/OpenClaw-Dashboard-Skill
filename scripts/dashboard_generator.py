#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BI 看板生成器 (dashboard_generator.py) — OpenClaw Skill 版
==========================================================
功能：读取 Excel/CSV 数据 + 用户配置，生成交互式 HTML 数据看板。
技术栈：pandas + pyecharts
适配：OpenClaw Skill 目录规范（scripts/ 子目录）

使用方式：
    1. 数据探查：python dashboard_generator.py --probe '文件路径.xlsx'
    2. 生成看板：python dashboard_generator.py --config '{"source_file":"xx.xlsx", ...}' --output output.html
    3. Python调用：from dashboard_generator import generate_dashboard; generate_dashboard(config, output_path)

运行前请确保已安装依赖：
    pip install pandas openpyxl pyecharts
    或运行: bash scripts/setup.sh
"""

import json
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# ========== 第三方库导入（带友好报错提示） ==========
try:
    import pandas as pd
except ImportError:
    print("❌ 缺少 pandas 库，请运行: pip install pandas openpyxl")
    print("   或执行安装脚本: bash scripts/setup.sh")
    sys.exit(1)

try:
    from pyecharts.charts import Bar, Line, Pie, Scatter, Page, Grid
    from pyecharts import options as opts
    from pyecharts.globals import ThemeType
except ImportError:
    print("❌ 缺少 pyecharts 库，请运行: pip install pyecharts")
    print("   或执行安装脚本: bash scripts/setup.sh")
    sys.exit(1)


# ========== 主题配色方案 ==========
# business（商务蓝）对应 pyecharts 的 WALDEN 主题，dark 对应 DARK
THEME_MAP = {
    "business": ThemeType.WALDEN,
    "dark": ThemeType.DARK,
    "light": ThemeType.LIGHT,
}


def probe_data(source_file: str, sheet: int = 0) -> str:
    """
    探查数据文件结构，返回人类可读的概况报告。
    
    这是 OpenClaw 新增的功能：用户说"帮我看看这个文件"时，
    先用 --probe 模式快速了解数据长什么样，再决定做什么图表。
    
    参数：
        source_file: Excel/CSV 文件路径
        sheet: Sheet 索引，默认第一个 Sheet
    返回：
        格式化的数据概况字符串
    """
    df = read_excel_data(source_file, sheet)
    
    # 收集字段信息
    fields_info = []
    for col in df.columns:
        dtype = df[col].dtype
        non_null = df[col].count()
        null_count = df[col].isnull().sum()
        unique_count = df[col].nunique()
        
        # 判断字段类型标签
        if pd.api.types.is_numeric_dtype(df[col]):
            type_label = "数值"
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            type_label = "日期"
        else:
            type_label = "文本"
        
        # 采样前3个值作为示例
        sample_vals = df[col].dropna().head(3).tolist()
        sample_str = ", ".join([str(v) for v in sample_vals])
        
        fields_info.append(f"  {col}({type_label}, {unique_count}种值) 示例: {sample_str}")
        if null_count > 0:
            fields_info[-1] += f" [缺失{null_count}个]"
    
    # 自动推荐维度和度量
    dimensions = []
    measures = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            measures.append(col)
        elif df[col].nunique() < len(df) * 0.3:
            dimensions.append(col)
    
    # 组装报告
    report = f"""
📊 数据探查报告
━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 文件：{source_file}
📏 规模：{len(df):,}行 × {len(df.columns)}列

📌 字段详情：
{chr(10).join(fields_info)}

🎯 自动识别：
  [维度字段] {', '.join(dimensions) if dimensions else '(未识别到)'}
  [度量字段] {', '.join(measures) if measures else '(未识别到)'}
"""
    
    # 生成推荐配置
    if dimensions and measures:
        report += "\n💡 推荐配置：\n"
        suggestions = []
        if len(dimensions) >= 1 and len(measures) >= 1:
            suggestions.append(
                f'  1. 柱状图: {{"type":"bar", "dimension":"{dimensions[0]}", "measure":"{measures[0]}", "agg":"sum"}}'
            )
        if len(dimensions) >= 1 and len(measures) >= 1:
            suggestions.append(
                f'  2. 饼图: {{"type":"pie", "dimension":"{dimensions[0]}", "measure":"{measures[0]}", "agg":"sum"}}'
            )
        if len(measures) >= 1:
            suggestions.append(
                f'  3. KPI: {{"type":"kpi_card", "measure":"{measures[0]}", "agg":"sum"}}'
            )
        report += "\n".join(suggestions)
    
    report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return report


def read_excel_data(source_file: str, sheet: int = 0) -> pd.DataFrame:
    """
    读取 Excel 文件，返回 DataFrame。
    
    参数：
        source_file: Excel 文件路径（支持 .xlsx / .xls / .csv）
        sheet: Sheet 索引，默认第一个 Sheet
    返回：
        pandas DataFrame
    """
    # 使用 pathlib 确保跨平台路径兼容（Windows / macOS / Linux 都能跑）
    file_path = Path(source_file).expanduser().resolve()
    
    if not file_path.exists():
        raise FileNotFoundError(f"❌ 文件不存在: {file_path}")
    
    # 根据文件后缀选择读取方式
    suffix = file_path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, sheet_name=sheet)
    elif suffix == ".csv":
        df = pd.read_csv(file_path)
    else:
        raise ValueError(f"❌ 不支持的文件格式: {suffix}，请使用 .xlsx / .xls / .csv")
    
    if df.empty:
        raise ValueError("❌ 文件中没有数据，请检查文件内容")
    
    return df


def aggregate_data(df: pd.DataFrame, dimension: str, measure: str, agg: str = "sum") -> pd.DataFrame:
    """
    按维度字段对度量字段做聚合计算。
    
    参数：
        df: 原始数据
        dimension: 维度字段名（如"地区"）—— 用来分组
        measure: 度量字段名（如"销售额"）—— 用来计算
        agg: 聚合方式，可选 sum/mean/count/max/min
    返回：
        聚合后的 DataFrame，包含 dimension 和 measure 两列
    """
    # 校验字段名是否存在
    available_cols = list(df.columns)
    if dimension not in available_cols:
        raise ValueError(f"❌ 维度字段 '{dimension}' 不存在。可用字段: {available_cols}")
    if measure not in available_cols:
        raise ValueError(f"❌ 度量字段 '{measure}' 不存在。可用字段: {available_cols}")
    
    # 执行分组聚合
    agg_map = {"sum": "sum", "mean": "mean", "count": "count", "max": "max", "min": "min"}
    agg_func = agg_map.get(agg, "sum")  # 默认 sum
    
    result = df.groupby(dimension, as_index=False).agg({measure: agg_func})
    
    # 按度量值降序排列，让图表更好看
    result = result.sort_values(by=measure, ascending=False)
    
    return result


def create_bar_chart(df: pd.DataFrame, dimension: str, measure: str,
                     agg: str = "sum", label: str = "", theme: str = "business") -> Bar:
    """
    生成柱状图。
    
    参数：
        df: 原始 DataFrame
        dimension: X 轴字段名
        measure: Y 轴字段名
        agg: 聚合方式
        label: 图表标题（可选，默认自动生成）
        theme: 配色主题
    返回：
        pyecharts Bar 对象
    """
    data = aggregate_data(df, dimension, measure, agg)
    
    # X 轴标签（维度值）和 Y 轴数据（度量值）
    x_data = [str(x) for x in data[dimension].tolist()]
    y_data = [round(float(y), 2) for y in data[measure].tolist()]
    
    # 自动生成标题：如 "各地区的销售额（求和）"
    agg_label = {"sum": "求和", "mean": "平均", "count": "计数", "max": "最大值", "min": "最小值"}
    chart_title = label or f"各{dimension}的{measure}（{agg_label.get(agg, agg)}）"
    
    bar = (
        Bar(init_opts=opts.InitOpts(
            theme=THEME_MAP.get(theme, ThemeType.WALDEN),
            width="100%",
            height="400px",
        ))
        .add_xaxis(x_data)
        .add_yaxis(measure, y_data, label_opts=opts.LabelOpts(is_show=True, position="top"))
        .set_global_opts(
            title_opts=opts.TitleOpts(title=chart_title),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),  # X轴标签倾斜防重叠
            datazoom_opts=opts.DataZoomOpts() if len(x_data) > 10 else None,  # 数据多时加滚动条
        )
    )
    return bar


def create_line_chart(df: pd.DataFrame, dimension: str, measure: str,
                      agg: str = "sum", label: str = "", theme: str = "business") -> Line:
    """
    生成折线图（适合趋势分析，如按月份看变化）。
    """
    data = aggregate_data(df, dimension, measure, agg)
    
    x_data = [str(x) for x in data[dimension].tolist()]
    y_data = [round(float(y), 2) for y in data[measure].tolist()]
    
    agg_label = {"sum": "求和", "mean": "平均", "count": "计数", "max": "最大值", "min": "最小值"}
    chart_title = label or f"{measure}随{dimension}的变化趋势（{agg_label.get(agg, agg)}）"
    
    line = (
        Line(init_opts=opts.InitOpts(
            theme=THEME_MAP.get(theme, ThemeType.WALDEN),
            width="100%",
            height="400px",
        ))
        .add_xaxis(x_data)
        .add_yaxis(
            measure, y_data,
            is_smooth=True,  # 平滑曲线
            label_opts=opts.LabelOpts(is_show=False),
            markpoint_opts=opts.MarkPointOpts(data=[
                opts.MarkPointItem(type_="max", name="最大值"),
                opts.MarkPointItem(type_="min", name="最小值"),
            ]),
            markline_opts=opts.MarkLineOpts(data=[
                opts.MarkLineItem(type_="average", name="平均值"),
            ]),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title=chart_title),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
        )
    )
    return line


def create_pie_chart(df: pd.DataFrame, dimension: str, measure: str,
                     agg: str = "sum", label: str = "", theme: str = "business") -> Pie:
    """
    生成饼图（适合占比分析）。
    """
    data = aggregate_data(df, dimension, measure, agg)
    
    # 饼图数据格式：[(名称, 数值), (名称, 数值), ...]
    pie_data = [(str(row[dimension]), round(float(row[measure]), 2))
                for _, row in data.iterrows()]
    
    agg_label = {"sum": "求和", "mean": "平均", "count": "计数", "max": "最大值", "min": "最小值"}
    chart_title = label or f"{measure}的{dimension}分布（{agg_label.get(agg, agg)}）"
    
    pie = (
        Pie(init_opts=opts.InitOpts(
            theme=THEME_MAP.get(theme, ThemeType.WALDEN),
            width="100%",
            height="400px",
        ))
        .add(
            measure,
            pie_data,
            radius=["30%", "60%"],  # 环形图，更美观
            label_opts=opts.LabelOpts(formatter="{b}: {d}%"),  # 显示百分比
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title=chart_title),
            tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{b}: {c} ({d}%)"),
            legend_opts=opts.LegendOpts(orient="vertical", pos_left="left"),
        )
    )
    return pie


def create_scatter_chart(df: pd.DataFrame, dimension: str, measure: str,
                         agg: str = "sum", label: str = "", theme: str = "business") -> Scatter:
    """
    生成散点图（适合相关性分析）。
    """
    data = aggregate_data(df, dimension, measure, agg)
    
    x_data = [str(x) for x in data[dimension].tolist()]
    y_data = [round(float(y), 2) for y in data[measure].tolist()]
    
    chart_title = label or f"{dimension} vs {measure} 散点分布"
    
    scatter = (
        Scatter(init_opts=opts.InitOpts(
            theme=THEME_MAP.get(theme, ThemeType.WALDEN),
            width="100%",
            height="400px",
        ))
        .add_xaxis(x_data)
        .add_yaxis(measure, y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title=chart_title),
            tooltip_opts=opts.TooltipOpts(trigger="item"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
        )
    )
    return scatter


def create_kpi_html(df: pd.DataFrame, measure: str, agg: str = "sum", label: str = "") -> str:
    """
    生成 KPI 卡片的 HTML 片段（不是 pyecharts 图表，是纯 HTML）。
    
    参数：
        df: 原始 DataFrame
        measure: 度量字段名
        agg: 聚合方式
        label: 卡片标题
    返回：
        HTML 字符串
    """
    if measure not in df.columns:
        raise ValueError(f"❌ 度量字段 '{measure}' 不存在。可用字段: {list(df.columns)}")
    
    # 计算聚合值
    agg_func = {"sum": "sum", "mean": "mean", "count": "count", "max": "max", "min": "min"}
    value = getattr(df[measure], agg_func.get(agg, "sum"))()
    
    # 格式化数字：大数字加逗号分隔
    if isinstance(value, float):
        formatted = f"{value:,.2f}"
    else:
        formatted = f"{value:,}"
    
    agg_label = {"sum": "合计", "mean": "平均", "count": "总数", "max": "最大", "min": "最小"}
    card_title = label or f"{measure}（{agg_label.get(agg, agg)}）"
    
    return f"""
    <div class="kpi-card">
        <div class="kpi-title">{card_title}</div>
        <div class="kpi-value">{formatted}</div>
    </div>
    """


def create_table_html(df: pd.DataFrame, columns: list = None, max_rows: int = 50) -> str:
    """
    生成数据明细表格的 HTML 片段。
    
    参数：
        df: 原始 DataFrame
        columns: 要展示的列名列表（为空则展示全部）
        max_rows: 最多展示多少行（防止 HTML 太大）
    返回：
        HTML 字符串
    """
    if columns:
        # 过滤存在的列
        valid_cols = [c for c in columns if c in df.columns]
        if not valid_cols:
            raise ValueError(f"❌ 指定的列都不存在。可用字段: {list(df.columns)}")
        display_df = df[valid_cols].head(max_rows)
    else:
        display_df = df.head(max_rows)
    
    # 用 pandas 自带的 to_html 生成表格
    table_html = display_df.to_html(
        index=False,
        classes="data-table",
        border=0,
        na_rep="-",  # 空值显示为 "-"
    )
    
    row_info = f"（展示前{min(max_rows, len(df))}行，共{len(df)}行）"
    
    return f"""
    <div class="table-section">
        <h3>📋 数据明细 {row_info}</h3>
        <div class="table-wrapper">
            {table_html}
        </div>
    </div>
    """


def generate_dashboard(config: dict, output_path: str = None) -> str:
    """
    主函数：根据配置生成完整的 HTML 看板。
    
    参数：
        config: 看板配置字典，格式参考 SKILL.md
        output_path: 输出 HTML 文件路径（为空则自动生成）
    返回：
        生成的 HTML 文件路径
    """
    # ========== 1. 解析配置 ==========
    source_file = config.get("source_file", "")
    sheet = config.get("sheet", 0)
    title = config.get("title", "数据看板")
    theme = config.get("style", "business")
    charts_config = config.get("charts", [])
    
    if not source_file:
        raise ValueError("❌ 配置中缺少 source_file（Excel文件路径）")
    if not charts_config:
        raise ValueError("❌ 配置中缺少 charts（至少需要一个图表配置）")
    
    # ========== 2. 读取数据 ==========
    print(f"📂 正在读取文件: {source_file}")
    df = read_excel_data(source_file, sheet)
    print(f"✅ 读取成功: {len(df)}行 × {len(df.columns)}列")
    
    # ========== 3. 生成各图表 ==========
    # 图表生成函数映射
    chart_creators = {
        "bar": create_bar_chart,
        "line": create_line_chart,
        "pie": create_pie_chart,
        "scatter": create_scatter_chart,
    }
    
    # 存储 pyecharts 图表对象
    chart_objects = []
    # 存储 KPI 卡片和表格的 HTML 片段
    kpi_html_list = []
    table_html_list = []
    
    for i, chart_cfg in enumerate(charts_config):
        chart_type = chart_cfg.get("type", "bar")
        print(f"📊 正在生成图表 {i+1}: {chart_type}")
        
        try:
            if chart_type == "kpi_card":
                # KPI 卡片单独处理（不是 pyecharts 图表）
                html = create_kpi_html(
                    df,
                    measure=chart_cfg.get("measure", ""),
                    agg=chart_cfg.get("agg", "sum"),
                    label=chart_cfg.get("label", ""),
                )
                kpi_html_list.append(html)
            elif chart_type == "table":
                # 数据表格单独处理
                html = create_table_html(
                    df,
                    columns=chart_cfg.get("columns", None),
                    max_rows=chart_cfg.get("max_rows", 50),
                )
                table_html_list.append(html)
            elif chart_type in chart_creators:
                # pyecharts 图表
                chart = chart_creators[chart_type](
                    df,
                    dimension=chart_cfg.get("dimension", ""),
                    measure=chart_cfg.get("measure", ""),
                    agg=chart_cfg.get("agg", "sum"),
                    label=chart_cfg.get("label", ""),
                    theme=theme,
                )
                chart_objects.append(chart)
            else:
                print(f"⚠️ 不支持的图表类型: {chart_type}，已跳过")
        except Exception as e:
            print(f"⚠️ 图表 {i+1} 生成失败: {e}")
    
    # ========== 4. 组装 HTML 看板 ==========
    
    # 当前时间作为"数据更新时间"
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # KPI 卡片区域
    kpi_section = ""
    if kpi_html_list:
        kpi_section = f'<div class="kpi-section">{"".join(kpi_html_list)}</div>'
    
    # 图表区域：每个 pyecharts 图表渲染成独立 div
    charts_html = ""
    chart_js_list = []
    for idx, chart in enumerate(chart_objects):
        chart_id = f"chart_{idx}"
        # 获取 pyecharts 渲染所需的 option JSON
        chart.chart_id = chart_id
        # 用 render_embed() 获取嵌入式 HTML 片段
        chart_html_snippet = chart.render_embed()
        charts_html += f'<div class="chart-container">{chart_html_snippet}</div>\n'
    
    # 表格区域
    table_section = "\n".join(table_html_list)
    
    # ========== 5. 生成完整 HTML ==========
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        /* ===== 全局样式 ===== */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                         "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: #f0f2f5;
            color: #333;
            padding: 20px;
        }}

        /* ===== 看板头部 ===== */
        .dashboard-header {{
            background: linear-gradient(135deg, #1a73e8, #4285f4);
            color: white;
            padding: 24px 32px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 12px rgba(26, 115, 232, 0.3);
        }}
        .dashboard-header h1 {{
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .dashboard-header .update-time {{
            font-size: 14px;
            opacity: 0.85;
        }}

        /* ===== KPI 卡片区 ===== */
        .kpi-section {{
            display: flex;
            gap: 16px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .kpi-card {{
            flex: 1;
            min-width: 200px;
            background: white;
            border-radius: 10px;
            padding: 20px 24px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            text-align: center;
            transition: transform 0.2s;
        }}
        .kpi-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
        }}
        .kpi-title {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }}
        .kpi-value {{
            font-size: 32px;
            font-weight: 700;
            color: #1a73e8;
        }}

        /* ===== 图表容器 ===== */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .chart-container {{
            background: white;
            border-radius: 10px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }}

        /* ===== 数据表格 ===== */
        .table-section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            margin-bottom: 20px;
        }}
        .table-section h3 {{
            margin-bottom: 12px;
            color: #333;
        }}
        .table-wrapper {{
            overflow-x: auto;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        .data-table th {{
            background: #f5f7fa;
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #e0e0e0;
            position: sticky;
            top: 0;
        }}
        .data-table td {{
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
        }}
        .data-table tr:hover {{
            background: #f5f7fa;
        }}

        /* ===== 页脚 ===== */
        .dashboard-footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            padding: 16px;
        }}

        /* ===== 响应式适配 ===== */
        @media (max-width: 768px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            .kpi-section {{
                flex-direction: column;
            }}
            body {{
                padding: 12px;
            }}
            .dashboard-header h1 {{
                font-size: 22px;
            }}
        }}
    </style>
</head>
<body>

    <!-- 看板头部 -->
    <div class="dashboard-header">
        <h1>📊 {title}</h1>
        <div class="update-time">数据更新时间: {update_time} | 数据量: {len(df):,}行 × {len(df.columns)}列</div>
    </div>

    <!-- KPI 卡片区 -->
    {kpi_section}

    <!-- 图表区 -->
    <div class="charts-grid">
        {charts_html}
    </div>

    <!-- 数据表格区 -->
    {table_section}

    <!-- 页脚 -->
    <div class="dashboard-footer">
        由 BI看板生成器 自动生成 | Powered by PyEcharts | OpenClaw Skill: dashboard-gen
    </div>

</body>
</html>"""
    
    # ========== 6. 写入文件 ==========
    if not output_path:
        # 自动命名：标题_日期.html
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = title.replace(" ", "_").replace("/", "_")
        output_path = f"{safe_title}_{date_str}.html"
    
    output_file = Path(output_path).expanduser().resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)  # 自动创建目录
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    print(f"\n✅ 看板已生成: {output_file}")
    print(f"🌐 请用浏览器打开查看")
    
    return str(output_file)


# ========== 命令行入口 ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BI 看板生成器 (OpenClaw Skill)")
    parser.add_argument("--config", type=str, default=None,
                        help="看板配置（JSON字符串或JSON文件路径）")
    parser.add_argument("--output", type=str, default=None,
                        help="输出HTML文件路径（可选，默认自动命名）")
    parser.add_argument("--probe", type=str, default=None,
                        help="数据探查模式：传入Excel/CSV文件路径，输出数据概况")
    
    args = parser.parse_args()
    
    # ===== 模式1：数据探查 =====
    if args.probe:
        try:
            report = probe_data(args.probe)
            print(report)
        except Exception as e:
            print(f"\n❌ 探查失败: {e}")
            sys.exit(1)
        sys.exit(0)
    
    # ===== 模式2：生成看板 =====
    if not args.config:
        print("❌ 请指定 --config 或 --probe 参数")
        print("   探查数据: python dashboard_generator.py --probe '文件.xlsx'")
        print("   生成看板: python dashboard_generator.py --config '{...}' --output output.html")
        sys.exit(1)
    
    # 尝试解析 config：可能是 JSON 字符串，也可能是 JSON 文件路径
    try:
        config = json.loads(args.config)
    except json.JSONDecodeError:
        # 不是合法 JSON 字符串，当作文件路径尝试
        config_path = Path(args.config).expanduser().resolve()
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            print(f"❌ 无法解析配置: 既不是合法JSON，文件也不存在 -> {args.config}")
            sys.exit(1)
    
    try:
        generate_dashboard(config, args.output)
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        sys.exit(1)
