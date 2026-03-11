from flask import Flask, Blueprint, jsonify
import os

app = Flask(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.get("/api/csv-files")
def list_csv_files():
    static_dir = app.static_folder
    files = [f for f in os.listdir(static_dir) if f.endswith('.csv')]
    return jsonify(sorted(files))

app.register_blueprint(api_bp)


@app.get("/")
def read_root():
    return app.response_class(HTML, mimetype='text/html')


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JUT Performance Analysis — Dynamic</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #111118;
    --surface2: #16161f;
    --border: #1e1e2e;
    --accent: #e8c547;
    --accent2: #47e8c5;
    --accent3: #e847a0;
    --text: #e8e8f0;
    --muted: #6b6b8a;
    --phy: #4fc3f7;
    --chem: #a78bfa;
    --math: #fb923c;
    --gold: #fbbf24;
    --silver: #94a3b8;
    --bronze: #cd7f32;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  html { scroll-behavior: smooth; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    overflow-x: hidden;
  }

  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 1000;
    opacity: 0.4;
  }

  .hero {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    position: relative;
    padding: 2rem;
    overflow: hidden;
  }

  .hero-bg {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 80% 50% at 20% 40%, rgba(232,197,71,0.08) 0%, transparent 60%),
      radial-gradient(ellipse 60% 60% at 80% 60%, rgba(71,232,197,0.06) 0%, transparent 60%),
      radial-gradient(ellipse 40% 40% at 50% 10%, rgba(232,71,160,0.05) 0%, transparent 50%);
  }

  .hero-grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
    background-size: 60px 60px;
  }

  .hero-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.3em;
    color: var(--accent);
    text-transform: uppercase;
    margin-bottom: 1.5rem;
    opacity: 0;
    animation: fadeUp 0.6s 0.2s forwards;
  }

  .hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(4rem, 12vw, 10rem);
    line-height: 0.9;
    letter-spacing: 0.02em;
    color: var(--text);
    opacity: 0;
    animation: fadeUp 0.8s 0.4s forwards;
  }

  .hero-title span {
    -webkit-text-stroke: 1px var(--accent);
    color: transparent;
  }

  .hero-sub {
    font-size: 0.85rem;
    color: var(--muted);
    letter-spacing: 0.15em;
    margin-top: 1.5rem;
    opacity: 0;
    animation: fadeUp 0.8s 0.6s forwards;
  }

  .hero-stats {
    display: flex;
    gap: 3rem;
    margin-top: 3rem;
    opacity: 0;
    animation: fadeUp 0.8s 0.8s forwards;
    justify-content: center;
  }

  .hero-stat { text-align: center; }

  .hero-stat-val {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    color: var(--accent);
    line-height: 1;
  }

  .hero-stat-label {
    font-size: 0.6rem;
    color: var(--muted);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: 0.3rem;
  }

  section {
    padding: 5rem 2rem;
    max-width: 1400px;
    margin: 0 auto;
  }

  .section-label {
    font-size: 0.65rem;
    letter-spacing: 0.4em;
    color: var(--accent);
    text-transform: uppercase;
    margin-bottom: 1rem;
  }

  .section-title {
    font-family: 'DM Serif Display', serif;
    font-size: clamp(2rem, 5vw, 3.5rem);
    line-height: 1.1;
    margin-bottom: 3rem;
    color: var(--text);
  }

  .podium-section {
    padding: 5rem 2rem;
    background: var(--surface);
    position: relative;
    overflow: hidden;
  }

  .podium-section::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(232,197,71,0.05) 0%, transparent 70%);
  }

  .podium-inner {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 2rem;
  }

  .podium {
    display: flex;
    align-items: flex-end;
    justify-content: center;
    gap: 0;
    margin-top: 3rem;
    perspective: 1000px;
  }

  .podium-card {
    flex: 1;
    max-width: 280px;
    text-align: center;
    cursor: default;
    transition: transform 0.3s ease;
  }

  .podium-card:hover { transform: translateY(-8px); }

  .podium-name {
    font-family: 'DM Serif Display', serif;
    font-size: 1.1rem;
    margin-bottom: 0.3rem;
    color: var(--text);
  }

  .podium-score {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3.5rem;
    line-height: 1;
  }

  .podium-rank-label {
    font-size: 0.6rem;
    letter-spacing: 0.3em;
    color: var(--muted);
    text-transform: uppercase;
    margin-top: 0.3rem;
  }

  .podium-block {
    margin-top: 1rem;
    border-radius: 4px 4px 0 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
  }

  .p1 .podium-score { color: var(--gold); }
  .p1 .podium-block { background: linear-gradient(135deg, #fbbf24, #f59e0b); height: 160px; }
  .p2 .podium-score { color: var(--silver); }
  .p2 .podium-block { background: linear-gradient(135deg, #94a3b8, #64748b); height: 120px; }
  .p3 .podium-score { color: var(--bronze); }
  .p3 .podium-block { background: linear-gradient(135deg, #cd7f32, #a0632a); height: 90px; }

  .leaderboard-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 4px;
  }

  .leaderboard-table th {
    font-size: 0.6rem;
    letter-spacing: 0.25em;
    color: var(--muted);
    text-transform: uppercase;
    padding: 0.5rem 1rem;
    text-align: left;
    font-weight: 400;
  }

  .leaderboard-table tr.row {
    background: var(--surface);
    transition: all 0.25s ease;
    cursor: default;
  }

  .leaderboard-table tr.row:hover { background: var(--surface2); transform: translateX(4px); }

  .leaderboard-table td {
    padding: 0.9rem 1rem;
    font-size: 0.78rem;
    border-top: 1px solid transparent;
    border-bottom: 1px solid transparent;
  }

  .leaderboard-table tr.row:hover td { border-color: var(--border); }

  .rank-badge {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.3rem;
    width: 36px;
    text-align: center;
    display: inline-block;
  }

  .rank-1 { color: var(--gold); }
  .rank-2 { color: var(--silver); }
  .rank-3 { color: var(--bronze); }
  .rank-other { color: var(--muted); }

  .score-pill {
    display: inline-block;
    padding: 0.2rem 0.8rem;
    border-radius: 2px;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.2rem;
    letter-spacing: 0.05em;
  }

  .mini-bar-wrap { display: flex; gap: 3px; align-items: center; }

  .mini-bar {
    height: 6px;
    border-radius: 1px;
    flex-shrink: 0;
    transition: width 1s ease;
  }

  .name-cell {
    font-family: 'DM Serif Display', serif;
    font-size: 0.9rem;
    color: var(--text);
  }

  .charts-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    margin-top: 2rem;
  }

  .chart-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2rem;
    position: relative;
    overflow: hidden;
  }

  .chart-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
  }

  .chart-title {
    font-size: 0.65rem;
    letter-spacing: 0.3em;
    color: var(--muted);
    text-transform: uppercase;
    margin-bottom: 1.5rem;
  }

  canvas { width: 100% !important; max-height: 300px; }

  .subject-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.5rem;
    margin-top: 2rem;
  }

  .subj-card {
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 1.5rem;
    border-radius: 4px;
    position: relative;
    overflow: hidden;
    transition: transform 0.25s;
  }

  .subj-card:hover { transform: translateY(-4px); }
  .subj-card.phy { border-top: 3px solid var(--phy); }
  .subj-card.chem { border-top: 3px solid var(--chem); }
  .subj-card.math { border-top: 3px solid var(--math); }

  .subj-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
  }

  .subj-card.phy .subj-name { color: var(--phy); }
  .subj-card.chem .subj-name { color: var(--chem); }
  .subj-card.math .subj-name { color: var(--math); }

  .subj-stat-row {
    display: flex;
    justify-content: space-between;
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.72rem;
  }

  .subj-stat-row:last-child { border-bottom: none; }
  .subj-stat-key { color: var(--muted); }
  .subj-stat-val { color: var(--text); font-weight: 600; }

  .matrix-wrap { overflow-x: auto; }

  .matrix-grid {
    display: grid;
    justify-content: center;
    gap: 3px;
    min-width: 600px;
  }

  .matrix-cell {
    aspect-ratio: 1;
    border-radius: 2px;
    position: relative;
    cursor: pointer;
    transition: transform 0.15s;
  }

  .matrix-cell:hover { transform: scale(1.15); z-index: 10; }

  .matrix-cell .tooltip {
    position: absolute;
    bottom: calc(100% + 6px);
    left: 50%;
    transform: translateX(-50%);
    background: #000;
    border: 1px solid var(--border);
    padding: 0.4rem 0.6rem;
    border-radius: 3px;
    font-size: 0.6rem;
    white-space: nowrap;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s;
    z-index: 100;
    color: var(--text);
  }

  .matrix-cell:hover .tooltip { opacity: 1; }

  .dist-bar-container { margin-top: 1.5rem; }

  .dist-bar-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.6rem;
  }

  .dist-range { font-size: 0.65rem; color: var(--muted); width: 80px; flex-shrink: 0; }

  .dist-bar-outer {
    flex: 1;
    height: 24px;
    background: var(--surface2);
    border-radius: 2px;
    overflow: hidden;
    position: relative;
  }

  .dist-bar-inner {
    height: 100%;
    border-radius: 2px;
    display: flex;
    align-items: center;
    padding-left: 8px;
    font-size: 0.65rem;
    font-weight: 600;
    color: rgba(0,0,0,0.7);
    transition: width 1.5s cubic-bezier(0.4,0,0.2,1);
    width: 0;
  }

  .dist-count { font-size: 0.7rem; color: var(--muted); width: 20px; text-align: right; flex-shrink: 0; }

  footer {
    text-align: center;
    padding: 3rem 2rem;
    color: var(--muted);
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    border-top: 1px solid var(--border);
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .reveal {
    opacity: 0;
    transform: translateY(30px);
    transition: opacity 0.7s ease, transform 0.7s ease;
  }

  .reveal.visible { opacity: 1; transform: translateY(0); }

  .divider {
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
  }

  .filter-bar {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .search-input {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 0.6rem 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    border-radius: 2px;
    outline: none;
    flex: 1;
    min-width: 200px;
    transition: border-color 0.2s;
  }

  .search-input:focus { border-color: var(--accent); }
  .search-input::placeholder { color: var(--muted); }

  .sort-btn {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 0.6rem 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    cursor: pointer;
    border-radius: 2px;
    transition: all 0.2s;
  }

  .sort-btn:hover, .sort-btn.active { border-color: var(--accent); color: var(--accent); }

  .tier-excellent { background: rgba(71,232,197,0.1); }
  .tier-good { background: rgba(232,197,71,0.1); }
  .tier-average { background: rgba(251,146,60,0.1); }
  .tier-poor { background: rgba(232,71,160,0.08); }

  /* ---- CSV PICKER ---- */
  #uploadOverlay {
    position: fixed;
    inset: 0;
    z-index: 2000;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(10,10,15,0.95);
    backdrop-filter: blur(10px);
    transition: opacity 0.5s;
  }

  .picker-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    color: #e8c547;
    line-height: 1;
    text-align: center;
  }

  .picker-sub {
    font-size: 0.7rem;
    letter-spacing: 0.25em;
    color: #6b6b8a;
    margin-top: 0.75rem;
    text-transform: uppercase;
    text-align: center;
  }

  #csvMenu {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    width: 90%;
    max-width: 480px;
    margin-top: 2rem;
    max-height: 60vh;
    overflow-y: auto;
  }

  .csv-btn {
    background: #111118;
    border: 1px solid #1e1e2e;
    color: #e8e8f0;
    padding: 1rem 1.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    cursor: pointer;
    border-radius: 3px;
    text-align: left;
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: border-color 0.2s, background 0.2s, color 0.2s;
  }

  .csv-btn:hover {
    border-color: #e8c547;
    color: #e8c547;
    background: #16161f;
  }

  .csv-btn-filename {
    color: #6b6b8a;
    font-size: 0.6rem;
  }

  #uploadError {
    color: #e847a0;
    font-size: 0.7rem;
    margin-top: 1.5rem;
    display: none;
  }

  @media (max-width: 768px) {
    .charts-grid { grid-template-columns: 1fr; }
    .subject-grid { grid-template-columns: 1fr; }
    .hero-stats { gap: 1.5rem; }
    .podium { gap: 0.5rem; }
  }
