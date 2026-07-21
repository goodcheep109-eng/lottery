"""
台灣大樂透 主程式
功能：整合爬蟲、分析、選號，產生互動式 HTML Dashboard
用法：
    python main.py --update     # 更新資料
    python main.py --analyze    # 產生 Dashboard（用瀏覽器開啟）
    python main.py              # 更新資料 + 產生 Dashboard
"""

import argparse
import json
import os
import webbrowser
import pandas as pd
from datetime import datetime

from scraper import update_data, load_data
from analyzer import generate_summary
from selector import recommend_numbers, format_recommendation

OUTPUT_HTML = os.path.join(os.path.dirname(__file__), "dashboard.html")


def build_dashboard(df):
    """產生互動式 HTML Dashboard"""
    print("📊 正在產生分析 Dashboard...")

    summary = generate_summary(df)

    # 產生各模式推薦號碼
    conditions = {
        "奇偶比": (2, 4),
        "大小比": (2, 4),
        "和值範圍": (90, 180),
        "連號上限": 2,
    }

    recommendations = {}
    for mode in ["綜合", "熱號優先", "冷號優先", "歷史最強", "隨機"]:
        recs = recommend_numbers(df, mode=mode, n_recommend=5, conditions=conditions)
        recommendations[mode] = format_recommendation(recs)

    # 年度趨勢資料（近10年）
    yearly = summary.get("年度分析", {})
    recent_years = sorted(yearly.keys())[-10:]
    yearly_top5 = {}
    for y in recent_years:
        top5 = sorted(yearly[y].items(), key=lambda x: x[1], reverse=True)[:5]
        yearly_top5[y] = top5

    # 序列化為 JSON
    def make_serializable(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [make_serializable(i) for i in obj]
        return obj

    import numpy as np

    data = {
        "summary": {
            "總期數": summary["總期數"],
            "最早日期": summary["最早日期"],
            "最新日期": summary["最新日期"],
        },
        "全期頻率": make_serializable(summary["全期頻率"]),
        "冷熱號": {
            "近30期": make_serializable(summary["冷熱號_近30期"]),
            "近50期": make_serializable(summary["冷熱號_近50期"]),
            "近100期": make_serializable(summary["冷熱號_近100期"]),
        },
        "號碼間隔": make_serializable(summary["號碼間隔"]),
        "月份分析": make_serializable(summary["月份分析"]),
        "季度分析": make_serializable(summary["季度分析"]),
        "年度Top5": make_serializable(yearly_top5),
        "奇偶分析": make_serializable(dict(summary["奇偶分析"])),
        "大小號分析": make_serializable(dict(summary["大小號分析"])),
        "和值分析": make_serializable(summary["和值分析"]),
        "連號分析": {
            "平均連號組數": summary["連號分析"]["平均連號組數"],
            "有連號比例": summary["連號分析"]["有連號比例"],
            "分佈": make_serializable(dict(summary["連號分析"]["分佈"])),
        },
        "推薦號碼": make_serializable(recommendations),
    }

    json_str = json.dumps(data, ensure_ascii=False)

    html = generate_html(json_str)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Dashboard 已產生：{OUTPUT_HTML}")
    return OUTPUT_HTML


def generate_html(json_data_str):
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎰 台灣大樂透分析系統</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0d1117;
    --panel: rgba(22,27,42,0.92);
    --border: rgba(140,160,220,0.18);
    --text: #e6edf3;
    --muted: #8b949e;
    --accent: #58a6ff;
    --hot: #ff7b72;
    --cold: #79c0ff;
    --green: #3fb950;
    --yellow: #d29922;
    --btn: #21262d;
    --btn-hover: #30363d;
    --radius: 12px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, 'Microsoft JhengHei', 'Noto Sans TC', sans-serif;
    font-size: 14px;
    min-height: 100vh;
  }}
  /* 頂部 */
  .header {{
    background: linear-gradient(135deg, #1a1f35, #0d2137, #1a3a5c);
    padding: 20px 32px;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  }}
  .header h1 {{ font-size: 1.5rem; font-weight: 800; color: #fff; }}
  .header h1 span {{ color: var(--accent); }}
  .header-info {{ color: var(--muted); font-size: 0.82rem; text-align: right; }}
  .update-btn {{
    background: linear-gradient(135deg, #1f6feb, #388bfd);
    color: #fff; border: none; border-radius: 8px;
    padding: 8px 18px; font-size: 0.85rem; font-weight: 600;
    cursor: pointer; transition: opacity .2s;
  }}
  .update-btn:hover {{ opacity: 0.85; }}
  /* 導覽 Tab */
  .nav {{
    display: flex; gap: 4px; padding: 16px 32px 0;
    border-bottom: 1px solid var(--border);
    background: rgba(13,17,23,0.8);
    position: sticky; top: 0; z-index: 100;
    backdrop-filter: blur(12px);
  }}
  .nav-tab {{
    padding: 10px 20px; border-radius: 8px 8px 0 0;
    cursor: pointer; font-size: 0.88rem; font-weight: 600;
    color: var(--muted); border: 1px solid transparent;
    border-bottom: none; transition: all .2s;
  }}
  .nav-tab:hover {{ color: var(--text); background: var(--btn); }}
  .nav-tab.active {{
    color: var(--accent); background: var(--panel);
    border-color: var(--border);
  }}
  /* 主內容 */
  .main {{ padding: 24px 32px; max-width: 1400px; margin: 0 auto; }}
  .page {{ display: none; }}
  .page.active {{ display: block; }}
  /* 卡片 */
  .card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px; margin-bottom: 20px;
  }}
  .card-title {{
    font-size: 1rem; font-weight: 700; color: var(--text);
    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
  }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }}
  .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
  /* 統計數字 */
  .stat-card {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 16px; text-align: center;
  }}
  .stat-num {{ font-size: 2rem; font-weight: 800; color: var(--accent); }}
  .stat-label {{ color: var(--muted); font-size: 0.78rem; margin-top: 4px; }}
  /* 號碼球 */
  .ball {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; border-radius: 50%;
    font-weight: 700; font-size: 0.85rem;
    margin: 3px;
  }}
  .ball-hot {{ background: linear-gradient(135deg, #ff4444, #ff7b72); color: #fff; }}
  .ball-cold {{ background: linear-gradient(135deg, #1f6feb, #79c0ff); color: #fff; }}
  .ball-normal {{ background: linear-gradient(135deg, #21262d, #30363d); color: var(--text); border: 1px solid var(--border); }}
  .ball-special {{ background: linear-gradient(135deg, #d29922, #f0c040); color: #000; }}
  .ball-rec {{ background: linear-gradient(135deg, #238636, #3fb950); color: #fff; }}
  /* 頻率條 */
  .freq-bar-wrap {{ margin: 4px 0; display: flex; align-items: center; gap: 8px; }}
  .freq-num {{ width: 28px; text-align: right; font-weight: 700; font-size: 0.82rem; }}
  .freq-bar-bg {{ flex: 1; background: rgba(255,255,255,0.06); border-radius: 4px; height: 18px; overflow: hidden; }}
  .freq-bar {{ height: 100%; border-radius: 4px; transition: width .5s ease; display: flex; align-items: center; padding-left: 6px; font-size: 0.72rem; color: #fff; font-weight: 600; }}
  .freq-count {{ width: 36px; text-align: right; color: var(--muted); font-size: 0.78rem; }}
  /* 推薦組合 */
  .rec-card {{
    background: rgba(35,134,54,0.08);
    border: 1px solid rgba(63,185,80,0.25);
    border-radius: var(--radius); padding: 16px; margin-bottom: 12px;
  }}
  .rec-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
  .rec-label {{ font-weight: 700; color: var(--green); }}
  .rec-meta {{ color: var(--muted); font-size: 0.78rem; }}
  .rec-balls {{ display: flex; flex-wrap: wrap; gap: 4px; }}
  /* 篩選控制 */
  .filter-row {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 16px; }}
  .filter-group {{ display: flex; flex-direction: column; gap: 4px; }}
  .filter-label {{ font-size: 0.75rem; color: var(--muted); }}
  .filter-input {{
    background: var(--btn); border: 1px solid var(--border);
    color: var(--text); border-radius: 6px; padding: 6px 10px;
    font-size: 0.85rem; width: 80px;
  }}
  .filter-select {{
    background: var(--btn); border: 1px solid var(--border);
    color: var(--text); border-radius: 6px; padding: 6px 10px;
    font-size: 0.85rem;
  }}
  .gen-btn {{
    background: linear-gradient(135deg, #238636, #2ea043);
    color: #fff; border: none; border-radius: 8px;
    padding: 10px 24px; font-size: 0.9rem; font-weight: 700;
    cursor: pointer; transition: opacity .2s; margin-top: 16px;
  }}
  .gen-btn:hover {{ opacity: 0.85; }}
  /* 間隔熱力圖 */
  .interval-grid {{
    display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px;
  }}
  .interval-cell {{
    border-radius: 6px; padding: 6px 4px; text-align: center;
    font-size: 0.75rem; font-weight: 700;
  }}
  /* 月份/季度 chips */
  .period-chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }}
  .chip {{
    padding: 6px 14px; border-radius: 20px; font-size: 0.82rem;
    cursor: pointer; border: 1px solid var(--border);
    background: var(--btn); color: var(--muted); transition: all .2s;
  }}
  .chip.active {{ background: var(--accent); color: #000; border-color: var(--accent); font-weight: 700; }}
  /* 表格 */
  .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  .data-table th {{ background: rgba(255,255,255,0.05); padding: 8px 12px; text-align: left; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border); }}
  .data-table td {{ padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); }}
  .data-table tr:hover td {{ background: rgba(255,255,255,0.03); }}
  /* 警告 */
  .disclaimer {{
    background: rgba(210,153,34,0.08); border: 1px solid rgba(210,153,34,0.3);
    border-radius: 8px; padding: 12px 16px; color: #d29922;
    font-size: 0.8rem; margin-bottom: 20px;
  }}
  canvas {{ max-height: 320px; }}
  @media (max-width: 768px) {{
    .main {{ padding: 16px; }}
    .grid-2, .grid-3, .grid-4 {{ grid-template-columns: 1fr; }}
    .nav {{ padding: 12px 16px 0; overflow-x: auto; }}
    .header {{ padding: 16px; flex-wrap: wrap; gap: 10px; }}
  }}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>🎰 台灣大樂透 <span>智慧分析系統</span></h1>
    <div style="color:var(--muted);font-size:0.8rem;margin-top:4px;">資料來源：台灣彩券官網</div>
  </div>
  <div style="display:flex;gap:12px;align-items:center;">
    <div class="header-info" id="dataInfo">載入中...</div>
    <button class="update-btn" onclick="alert('請在終端機執行：python main.py --update')">🔄 更新資料</button>
  </div>
</div>

<div class="nav">
  <div class="nav-tab active" onclick="switchPage('overview')">📊 總覽</div>
  <div class="nav-tab" onclick="switchPage('frequency')">🔢 頻率分析</div>
  <div class="nav-tab" onclick="switchPage('hotcold')">🌡️ 冷熱號</div>
  <div class="nav-tab" onclick="switchPage('period')">📅 時間分析</div>
  <div class="nav-tab" onclick="switchPage('pattern')">🔍 規律分析</div>
  <div class="nav-tab" onclick="switchPage('recommend')">🎯 智慧選號</div>
</div>

<div class="main">

<!-- ===== 總覽 ===== -->
<div class="page active" id="page-overview">
  <div class="disclaimer">⚠️ 本系統僅供娛樂參考，樂透為隨機事件，任何分析均無法保證中獎。請理性購彩，量力而為。</div>
  <div class="grid-4" id="statsGrid"></div>
  <div class="grid-2" style="margin-top:20px;">
    <div class="card">
      <div class="card-title">🔥 全期最熱 Top 10</div>
      <div id="topHotBalls"></div>
    </div>
    <div class="card">
      <div class="card-title">❄️ 全期最冷 Top 10</div>
      <div id="topColdBalls"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📈 全期號碼出現頻率</div>
    <canvas id="overviewChart"></canvas>
  </div>
</div>

<!-- ===== 頻率分析 ===== -->
<div class="page" id="page-frequency">
  <div class="card">
    <div class="card-title">🔢 號碼出現頻率排行（1–49）</div>
    <div id="freqBars"></div>
  </div>
  <div class="card">
    <div class="card-title">📊 號碼間隔熱力圖（距上次出現期數，越深=越久沒出現）</div>
    <div class="interval-grid" id="intervalGrid"></div>
  </div>
</div>

<!-- ===== 冷熱號 ===== -->
<div class="page" id="page-hotcold">
  <div class="period-chips" id="hotcoldChips">
    <div class="chip active" onclick="switchHotCold('近30期',this)">近 30 期</div>
    <div class="chip" onclick="switchHotCold('近50期',this)">近 50 期</div>
    <div class="chip" onclick="switchHotCold('近100期',this)">近 100 期</div>
  </div>
  <div class="grid-2">
    <div class="card">
      <div class="card-title">🔥 熱號 Top 10</div>
      <div id="hotBalls"></div>
    </div>
    <div class="card">
      <div class="card-title">❄️ 冷號 Top 10</div>
      <div id="coldBalls"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📊 冷熱號頻率分佈</div>
    <canvas id="hotcoldChart"></canvas>
  </div>
</div>

<!-- ===== 時間分析 ===== -->
<div class="page" id="page-period">
  <div class="period-chips">
    <div class="chip active" onclick="switchPeriod('month',this)">月份分析</div>
    <div class="chip" onclick="switchPeriod('quarter',this)">季度分析</div>
    <div class="chip" onclick="switchPeriod('year',this)">年度分析</div>
  </div>
  <div id="periodContent"></div>
</div>

<!-- ===== 規律分析 ===== -->
<div class="page" id="page-pattern">
  <div class="grid-2">
    <div class="card">
      <div class="card-title">⚖️ 奇偶比分佈</div>
      <canvas id="oddEvenChart"></canvas>
    </div>
    <div class="card">
      <div class="card-title">📏 大小號分佈（以25為界）</div>
      <canvas id="bigSmallChart"></canvas>
    </div>
  </div>
  <div class="grid-2">
    <div class="card">
      <div class="card-title">➕ 和值分佈</div>
      <canvas id="sumChart"></canvas>
    </div>
    <div class="card">
      <div class="card-title">🔗 連號分析</div>
      <div id="consecInfo"></div>
      <canvas id="consecChart"></canvas>
    </div>
  </div>
</div>

<!-- ===== 智慧選號 ===== -->
<div class="page" id="page-recommend">
  <div class="disclaimer">⚠️ 以下號碼由統計模型產生，僅供參考，不代表任何中獎保證。</div>
  <div class="card">
    <div class="card-title">⚙️ 篩選條件設定</div>
    <div class="filter-row">
      <div class="filter-group">
        <div class="filter-label">選號模式</div>
        <select class="filter-select" id="recMode">
          <option value="綜合">綜合（熱冷平衡）</option>
          <option value="熱號優先">熱號優先</option>
          <option value="冷號優先">冷號優先</option>
          <option value="歷史最強">歷史最強</option>
          <option value="隨機">純隨機</option>
        </select>
      </div>
      <div class="filter-group">
        <div class="filter-label">奇數個數（最少）</div>
        <input class="filter-input" type="number" id="oddMin" value="2" min="0" max="6">
      </div>
      <div class="filter-group">
        <div class="filter-label">奇數個數（最多）</div>
        <input class="filter-input" type="number" id="oddMax" value="4" min="0" max="6">
      </div>
      <div class="filter-group">
        <div class="filter-label">大號個數（最少）</div>
        <input class="filter-input" type="number" id="bigMin" value="2" min="0" max="6">
      </div>
      <div class="filter-group">
        <div class="filter-label">大號個數（最多）</div>
        <input class="filter-input" type="number" id="bigMax" value="4" min="0" max="6">
      </div>
      <div class="filter-group">
        <div class="filter-label">和值下限</div>
        <input class="filter-input" type="number" id="sumMin" value="90" min="21" max="279">
      </div>
      <div class="filter-group">
        <div class="filter-label">和值上限</div>
        <input class="filter-input" type="number" id="sumMax" value="180" min="21" max="279">
      </div>
      <div class="filter-group">
        <div class="filter-label">連號上限</div>
        <input class="filter-input" type="number" id="consecMax" value="2" min="0" max="5">
      </div>
      <div class="filter-group">
        <div class="filter-label">推薦組數</div>
        <input class="filter-input" type="number" id="recCount" value="5" min="1" max="20">
      </div>
    </div>
    <button class="gen-btn" onclick="generateRec()">🎲 產生推薦號碼</button>
  </div>
  <div id="recResults"></div>
  <div class="card" style="margin-top:20px;">
    <div class="card-title">📋 各模式預設推薦（5組）</div>
    <div id="allModeRec"></div>
  </div>
</div>

</div><!-- /main -->

<script>
const DATA = {json_data_str};

// ===== 工具函式 =====
function ball(n, type='normal') {{
  return `<span class="ball ball-${{type}}">${{String(n).padStart(2,'0')}}</span>`;
}}

function switchPage(id) {{
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('page-'+id).classList.add('active');
  event.target.classList.add('active');
  if(id==='period') renderPeriod('month');
  if(id==='hotcold') renderHotCold('近50期');
  if(id==='pattern') renderPattern();
  if(id==='recommend') renderAllModeRec();
}}

// ===== 初始化 =====
function init() {{
  const s = DATA.summary;
  document.getElementById('dataInfo').innerHTML =
    `共 ${{s.總期數}} 期｜${{s.最早日期}} ~ ${{s.最新日期}}`;

  // 統計卡片
  const statsGrid = document.getElementById('statsGrid');
  const stats = [
    {{ num: s.總期數, label: '歷史總期數' }},
    {{ num: s.最新日期, label: '最新開獎日' }},
    {{ num: DATA.和值分析.平均和值, label: '平均和值' }},
    {{ num: DATA.連號分析.有連號比例 + '%', label: '有連號比例' }},
  ];
  statsGrid.innerHTML = stats.map(s =>
    `<div class="stat-card"><div class="stat-num">${{s.num}}</div><div class="stat-label">${{s.label}}</div></div>`
  ).join('');

  // 全期熱冷號
  const freqSorted = Object.entries(DATA.全期頻率).sort((a,b)=>b[1]-a[1]);
  const top10Hot = freqSorted.slice(0,10);
  const top10Cold = freqSorted.slice(-10).reverse();

  document.getElementById('topHotBalls').innerHTML =
    top10Hot.map(([n,c]) => `${{ball(n,'hot')}} <small style="color:var(--muted)">${{c}}次</small> `).join('');
  document.getElementById('topColdBalls').innerHTML =
    top10Cold.map(([n,c]) => `${{ball(n,'cold')}} <small style="color:var(--muted)">${{c}}次</small> `).join('');

  // 總覽圖表
  renderOverviewChart();
  renderFreqBars();
  renderIntervalGrid();
}}

function renderOverviewChart() {{
  const labels = Array.from({{length:49}},(_,i)=>i+1);
  const values = labels.map(n => DATA.全期頻率[n] || 0);
  const maxV = Math.max(...values);
  const colors = values.map(v => {{
    const ratio = v/maxV;
    if(ratio > 0.8) return '#ff7b72';
    if(ratio > 0.6) return '#ffa657';
    if(ratio > 0.4) return '#58a6ff';
    return '#79c0ff';
  }});
  new Chart(document.getElementById('overviewChart'), {{
    type: 'bar',
    data: {{ labels: labels.map(n=>String(n).padStart(2,'0')), datasets: [{{
      data: values, backgroundColor: colors, borderRadius: 4,
    }}]}},
    options: {{
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ ticks: {{ color: '#8b949e', font: {{size:10}} }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }},
        y: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: 'rgba(255,255,255,0.06)' }} }},
      }},
    }}
  }});
}}

function renderFreqBars() {{
  const sorted = Object.entries(DATA.全期頻率).sort((a,b)=>b[1]-a[1]);
  const maxV = sorted[0][1];
  document.getElementById('freqBars').innerHTML = sorted.map(([n,c]) => {{
    const pct = (c/maxV*100).toFixed(1);
    const color = pct>80?'#ff7b72':pct>60?'#ffa657':pct>40?'#58a6ff':'#79c0ff';
    return `<div class="freq-bar-wrap">
      <div class="freq-num">${{String(n).padStart(2,'0')}}</div>
      <div class="freq-bar-bg"><div class="freq-bar" style="width:${{pct}}%;background:${{color}}">${{c}}</div></div>
      <div class="freq-count">${{c}}</div>
    </div>`;
  }}).join('');
}}

function renderIntervalGrid() {{
  const data = DATA.號碼間隔;
  const maxV = Math.max(...Object.values(data));
  const grid = document.getElementById('intervalGrid');
  grid.innerHTML = Array.from({{length:49}},(_,i)=>i+1).map(n => {{
    const v = data[n] || 0;
    const ratio = v/maxV;
    const r = Math.round(255*ratio);
    const b = Math.round(255*(1-ratio));
    const bg = `rgba(${{r}},80,${{b}},0.7)`;
    return `<div class="interval-cell" style="background:${{bg}};color:#fff" title="號碼${{n}}：${{v}}期未出現">
      <div style="font-size:0.7rem">${{String(n).padStart(2,'0')}}</div>
      <div style="font-size:0.65rem;opacity:0.8">${{v}}期</div>
    </div>`;
  }}).join('');
}}

// ===== 冷熱號 =====
let hotcoldChart = null;
function switchHotCold(period, el) {{
  document.querySelectorAll('#hotcoldChips .chip').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  renderHotCold(period);
}}

function renderHotCold(period) {{
  const d = DATA.冷熱號[period];
  const freq = d.全部頻率;
  const sorted = Object.entries(freq).sort((a,b)=>b[1]-a[1]);
  const hot = sorted.slice(0,10);
  const cold = sorted.slice(-10).reverse();

  document.getElementById('hotBalls').innerHTML =
    hot.map(([n,c]) => `${{ball(n,'hot')}} <small style="color:var(--muted)">${{c}}次</small> `).join('');
  document.getElementById('coldBalls').innerHTML =
    cold.map(([n,c]) => `${{ball(n,'cold')}} <small style="color:var(--muted)">${{c}}次</small> `).join('');

  const labels = Array.from({{length:49}},(_,i)=>String(i+1).padStart(2,'0'));
  const values = Array.from({{length:49}},(_,i)=>freq[i+1]||0);
  const maxV = Math.max(...values);
  const colors = values.map(v=>v/maxV>0.7?'#ff7b72':v/maxV>0.4?'#ffa657':'#79c0ff');

  if(hotcoldChart) hotcoldChart.destroy();
  hotcoldChart = new Chart(document.getElementById('hotcoldChart'), {{
    type:'bar',
    data:{{labels, datasets:[{{data:values,backgroundColor:colors,borderRadius:4}}]}},
    options:{{
      plugins:{{legend:{{display:false}}}},
      scales:{{
        x:{{ticks:{{color:'#8b949e',font:{{size:10}}}},grid:{{color:'rgba(255,255,255,0.04)'}}}},
        y:{{ticks:{{color:'#8b949e'}},grid:{{color:'rgba(255,255,255,0.06)'}}}},
      }}
    }}
  }});
}}

// ===== 時間分析 =====
let periodChart = null;
function switchPeriod(type, el) {{
  document.querySelectorAll('.period-chips .chip').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  renderPeriod(type);
}}

function renderPeriod(type) {{
  const container = document.getElementById('periodContent');
  if(type==='month') {{
    const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
    let html = '<div class="period-chips" id="monthChips">';
    months.forEach((m,i) => {{
      html += `<div class="chip ${{i===0?'active':''}}" onclick="showMonthDetail(${{i+1}},this)">${{m}}</div>`;
    }});
    html += '</div><div id="monthDetail"></div>';
    container.innerHTML = html;
    showMonthDetail(1, document.querySelector('#monthChips .chip'));
  }} else if(type==='quarter') {{
    const quarters = ['第一季(1-3月)','第二季(4-6月)','第三季(7-9月)','第四季(10-12月)'];
    let html = '<div class="period-chips" id="qChips">';
    quarters.forEach((q,i) => {{
      html += `<div class="chip ${{i===0?'active':''}}" onclick="showQuarterDetail(${{i+1}},this)">${{q}}</div>`;
    }});
    html += '</div><div id="quarterDetail"></div>';
    container.innerHTML = html;
    showQuarterDetail(1, document.querySelector('#qChips .chip'));
  }} else {{
    const years = Object.keys(DATA.年度Top5).sort();
    let html = '<div class="card"><div class="card-title">📅 各年度 Top 5 號碼</div><table class="data-table"><thead><tr><th>年份</th><th>Top 5 號碼</th></tr></thead><tbody>';
    years.forEach(y => {{
      const top5 = DATA.年度Top5[y];
      html += `<tr><td><b>${{y}}</b></td><td>${{top5.map(([n,c])=>`${{ball(n,'normal')}} <small style="color:var(--muted)">${{c}}</small>`).join(' ')}}</td></tr>`;
    }});
    html += '</tbody></table></div>';
    container.innerHTML = html;
  }}
}}

function showMonthDetail(month, el) {{
  document.querySelectorAll('#monthChips .chip').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  const freq = DATA.月份分析[month];
  const sorted = Object.entries(freq).sort((a,b)=>b[1]-a[1]);
  const top10 = sorted.slice(0,10);
  const bot10 = sorted.slice(-10).reverse();
  document.getElementById('monthDetail').innerHTML = `
    <div class="grid-2">
      <div class="card"><div class="card-title">🔥 ${{month}}月 熱號 Top 10</div>
        ${{top10.map(([n,c])=>`${{ball(n,'hot')}} <small style="color:var(--muted)">${{c}}次</small>`).join(' ')}}
      </div>
      <div class="card"><div class="card-title">❄️ ${{month}}月 冷號 Top 10</div>
        ${{bot10.map(([n,c])=>`${{ball(n,'cold')}} <small style="color:var(--muted)">${{c}}次</small>`).join(' ')}}
      </div>
    </div>`;
}}

function showQuarterDetail(q, el) {{
  document.querySelectorAll('#qChips .chip').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  const freq = DATA.季度分析[q];
  const sorted = Object.entries(freq).sort((a,b)=>b[1]-a[1]);
  const top10 = sorted.slice(0,10);
  const bot10 = sorted.slice(-10).reverse();
  const qNames = {{1:'第一季',2:'第二季',3:'第三季',4:'第四季'}};
  document.getElementById('quarterDetail').innerHTML = `
    <div class="grid-2">
      <div class="card"><div class="card-title">🔥 ${{qNames[q]}} 熱號 Top 10</div>
        ${{top10.map(([n,c])=>`${{ball(n,'hot')}} <small style="color:var(--muted)">${{c}}次</small>`).join(' ')}}
      </div>
      <div class="card"><div class="card-title">❄️ ${{qNames[q]}} 冷號 Top 10</div>
        ${{bot10.map(([n,c])=>`${{ball(n,'cold')}} <small style="color:var(--muted)">${{c}}次</small>`).join(' ')}}
      </div>
    </div>`;
}}

// ===== 規律分析 =====
function renderPattern() {{
  // 奇偶
  const oe = DATA.奇偶分析;
  const oeLabels = Object.keys(oe).sort();
  new Chart(document.getElementById('oddEvenChart'), {{
    type:'doughnut',
    data:{{labels:oeLabels, datasets:[{{data:oeLabels.map(k=>oe[k]),
      backgroundColor:['#ff7b72','#ffa657','#58a6ff','#3fb950','#d29922','#bc8cff','#79c0ff'],
      borderWidth:0}}]}},
    options:{{plugins:{{legend:{{labels:{{color:'#e6edf3',font:{{size:11}}}}}}}}}}
  }});

  // 大小號
  const bs = DATA.大小號分析;
  const bsLabels = Object.keys(bs).sort();
  new Chart(document.getElementById('bigSmallChart'), {{
    type:'doughnut',
    data:{{labels:bsLabels, datasets:[{{data:bsLabels.map(k=>bs[k]),
      backgroundColor:['#ff7b72','#ffa657','#58a6ff','#3fb950','#d29922','#bc8cff','#79c0ff'],
      borderWidth:0}}]}},
    options:{{plugins:{{legend:{{labels:{{color:'#e6edf3',font:{{size:11}}}}}}}}}}
  }});

  // 和值
  const sumDist = DATA.和值分析.和值分佈;
  const sumKeys = Object.keys(sumDist).map(Number).sort((a,b)=>a-b);
  new Chart(document.getElementById('sumChart'), {{
    type:'bar',
    data:{{labels:sumKeys, datasets:[{{data:sumKeys.map(k=>sumDist[k]),
      backgroundColor:'#58a6ff',borderRadius:2}}]}},
    options:{{
      plugins:{{legend:{{display:false}}}},
      scales:{{
        x:{{ticks:{{color:'#8b949e',maxTicksLimit:20}},grid:{{color:'rgba(255,255,255,0.04)'}}}},
        y:{{ticks:{{color:'#8b949e'}},grid:{{color:'rgba(255,255,255,0.06)'}}}},
      }}
    }}
  }});

  // 連號
  const cd = DATA.連號分析;
  document.getElementById('consecInfo').innerHTML = `
    <div style="display:flex;gap:20px;margin-bottom:12px;">
      <div><span style="color:var(--accent);font-weight:700">${{cd.平均連號組數}}</span> <span style="color:var(--muted)">平均連號組數</span></div>
      <div><span style="color:var(--accent);font-weight:700">${{cd.有連號比例}}%</span> <span style="color:var(--muted)">有連號比例</span></div>
    </div>`;
  const cDist = cd.分佈;
  const cKeys = Object.keys(cDist).map(Number).sort((a,b)=>a-b);
  new Chart(document.getElementById('consecChart'), {{
    type:'bar',
    data:{{labels:cKeys.map(k=>`${{k}}組連號`), datasets:[{{data:cKeys.map(k=>cDist[k]),
      backgroundColor:'#3fb950',borderRadius:4}}]}},
    options:{{
      plugins:{{legend:{{display:false}}}},
      scales:{{
        x:{{ticks:{{color:'#8b949e'}},grid:{{color:'rgba(255,255,255,0.04)'}}}},
        y:{{ticks:{{color:'#8b949e'}},grid:{{color:'rgba(255,255,255,0.06)'}}}},
      }}
    }}
  }});
}}

// ===== 智慧選號 =====
function renderAllModeRec() {{
  const container = document.getElementById('allModeRec');
  const modes = Object.keys(DATA.推薦號碼);
  let html = '';
  modes.forEach(mode => {{
    html += `<div style="margin-bottom:16px"><div style="font-weight:700;color:var(--accent);margin-bottom:8px">📌 ${{mode}}</div>`;
    DATA.推薦號碼[mode].forEach(r => {{
      html += `<div class="rec-card">
        <div class="rec-header">
          <span class="rec-label">${{r.組別}}</span>
          <span class="rec-meta">和值:${{r.和值}} ｜ 奇:${{r.奇數個數}}偶:${{6-r.奇數個數}} ｜ 大:${{r.大號個數}}小:${{6-r.大號個數}}</span>
        </div>
        <div class="rec-balls">${{r.號碼.map(n=>ball(n,'rec')).join('')}}</div>
      </div>`;
    }});
    html += '</div>';
  }});
  container.innerHTML = html;
}}

function generateRec() {{
  const mode = document.getElementById('recMode').value;
  const oddMin = parseInt(document.getElementById('oddMin').value);
  const oddMax = parseInt(document.getElementById('oddMax').value);
  const bigMin = parseInt(document.getElementById('bigMin').value);
  const bigMax = parseInt(document.getElementById('bigMax').value);
  const sumMin = parseInt(document.getElementById('sumMin').value);
  const sumMax = parseInt(document.getElementById('sumMax').value);
  const consecMax = parseInt(document.getElementById('consecMax').value);
  const count = parseInt(document.getElementById('recCount').value);

  // 前端隨機產生（符合條件）
  const results = [];
  let attempts = 0;
  while(results.length < count && attempts < 50000) {{
    attempts++;
    let pool = Array.from({{length:49}},(_,i)=>i+1);

    // 依模式調整權重
    let nums;
    if(mode==='熱號優先') {{
      const hotNums = Object.entries(DATA.冷熱號['近50期'].全部頻率).sort((a,b)=>b[1]-a[1]).slice(0,25).map(([n])=>parseInt(n));
      nums = sampleWeighted(hotNums, pool, 6);
    }} else if(mode==='冷號優先') {{
      const coldNums = Object.entries(DATA.號碼間隔).sort((a,b)=>b[1]-a[1]).slice(0,25).map(([n])=>parseInt(n));
      nums = sampleWeighted(coldNums, pool, 6);
    }} else {{
      nums = shuffle(pool).slice(0,6);
    }}
    nums = nums.sort((a,b)=>a-b);

    // 篩選條件
    const odd = nums.filter(n=>n%2===1).length;
    const big = nums.filter(n=>n>25).length;
    const s = nums.reduce((a,b)=>a+b,0);
    const consec = nums.reduce((c,n,i)=>i>0&&nums[i]-nums[i-1]===1?c+1:c,0);

    if(odd<oddMin||odd>oddMax) continue;
    if(big<bigMin||big>bigMax) continue;
    if(s<sumMin||s>sumMax) continue;
    if(consec>consecMax) continue;

    // 確保組合不重複且差異夠大
    const tooSimilar = results.some(r=>r.filter(n=>nums.includes(n)).length>=4);
    if(tooSimilar) continue;

    results.push(nums);
  }}

  const container = document.getElementById('recResults');
  if(results.length===0) {{
    container.innerHTML = '<div class="card" style="color:var(--hot)">⚠️ 條件太嚴，找不到符合的組合，請放寬篩選條件</div>';
    return;
  }}

  let html = `<div class="card"><div class="card-title">🎯 ${{mode}} 模式推薦結果（共 ${{results.length}} 組）</div>`;
  results.forEach((nums,i) => {{
    const odd = nums.filter(n=>n%2===1).length;
    const big = nums.filter(n=>n>25).length;
    const s = nums.reduce((a,b)=>a+b,0);
    html += `<div class="rec-card">
      <div class="rec-header">
        <span class="rec-label">第 ${{i+1}} 組</span>
        <span class="rec-meta">和值:${{s}} ｜ 奇:${{odd}}偶:${{6-odd}} ｜ 大:${{big}}小:${{6-big}}</span>
      </div>
      <div class="rec-balls">${{nums.map(n=>ball(n,'rec')).join('')}}</div>
    </div>`;
  }});
  html += '</div>';
  container.innerHTML = html;
}}

function shuffle(arr) {{
  const a = [...arr];
  for(let i=a.length-1;i>0;i--) {{
    const j=Math.floor(Math.random()*(i+1));
    [a[i],a[j]]=[a[j],a[i]];
  }}
  return a;
}}

function sampleWeighted(preferred, all, n) {{
  const pool = [...new Set([...preferred, ...all])];
  return shuffle(pool).slice(0,n);
}}

// 啟動
init();
</script>
</body>
</html>"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="台灣大樂透分析系統")
    parser.add_argument("--update", action="store_true", help="更新開獎資料")
    parser.add_argument("--analyze", action="store_true", help="產生分析 Dashboard")
    parser.add_argument("--no-open", action="store_true", help="不自動開啟瀏覽器")
    args = parser.parse_args()

    if args.update or (not args.update and not args.analyze):
        df = update_data()
    else:
        df = load_data()

    if df.empty:
        print("❌ 無資料可分析，請先執行 --update 匯入資料")
        exit(1)

    if args.analyze or (not args.update and not args.analyze):
        html_path = build_dashboard(df)
        if not args.no_open:
            print(f"🌐 正在開啟瀏覽器...")
            webbrowser.open(f"file://{html_path}")
