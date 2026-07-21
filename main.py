"""
台灣大樂透 主程式
用法：
    python main.py --update     # 更新資料
    python main.py --analyze    # 產生 Dashboard
    python main.py              # 更新 + 產生 Dashboard
"""

import argparse
import json
import os
import webbrowser
import numpy as np
import pandas as pd
from datetime import datetime

from scraper import update_data, load_data
from analyzer import generate_summary
from selector import predict_next, predict_season, predict_two_years, format_results

OUTPUT_HTML = os.path.join(os.path.dirname(__file__), "docs", "index.html")
os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)


def make_serializable(obj):
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, dict): return {str(k): make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)): return [make_serializable(i) for i in obj]
    return obj


def build_dashboard(df):
    print("📊 正在產生 Dashboard...")
    summary = generate_summary(df)
    update_time = datetime.now().strftime("%Y/%m/%d %H:%M")

    # 三大選號模式
    rec = {
        "下期預測": format_results(predict_next(df, 5), "下期預測"),
        "本季預測": format_results(predict_season(df, 5), "本季預測"),
        "兩年綜合": format_results(predict_two_years(df, 5), "兩年綜合"),
    }

    data = {
        "updateTime": update_time,
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
        "奇偶分析": make_serializable(dict(summary["奇偶分析"])),
        "大小號分析": make_serializable(dict(summary["大小號分析"])),
        "和值分析": make_serializable(summary["和值分析"]),
        "連號分析": {
            "平均連號組數": summary["連號分析"]["平均連號組數"],
            "有連號比例": summary["連號分析"]["有連號比例"],
            "分佈": make_serializable(dict(summary["連號分析"]["分佈"])),
        },
        "推薦號碼": make_serializable(rec),
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
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>🎰 大樂透分析</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg:#0d1117; --panel:rgba(22,27,42,0.95); --border:rgba(140,160,220,0.18);
  --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; --hot:#ff7b72; --cold:#79c0ff;
  --green:#3fb950; --yellow:#d29922; --btn:#21262d; --btn-hover:#30363d;
  --special:#f0c040; --radius:14px;
}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,'Microsoft JhengHei','Noto Sans TC',sans-serif;font-size:14px;min-height:100vh;padding-bottom:80px;}}