</style>
</head>
<body>

<div class="hero">
  <div class="hero-bg"></div>
  <div class="hero-grid"></div>
  <div style="position:relative;z-index:2;">
    <div class="hero-tag" id="heroTag">NEW JUT · Batch Analysis</div>
    <div class="hero-title">PERFOR<span>MANCE</span><br>REPORT</div>
    <div class="hero-sub" id="heroSub">SELECT A TEST TO BEGIN</div>
    <div class="hero-stats">
      <div class="hero-stat">
        <div class="hero-stat-val" id="hs-avg">—</div>
        <div class="hero-stat-label">Avg Score</div>
      </div>
      <div class="hero-stat">
        <div class="hero-stat-val" id="hs-high">—</div>
        <div class="hero-stat-label">Top Score</div>
      </div>
      <div class="hero-stat">
        <div class="hero-stat-val" id="hs-acc">—</div>
        <div class="hero-stat-label">Avg Accuracy</div>
      </div>
      <div class="hero-stat">
        <div class="hero-stat-val" id="hs-count">—</div>
        <div class="hero-stat-label">Students</div>
      </div>
    </div>
  </div>
</div>

<div class="podium-section">
  <div class="podium-inner">
    <div class="section-label reveal">Top Performers</div>
    <div class="section-title reveal">The Podium</div>
    <div class="podium reveal" id="podium"></div>
  </div>
</div>

<div class="divider"></div>

<section>
  <div class="section-label reveal">Full Results</div>
  <div class="section-title reveal">Leaderboard</div>
  <div class="filter-bar reveal">
    <input class="search-input" id="searchInput" type="text" placeholder="Search student…">
    <button class="sort-btn active" data-sort="total">Total ↕</button>
    <button class="sort-btn" data-sort="phy">Physics ↕</button>
    <button class="sort-btn" data-sort="chem">Chemistry ↕</button>
    <button class="sort-btn" data-sort="math">Maths ↕</button>
    <button class="sort-btn" data-sort="acc">Accuracy ↕</button>
  </div>
  <div class="reveal">
    <table class="leaderboard-table">
      <thead>
        <tr>
          <th>#</th><th>Student</th><th>Score</th><th>Subject Breakdown</th><th>Accuracy</th><th>Attempted</th>
        </tr>
      </thead>
      <tbody id="leaderboardBody"></tbody>
    </table>
  </div>
</section>

<div class="divider"></div>

<section>
  <div class="section-label reveal">Subject Performance</div>
  <div class="section-title reveal">Deep Dive</div>
  <div class="subject-grid">
    <div class="subj-card phy reveal" id="physCard"></div>
    <div class="subj-card chem reveal" id="chemCard"></div>
    <div class="subj-card math reveal" id="mathCard"></div>
  </div>