/* 頂部 */
.header{{background:linear-gradient(135deg,#1a1f35,#0d2137,#1a3a5c);padding:16px 20px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 4px 24px rgba(0,0,0,0.4);position:sticky;top:0;z-index:100;}}
.header h1{{font-size:1.15rem;font-weight:800;color:#fff;}}
.header h1 span{{color:var(--accent);}}
.update-time{{color:var(--muted);font-size:0.72rem;margin-top:2px;}}

/* 底部導覽 */
.bottom-nav{{position:fixed;bottom:0;left:0;right:0;background:rgba(13,17,23,0.97);border-top:1px solid var(--border);display:flex;z-index:200;backdrop-filter:blur(12px);}}
.nav-item{{flex:1;display:flex;flex-direction:column;align-items:center;padding:10px 4px 8px;cursor:pointer;color:var(--muted);font-size:0.68rem;gap:3px;transition:color .2s;border:none;background:none;}}
.nav-item .icon{{font-size:1.3rem;}}
.nav-item.active{{color:var(--accent);}}

/* 頁面 */
.page{{display:none;padding:16px;max-width:600px;margin:0 auto;}}
.page.active{{display:block;}}

/* 卡片 */
.card{{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin-bottom:14px;}}
.card-title{{font-size:0.95rem;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:6px;}}

/* 統計卡片 */
.stats-row{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;}}
.stat-card{{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:14px;text-align:center;}}
.stat-num{{font-size:1.5rem;font-weight:800;color:var(--accent);}}
.stat-label{{color:var(--muted);font-size:0.72rem;margin-top:3px;}}

/* 號碼球 */
.ball{{display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;border-radius:50%;font-weight:700;font-size:0.88rem;margin:3px;flex-shrink:0;}}
.ball-hot{{background:linear-gradient(135deg,#ff4444,#ff7b72);color:#fff;}}
.ball-cold{{background:linear-gradient(135deg,#1f6feb,#79c0ff);color:#fff;}}
.ball-normal{{background:linear-gradient(135deg,#21262d,#30363d);color:var(--text);border:1px solid var(--border);}}
.ball-special{{background:linear-gradient(135deg,#b8860b,#f0c040);color:#000;font-weight:800;}}
.ball-rec{{background:linear-gradient(135deg,#238636,#3fb950);color:#fff;}}

/* 選號大按鈕 */
.mode-grid{{display:grid;grid-template-columns:1fr;gap:12px;margin-bottom:16px;}}
.mode-btn{{border:none;border-radius:var(--radius);padding:18px 20px;cursor:pointer;text-align:left;transition:transform .15s,opacity .2s;}}
.mode-btn:active{{transform:scale(.97);}}
.mode-btn-1{{background:linear-gradient(135deg,#1a3a6c,#1f6feb);}}
.mode-btn-2{{background:linear-gradient(135deg,#1a4a2e,#238636);}}
.mode-btn-3{{background:linear-gradient(135deg,#4a1a6c,#8957e5);}}
.mode-btn .btn-icon{{font-size:1.8rem;}}
.mode-btn .btn-title{{font-size:1rem;font-weight:700;color:#fff;margin-top:4px;}}
.mode-btn .btn-desc{{font-size:0.75rem;color:rgba(255,255,255,0.7);margin-top:2px;}}

/* 推薦結果卡片 */
.rec-result{{background:rgba(35,134,54,0.08);border:1px solid rgba(63,185,80,0.25);border-radius:var(--radius);padding:14px;margin-bottom:10px;}}
.rec-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}}
.rec-label{{font-weight:700;color:var(--green);font-size:0.9rem;}}
.rec-meta{{color:var(--muted);font-size:0.72rem;}}
.rec-balls{{display:flex;flex-wrap:wrap;align-items:center;gap:2px;}}
.plus-sign{{color:var(--muted);font-size:1rem;margin:0 4px;}}

/* 頻率條 */
.freq-bar-wrap{{margin:3px 0;display:flex;align-items:center;gap:6px;}}
.freq-num{{width:26px;text-align:right;font-weight:700;font-size:0.8rem;}}
.freq-bar-bg{{flex:1;background:rgba(255,255,255,0.06);border-radius:4px;height:16px;overflow:hidden;}}
.freq-bar{{height:100%;border-radius:4px;transition:width .5s ease;display:flex;align-items:center;padding-left:5px;font-size:0.68rem;color:#fff;font-weight:600;}}
.freq-count{{width:32px;text-align:right;color:var(--muted);font-size:0.75rem;}}

/* 間隔熱力圖 */
.interval-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:5px;}}
.interval-cell{{border-radius:6px;padding:5px 2px;text-align:center;font-size:0.7rem;font-weight:700;}}

/* Chips */
.chips{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;}}
.chip{{padding:5px 12px;border-radius:20px;font-size:0.8rem;cursor:pointer;border:1px solid var(--border);background:var(--btn);color:var(--muted);transition:all .2s;}}
.chip.active{{background:var(--accent);color:#000;border-color:var(--accent);font-weight:700;}}

/* 免責聲明 */
.disclaimer{{background:rgba(210,153,34,0.08);border:1px solid rgba(210,153,34,0.3);border-radius:8px;padding:10px 14px;color:#d29922;font-size:0.75rem;margin-bottom:14px;}}

canvas{{max-height:280px;}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>🎰 台灣大樂透 <span>智慧分析</span></h1>
    <div class="update-time" id="updateTime">載入中...</div>
  </div>
</div>

<!-- ===== 選號頁 ===== -->
<div class="page active" id="page-pick">
  <div class="disclaimer">⚠️ 本系統僅供娛樂參考，樂透為隨機事件，無法保證中獎，請理性購彩。</div>
  <div class="mode-grid">
    <button class="mode-btn mode-btn-1" onclick="showRec('下期預測')">
      <div class="btn-icon">🔮</div>
      <div class="btn-title">下期開獎號碼預測</div>
      <div class="btn-desc">綜合近30期熱號 + 久未出現號碼</div>
    </button>
    <button class="mode-btn mode-btn-2" onclick="showRec('本季預測')">
      <div class="btn-icon">🌸</div>
      <div class="btn-title">本季機率預測</div>
      <div class="btn-desc">當前季度歷年最常出現的號碼</div>
    </button>
    <button class="mode-btn mode-btn-3" onclick="showRec('兩年綜合')">
      <div class="btn-icon">📅</div>
      <div class="btn-title">前後兩年綜合預測</div>
      <div class="btn-desc">近兩年開獎資料頻率最高號碼</div>
    </button>
  </div>
  <div id="recArea"></div>
</div>

<!-- ===== 分析頁 ===== -->
<div class="page" id="page-analysis">
  <div class="stats-row" id="statsRow"></div>
  <div class="card">
    <div class="card-title">🌡️ 冷熱號分析</div>
    <div class="chips" id="hotcoldChips">
      <div class="chip active" onclick="switchHC('近30期',this)">近 30 期</div>
      <div class="chip" onclick="switchHC('近50期',this)">近 50 期</div>
      <div class="chip" onclick="switchHC('近100期',this)">近 100 期</div>
    </div>
    <div style="margin-bottom:10px;">
      <div style="color:var(--hot);font-weight:700;font-size:0.82rem;margin-bottom:6px;">🔥 熱號 Top 10</div>
      <div id="hotBalls"></div>
    </div>
    <div>
      <div style="color:var(--cold);font-weight:700;font-size:0.82rem;margin-bottom:6px;">❄️ 冷號 Top 10</div>
      <div id="coldBalls"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📊 全期號碼頻率</div>
    <canvas id="freqChart"></canvas>
  </div>
  <div class="card">
    <div class="card-title">⏱️ 號碼間隔熱力圖</div>
    <div class="interval-grid" id="intervalGrid"></div>
  </div>
</div>

<!-- ===== 統計頁 ===== -->
<div class="page" id="page-stats">
  <div class="card">
    <div class="card-title">📅 時間分析</div>
    <div class="chips" id="periodChips">
      <div class="chip active" onclick="switchPeriod('month',this)">月份</div>
      <div class="chip" onclick="switchPeriod('quarter',this)">季度</div>
    </div>
    <div id="periodDetail"></div>
  </div>
  <div class="card">
    <div class="card-title">⚖️ 奇偶比分佈</div>
    <div style="color:var(--muted);font-size:0.75rem;margin-bottom:10px;">每期6個號碼中，奇數（1,3,5...）與偶數（2,4,6...）的比例分佈。歷史上「3奇3偶」最常出現。</div>
    <canvas id="oddEvenChart"></canvas>
  </div>
  <div class="card">
    <div class="card-title">📏 大小號分佈（以25為界）</div>
    <div style="color:var(--muted);font-size:0.75rem;margin-bottom:10px;">1–25 為小號，26–49 為大號。歷史上「3大3小」最常出現，選號時可參考此比例。</div>
    <canvas id="bigSmallChart"></canvas>
  </div>
  <div class="card">
    <div class="card-title">➕ 和值分佈</div>
    <div style="color:var(--muted);font-size:0.75rem;margin-bottom:10px;">6個號碼加總的分佈。歷史平均和值約 <span id="avgSum" style="color:var(--accent);font-weight:700;"></span>，選號時和值落在 100–180 之間機率最高。</div>
    <canvas id="sumChart"></canvas>
  </div>
  <div class="card">
    <div class="card-title">🔗 連號分析</div>
    <div style="color:var(--muted);font-size:0.75rem;margin-bottom:12px;">「連號」是指開獎號碼中相鄰的數字，例如 12、13 就是一組連號。大多數期別都有 1~2 組連號，完全沒有連號反而比較少見。</div>
    <div id="consecSummary" style="display:flex;gap:20px;margin-bottom:12px;"></div>
    <canvas id="consecChart"></canvas>
  </div>
</div>

<!-- ===== 底部導覽 ===== -->
<div class="bottom-nav">
  <button class="nav-item active" onclick="goPage('pick',this)"><span class="icon">🎯</span>選號</button>
  <button class="nav-item" onclick="goPage('analysis',this)"><span class="icon">📊</span>分析</button>
  <button class="nav-item" onclick="goPage('stats',this)"><span class="icon">📈</span>統計</button>
</div>

<script>
const DATA = {json_data_str};
let freqChartInst = null, oeChartInst = null, bsChartInst = null, sumChartInst = null;
let analysisInited = false, statsInited = false;

// 初始化
function init() {{
  document.getElementById('updateTime').textContent = '最後更新：' + DATA.updateTime;
  const s = DATA.summary;
  document.getElementById('statsRow').innerHTML = [
    {{num: s.總期數, label: '歷史總期數'}},
    {{num: s.最新日期, label: '最新開獎日'}},
  ].map(x => `<div class="stat-card"><div class="stat-num">${{x.num}}</div><div class="stat-label">${{x.label}}</div></div>`).join('');
}}

// 頁面切換
function goPage(id, el) {{
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');
  el.classList.add('active');
  if(id === 'analysis' && !analysisInited) {{ initAnalysis(); analysisInited = true; }}
  if(id === 'stats' && !statsInited) {{ initStats(); statsInited = true; }}
}}

// ===== 選號頁 =====
function ball(n, type='rec') {{
  return `<span class="ball ball-${{type}}">${{String(n).padStart(2,'0')}}</span>`;
}}

function showRec(mode) {{
  const recs = DATA.推薦號碼[mode];
  const colors = {{'下期預測':'#1f6feb','本季預測':'#238636','兩年綜合':'#8957e5'}};
  const icons = {{'下期預測':'🔮','本季預測':'🌸','兩年綜合':'📅'}};
  let html = `<div class="card"><div class="card-title" style="color:${{colors[mode]}}">${{icons[mode]}} ${{mode}} — 推薦 5 組</div>`;
  recs.forEach(r => {{
    html += `<div class="rec-result">
      <div class="rec-header">
        <span class="rec-label">${{r.組別}}</span>
        <span class="rec-meta">和值:${{r.和值}} ｜ 奇:${{r.奇數}}偶:${{6-r.奇數}} ｜ 大:${{r.大號}}小:${{6-r.大號}}</span>
      </div>
      <div class="rec-balls">
        ${{r.號碼.map(n => ball(n,'rec')).join('')}}
        <span class="plus-sign">＋</span>
        ${{ball(r.特別號, 'special')}}
        <span style="color:var(--muted);font-size:0.72rem;margin-left:4px;">特別號</span>
      </div>
    </div>`;
  }});
  html += '</div>';
  document.getElementById('recArea').innerHTML = html;
  document.getElementById('recArea').scrollIntoView({{behavior:'smooth', block:'start'}});
}}

// ===== 分析頁 =====
function initAnalysis() {{
  renderHotCold('近30期');
  renderFreqChart();
  renderIntervalGrid();
}}

function switchHC(period, el) {{
  document.querySelectorAll('#hotcoldChips .chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  renderHotCold(period);
}}

function renderHotCold(period) {{
  const freq = DATA.冷熱號[period].全部頻率;
  const sorted = Object.entries(freq).sort((a,b) => b[1]-a[1]);
  document.getElementById('hotBalls').innerHTML =
    sorted.slice(0,10).map(([n,c]) => `${{ball(n,'hot')}} <small style="color:var(--muted)">${{c}}</small> `).join('');
  document.getElementById('coldBalls').innerHTML =
    sorted.slice(-10).reverse().map(([n,c]) => `${{ball(n,'cold')}} <small style="color:var(--muted)">${{c}}</small> `).join('');
}}

function renderFreqChart() {{
  const labels = Array.from({{length:49}},(_,i) => String(i+1).padStart(2,'0'));
  const values = Array.from({{length:49}},(_,i) => DATA.全期頻率[i+1]||0);
  const maxV = Math.max(...values);
  const colors = values.map(v => v/maxV>0.8?'#ff7b72':v/maxV>0.6?'#ffa657':v/maxV>0.4?'#58a6ff':'#79c0ff');
  if(freqChartInst) freqChartInst.destroy();
  freqChartInst = new Chart(document.getElementById('freqChart'), {{
    type:'bar', data:{{labels, datasets:[{{data:values,backgroundColor:colors,borderRadius:3}}]}},
    options:{{plugins:{{legend:{{display:false}}}},scales:{{
      x:{{ticks:{{color:'#8b949e',font:{{size:9}}}},grid:{{color:'rgba(255,255,255,0.04)'}}}},
      y:{{ticks:{{color:'#8b949e'}},grid:{{color:'rgba(255,255,255,0.06)'}}}}
    }}}}
  }});
}}

function renderIntervalGrid() {{
  const data = DATA.號碼間隔;
  const maxV = Math.max(...Object.values(data));
  document.getElementById('intervalGrid').innerHTML =
    Array.from({{length:49}},(_,i)=>i+1).map(n => {{
      const v = data[n]||0;
      const ratio = v/maxV;
      const r = Math.round(255*ratio), b = Math.round(255*(1-ratio));
      return `<div class="interval-cell" style="background:rgba(${{r}},80,${{b}},0.7);color:#fff" title="${{n}}號：${{v}}期未出現">
        <div>${{String(n).padStart(2,'0')}}</div>
        <div style="font-size:0.6rem;opacity:.8">${{v}}期</div>
      </div>`;
    }}).join('');
}}

// ===== 統計頁 =====
function initStats() {{
  renderPeriod('month');
  renderDoughnut('oddEvenChart', DATA.奇偶分析);
  renderDoughnut('bigSmallChart', DATA.大小號分析);
  renderSumChart();
  renderConsecChart();
  // 顯示平均和值
  document.getElementById('avgSum').textContent = DATA.和值分析.平均和值;
}}

function switchPeriod(type, el) {{
  document.querySelectorAll('#periodChips .chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  renderPeriod(type);
}}

function renderPeriod(type) {{
  const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
  const quarters = ['第一季','第二季','第三季','第四季'];
  const data = type==='month' ? DATA.月份分析 : DATA.季度分析;
  const labels = type==='month' ? months : quarters;
  const keys = type==='month' ? [1,2,3,4,5,6,7,8,9,10,11,12] : [1,2,3,4];

  let html = '<div class="chips" id="subChips">';
  keys.forEach((k,i) => {{
    html += `<div class="chip ${{i===0?'active':''}}" onclick="showPeriodDetail('${{type}}',${{k}},this)">${{labels[i]}}</div>`;
  }});
  html += '</div><div id="subDetail"></div>';
  document.getElementById('periodDetail').innerHTML = html;
  showPeriodDetail(type, keys[0], document.querySelector('#subChips .chip'));
}}

function showPeriodDetail(type, key, el) {{
  document.querySelectorAll('#subChips .chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  const data = type==='month' ? DATA.月份分析 : DATA.季度分析;
  const freq = data[key];
  const sorted = Object.entries(freq).sort((a,b) => b[1]-a[1]);
  document.getElementById('subDetail').innerHTML = `
    <div style="margin-bottom:8px"><span style="color:var(--hot);font-weight:700;font-size:0.8rem;">🔥 熱號 Top 8</span><br>
      ${{sorted.slice(0,8).map(([n,c])=>`${{ball(n,'hot')}} <small style="color:var(--muted)">${{c}}</small>`).join(' ')}}
    </div>
    <div><span style="color:var(--cold);font-weight:700;font-size:0.8rem;">❄️ 冷號 Top 8</span><br>
      ${{sorted.slice(-8).reverse().map(([n,c])=>`${{ball(n,'cold')}} <small style="color:var(--muted)">${{c}}</small>`).join(' ')}}
    </div>`;
}}

function renderDoughnut(id, dataObj) {{
  const labels = Object.keys(dataObj).sort();
  const values = labels.map(k => dataObj[k]);
  const colors = ['#ff7b72','#ffa657','#58a6ff','#3fb950','#d29922','#bc8cff','#79c0ff'];
  new Chart(document.getElementById(id), {{
    type:'doughnut',
    data:{{labels, datasets:[{{data:values,backgroundColor:colors,borderWidth:0}}]}},
    options:{{plugins:{{legend:{{labels:{{color:'#e6edf3',font:{{size:11}}}}}}}}}}
  }});
}}

function renderSumChart() {{
  const dist = DATA.和值分析.和值分佈;
  const keys = Object.keys(dist).map(Number).sort((a,b)=>a-b);
  new Chart(document.getElementById('sumChart'), {{
    type:'bar',
    data:{{labels:keys, datasets:[{{data:keys.map(k=>dist[k]),backgroundColor:'#58a6ff',borderRadius:2}}]}},
    options:{{plugins:{{legend:{{display:false}}}},scales:{{
      x:{{ticks:{{color:'#8b949e',maxTicksLimit:15}},grid:{{color:'rgba(255,255,255,0.04)'}}}},
      y:{{ticks:{{color:'#8b949e'}},grid:{{color:'rgba(255,255,255,0.06)'}}}}
    }}}}
  }});
}}

function renderConsecChart() {{
  const cd = DATA.連號分析;
  // 摘要
  document.getElementById('consecSummary').innerHTML = `
    <div><span style="color:var(--accent);font-weight:700;font-size:1.1rem">${{cd.平均連號組數}}</span><br><span style="color:var(--muted);font-size:0.75rem">平均連號組數</span></div>
    <div><span style="color:var(--accent);font-weight:700;font-size:1.1rem">${{cd.有連號比例}}%</span><br><span style="color:var(--muted);font-size:0.75rem">有連號的期別比例</span></div>`;
  // 圖表
  const dist = cd.分佈;
  const keys = Object.keys(dist).map(Number).sort((a,b)=>a-b);
  // X軸標籤：0→無連號，1→1組連號...
  const labels = keys.map(k => k===0 ? '無連號' : k===1 ? '1組連號' : k===2 ? '2組連號' : k===3 ? '3組連號' : k+'組連號');
  new Chart(document.getElementById('consecChart'), {{
    type:'bar',
    data:{{labels, datasets:[{{
      data:keys.map(k=>dist[k]),
      backgroundColor:keys.map(k=>k===0?'#8b949e':k===1?'#3fb950':k===2?'#58a6ff':'#ffa657'),
      borderRadius:6,
    }}]}},
    options:{{
      plugins:{{
        legend:{{display:false}},
        tooltip:{{callbacks:{{label: ctx => ` 出現 ${{ctx.raw}} 期`}}}}
      }},
      scales:{{
        x:{{ticks:{{color:'#e6edf3',font:{{size:12}}}},grid:{{color:'rgba(255,255,255,0.04)'}}}},
        y:{{ticks:{{color:'#8b949e'}},grid:{{color:'rgba(255,255,255,0.06)'}},title:{{display:true,text:'出現期數',color:'#8b949e'}}}}
      }}
    }}
  }});
}}

init();
</script>
<script>
  <div style="text-align:center;padding:20px 0 10px;color:var(--muted);font-size:0.72rem;">
  🏛️ Designed by <span style="color:var(--accent);font-weight:700;">筱鯉兒 × 雅典</span> ｜ 2026<br>
  <span style="font-size:0.65rem;opacity:0.6;">資料來源：台灣彩券官網 ｜ 僅供娛樂參考</span>
</div>
  function sendHeight() {{
    window.parent.postMessage({{ iframeHeight: document.documentElement.scrollHeight }}, '*');
  }}
  window.addEventListener('load', sendHeight);
  window.addEventListener('resize', sendHeight);
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
        print("❌ 無資料，請先執行 --update")
        exit(1)

    if args.analyze or (not args.update and not args.analyze):
        html_path = build_dashboard(df)
        if not args.no_open:
            webbrowser.open(f"file://{html_path}")