</section>

<div class="divider"></div>

<section>
  <div class="section-label reveal">Visual Analysis</div>
  <div class="section-title reveal">Score Insights</div>
  <div class="charts-grid">
    <div class="chart-card reveal">
      <div class="chart-title">Score Distribution</div>
      <div class="dist-bar-container" id="distBars"></div>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Subject Average Comparison</div>
      <canvas id="radarChart"></canvas>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Correct vs Wrong vs Unattempted</div>
      <canvas id="stackedChart"></canvas>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Accuracy per Student</div>
      <canvas id="accuracyChart"></canvas>
    </div>
  </div>
</section>

<div class="divider"></div>

<section>
  <div class="section-label reveal">Accuracy Heatmap</div>
  <div class="section-title reveal">Who Got What Right</div>
  <div class="matrix-wrap reveal">
    <div style="display:flex;gap:0.5rem;margin-bottom:1rem;align-items:center;flex-wrap:wrap;justify-content:center;">
      <span style="font-size:0.6rem;letter-spacing:0.15em;color:var(--muted);text-transform:uppercase;">Subject:</span>
      <span style="font-size:0.65rem;color:var(--phy);">&#9632; Physics</span>
      <span style="font-size:0.65rem;color:var(--chem);">&#9632; Chemistry</span>
      <span style="font-size:0.65rem;color:var(--math);">&#9632; Maths</span>
    </div>
    <div id="heatmapGrid" class="matrix-grid"></div>
  </div>
</section>

<footer id="footerBar">JUT ANALYSIS DASHBOARD</footer>

<!-- CSV PICKER OVERLAY -->
<div id="uploadOverlay">
  <div class="picker-title">SELECT TEST</div>
  <div class="picker-sub">Choose a CSV file to analyse</div>
  <div id="csvMenu"></div>
  <div id="uploadError"></div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script>
function firstMeaningfulName(fullName) {
  const parts = fullName.trim().split(/\s+/);
  for (const part of parts) { if (part.length > 1) return part; }
  return parts[0] || fullName;
}

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/\s+/g,'_'));
  return lines.slice(1).map(line => {
    const vals = line.split(',');
    const obj = {};
    headers.forEach((h,i) => { obj[h] = vals[i] !== undefined ? vals[i].trim() : ''; });
    return obj;
  }).filter(r => r[headers[0]]);
}

function n(v) { return parseFloat(v) || 0; }

function mapRow(r) {
  const get = (...keys) => { for(const k of keys){ if(r[k]!==undefined) return r[k]; } return '0'; };
  return {
    name:   get('name') || 'Unknown',
    total:  n(get('total_marks','total_score','total')),
    rank:   n(get('rank')),
    phy_a:  n(get('phy_attempt','physics_attempt')),
    chem_a: n(get('chem_attempt','chemistry_attempt')),
    math_a: n(get('math_attempt','maths_attempt')),
    tot_a:  n(get('total_attempt')),
    phy_c:  n(get('phy_correct','physics_correct')),
    chem_c: n(get('chem_correct','chemistry_correct')),
    math_c: n(get('math_correct','maths_correct')),
    tot_c:  n(get('total_correct')),
    phy_w:  n(get('phy_wrong','physics_wrong')),
    chem_w: n(get('chem_wrong','chemistry_wrong')),
    math_w: n(get('math_wrong','maths_wrong')),
    tot_w:  n(get('total_wrong')),
    phy_m:  n(get('phy_marks','physics_marks')),
    chem_m: n(get('chem_marks','chemistry_marks')),
    math_m: n(get('math_marks','maths_marks')),
  };
}

let radarInst, stackedInst, accuracyInst;

function buildDashboard(raw, filename) {
  raw.forEach(s => { s.accuracy = s.tot_a > 0 ? Math.round((s.tot_c / s.tot_a) * 100) : 0; });
  const sorted = [...raw].sort((a,b) => b.total - a.total);
  const avg = Math.round(raw.reduce((s,r) => s+r.total, 0) / raw.length);
  const high = Math.max(...raw.map(r => r.total));
  const avgAcc = Math.round(raw.reduce((s,r) => s+r.accuracy, 0) / raw.length);

  document.getElementById('hs-avg').textContent = avg;
  document.getElementById('hs-high').textContent = high;
  document.getElementById('hs-acc').textContent = avgAcc + '%';
  document.getElementById('hs-count').textContent = raw.length;
  document.getElementById('heroSub').textContent = raw.length + ' STUDENTS · PHYSICS · CHEMISTRY · MATHEMATICS';
  const label = filename.replace('.csv','').replace(/_/g,' ').toUpperCase();
  document.getElementById('heroTag').textContent = 'NEW JUT · ' + label + ' · BATCH ANALYSIS';
  document.getElementById('footerBar').textContent = 'JUT ANALYSIS DASHBOARD · ' + raw.length + ' STUDENTS';

  // PODIUM
  const podiumEl = document.getElementById('podium');
  podiumEl.innerHTML = '';
  const top3 = sorted.slice(0,3);
  const podiumOrder = [top3[1], top3[0], top3[2]].filter(Boolean);
  const heights = [120, 160, 90];
  const podiumClasses = ['p2','p1','p3'];
  const medals = ['medal2','medal1','medal3'];
  const bgColors = ['linear-gradient(135deg,#94a3b8,#64748b)','linear-gradient(135deg,#fbbf24,#f59e0b)','linear-gradient(135deg,#cd7f32,#a0632a)'];
  const scoreColors = ['var(--silver)','var(--gold)','var(--bronze)'];
  const medalEmoji = ['\u{1F948}','\u{1F947}','\u{1F949}'];
  podiumOrder.forEach((s,i) => {
    const c = document.createElement('div');
    c.className = 'podium-card ' + podiumClasses[i];
    c.innerHTML = '<div class="podium-name">' + s.name + '</div>' +
      '<div class="podium-score" style="color:' + scoreColors[i] + '">' + s.total + '</div>' +
      '<div class="podium-rank-label">Overall Rank ' + (s.rank || i+1) + '</div>' +
      '<div class="podium-block" style="height:' + heights[i] + 'px;background:' + bgColors[i] + ';">' +
      '<span style="font-size:2rem;">' + medalEmoji[i] + '</span></div>';
    podiumEl.appendChild(c);
  });

  // LEADERBOARD
  let currentSort = 'total', sortDir = -1, filterText = '';

  function getTier(score) {
    if (score >= high * 0.75) return 'tier-excellent';
    if (score >= high * 0.5)  return 'tier-good';
    if (score >= high * 0.25) return 'tier-average';
    return 'tier-poor';
  }

  function renderLeaderboard() {
    let data = [...raw];
    if (filterText) data = data.filter(s => s.name.toLowerCase().includes(filterText.toLowerCase()));
    const valKeys = {total:'total',phy:'phy_m',chem:'chem_m',math:'math_m',acc:'accuracy'};
    data.sort((a,b) => sortDir * (b[valKeys[currentSort]] - a[valKeys[currentSort]]));
    const tbody = document.getElementById('leaderboardBody');
    tbody.innerHTML = '';
    data.forEach(s => {
      const maxScore = high || 300;
      const phyPct  = Math.max(0, (s.phy_m  / maxScore) * 100);
      const chemPct = Math.max(0, (s.chem_m / maxScore) * 100);
      const mathPct = Math.max(0, (s.math_m / maxScore) * 100);
      const localRank = sorted.indexOf(s) + 1;
      const rankClass = localRank===1 ? 'rank-1' : localRank===2 ? 'rank-2' : localRank===3 ? 'rank-3' : 'rank-other';
      const scoreColor = s.total >= high*0.75 ? 'var(--accent2)' : s.total >= high*0.5 ? 'var(--accent)' : s.total >= high*0.25 ? 'var(--math)' : 'var(--accent3)';
      const accColor = s.accuracy>=60 ? 'var(--accent2)' : s.accuracy>=40 ? 'var(--accent)' : 'var(--accent3)';
      const tr = document.createElement('tr');
      tr.className = 'row ' + getTier(s.total);
      tr.innerHTML =
        '<td><span class="rank-badge ' + rankClass + '">' + localRank + '</span></td>' +
        '<td><div class="name-cell">' + s.name + '</div></td>' +
        '<td><span class="score-pill" style="background:' + scoreColor + '22;color:' + scoreColor + '">' + s.total + '</span></td>' +
        '<td><div class="mini-bar-wrap">' +
          '<div class="mini-bar" style="width:' + (phyPct*2) + 'px;background:var(--phy)"></div>' +
          '<div class="mini-bar" style="width:' + (chemPct*2) + 'px;background:var(--chem)"></div>' +
          '<div class="mini-bar" style="width:' + (mathPct*2) + 'px;background:var(--math)"></div>' +
        '</div><div style="font-size:0.6rem;color:var(--muted);margin-top:3px;">P:' + s.phy_m + ' \u00b7 C:' + s.chem_m + ' \u00b7 M:' + s.math_m + '</div></td>' +
        '<td style="color:' + accColor + '">' + s.accuracy + '%</td>' +
        '<td style="color:var(--muted)">' + s.tot_a + '/75</td>';
      tbody.appendChild(tr);
    });
  }
  renderLeaderboard();

  document.getElementById('searchInput').oninput = e => { filterText = e.target.value; renderLeaderboard(); };
  document.querySelectorAll('.sort-btn').forEach(btn => {
    btn.onclick = () => {
      const sv = btn.dataset.sort;
      if (sv === currentSort) sortDir *= -1; else { currentSort = sv; sortDir = -1; }
      document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderLeaderboard();
    };
  });

  // SUBJECT CARDS
  function subjectStats(marks, correct, wrong, attempt) {
    const avg = (marks.reduce((a,b)=>a+b,0)/marks.length).toFixed(1);
    const best = Math.max(...marks), worst = Math.min(...marks);
    const avgC = (correct.reduce((a,b)=>a+b,0)/correct.length).toFixed(1);
    const avgW = (wrong.reduce((a,b)=>a+b,0)/wrong.length).toFixed(1);
    const totalC = correct.reduce((a,b)=>a+b,0), totalA = attempt.reduce((a,b)=>a+b,0);
    const acc = totalA > 0 ? Math.round((totalC/totalA)*100) : 0;
    return {avg, best, worst, avgC, avgW, acc};
  }
  function makeSubjectCard(id, label, color, marks, correct, wrong, attempt) {
    const s = subjectStats(marks, correct, wrong, attempt);
    document.getElementById(id).innerHTML =
      '<div class="subj-name">' + label + '</div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Avg Marks</span><span class="subj-stat-val" style="color:' + color + '">' + s.avg + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Highest</span><span class="subj-stat-val">' + s.best + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Lowest</span><span class="subj-stat-val">' + s.worst + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Avg Correct</span><span class="subj-stat-val">' + s.avgC + ' / 25</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Avg Wrong</span><span class="subj-stat-val">' + s.avgW + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Accuracy</span><span class="subj-stat-val">' + s.acc + '%</span></div>';
  }
  makeSubjectCard('physCard','Physics','var(--phy)',raw.map(r=>r.phy_m),raw.map(r=>r.phy_c),raw.map(r=>r.phy_w),raw.map(r=>r.phy_a));
  makeSubjectCard('chemCard','Chemistry','var(--chem)',raw.map(r=>r.chem_m),raw.map(r=>r.chem_c),raw.map(r=>r.chem_w),raw.map(r=>r.chem_a));
  makeSubjectCard('mathCard','Maths','var(--math)',raw.map(r=>r.math_m),raw.map(r=>r.math_c),raw.map(r=>r.math_w),raw.map(r=>r.math_a));

  // DISTRIBUTION BARS
  const distContainer = document.getElementById('distBars');
  distContainer.innerHTML = '';
  const step = high > 0 ? Math.ceil(high / 5) : 60;
  const ranges = [];
  for(let i=4;i>=0;i--) ranges.push([i*step, (i+1)*step - (i<4?1:0)]);
  const rangeLabels = ranges.map(([lo,hi],i) => i===0 ? lo+'+' : lo+'\u2013'+hi);
  const rangeCounts = ranges.map(([lo,hi]) => raw.filter(s=>s.total>=lo&&s.total<=hi).length);
  const maxCount = Math.max(...rangeCounts, 1);
  const barColors = ['#47e8c5','#e8c547','#fb923c','#a78bfa','#e847a0'];
  ranges.forEach((_,i) => {
    const pct = (rangeCounts[i]/maxCount)*100;
    const row = document.createElement('div');
    row.className = 'dist-bar-row';
    row.innerHTML =
      '<div class="dist-range">' + rangeLabels[i] + '</div>' +
      '<div class="dist-bar-outer"><div class="dist-bar-inner" data-pct="' + pct + '" style="background:' + barColors[i] + ';width:0%">' +
      (rangeCounts[i]>0 ? rangeCounts[i]+' student'+(rangeCounts[i]>1?'s':'') : '') + '</div></div>' +
      '<div class="dist-count">' + rangeCounts[i] + '</div>';
    distContainer.appendChild(row);
  });
  setTimeout(() => { document.querySelectorAll('.dist-bar-inner').forEach(b => { b.style.width = b.dataset.pct + '%'; }); }, 300);

  // RADAR
  const phyAvg = raw.reduce((a,r)=>a+r.phy_m,0)/raw.length;
  const chemAvg = raw.reduce((a,r)=>a+r.chem_m,0)/raw.length;
  const mathAvg = raw.reduce((a,r)=>a+r.math_m,0)/raw.length;
  if(radarInst) radarInst.destroy();
  radarInst = new Chart(document.getElementById('radarChart'), {
    type:'radar',
    data:{labels:['Physics','Chemistry','Mathematics'],datasets:[{label:'Avg Marks',data:[phyAvg.toFixed(1),chemAvg.toFixed(1),mathAvg.toFixed(1)],borderColor:'#e8c547',backgroundColor:'rgba(232,197,71,0.1)',pointBackgroundColor:['#4fc3f7','#a78bfa','#fb923c'],pointRadius:6,borderWidth:2}]},
    options:{scales:{r:{grid:{color:'#1e1e2e'},ticks:{display:false},pointLabels:{color:'#e8e8f0',font:{family:'JetBrains Mono',size:11}}}},plugins:{legend:{display:false}}}
  });

  // STACKED BAR
  const top10 = sorted.slice(0,10);
  if(stackedInst) stackedInst.destroy();
  stackedInst = new Chart(document.getElementById('stackedChart'), {
    type:'bar',
    data:{labels:top10.map(s=>firstMeaningfulName(s.name)),datasets:[
      {label:'Correct',data:top10.map(s=>s.tot_c),backgroundColor:'#47e8c5bb',stack:'s'},
      {label:'Wrong',data:top10.map(s=>s.tot_w),backgroundColor:'#e847a0bb',stack:'s'},
      {label:'Unattempted',data:top10.map(s=>75-s.tot_a),backgroundColor:'#1e1e2e',stack:'s'},
    ]},
    options:{scales:{x:{ticks:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}},grid:{color:'#1e1e2e'}},y:{ticks:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}},grid:{color:'#1e1e2e'},max:75}},plugins:{legend:{labels:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}}}}}
  });

  // ACCURACY CHART
  const accSorted = [...raw].sort((a,b)=>b.accuracy-a.accuracy);
  if(accuracyInst) accuracyInst.destroy();
  accuracyInst = new Chart(document.getElementById('accuracyChart'), {
    type:'bar',
    data:{labels:accSorted.map(s=>firstMeaningfulName(s.name)),datasets:[{label:'Accuracy %',data:accSorted.map(s=>s.accuracy),backgroundColor:accSorted.map(s=>s.accuracy>=70?'#47e8c5aa':s.accuracy>=50?'#e8c547aa':s.accuracy>=35?'#fb923caa':'#e847a0aa'),borderRadius:2}]},
    options:{indexAxis:'y',scales:{x:{ticks:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}},grid:{color:'#1e1e2e'},max:100},y:{ticks:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}},grid:{color:'transparent'}}},plugins:{legend:{display:false}}}
  });

  // HEATMAP
  const hmGrid = document.getElementById('heatmapGrid');
  hmGrid.innerHTML = '';
  const subjects = ['phy','chem','math'];
  const subjColors = {'phy':'79,195,247','chem':'167,139,250','math':'251,146,60'};
  hmGrid.style.gridTemplateColumns = 'repeat(' + (subjects.length * 3) + ', 28px)';
  ['P','C','M'].forEach(s => { ['C','W','%'].forEach(t => {
    const cell = document.createElement('div');
    cell.style.cssText = 'font-size:0.55rem;color:var(--muted);letter-spacing:0.1em;text-align:center;padding-bottom:4px;';
    cell.textContent = s + '\u00b7' + t;
    hmGrid.appendChild(cell);
  }); });
  sorted.forEach(s => {
    subjects.forEach(subj => {
      const c = s[subj+'_c'], w = s[subj+'_w'], a = s[subj+'_a'];
      const acc = a > 0 ? Math.round((c/a)*100) : 0;
      const rgb = subjColors[subj];
      const dn = firstMeaningfulName(s.name);
      const mk = (bg, tip) => {
        const el = document.createElement('div');
        el.className = 'matrix-cell';
        el.style.cssText = 'background:' + bg + ';width:28px;height:28px;';
        el.innerHTML = '<div class="tooltip">' + dn + ' \u00b7 ' + subj.toUpperCase() + ' ' + tip + '</div>';
        hmGrid.appendChild(el);
      };
      mk('rgba('+rgb+','+(0.1+(c/25)*0.7)+')', 'correct: '+c);
      mk('rgba(232,71,160,'+(0.05+(w/25)*0.7)+')', 'wrong: '+w);
      mk('rgba(232,197,71,'+(0.05+(acc/100)*0.7)+')', 'accuracy: '+acc+'%');
    });
  });

  // SCROLL REVEAL
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if(e.isIntersecting){
        e.target.classList.add('visible');
        e.target.querySelectorAll('.dist-bar-inner').forEach(b => { b.style.width = b.dataset.pct + '%'; });
      }
    });
  }, {threshold:0.1});
  document.querySelectorAll('.reveal').forEach(el => { el.classList.remove('visible'); observer.observe(el); });
}

// ─── FILE PICKER ──────────────────────────────────────────────
function showError(msg) {
  const el = document.getElementById('uploadError');
  el.textContent = msg;
  el.style.display = 'block';
}

async function loadCSVByName(filename) {
  try {
    const res = await fetch('/static/' + filename);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const text = await res.text();
    const rows = parseCSV(text);
    if (rows.length === 0) { showError('CSV appears to be empty or malformed'); return; }
    const mapped = rows.map(mapRow);
    const overlay = document.getElementById('uploadOverlay');
    overlay.style.opacity = '0';
    setTimeout(() => { overlay.style.display = 'none'; }, 500);
    buildDashboard(mapped, filename);
  } catch(err) {
    showError('Error loading file: ' + err.message);
  }
}

async function populateMenu() {
  const menu = document.getElementById('csvMenu');
  try {
    const res = await fetch('/api/csv-files');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const files = await res.json();
    if (files.length === 0) {
      menu.innerHTML = '<div style="color:#6b6b8a;font-size:0.75rem;letter-spacing:0.15em;">NO CSV FILES FOUND IN /static</div>';
      return;
    }
    files.forEach(filename => {
      const label = filename.replace('.csv','').replace(/_/g,' ').toUpperCase();
      const btn = document.createElement('button');
      btn.className = 'csv-btn';
      btn.innerHTML = '<span>' + label + '</span><span class="csv-btn-filename">' + filename + '</span>';
      btn.addEventListener('click', () => loadCSVByName(filename));
      menu.appendChild(btn);
    });
  } catch(err) {
    menu.innerHTML = '<div style="color:#e847a0;font-size:0.7rem;">Failed to load file list: ' + err.message + '</div>';
  }
}

populateMenu();
</script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(debug=True)
