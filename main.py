from flask import Flask, Blueprint, jsonify, request
import os
import csv

app = Flask(__name__)

api_bp = Blueprint('api', __name__)

# ── ALL blueprint routes MUST be defined before app.register_blueprint() ──

@api_bp.get("/api/csv-files")
def list_csv_files():
    static_dir = app.static_folder
    files = [f for f in os.listdir(static_dir) if f.endswith('.csv')]
    return jsonify(sorted(files))


@api_bp.get("/api/master-data")
def get_master_data():
    """Return all rows from master/master.csv as JSON."""
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    rows = []
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()})
    return jsonify(rows)


@api_bp.get("/api/student/<path:student_name>")
def get_student_data(student_name):
    """Return all rows for a specific student from master.csv."""
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    results = []
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
            if clean.get('name', '').strip().lower() == student_name.strip().lower():
                results.append(clean)
    return jsonify(results)


# ── Register blueprint AFTER all routes are defined ──
app.register_blueprint(api_bp)


# ── Page routes (these go on `app` directly, not the blueprint) ──

@app.get("/")
def read_root():
    return app.response_class(HOME_HTML, mimetype='text/html')


@app.get("/analysis")
def analysis():
    return app.response_class(ANALYSIS_HTML, mimetype='text/html')


INDIVIDUAL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JUT · Student Profile</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@300;400;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
:root {
  --bg: #0a0a0f;
  --surface: #111118;
  --surface2: #16161f;
  --surface3: #1a1a28;
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
  --green: #4ade80;
  --red: #f87171;
}

* { margin:0; padding:0; box-sizing:border-box; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'JetBrains Mono', monospace;
  overflow-x: hidden;
}

/* noise */
body::after {
  content:'';
  position:fixed; inset:0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
  pointer-events:none; z-index:9999; opacity:0.4;
}

/* ── TOPNAV ── */
.topnav {
  position:fixed; top:0; left:0; right:0; z-index:500;
  background:rgba(10,10,15,0.88);
  backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);
  display:flex; align-items:center; justify-content:space-between;
  padding:0.9rem 2rem;
}
.topnav-logo {
  font-family:'Bebas Neue',sans-serif; font-size:1.4rem;
  letter-spacing:0.08em; color:var(--text); text-decoration:none;
}
.topnav-logo span{color:var(--accent);}
.topnav-back {
  font-size:0.6rem; letter-spacing:0.25em; text-transform:uppercase;
  color:var(--muted); text-decoration:none;
  display:flex; align-items:center; gap:0.4rem; transition:color 0.2s;
}
.topnav-back:hover{color:var(--accent);}
.nav-breadcrumb {
  font-size:0.58rem; letter-spacing:0.18em; color:var(--accent2);
  text-transform:uppercase; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  max-width:240px;
}

/* ── HERO ── */
.hero {
  min-height:100vh; display:flex; flex-direction:column;
  justify-content:flex-end; align-items:flex-start;
  padding:8rem 4rem 5rem;
  position:relative; overflow:hidden;
}
.hero-bg-layers {
  position:absolute; inset:0;
  background:
    radial-gradient(ellipse 100% 70% at 80% 20%, rgba(232,197,71,0.06) 0%, transparent 60%),
    radial-gradient(ellipse 60% 80% at 0% 80%, rgba(71,232,197,0.05) 0%, transparent 60%),
    radial-gradient(ellipse 50% 50% at 50% 50%, rgba(232,71,160,0.03) 0%, transparent 60%);
}
.hero-scanlines {
  position:absolute; inset:0;
  background: repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(255,255,255,0.005) 2px,rgba(255,255,255,0.005) 4px);
  pointer-events:none;
}
.hero-grid {
  position:absolute; inset:0;
  background-image:
    linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
  background-size:80px 80px;
  animation: gridDrift 40s linear infinite;
}
@keyframes gridDrift { 0%{background-position:0 0} 100%{background-position:80px 80px} }

.hero-num {
  position:absolute; right:4rem; top:50%;
  transform:translateY(-50%);
  font-family:'Bebas Neue',sans-serif;
  font-size:clamp(12rem,25vw,22rem);
  line-height:1;
  -webkit-text-stroke:1px rgba(232,197,71,0.1);
  color:transparent;
  user-select:none; pointer-events:none;
  opacity:0; animation:fadeIn 1.2s 0.5s forwards;
  letter-spacing:-0.02em;
}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}

.hero-content{position:relative;z-index:5;}
.hero-eyebrow {
  font-size:0.65rem; letter-spacing:0.45em; color:var(--accent2);
  text-transform:uppercase; margin-bottom:1.2rem;
  opacity:0; animation:slideUp 0.6s 0.2s forwards;
  display:flex; align-items:center; gap:1rem;
}
.hero-eyebrow::before {
  content:''; display:block; width:40px; height:1px; background:var(--accent2);
}
.hero-name {
  font-family:'Bebas Neue',sans-serif;
  font-size:clamp(4rem,12vw,9rem);
  line-height:0.85; letter-spacing:0.02em;
  color:var(--text);
  opacity:0; animation:slideUp 0.8s 0.35s forwards;
}
.hero-name .outline {
  -webkit-text-stroke:1.5px var(--accent); color:transparent;
  display:block;
}
.hero-tagline {
  font-size:0.75rem; color:var(--muted); letter-spacing:0.2em;
  margin-top:1.5rem;
  opacity:0; animation:slideUp 0.7s 0.55s forwards;
}
.hero-metrics {
  display:flex; gap:2rem; margin-top:3rem;
  opacity:0; animation:slideUp 0.7s 0.7s forwards;
  flex-wrap:wrap;
}
.hero-metric { text-align:left; }
.hero-metric-val {
  font-family:'Bebas Neue',sans-serif; font-size:3.5rem;
  color:var(--accent); line-height:1;
}
.hero-metric-label {
  font-size:0.55rem; letter-spacing:0.3em; color:var(--muted);
  text-transform:uppercase; margin-top:0.2rem;
}

@keyframes slideUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}

/* ── PROGRESS RING ── */
.ring-cluster {
  position:absolute; right:3rem; bottom:3rem; z-index:5;
  display:flex; gap:1.5rem; align-items:flex-end;
  opacity:0; animation:fadeIn 1s 1s forwards;
}
.ring-wrap{ text-align:center; }
.ring-label{font-size:0.55rem;letter-spacing:0.2em;color:var(--muted);text-transform:uppercase;margin-top:0.4rem;}
svg.ring{transform:rotate(-90deg);}
.ring-bg{fill:none;stroke:var(--border);stroke-width:6;}
.ring-fill{fill:none;stroke-width:6;stroke-linecap:round;transition:stroke-dashoffset 1.5s cubic-bezier(0.4,0,0.2,1);}
.ring-text{
  font-family:'Bebas Neue',sans-serif; font-size:1.1rem;
  position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
}
.ring-container{position:relative;display:inline-block;}

/* ── SECTIONS ── */
.main-content{max-width:1400px;margin:0 auto;padding:0 3rem 6rem;}
section{padding:5rem 0;}
.section-label{
  font-size:0.62rem;letter-spacing:0.45em;color:var(--accent);
  text-transform:uppercase;margin-bottom:0.8rem;
  display:flex;align-items:center;gap:1rem;
}
.section-label::before{content:'';display:block;width:30px;height:1px;background:var(--accent);}
.section-title{
  font-family:'DM Serif Display',serif;
  font-size:clamp(2rem,5vw,3.2rem); margin-bottom:2.5rem;
}
.divider{
  height:1px;
  background:linear-gradient(90deg,transparent,var(--border) 20%,var(--border) 80%,transparent);
}

/* ── JUT TIMELINE ── */
.timeline{position:relative;padding-left:3rem;margin-top:2rem;}
.timeline::before{
  content:''; position:absolute; left:12px; top:0; bottom:0;
  width:1px; background:linear-gradient(to bottom,var(--accent),var(--border));
}
.tl-item{
  position:relative; margin-bottom:2rem;
  opacity:0; transform:translateX(-20px);
  transition:opacity 0.6s,transform 0.6s;
}
.tl-item.vis{opacity:1;transform:translateX(0);}
.tl-dot{
  position:absolute; left:-2.35rem; top:1.2rem;
  width:12px;height:12px;border-radius:50%;
  border:2px solid var(--accent);background:var(--bg);
  box-shadow:0 0 12px rgba(232,197,71,0.4);
}
.tl-dot.absent{border-color:var(--muted);box-shadow:none;background:var(--muted);}
.tl-dot.best{border-color:var(--accent2);box-shadow:0 0 16px rgba(71,232,197,0.6);}
.tl-card{
  background:var(--surface);border:1px solid var(--border);
  border-radius:6px;padding:1.5rem 2rem;
  position:relative;overflow:hidden;
  transition:transform 0.3s,border-color 0.3s;cursor:default;
}
.tl-card:hover{transform:translateX(8px);border-color:var(--accent);}
.tl-card::before{
  content:'';position:absolute;left:0;top:0;bottom:0;width:3px;
  background:linear-gradient(to bottom,var(--accent),var(--accent2));
}
.tl-card.absent::before{background:var(--muted);}
.tl-card.best-ever::before{background:linear-gradient(to bottom,var(--accent2),#4ade80);}
.tl-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem;flex-wrap:wrap;gap:0.5rem;}
.tl-test-name{
  font-family:'DM Serif Display',serif;font-size:1.2rem;color:var(--text);
}
.tl-score{
  font-family:'Bebas Neue',sans-serif;font-size:2.5rem;line-height:1;
}
.tl-badge{
  font-size:0.55rem;letter-spacing:0.2em;padding:0.25rem 0.7rem;
  border-radius:20px;text-transform:uppercase;
}
.badge-absent{background:rgba(107,107,138,0.15);color:var(--muted);}
.badge-best{background:rgba(71,232,197,0.15);color:var(--accent2);}
.badge-good{background:rgba(232,197,71,0.12);color:var(--accent);}
.badge-avg{background:rgba(251,146,60,0.12);color:var(--math);}
.badge-low{background:rgba(232,71,160,0.1);color:var(--accent3);}

.tl-subjects{display:flex;gap:1.5rem;margin-top:0.5rem;flex-wrap:wrap;}
.tl-subj{display:flex;align-items:center;gap:0.5rem;font-size:0.7rem;}
.tl-subj-dot{width:6px;height:6px;border-radius:50%;}
.tl-rank{font-size:0.65rem;color:var(--muted);margin-top:0.8rem;letter-spacing:0.12em;}
.tl-bar-row{margin-top:1rem;display:flex;flex-direction:column;gap:4px;}
.tl-bar-label{display:flex;justify-content:space-between;font-size:0.6rem;color:var(--muted);margin-bottom:2px;}
.tl-bar-outer{height:5px;background:var(--border);border-radius:3px;overflow:hidden;}
.tl-bar-inner{height:100%;border-radius:3px;transition:width 1.2s cubic-bezier(0.4,0,0.2,1);}

/* ── STAT CARDS ── */
.stat-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:1.2rem;margin-top:2rem;}
.stat-card{
  background:var(--surface);border:1px solid var(--border);
  border-radius:6px;padding:1.8rem;
  position:relative;overflow:hidden;
  transition:transform 0.3s,border-color 0.3s;
}
.stat-card:hover{transform:translateY(-5px);}
.stat-card::after{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;
}
.stat-card.sc-total::after{background:linear-gradient(90deg,var(--accent),var(--accent2));}
.stat-card.sc-phy::after{background:var(--phy);}
.stat-card.sc-chem::after{background:var(--chem);}
.stat-card.sc-math::after{background:var(--math);}
.stat-card.sc-acc::after{background:var(--accent3);}
.stat-card.sc-rank::after{background:var(--gold);}
.sc-label{font-size:0.58rem;letter-spacing:0.3em;color:var(--muted);text-transform:uppercase;margin-bottom:0.8rem;}
.sc-val{font-family:'Bebas Neue',sans-serif;font-size:3.5rem;line-height:1;}
.sc-sub{font-size:0.6rem;color:var(--muted);margin-top:0.4rem;letter-spacing:0.1em;}
.sc-trend{
  font-size:0.65rem;margin-top:0.8rem;padding:0.3rem 0.6rem;
  display:inline-block;border-radius:2px;
}
.trend-up{background:rgba(74,222,128,0.1);color:#4ade80;}
.trend-down{background:rgba(248,113,113,0.1);color:#f87171;}
.trend-flat{background:rgba(107,107,138,0.1);color:var(--muted);}

/* ── CHARTS ZONE ── */
.charts-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-top:2rem;}
.chart-card{
  background:var(--surface);border:1px solid var(--border);
  border-radius:6px;padding:2rem;position:relative;overflow:hidden;
}
.chart-card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,var(--accent),var(--accent2));
}
.chart-card.full-w{grid-column:1/-1;}
.chart-title{font-size:0.62rem;letter-spacing:0.3em;color:var(--muted);text-transform:uppercase;margin-bottom:1.5rem;}
canvas{width:100%!important;}

/* ── RANK TABLE ── */
.rank-table{width:100%;border-collapse:separate;border-spacing:0 3px;margin-top:1.5rem;}
.rank-table th{font-size:0.58rem;letter-spacing:0.25em;color:var(--muted);text-transform:uppercase;padding:0.4rem 0.8rem;text-align:left;font-weight:400;}
.rank-table tr.rrow{background:var(--surface);transition:all 0.2s;}
.rank-table tr.rrow:hover{background:var(--surface2);transform:translateX(4px);}
.rank-table td{padding:0.75rem 0.8rem;font-size:0.72rem;border-top:1px solid transparent;border-bottom:1px solid transparent;}
.rank-table tr.rrow:hover td{border-color:var(--border);}
.rank-table tr.rrow.highlight-row{background:rgba(232,197,71,0.07);border:1px solid rgba(232,197,71,0.25);}
.rank-badge{font-family:'Bebas Neue',sans-serif;font-size:1.4rem;}
.rank-1c{color:var(--gold);}
.rank-2c{color:var(--silver);}
.rank-3c{color:var(--bronze);}
.rank-oc{color:var(--muted);}

/* ── STRENGTH/WEAKNESS METER ── */
.sw-grid{display:grid;grid-template-columns:1fr 1fr;gap:2rem;margin-top:2rem;}
.sw-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:2rem;}
.sw-title{
  font-family:'DM Serif Display',serif;font-size:1.4rem;margin-bottom:1.5rem;
  display:flex;align-items:center;gap:0.8rem;
}
.sw-item{
  display:flex;align-items:center;gap:1rem;margin-bottom:1rem;
}
.sw-name{font-size:0.7rem;width:90px;color:var(--muted);flex-shrink:0;}
.sw-bar-outer{flex:1;height:20px;background:var(--border);border-radius:3px;overflow:hidden;}
.sw-bar-inner{height:100%;border-radius:3px;display:flex;align-items:center;padding-left:6px;font-size:0.58rem;font-weight:600;color:rgba(0,0,0,0.7);transition:width 1.5s cubic-bezier(0.4,0,0.2,1);}
.sw-pct{font-size:0.7rem;width:36px;text-align:right;flex-shrink:0;}

/* ── HEATMAP ── */
.big-heatmap{
  display:grid; gap:3px;
  justify-content:start;
  margin-top:1.5rem;
  overflow-x:auto;
}
.hm-cell{
  width:36px;height:36px;border-radius:3px;
  position:relative;cursor:pointer;
  transition:transform 0.15s,box-shadow 0.15s;
  display:flex;align-items:center;justify-content:center;
  font-size:0.55rem;font-weight:600;color:rgba(255,255,255,0.7);
}
.hm-cell:hover{transform:scale(1.3);z-index:20;box-shadow:0 4px 20px rgba(0,0,0,0.5);}
.hm-tooltip{
  position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);
  background:#000;border:1px solid var(--border);
  padding:0.5rem 0.8rem;border-radius:4px;
  font-size:0.58rem;white-space:nowrap;
  pointer-events:none;opacity:0;transition:opacity 0.15s;
  z-index:100;color:var(--text);min-width:120px;text-align:center;
}
.hm-cell:hover .hm-tooltip{opacity:1;}

/* ── PROFILE CARD ── */
.profile-strip{
  display:flex;gap:2rem;margin-top:2rem;
  background:var(--surface);border:1px solid var(--border);border-radius:6px;
  padding:2rem;align-items:center;flex-wrap:wrap;
  position:relative;overflow:hidden;
}
.profile-strip::before{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,var(--accent),var(--accent2),var(--accent3));
}
.profile-avatar{
  width:80px;height:80px;border-radius:50%;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  display:flex;align-items:center;justify-content:center;
  font-family:'Bebas Neue',sans-serif;font-size:2.5rem;
  color:var(--bg);flex-shrink:0;
}
.profile-info h1{font-family:'DM Serif Display',serif;font-size:2rem;margin-bottom:0.3rem;}
.profile-info p{font-size:0.65rem;color:var(--muted);letter-spacing:0.2em;}
.profile-pills{display:flex;gap:0.5rem;margin-top:0.6rem;flex-wrap:wrap;}
.ppill{
  font-size:0.55rem;letter-spacing:0.15em;padding:0.25rem 0.7rem;
  border-radius:20px;text-transform:uppercase;
}
.ppill-total{background:rgba(232,197,71,0.12);color:var(--accent);}
.ppill-rank{background:rgba(251,191,36,0.12);color:var(--gold);}
.ppill-acc{background:rgba(71,232,197,0.1);color:var(--accent2);}

/* ── IMPROVEMENT TRACKER ── */
.imp-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.2rem;margin-top:2rem;}
.imp-card{
  background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.5rem;
  text-align:center;
}
.imp-arrow{font-size:2.5rem;margin-bottom:0.5rem;}
.imp-label{font-size:0.58rem;letter-spacing:0.2em;color:var(--muted);text-transform:uppercase;margin-bottom:0.5rem;}
.imp-val{font-family:'Bebas Neue',sans-serif;font-size:2rem;}
.imp-sub{font-size:0.6rem;color:var(--muted);margin-top:0.3rem;}

/* ── ABSENT NOTICE ── */
.absent-notice{
  background:rgba(107,107,138,0.06);border:1px solid rgba(107,107,138,0.2);
  border-radius:6px;padding:1.5rem;text-align:center;
  font-size:0.7rem;letter-spacing:0.15em;color:var(--muted);
  text-transform:uppercase;
}

/* ── REVEAL ── */
.reveal{opacity:0;transform:translateY(30px);transition:opacity 0.7s,transform 0.7s;}
.reveal.vis{opacity:1;transform:translateY(0);}

/* ── SELECTOR OVERLAY ── */
#selectorOverlay{
  position:fixed;inset:0;z-index:2000;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  background:rgba(10,10,15,0.98);backdrop-filter:blur(12px);
}
.sel-title{font-family:'Bebas Neue',sans-serif;font-size:3.5rem;color:var(--accent);margin-bottom:0.5rem;text-align:center;}
.sel-sub{font-size:0.65rem;letter-spacing:0.35em;color:var(--muted);text-transform:uppercase;margin-bottom:2rem;text-align:center;}
.sel-search{
  background:var(--surface);border:1px solid var(--border);
  color:var(--text);padding:0.9rem 1.5rem;
  font-family:'JetBrains Mono',monospace;font-size:0.85rem;
  border-radius:4px;outline:none;width:90%;max-width:520px;
  transition:border-color 0.2s;margin-bottom:1rem;
}
.sel-search:focus{border-color:var(--accent);}
.sel-search::placeholder{color:var(--muted);}
.sel-list{
  width:90%;max-width:520px;
  max-height:55vh;overflow-y:auto;
  display:flex;flex-direction:column;gap:4px;
}
.sel-item{
  background:var(--surface);border:1px solid var(--border);
  color:var(--text);padding:0.9rem 1.5rem;
  font-family:'JetBrains Mono',monospace;font-size:0.75rem;
  letter-spacing:0.12em;text-transform:uppercase;
  cursor:pointer;border-radius:3px;
  display:flex;justify-content:space-between;align-items:center;
  transition:border-color 0.2s,background 0.2s,color 0.2s;
}
.sel-item:hover{border-color:var(--accent);color:var(--accent);background:var(--surface2);}
.sel-item-sub{font-size:0.58rem;color:var(--muted);}
.sel-back{
  margin-top:1.5rem;font-size:0.6rem;letter-spacing:0.2em;
  color:var(--muted);text-decoration:none;text-transform:uppercase;
  transition:color 0.2s;
}
.sel-back:hover{color:var(--accent);}

@media(max-width:768px){
  .hero{padding:8rem 2rem 4rem;}
  .hero-num{display:none;}
  .ring-cluster{position:static;margin-top:2rem;flex-wrap:wrap;justify-content:center;}
  .charts-grid{grid-template-columns:1fr;}
  .sw-grid{grid-template-columns:1fr;}
  .imp-grid{grid-template-columns:1fr;}
  .main-content{padding:0 1.5rem 4rem;}
  .hero-metrics{gap:1.5rem;}
}
</style>
</head>
<body>

<!-- TOPNAV -->
<nav class="topnav">
  <a class="topnav-logo" href="/">JUT<span>·</span>HUB</a>
  <div class="nav-breadcrumb" id="navBreadcrumb">Loading…</div>
  <a class="topnav-back" href="/">← All Tests</a>
</nav>

<!-- HERO -->
<div class="hero">
  <div class="hero-bg-layers"></div>
  <div class="hero-scanlines"></div>
  <div class="hero-grid"></div>
  <div class="hero-num" id="heroNum">1</div>

  <div class="hero-content">
    <div class="hero-eyebrow" id="heroEyebrow">JUT · Student Profile</div>
    <div class="hero-name" id="heroName">
      <span id="heroFirstName">Loading</span>
      <span class="outline" id="heroLastName">Student</span>
    </div>
    <div class="hero-tagline" id="heroTagline">Physics · Chemistry · Mathematics</div>
    <div class="hero-metrics">
      <div class="hero-metric">
        <div class="hero-metric-val" id="hmBest">—</div>
        <div class="hero-metric-label">Best Score</div>
      </div>
      <div class="hero-metric">
        <div class="hero-metric-val" id="hmAvg">—</div>
        <div class="hero-metric-label">Avg Score</div>
      </div>
      <div class="hero-metric">
        <div class="hero-metric-val" id="hmTests">—</div>
        <div class="hero-metric-label">Tests Attended</div>
      </div>
      <div class="hero-metric">
        <div class="hero-metric-val" id="hmBestRank">—</div>
        <div class="hero-metric-label">Best Rank</div>
      </div>
    </div>
  </div>

  <div class="ring-cluster" id="ringCluster"></div>
</div>

<!-- MAIN -->
<div class="main-content">

  <!-- PROFILE STRIP -->
  <section>
    <div class="profile-strip reveal" id="profileStrip">
      <div class="profile-avatar" id="avatarEl">?</div>
      <div class="profile-info">
        <h1 id="fullNameEl">—</h1>
        <p id="testSummaryEl">Loading…</p>
        <div class="profile-pills" id="profilePills"></div>
      </div>
    </div>
  </section>

  <div class="divider"></div>

  <!-- AGGREGATE STATS -->
  <section>
    <div class="section-label reveal">Performance Overview</div>
    <div class="section-title reveal">Key Statistics</div>
    <div class="stat-cards reveal" id="statCards"></div>
  </section>

  <div class="divider"></div>

  <!-- TIMELINE -->
  <section>
    <div class="section-label reveal">Test History</div>
    <div class="section-title reveal">JUT Timeline</div>
    <div class="timeline" id="timeline"></div>
  </section>

  <div class="divider"></div>

  <!-- IMPROVEMENT TRACKER -->
  <section>
    <div class="section-label reveal">Growth Analysis</div>
    <div class="section-title reveal">Improvement Tracker</div>
    <div class="imp-grid reveal" id="impGrid"></div>
  </section>

  <div class="divider"></div>

  <!-- CHARTS -->
  <section>
    <div class="section-label reveal">Visual Analytics</div>
    <div class="section-title reveal">Score Intelligence</div>
    <div class="charts-grid">
      <div class="chart-card full-w reveal">
        <div class="chart-title">Score Across All JUTs</div>
        <canvas id="progressChart" height="100"></canvas>
      </div>
      <div class="chart-card reveal">
        <div class="chart-title">Subject Breakdown (Average)</div>
        <canvas id="radarChart" height="260"></canvas>
      </div>
      <div class="chart-card reveal">
        <div class="chart-title">Correct · Wrong · Unattempted per JUT</div>
        <canvas id="stackedChart" height="260"></canvas>
      </div>
      <div class="chart-card reveal">
        <div class="chart-title">Accuracy per JUT (%)</div>
        <canvas id="accuracyLine" height="260"></canvas>
      </div>
      <div class="chart-card reveal">
        <div class="chart-title">Subject Marks per JUT</div>
        <canvas id="subjectTrendChart" height="260"></canvas>
      </div>
    </div>
  </section>

  <div class="divider"></div>

  <!-- STRENGTH / WEAKNESS -->
  <section>
    <div class="section-label reveal">Subject Intelligence</div>
    <div class="section-title reveal">Strengths & Weaknesses</div>
    <div class="sw-grid reveal" id="swSection">
      <div class="sw-card" id="swStrengths"></div>
      <div class="sw-card" id="swWeaknesses"></div>
    </div>
  </section>

  <div class="divider"></div>

  <!-- HEATMAP -->
  <section>
    <div class="section-label reveal">Micro Analysis</div>
    <div class="section-title reveal">Per-JUT Heatmap</div>
    <p class="reveal" style="font-size:0.65rem;color:var(--muted);margin-bottom:1rem;letter-spacing:0.15em;">Each column = one JUT. Rows = Physics, Chemistry, Maths. Color = performance intensity.</p>
    <div class="reveal" style="overflow-x:auto;">
      <div id="bigHeatmap" class="big-heatmap"></div>
    </div>
  </section>

  <div class="divider"></div>

  <!-- RANK TABLE -->
  <section>
    <div class="section-label reveal">Class Standing</div>
    <div class="section-title reveal">JUT-wise Rank</div>
    <div class="reveal" style="overflow-x:auto;">
      <table class="rank-table">
        <thead>
          <tr>
            <th>JUT</th>
            <th>Status</th>
            <th>Score</th>
            <th>Rank</th>
            <th>Batch Avg</th>
            <th>vs Avg</th>
            <th>Accuracy</th>
          </tr>
        </thead>
        <tbody id="rankTableBody"></tbody>
      </table>
    </div>
  </section>

</div>

<footer style="text-align:center;padding:2rem;color:var(--muted);font-size:0.6rem;letter-spacing:0.2em;border-top:1px solid var(--border);" id="footerEl">
  JUT INDIVIDUAL ANALYTICS
</footer>

<!-- SELECTOR OVERLAY -->
<div id="selectorOverlay">
  <div class="sel-title">WHO'S PROFILE?</div>
  <div class="sel-sub">Select a student to view their full analysis</div>
  <input class="sel-search" id="selSearch" type="text" placeholder="Search student name…" autocomplete="off">
  <div class="sel-list" id="selList">
    <div style="font-size:0.7rem;color:var(--muted);text-align:center;padding:2rem;">Loading students…</div>
  </div>
  <a class="sel-back" href="/">← Back to Hub</a>
</div>

<script>
/* ─────────────────────── UTILS ─────────────────────── */
const $ = id => document.getElementById(id);
const n = v => parseFloat(v) || 0;
const pct = (a,b) => b > 0 ? Math.round((a/b)*100) : 0;

function initials(name){
  return name.trim().split(/\s+/).map(w=>w[0]?.toUpperCase()||'').join('').slice(0,2) || '?';
}

function mapRow(r){
  const g = (...keys) => { for(const k of keys){ if(r[k]!==undefined && r[k]!=='') return r[k]; } return '0'; };
  const gStr = (...keys) => { for(const k of keys){ if(r[k]!==undefined && r[k]!=='') return r[k]; } return ''; };
  return {
    name:    gStr('name') || 'Unknown',
    test:    gStr('test','test_name','filename','jut','jut_name') || 'Unknown JUT',
    total:   n(g('total_marks','total_score','total')),
    rank:    n(g('rank')),
    phy_a:   n(g('phy_attempt','physics_attempt')),
    chem_a:  n(g('chem_attempt','chemistry_attempt')),
    math_a:  n(g('math_attempt','maths_attempt')),
    tot_a:   n(g('total_attempt')),
    phy_c:   n(g('phy_correct','physics_correct')),
    chem_c:  n(g('chem_correct','chemistry_correct')),
    math_c:  n(g('math_correct','maths_correct')),
    tot_c:   n(g('total_correct')),
    phy_w:   n(g('phy_wrong','physics_wrong')),
    chem_w:  n(g('chem_wrong','chemistry_wrong')),
    math_w:  n(g('math_wrong','maths_wrong')),
    tot_w:   n(g('total_wrong')),
    phy_m:   n(g('phy_marks','physics_marks')),
    chem_m:  n(g('chem_marks','chemistry_marks')),
    math_m:  n(g('math_marks','maths_marks')),
  };
}

function avg(arr){ return arr.length ? arr.reduce((a,b)=>a+b,0)/arr.length : 0; }

/* ── chart defaults ── */
Chart.defaults.font.family = 'JetBrains Mono';
Chart.defaults.color = '#6b6b8a';

let charts = {};

function destroyCharts(){
  Object.values(charts).forEach(c => { try{ c.destroy(); }catch(e){} });
  charts = {};
}

/* ─────────────────────── SELECTOR ─────────────────────── */
let allMasterRows = [];
let allStudents = [];

async function loadSelector(){
  try{
    const res = await fetch('/api/master-data');
    if(!res.ok) throw new Error('HTTP '+res.status);
    const raw = await res.json();
    allMasterRows = raw.map(mapRow);

    // unique students sorted alphabetically
    const nameSet = {};
    allMasterRows.forEach(r => {
      if(!nameSet[r.name.toLowerCase()]) nameSet[r.name.toLowerCase()] = r.name;
    });
    allStudents = Object.values(nameSet).sort();
    renderSelList(allStudents);
  } catch(e){
    $('selList').innerHTML = `<div style="color:var(--accent3);font-size:0.7rem;text-align:center;padding:1rem;">Error: ${e.message}</div>`;
  }
}

function renderSelList(students){
  const list = $('selList');
  list.innerHTML = '';
  if(!students.length){
    list.innerHTML = '<div style="font-size:0.7rem;color:var(--muted);text-align:center;padding:1rem;">No results</div>';
    return;
  }
  students.forEach(name => {
    const rows = allMasterRows.filter(r=>r.name.toLowerCase()===name.toLowerCase());
    const attended = rows.filter(r=>r.total>0||r.tot_a>0).length;
    const el = document.createElement('div');
    el.className = 'sel-item';
    el.innerHTML = `<span>${name}</span><span class="sel-item-sub">${attended} JUT${attended!==1?'s':''} attended · ${rows.length} records</span>`;
    el.addEventListener('click', () => loadStudentProfile(name));
    list.appendChild(el);
  });
}

$('selSearch').addEventListener('input', e => {
  const q = e.target.value.toLowerCase();
  renderSelList(allStudents.filter(n => n.toLowerCase().includes(q)));
});

/* ─────────────────────── PROFILE BUILDER ─────────────────────── */
async function loadStudentProfile(name){
  // update URL
  const url = new URL(window.location);
  url.searchParams.set('student', name);
  history.replaceState(null,'',url.toString());

  // hide overlay
  const ov = $('selectorOverlay');
  ov.style.opacity='0';
  setTimeout(()=>{ ov.style.display='none'; },500);

  destroyCharts();
  buildProfile(name, allMasterRows);
}

/* ─────────────────────── MASTER BUILDER ─────────────────────── */
function buildProfile(studentName, masterRows){
  // rows for this student
  const sRows = masterRows.filter(r => r.name.toLowerCase() === studentName.toLowerCase());
  // all rows grouped by test
  const testMap = {};
  masterRows.forEach(r => {
    if(!testMap[r.test]) testMap[r.test] = [];
    testMap[r.test].push(r);
  });
  const allTests = Object.keys(testMap).sort();

  // build per-test data for this student (including absent)
  const perTest = allTests.map(testName => {
    const row = sRows.find(r => r.test === testName);
    const batchRows = testMap[testName];
    const batchScores = batchRows.map(r=>r.total).filter(t=>t>0||true);
    const batchAvg = avg(batchRows.map(r=>r.total));
    const batchMax = Math.max(...batchRows.map(r=>r.total));
    if(!row){
      return { testName, absent:true, batchAvg:Math.round(batchAvg), batchMax, batchSize:batchRows.length, rank:null, ...nullEntry() };
    }
    const absent = (row.total===0 && row.tot_a===0);
    // compute rank within this test
    const scored = batchRows.filter(r=>r.total>0||r.tot_a>0).map(r=>r.total).sort((a,b)=>b-a);
    const rankInTest = scored.indexOf(row.total)+1 || null;
    return { testName, absent, batchAvg:Math.round(batchAvg), batchMax, batchSize:batchRows.length, rank:rankInTest, ...row };
  });

  const attended = perTest.filter(t=>!t.absent);
  const scores   = attended.map(t=>t.total);
  const bestScore = scores.length ? Math.max(...scores) : 0;
  const avgScore  = scores.length ? Math.round(avg(scores)) : 0;
  const bestRank  = attended.filter(t=>t.rank).length ? Math.min(...attended.filter(t=>t.rank).map(t=>t.rank)) : '—';
  const bestTest  = attended.find(t=>t.total===bestScore);
  const overallAcc = attended.length ? Math.round(avg(attended.map(t=>pct(t.tot_c,t.tot_a)))) : 0;

  /* ── hero ── */
  const parts = studentName.trim().split(/\s+/);
  const firstName = parts[0] || studentName;
  const lastName  = parts.slice(1).join(' ') || '';
  $('heroFirstName').textContent = firstName;
  $('heroLastName').textContent  = lastName || firstName;
  if(!lastName) { $('heroLastName').style.display='none'; }
  $('heroNum').textContent = bestRank || '#';
  $('heroEyebrow').textContent = `JUT · Student Profile · ${attended.length}/${allTests.length} Tests`;
  $('hmBest').textContent     = bestScore || '—';
  $('hmAvg').textContent      = avgScore  || '—';
  $('hmTests').textContent    = attended.length;
  $('hmBestRank').textContent = bestRank  || '—';
  $('heroTagline').textContent = `Physics · Chemistry · Mathematics · ${allTests.length} JUTs`;
  $('navBreadcrumb').textContent = studentName.toUpperCase();
  document.title = `JUT · ${studentName}`;
  $('footerEl').textContent = `JUT INDIVIDUAL ANALYTICS · ${studentName.toUpperCase()} · ${attended.length} TESTS ATTENDED`;

  /* ── rings ── */
  const rc = $('ringCluster');
  rc.innerHTML='';
  const ringData = [
    { label:'Physics', pctVal: attended.length ? Math.round(avg(attended.map(t=>pct(t.phy_c,25)))) : 0, color:'var(--phy)' },
    { label:'Chemistry', pctVal: attended.length ? Math.round(avg(attended.map(t=>pct(t.chem_c,25)))) : 0, color:'var(--chem)' },
    { label:'Maths', pctVal: attended.length ? Math.round(avg(attended.map(t=>pct(t.math_c,25)))) : 0, color:'var(--math)' },
  ];
  ringData.forEach(({label,pctVal,color})=>{
    const r=50,circ=2*Math.PI*r;
    const offset=circ*(1-pctVal/100);
    const div=document.createElement('div');
    div.className='ring-wrap';
    div.innerHTML=`
      <div class="ring-container" style="width:90px;height:90px;">
        <svg class="ring" width="90" height="90" viewBox="0 0 110 110">
          <circle class="ring-bg" cx="55" cy="55" r="${r}"/>
          <circle class="ring-fill" cx="55" cy="55" r="${r}"
            stroke="${color}"
            stroke-dasharray="${circ}"
            stroke-dashoffset="${circ}"
            data-offset="${offset}"
            data-circ="${circ}"/>
        </svg>
        <div class="ring-text" style="color:${color}">${pctVal}%</div>
      </div>
      <div class="ring-label">${label}</div>`;
    rc.appendChild(div);
  });
  setTimeout(()=>{
    document.querySelectorAll('.ring-fill').forEach(c=>{
      c.style.strokeDashoffset = c.dataset.offset;
    });
  },600);

  /* ── profile strip ── */
  $('avatarEl').textContent = initials(studentName);
  $('fullNameEl').textContent = studentName;
  $('testSummaryEl').textContent = `${attended.length} of ${allTests.length} JUTs attended · ${perTest.filter(t=>t.absent).length} absent`;
  const pills = $('profilePills');
  pills.innerHTML='';
  [
    {cls:'ppill-total',txt:`Best: ${bestScore}`},
    {cls:'ppill-rank',txt:`Best Rank: #${bestRank}`},
    {cls:'ppill-acc',txt:`Avg Accuracy: ${overallAcc}%`},
  ].forEach(({cls,txt})=>{
    const p=document.createElement('span');p.className=`ppill ${cls}`;p.textContent=txt;pills.appendChild(p);
  });

  /* ── stat cards ── */
  const phyAvgM = attended.length ? Math.round(avg(attended.map(t=>t.phy_m))) : 0;
  const chemAvgM= attended.length ? Math.round(avg(attended.map(t=>t.chem_m))) : 0;
  const mathAvgM= attended.length ? Math.round(avg(attended.map(t=>t.math_m))) : 0;

  // trend: compare last two attended
  function trendTag(arr){
    if(arr.length<2) return '<span class="sc-trend trend-flat">— Not enough data</span>';
    const diff=arr[arr.length-1]-arr[arr.length-2];
    if(diff>0) return `<span class="sc-trend trend-up">↑ +${diff} from previous</span>`;
    if(diff<0) return `<span class="sc-trend trend-down">↓ ${diff} from previous</span>`;
    return '<span class="sc-trend trend-flat">→ Same as previous</span>';
  }

  $('statCards').innerHTML=[
    {cls:'sc-total',label:'Best Total Score',val:bestScore,sub:`Avg: ${avgScore}`,trend:trendTag(attended.map(t=>t.total))},
    {cls:'sc-phy',label:'Avg Physics',val:phyAvgM,sub:`Best: ${Math.max(0,...attended.map(t=>t.phy_m))}`,trend:trendTag(attended.map(t=>t.phy_m))},
    {cls:'sc-chem',label:'Avg Chemistry',val:chemAvgM,sub:`Best: ${Math.max(0,...attended.map(t=>t.chem_m))}`,trend:trendTag(attended.map(t=>t.chem_m))},
    {cls:'sc-math',label:'Avg Maths',val:mathAvgM,sub:`Best: ${Math.max(0,...attended.map(t=>t.math_m))}`,trend:trendTag(attended.map(t=>t.math_m))},
    {cls:'sc-acc',label:'Avg Accuracy',val:overallAcc+'%',sub:`Best: ${Math.max(0,...attended.map(t=>pct(t.tot_c,t.tot_a)))}%`,trend:trendTag(attended.map(t=>pct(t.tot_c,t.tot_a)))},
    {cls:'sc-rank',label:'Best Rank',val:'#'+(bestRank||'—'),sub:`Tests: ${attended.length}/${allTests.length}`,trend:''},
  ].map(({cls,label,val,sub,trend})=>`
    <div class="stat-card ${cls}">
      <div class="sc-label">${label}</div>
      <div class="sc-val">${val}</div>
      <div class="sc-sub">${sub}</div>
      ${trend}
    </div>`).join('');

  /* ── timeline ── */
  const tl=$('timeline'); tl.innerHTML='';
  perTest.forEach((t,i)=>{
    const isBest = !t.absent && t.total===bestScore && attended.length>0;
    const acc = t.absent ? 0 : pct(t.tot_c,t.tot_a);
    let badgeClass='badge-avg', badgeLabel='Average';
    if(t.absent){ badgeClass='badge-absent'; badgeLabel='Absent'; }
    else if(isBest){ badgeClass='badge-best'; badgeLabel='🏆 Personal Best'; }
    else if(t.total>=t.batchMax*0.8){ badgeClass='badge-best'; badgeLabel='Excellent'; }
    else if(t.total>=t.batchAvg*1.1){ badgeClass='badge-good'; badgeLabel='Above Avg'; }
    else if(t.total<t.batchAvg*0.7){ badgeClass='badge-low'; badgeLabel='Below Avg'; }

    const item=document.createElement('div');
    item.className='tl-item';
    item.style.transitionDelay=(i*0.07)+'s';
    item.innerHTML=`
      <div class="tl-dot${t.absent?' absent':isBest?' best':''}"></div>
      <div class="tl-card${t.absent?' absent':isBest?' best-ever':''}">
        <div class="tl-top">
          <div>
            <div class="tl-test-name">${t.testName.replace(/_/g,' ')}</div>
            <div class="tl-rank">${t.absent?'Not present':(`Rank #${t.rank||'?'} of ${t.batchSize} students`)}</div>
          </div>
          <div style="text-align:right;">
            <div class="tl-score" style="color:${t.absent?'var(--muted)':isBest?'var(--accent2)':'var(--accent)'}">${t.absent?'ABS':t.total}</div>
            <span class="tl-badge ${badgeClass}">${badgeLabel}</span>
          </div>
        </div>
        ${t.absent
          ? `<div class="absent-notice">Absent · No data recorded for this JUT</div>`
          : `
            <div class="tl-subjects">
              <div class="tl-subj"><div class="tl-subj-dot" style="background:var(--phy)"></div><span style="color:var(--muted)">P:</span>&nbsp;<strong style="color:var(--phy)">${t.phy_m}</strong></div>
              <div class="tl-subj"><div class="tl-subj-dot" style="background:var(--chem)"></div><span style="color:var(--muted)">C:</span>&nbsp;<strong style="color:var(--chem)">${t.chem_m}</strong></div>
              <div class="tl-subj"><div class="tl-subj-dot" style="background:var(--math)"></div><span style="color:var(--muted)">M:</span>&nbsp;<strong style="color:var(--math)">${t.math_m}</strong></div>
              <div class="tl-subj" style="margin-left:auto;color:var(--muted)">Accuracy: <strong style="color:${acc>=60?'var(--accent2)':acc>=40?'var(--accent)':'var(--accent3)'}">${acc}%</strong></div>
            </div>
            <div class="tl-bar-row">
              <div class="tl-bar-label"><span style="color:var(--phy)">Physics</span><span>${t.phy_m}/100</span></div>
              <div class="tl-bar-outer"><div class="tl-bar-inner" style="width:${pct(t.phy_m,100)}%;background:var(--phy);"></div></div>
              <div class="tl-bar-label" style="margin-top:4px;"><span style="color:var(--chem)">Chemistry</span><span>${t.chem_m}/100</span></div>
              <div class="tl-bar-outer"><div class="tl-bar-inner" style="width:${pct(t.chem_m,100)}%;background:var(--chem);"></div></div>
              <div class="tl-bar-label" style="margin-top:4px;"><span style="color:var(--math)">Maths</span><span>${t.math_m}/100</span></div>
              <div class="tl-bar-outer"><div class="tl-bar-inner" style="width:${pct(t.math_m,100)}%;background:var(--math);"></div></div>
              <div class="tl-bar-label" style="margin-top:4px;"><span style="color:var(--muted)">vs Batch Avg (${t.batchAvg})</span><span>${t.total}</span></div>
              <div class="tl-bar-outer">
                <div class="tl-bar-inner" style="width:${t.batchMax?pct(t.batchAvg,t.batchMax):0}%;background:rgba(107,107,138,0.5);"></div>
              </div>
            </div>`
        }
      </div>`;
    tl.appendChild(item);
  });

  /* ── improvement tracker ── */
  function safeFirst(arr){ return arr.length>0?arr[0]:null; }
  function safeLast(arr){ return arr.length>0?arr[arr.length-1]:null; }
  const first = safeFirst(attended), last = safeLast(attended);
  const firstToLast = (first && last && first!==last) ? last.total - first.total : null;
  const phyFirstLast = (first && last && first!==last) ? last.phy_m - first.phy_m : null;
  const chemFirstLast = (first && last && first!==last) ? last.chem_m - first.chem_m : null;
  const mathFirstLast = (first && last && first!==last) ? last.math_m - first.math_m : null;
  const consistency = scores.length>=2 ? (() => {
    const mn=avg(scores), sd=Math.sqrt(avg(scores.map(x=>(x-mn)**2)));
    return Math.round(100 - (sd/mn*100));
  })() : null;

  function impCard(label,val,sub,upGood=true){
    if(val===null) return `<div class="imp-card"><div class="imp-label">${label}</div><div class="imp-val" style="color:var(--muted)">—</div><div class="imp-sub">Insufficient data</div></div>`;
    const isPos=val>0, isZero=val===0;
    const arrow = isZero?'→':isPos?'↑':'↓';
    const col = isZero?'var(--muted)':((isPos&&upGood)||(!isPos&&!upGood))?'var(--green)':'var(--red)';
    return `<div class="imp-card"><div class="imp-arrow" style="color:${col}">${arrow}</div><div class="imp-label">${label}</div><div class="imp-val" style="color:${col}">${isPos?'+':''}${val}</div><div class="imp-sub">${sub}</div></div>`;
  }

  $('impGrid').innerHTML =
    impCard('Overall Change',firstToLast,`First JUT → Last JUT`) +
    impCard('Physics Trend',phyFirstLast,'First → Last JUT') +
    impCard('Chemistry Trend',chemFirstLast,'First → Last JUT') +
    impCard('Maths Trend',mathFirstLast,'First → Last JUT') +
    (consistency!==null
      ? `<div class="imp-card"><div class="imp-arrow" style="color:var(--accent2)">◎</div><div class="imp-label">Consistency Score</div><div class="imp-val" style="color:var(--accent2)">${consistency}%</div><div class="imp-sub">Higher = more consistent</div></div>`
      : impCard('Consistency',null,'')) +
    `<div class="imp-card"><div class="imp-arrow" style="color:var(--accent)">★</div><div class="imp-label">Tests Attended</div><div class="imp-val" style="color:var(--accent)">${attended.length}/${allTests.length}</div><div class="imp-sub">Attendance rate: ${Math.round(pct(attended.length,allTests.length))}%</div></div>`;

  /* ── CHARTS ── */
  const labels = allTests.map(t=>t.replace(/_/g,' ').replace('JUT','').trim()||t);
  const dataPoints = perTest.map(t=>t.absent?null:t.total);
  const batchAvgLine = perTest.map(t=>t.batchAvg);

  // progress line
  charts.progress = new Chart($('progressChart'), {
    type:'line',
    data:{
      labels,
      datasets:[
        { label:'Your Score', data:dataPoints, borderColor:'#e8c547', backgroundColor:'rgba(232,197,71,0.08)',
          borderWidth:2.5, pointRadius:6, pointBackgroundColor:dataPoints.map(v=>v===null?'transparent':'#e8c547'),
          tension:0.3, spanGaps:false },
        { label:'Batch Avg', data:batchAvgLine, borderColor:'rgba(107,107,138,0.5)',
          borderDash:[6,4], borderWidth:1.5, pointRadius:3, tension:0.3 },
      ]
    },
    options:{
      scales:{
        x:{grid:{color:'#1e1e2e'},ticks:{color:'#6b6b8a',maxRotation:40}},
        y:{grid:{color:'#1e1e2e'},ticks:{color:'#6b6b8a'},min:0}
      },
      plugins:{legend:{labels:{color:'#6b6b8a'}},tooltip:{callbacks:{
        label:ctx=>ctx.dataset.label+': '+(ctx.raw===null?'Absent':ctx.raw)
      }}}
    }
  });

  // radar
  const phyA=attended.length?avg(attended.map(t=>t.phy_m)):0;
  const chemA=attended.length?avg(attended.map(t=>t.chem_m)):0;
  const mathA=attended.length?avg(attended.map(t=>t.math_m)):0;
  charts.radar = new Chart($('radarChart'),{
    type:'radar',
    data:{
      labels:['Physics','Chemistry','Maths'],
      datasets:[
        { label:'You (avg)', data:[phyA.toFixed(1),chemA.toFixed(1),mathA.toFixed(1)],
          borderColor:'#e8c547',backgroundColor:'rgba(232,197,71,0.1)',
          pointBackgroundColor:['#4fc3f7','#a78bfa','#fb923c'],pointRadius:6,borderWidth:2 },
      ]
    },
    options:{
      scales:{r:{grid:{color:'#1e1e2e'},ticks:{display:false},pointLabels:{color:'#e8e8f0',font:{size:11}}}},
      plugins:{legend:{display:false}}
    }
  });

  // stacked correct/wrong/unattempted
  charts.stacked = new Chart($('stackedChart'),{
    type:'bar',
    data:{
      labels,
      datasets:[
        { label:'Correct', data:perTest.map(t=>t.absent?0:t.tot_c), backgroundColor:'#47e8c5bb',stack:'s' },
        { label:'Wrong',   data:perTest.map(t=>t.absent?0:t.tot_w), backgroundColor:'#e847a0bb',stack:'s' },
        { label:'Unattempted', data:perTest.map(t=>t.absent?0:(75-t.tot_a)), backgroundColor:'#1e1e2e',stack:'s' },
        { label:'Absent', data:perTest.map(t=>t.absent?75:0), backgroundColor:'rgba(107,107,138,0.15)',stack:'s' },
      ]
    },
    options:{
      scales:{
        x:{ticks:{color:'#6b6b8a',maxRotation:40},grid:{color:'#1e1e2e'}},
        y:{ticks:{color:'#6b6b8a'},grid:{color:'#1e1e2e'},max:75,stacked:true}
      },
      plugins:{legend:{labels:{color:'#6b6b8a',font:{size:9}}}}
    }
  });

  // accuracy line
  charts.accLine = new Chart($('accuracyLine'),{
    type:'line',
    data:{
      labels,
      datasets:[{
        label:'Accuracy %',
        data:perTest.map(t=>t.absent?null:pct(t.tot_c,t.tot_a)),
        borderColor:'#e847a0',backgroundColor:'rgba(232,71,160,0.07)',
        borderWidth:2,pointRadius:5,tension:0.35,spanGaps:false,fill:true,
      }]
    },
    options:{
      scales:{
        x:{ticks:{color:'#6b6b8a',maxRotation:40},grid:{color:'#1e1e2e'}},
        y:{ticks:{color:'#6b6b8a',callback:v=>v+'%'},grid:{color:'#1e1e2e'},min:0,max:100}
      },
      plugins:{legend:{display:false}}
    }
  });

  // subject trends
  charts.subjTrend = new Chart($('subjectTrendChart'),{
    type:'line',
    data:{
      labels,
      datasets:[
        { label:'Physics',   data:perTest.map(t=>t.absent?null:t.phy_m),  borderColor:'#4fc3f7',backgroundColor:'rgba(79,195,247,0.05)',borderWidth:2,tension:0.3,pointRadius:4,spanGaps:false },
        { label:'Chemistry', data:perTest.map(t=>t.absent?null:t.chem_m), borderColor:'#a78bfa',backgroundColor:'rgba(167,139,250,0.05)',borderWidth:2,tension:0.3,pointRadius:4,spanGaps:false },
        { label:'Maths',     data:perTest.map(t=>t.absent?null:t.math_m), borderColor:'#fb923c',backgroundColor:'rgba(251,146,60,0.05)',borderWidth:2,tension:0.3,pointRadius:4,spanGaps:false },
      ]
    },
    options:{
      scales:{
        x:{ticks:{color:'#6b6b8a',maxRotation:40},grid:{color:'#1e1e2e'}},
        y:{ticks:{color:'#6b6b8a'},grid:{color:'#1e1e2e'},min:0}
      },
      plugins:{legend:{labels:{color:'#6b6b8a',font:{size:9}}}}
    }
  });

  /* ── strengths/weaknesses ── */
  const subjectData = [
    { name:'Physics',   avgMark:phyA,   avgAcc:attended.length?avg(attended.map(t=>pct(t.phy_c,25))):0,  color:'var(--phy)',  avgCorrect:attended.length?avg(attended.map(t=>t.phy_c)):0  },
    { name:'Chemistry', avgMark:chemA,  avgAcc:attended.length?avg(attended.map(t=>pct(t.chem_c,25))):0, color:'var(--chem)', avgCorrect:attended.length?avg(attended.map(t=>t.chem_c)):0 },
    { name:'Maths',     avgMark:mathA,  avgAcc:attended.length?avg(attended.map(t=>pct(t.math_c,25))):0, color:'var(--math)', avgCorrect:attended.length?avg(attended.map(t=>t.math_c)):0 },
  ];
  const sorted3 = [...subjectData].sort((a,b)=>b.avgMark-a.avgMark);
  const maxAvgMark = Math.max(...subjectData.map(s=>s.avgMark),1);

  function swBar(item,isStrength){
    const pctW = (item.avgMark/maxAvgMark*100).toFixed(1);
    return `
      <div class="sw-item">
        <div class="sw-name">${item.name}</div>
        <div class="sw-bar-outer">
          <div class="sw-bar-inner" style="width:0%;background:${item.color}" data-pct="${pctW}">
            ${Math.round(item.avgMark)}
          </div>
        </div>
        <div class="sw-pct" style="color:${item.color}">${Math.round(item.avgAcc)}%</div>
      </div>`;
  }

  $('swStrengths').innerHTML = `
    <div class="sw-title">💪 Strengths</div>
    ${sorted3.slice(0,2).map(s=>swBar(s,true)).join('')}
    <div style="font-size:0.6rem;color:var(--muted);margin-top:1rem;letter-spacing:0.12em;">Your best subject: <span style="color:${sorted3[0].color}">${sorted3[0].name}</span> (avg ${sorted3[0].avgMark.toFixed(1)} marks)</div>`;

  $('swWeaknesses').innerHTML = `
    <div class="sw-title">🎯 Focus Areas</div>
    ${[...sorted3].reverse().slice(0,2).map(s=>swBar(s,false)).join('')}
    <div style="font-size:0.6rem;color:var(--muted);margin-top:1rem;letter-spacing:0.12em;">Needs work: <span style="color:${sorted3[2].color}">${sorted3[2].name}</span> (avg ${sorted3[2].avgMark.toFixed(1)} marks)</div>`;

  setTimeout(()=>{
    document.querySelectorAll('.sw-bar-inner').forEach(b=>{
      b.style.width = b.dataset.pct + '%';
    });
  }, 600);

  /* ── BIG HEATMAP ── */
  const hm = $('bigHeatmap');
  hm.innerHTML = '';
  // cols = tests, rows = [phy, chem, math] displayed per student
  // layout: for each test, 3 cells stacked vertically
  // We'll lay it out as: col per test, row per subject
  hm.style.gridTemplateColumns = `120px repeat(${allTests.length},44px)`;

  // header row: labels
  const headerLabel = document.createElement('div');
  headerLabel.style.cssText='font-size:0.55rem;color:var(--muted);letter-spacing:0.1em;display:flex;align-items:center;';
  headerLabel.textContent='Subject / JUT →';
  hm.appendChild(headerLabel);
  allTests.forEach(t=>{
    const cell=document.createElement('div');
    cell.style.cssText='font-size:0.5rem;color:var(--muted);letter-spacing:0.05em;text-align:center;writing-mode:vertical-rl;transform:rotate(180deg);height:70px;display:flex;align-items:center;justify-content:center;';
    cell.textContent=t.replace(/_/g,' ').replace('JUT','JUT ').trim();
    hm.appendChild(cell);
  });

  // rows for each subject
  const hmSubjects = [
    { name:'Physics', key:'phy_m', max:100, color:'79,195,247' },
    { name:'Chemistry', key:'chem_m', max:100, color:'167,139,250' },
    { name:'Maths', key:'math_m', max:100, color:'251,146,60' },
  ];
  hmSubjects.forEach(({name,key,max,color})=>{
    const rowLabel=document.createElement('div');
    rowLabel.style.cssText=`font-size:0.6rem;color:rgba(${color},0.9);display:flex;align-items:center;letter-spacing:0.1em;`;
    rowLabel.textContent=name;
    hm.appendChild(rowLabel);
    perTest.forEach(t=>{
      const val = t.absent ? null : t[key];
      const cell=document.createElement('div');
      cell.className='hm-cell';
      if(val===null){
        cell.style.background='rgba(107,107,138,0.1)';
        cell.textContent='ABS';
        cell.style.color='var(--muted)';
        cell.style.fontSize='0.45rem';
      } else {
        const intensity = 0.1 + (val/max)*0.75;
        cell.style.background=`rgba(${color},${intensity})`;
        cell.textContent=val;
      }
      cell.innerHTML+=`<div class="hm-tooltip">${t.testName.replace(/_/g,' ')}<br>${name}: ${val===null?'Absent':val+'/'+ max}</div>`;
      hm.appendChild(cell);
    });
  });

  /* ── RANK TABLE ── */
  const tbody=$('rankTableBody'); tbody.innerHTML='';
  perTest.forEach(t=>{
    const isStudent=(t.name&&t.name.toLowerCase()===studentName.toLowerCase());
    const acc=t.absent?'—':pct(t.tot_c,t.tot_a)+'%';
    const diff=t.absent?'—':t.total-t.batchAvg;
    const diffStr=t.absent?'—':(diff>=0?`<span style="color:var(--green)">+${diff}</span>`:`<span style="color:var(--red)">${diff}</span>`);
    const rankBadge=t.absent?'<span style="color:var(--muted)">ABS</span>':
      (t.rank===1?`<span class="rank-badge rank-1c">1</span>`:
       t.rank===2?`<span class="rank-badge rank-2c">2</span>`:
       t.rank===3?`<span class="rank-badge rank-3c">3</span>`:
       `<span class="rank-badge rank-oc">${t.rank||'?'}</span>`);
    const scoreColor = t.absent?'var(--muted)':t.total>=t.batchMax*0.8?'var(--accent2)':t.total>=t.batchAvg?'var(--accent)':'var(--accent3)';
    const tr=document.createElement('tr');
    tr.className='rrow';
    tr.innerHTML=`
      <td style="font-family:'DM Serif Display',serif;">${t.testName.replace(/_/g,' ')}</td>
      <td>${t.absent?`<span class="tl-badge badge-absent">Absent</span>`:`<span class="tl-badge badge-good">Attended</span>`}</td>
      <td><span style="font-family:'Bebas Neue',sans-serif;font-size:1.4rem;color:${scoreColor}">${t.absent?'—':t.total}</span></td>
      <td>${rankBadge}${!t.absent&&t.rank?`<span style="font-size:0.6rem;color:var(--muted)"> of ${t.batchSize}</span>`:''}</td>
      <td style="color:var(--muted)">${t.batchAvg}</td>
      <td>${diffStr}</td>
      <td style="color:${t.absent?'var(--muted)':pct(t.tot_c,t.tot_a)>=60?'var(--green)':'var(--accent3)'}">${acc}</td>`;
    tbody.appendChild(tr);
  });

  /* ── scroll reveal ── */
  const io = new IntersectionObserver(entries=>{
    entries.forEach(e=>{
      if(e.isIntersecting){ e.target.classList.add('vis'); }
    });
  },{threshold:0.08});
  document.querySelectorAll('.reveal,.tl-item').forEach(el=>{ el.classList.remove('vis'); io.observe(el); });
}

function nullEntry(){
  return {total:0,rank:null,phy_a:0,chem_a:0,math_a:0,tot_a:0,phy_c:0,chem_c:0,math_c:0,tot_c:0,phy_w:0,chem_w:0,math_w:0,tot_w:0,phy_m:0,chem_m:0,math_m:0};
}

/* ─────────────────────── BOOT ─────────────────────── */
(async function boot(){
  const overlay=$('selectorOverlay');
  overlay.style.display='flex'; overlay.style.opacity='1';
  await loadSelector();

  const params=new URLSearchParams(window.location.search);
  const studentParam=params.get('student');
  if(studentParam){
    const matched=allStudents.find(n=>n.toLowerCase()===studentParam.toLowerCase());
    if(matched) await loadStudentProfile(matched);
    else {
      // show overlay anyway, preload search
      $('selSearch').value=studentParam;
      $('selSearch').dispatchEvent(new Event('input'));
    }
  }
})();
</script>
</body>
</html>
"""


@app.get("/student")
def student_page():
    return app.response_class(INDIVIDUAL_HTML, mimetype='text/html')


# ══════════════════════════════════════════════════════════════════════════════
#  HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════
HOME_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JUT · Analytics Hub</title>
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
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { scroll-behavior: smooth; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh;
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

  .grid-bg {
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
    background-size: 60px 60px;
    animation: gridDrift 30s linear infinite;
  }
  @keyframes gridDrift {
    0% { background-position: 0 0; }
    100% { background-position: 60px 60px; }
  }

  .glow-1 {
    position: fixed;
    width: 700px; height: 700px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(232,197,71,0.07) 0%, transparent 70%);
    top: -200px; left: -200px;
    pointer-events: none;
    animation: floatA 18s ease-in-out infinite;
  }
  .glow-2 {
    position: fixed;
    width: 500px; height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(71,232,197,0.05) 0%, transparent 70%);
    bottom: -100px; right: -100px;
    pointer-events: none;
    animation: floatB 22s ease-in-out infinite;
  }
  .glow-3 {
    position: fixed;
    width: 400px; height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(232,71,160,0.04) 0%, transparent 70%);
    top: 50%; right: 20%;
    pointer-events: none;
    animation: floatC 26s ease-in-out infinite;
  }
  @keyframes floatA { 0%,100%{transform:translate(0,0)} 50%{transform:translate(60px,40px)} }
  @keyframes floatB { 0%,100%{transform:translate(0,0)} 50%{transform:translate(-50px,-30px)} }
  @keyframes floatC { 0%,100%{transform:translate(0,0)} 50%{transform:translate(30px,-50px)} }

  .page {
    position: relative;
    z-index: 10;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 2rem 0;
    border-bottom: 1px solid var(--border);
    opacity: 0;
    animation: fadeUp 0.6s 0.1s forwards;
  }
  .logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    letter-spacing: 0.08em;
    color: var(--text);
  }
  .logo span { color: var(--accent); }
  .header-tag {
    font-size: 0.6rem;
    letter-spacing: 0.3em;
    color: var(--muted);
    text-transform: uppercase;
  }
  @media (max-width: 600px) {
    .header-tag {display: none;}
  }

  .hero {
    padding: 6rem 0 4rem;
    text-align: center;
  }
  .hero-eyebrow {
    font-size: 0.65rem;
    letter-spacing: 0.45em;
    color: var(--accent);
    text-transform: uppercase;
    margin-bottom: 1.5rem;
    opacity: 0;
    animation: fadeUp 0.6s 0.3s forwards;
  }
  .hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(4.5rem, 14vw, 11rem);
    line-height: 0.88;
    letter-spacing: 0.02em;
    opacity: 0;
    animation: fadeUp 0.8s 0.45s forwards;
  }
  .hero-title .outline { -webkit-text-stroke: 1.5px var(--accent); color: transparent; }
  .hero-desc {
    font-size: 0.8rem;
    color: var(--muted);
    letter-spacing: 0.12em;
    margin-top: 2rem;
    max-width: 480px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.8;
    opacity: 0;
    animation: fadeUp 0.8s 0.6s forwards;
  }

  .divider {
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
    margin: 2rem 0;
    opacity: 0;
    animation: fadeUp 0.6s 0.75s forwards;
  }

  .section-label {
    font-size: 0.6rem;
    letter-spacing: 0.4em;
    color: var(--accent);
    text-transform: uppercase;
    margin-bottom: 0.75rem;
    opacity: 0;
    animation: fadeUp 0.6s 0.85s forwards;
  }
  .section-title {
    font-family: 'DM Serif Display', serif;
    font-size: clamp(1.6rem, 4vw, 2.5rem);
    margin-bottom: 2.5rem;
    opacity: 0;
    animation: fadeUp 0.7s 0.95s forwards;
  }

  #fileGrid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.2rem;
    margin-bottom: 5rem;
    opacity: 0;
    animation: fadeUp 0.8s 1.1s forwards;
  }

  .file-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1.8rem;
    cursor: pointer;
    text-decoration: none;
    display: block;
    position: relative;
    overflow: hidden;
    transition: transform 0.25s ease, border-color 0.25s ease, background 0.25s ease;
  }
  .file-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.3s ease;
  }
  .file-card:hover { transform: translateY(-5px); border-color: var(--accent); background: var(--surface2); }
  .file-card:hover::before { transform: scaleX(1); }

  .file-card-icon {
    font-size: 0.55rem;
    letter-spacing: 0.25em;
    color: var(--accent2);
    text-transform: uppercase;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .file-card-icon::before {
    content: '';
    display: inline-block;
    width: 24px; height: 1px;
    background: var(--accent2);
  }
  .file-card-name {
    font-family: 'DM Serif Display', serif;
    font-size: 1.3rem;
    color: var(--text);
    margin-bottom: 0.5rem;
    line-height: 1.2;
  }
  .file-card-filename {
    font-size: 0.6rem;
    color: var(--muted);
    letter-spacing: 0.12em;
  }
  .file-card-arrow {
    position: absolute;
    bottom: 1.8rem; right: 1.8rem;
    font-size: 1.4rem;
    color: var(--muted);
    transition: color 0.2s, transform 0.2s;
  }
  .file-card:hover .file-card-arrow { color: var(--accent); transform: translate(3px, -3px); }

  .subj-pills {
    display: flex;
    gap: 0.4rem;
    margin-top: 1rem;
    flex-wrap: wrap;
  }
  .pill {
    font-size: 0.55rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 0.25rem 0.6rem;
    border-radius: 2px;
  }
  .pill-p { background: rgba(79,195,247,0.12); color: #4fc3f7; }
  .pill-c { background: rgba(167,139,250,0.12); color: #a78bfa; }
  .pill-m { background: rgba(251,146,60,0.12); color: #fb923c; }

  .empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--muted);
    grid-column: 1/-1;
  }
  .empty-state-icon {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 4rem;
    color: var(--border);
    margin-bottom: 1rem;
  }
  .empty-state p {
    font-size: 0.75rem;
    letter-spacing: 0.15em;
    line-height: 2;
  }

  .loading-row {
    display: flex;
    gap: 0.4rem;
    align-items: center;
    grid-column: 1/-1;
    padding: 2rem 0;
  }
  .loading-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--accent);
    animation: blink 1.2s infinite;
  }
  .loading-dot:nth-child(2) { animation-delay: 0.2s; }
  .loading-dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes blink { 0%,100%{opacity:0.2} 50%{opacity:1} }

  .stats-strip {
    display: flex;
    gap: 0;
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 3rem;
    opacity: 0;
    animation: fadeUp 0.7s 1.0s forwards;
  }
  .stat-item {
    flex: 1;
    padding: 1.5rem 2rem;
    border-right: 1px solid var(--border);
    text-align: center;
  }
  .stat-item:last-child { border-right: none; }
  .stat-val {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.5rem;
    color: var(--accent);
    line-height: 1;
  }
  .stat-label {
    font-size: 0.55rem;
    letter-spacing: 0.25em;
    color: var(--muted);
    text-transform: uppercase;
    margin-top: 0.3rem;
  }

  footer {
    border-top: 1px solid var(--border);
    padding: 2rem 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    color: var(--muted);
    text-transform: uppercase;
  }

  @keyframes fadeUp {
    from { opacity:0; transform:translateY(20px); }
    to   { opacity:1; transform:translateY(0); }
  }

  @media(max-width:600px) {
    .stats-strip { flex-direction: column; }
    .stat-item { border-right: none; border-bottom: 1px solid var(--border); }
    .stat-item:last-child { border-bottom: none; }
    footer { flex-direction: column; gap: 0.5rem; text-align: center; }
  }
</style>
</head>
<body>
<div class="grid-bg"></div>
<div class="glow-1"></div>
<div class="glow-2"></div>
<div class="glow-3"></div>

<div class="page">
  <header>
    <div class="logo">JUT<span>·</span>HUB</div>
    <div class="header-tag">New JUT · Analytics Platform</div>
  </header>

  <div class="hero">
    <div class="hero-eyebrow">Batch Performance Intelligence</div>
    <div class="hero-title">ANALYSE<br><span class="outline">EVERY</span><br>TEST</div>
    <div class="hero-desc">
Score • Analyse • Improve
    </div>
  </div>

  <div class="divider"></div>

  <div class="stats-strip" id="statsStrip">
    <div class="stat-item">
      <div class="stat-val" id="strip-files">—</div>
      <div class="stat-label">Tests Available</div>
    </div>
    <div class="stat-item">
      <div class="stat-val">3</div>
      <div class="stat-label">Subjects Tracked</div>
    </div>
    <div class="stat-item">
      <div class="stat-val">75</div>
      <div class="stat-label">Questions / Test</div>
    </div>
    <div class="stat-item">
      <div class="stat-val">∞</div>
      <div class="stat-label">Insights</div>
    </div>
  </div>

  <div class="section-label">All Tests</div>
  <div class="section-title">Choose a JUT Result</div>

  <div id="fileGrid">
    <div class="loading-row">
      <div class="loading-dot"></div>
      <div class="loading-dot"></div>
      <div class="loading-dot"></div>
      <span style="font-size:0.65rem;letter-spacing:0.2em;color:var(--muted);margin-left:0.5rem;">LOADING FILES…</span>
    </div>
  </div>

  <footer>
    <span>JUT Analytics Hub</span>
    <span>Physics · Chemistry · Mathematics</span>
  </footer>
</div>

<script>
async function loadMenu() {
  const grid = document.getElementById('fileGrid');
  try {
    const res = await fetch('/api/csv-files');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const files = await res.json();

    document.getElementById('strip-files').textContent = files.length || '0';

    if (files.length === 0) {
      grid.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">NO FILES</div>
        <p>No CSV files found in the <code>/static</code> folder.<br>Add result CSVs and refresh.</p>
      </div>`;
      return;
    }

    grid.innerHTML = '';
    files.forEach((filename, idx) => {
      const label = filename.replace('.csv','').replace(/_/g,' ');
      const card = document.createElement('a');
      card.className = 'file-card';
      card.href = '/analysis?file=' + encodeURIComponent(filename);
      card.style.animationDelay = (idx * 0.06) + 's';
      card.innerHTML = `
        <div class="file-card-icon">JUT Result</div>
        <div class="file-card-name">${label}</div>
        <div class="file-card-filename">${filename}</div>
        <div class="subj-pills">
          <span class="pill pill-p">Physics</span>
          <span class="pill pill-c">Chemistry</span>
          <span class="pill pill-m">Maths</span>
        </div>
        <div class="file-card-arrow">↗</div>`;
      grid.appendChild(card);
    });
  } catch(err) {
    grid.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">ERROR</div>
      <p>Could not load file list.<br>${err.message}</p>
    </div>`;
  }
}
loadMenu();
</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSIS PAGE
# ══════════════════════════════════════════════════════════════════════════════
ANALYSIS_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JUT Performance Analysis</title>
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

  .topnav {
    position: fixed;
    top: 0; left: 0; right: 0;
    z-index: 500;
    background: rgba(10,10,15,0.85);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.9rem 2rem;
  }
  .topnav-logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.4rem;
    letter-spacing: 0.08em;
    color: var(--text);
    text-decoration: none;
  }
  .topnav-logo span { color: var(--accent); }
  .topnav-back {
    font-size: 0.6rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--muted);
    text-decoration: none;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    transition: color 0.2s;
  }
  .topnav-back:hover { color: var(--accent); }
  .topnav-file {
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    color: var(--accent2);
    text-transform: uppercase;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .hero {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    position: relative;
    padding: 6rem 2rem 3rem;
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
    flex-wrap: wrap;
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

  /* Clickable student name link */
  .name-cell a {
    color: inherit;
    text-decoration: none;
    border-bottom: 1px dashed var(--muted);
    transition: color 0.2s, border-color 0.2s;
  }
  .name-cell a:hover {
    color: var(--accent);
    border-color: var(--accent);
  }

  .charts-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
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

  #uploadOverlay {
    position: fixed;
    inset: 0;
    z-index: 2000;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(10,10,15,0.97);
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

  .csv-btn:hover { border-color: #e8c547; color: #e8c547; background: #16161f; }
  .csv-btn-filename { color: #6b6b8a; font-size: 0.6rem; }

  #uploadError { color: #e847a0; font-size: 0.7rem; margin-top: 1.5rem; display: none; }

  .picker-back {
    margin-top: 1.5rem;
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    color: var(--muted);
    text-decoration: none;
    text-transform: uppercase;
    transition: color 0.2s;
  }
  .picker-back:hover { color: var(--accent); }

  @media (max-width: 768px) {
    .hero-tag {letter-spacing: 0rem;}
    .charts-grid { grid-template-columns: 1fr; }
    .subject-grid { grid-template-columns: 1fr; }
    .hero-stats { gap: 5rem; }
    .podium { gap: 0.5rem; }
    .topnav-file { display: none; }
  }
</style>
</head>
<body>

<nav class="topnav">
  <a class="topnav-logo" href="/">JUT<span>·</span>HUB</a>
  <div class="topnav-file" id="topnavFile">—</div>
  <a class="topnav-back" href="/">← All Tests</a>
</nav>

<div class="hero">
  <div class="hero-bg"></div>
  <div class="hero-grid"></div>
  <div style="position:relative;z-index:2;">
    <div class="hero-tag" id="heroTag">NEW JUT · Batch Analysis</div>
    <div class="hero-title">PERFOR<span>MANCE</span><br>REPORT</div>
    <div class="hero-sub" id="heroSub">LOADING…</div>
    <div class="hero-stats">
      <div class="hero-stat"><div class="hero-stat-val" id="hs-avg">—</div><div class="hero-stat-label">Avg Score</div></div>
      <div class="hero-stat"><div class="hero-stat-val" id="hs-high">—</div><div class="hero-stat-label">Top Score</div></div>
      <div class="hero-stat"><div class="hero-stat-val" id="hs-acc">—</div><div class="hero-stat-label">Avg Accuracy</div></div>
      <div class="hero-stat"><div class="hero-stat-val" id="hs-count">—</div><div class="hero-stat-label">Students</div></div>
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
  <div style="overflow-x:auto">
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
  <div class="matrix-wrap reveal" style="display:flex;flex-direction:column;align-items:center;">
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

<div id="uploadOverlay" style="display:none;">
  <div class="picker-title">SELECT TEST</div>
  <div class="picker-sub">Choose a CSV file to analyse</div>
  <div id="csvMenu"></div>
  <div id="uploadError"></div>
  <a class="picker-back" href="/">← Back to Hub</a>
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
  const avg  = Math.round(raw.reduce((s,r) => s+r.total, 0) / raw.length);
  const high = Math.max(...raw.map(r => r.total));
  const avgAcc = Math.round(raw.reduce((s,r) => s+r.accuracy, 0) / raw.length);

  document.getElementById('hs-avg').textContent   = avg;
  document.getElementById('hs-high').textContent  = high;
  document.getElementById('hs-acc').textContent   = avgAcc + '%';
  document.getElementById('hs-count').textContent = raw.length;
  document.getElementById('heroSub').textContent  = raw.length + ' STUDENTS · PHYSICS · CHEMISTRY · MATHEMATICS';
  const label = filename.replace('.csv','').replace(/_/g,' ').toUpperCase();
  document.getElementById('heroTag').textContent  = 'NEW JUT · ' + label + ' · BATCH ANALYSIS';
  document.getElementById('topnavFile').textContent = label;
  document.getElementById('footerBar').textContent = 'JUT ANALYSIS DASHBOARD · ' + raw.length + ' STUDENTS · ' + label;
  document.title = 'JUT · ' + label;

  const podiumEl = document.getElementById('podium');
  podiumEl.innerHTML = '';
  const top3 = sorted.slice(0,3);
  const podiumOrder = [top3[1], top3[0], top3[2]].filter(Boolean);
  const heights = [120, 160, 90];
  const podiumClasses = ['p2','p1','p3'];
  const bgColors = ['linear-gradient(135deg,#94a3b8,#64748b)','linear-gradient(135deg,#fbbf24,#f59e0b)','linear-gradient(135deg,#cd7f32,#a0632a)'];
  const scoreColors = ['var(--silver)','var(--gold)','var(--bronze)'];
  const medalEmoji = ['\u{1F948}','\u{1F947}','\u{1F949}'];
  podiumOrder.forEach((s,i) => {
    const c = document.createElement('div');
    c.className = 'podium-card ' + podiumClasses[i];
    c.innerHTML =
      '<div class="podium-name">' + s.name + '</div>' +
      '<div class="podium-score" style="color:' + scoreColors[i] + '">' + s.total + '</div>' +
      '<div class="podium-rank-label">Overall Rank ' + (s.rank || i+1) + '</div>' +
      '<div class="podium-block" style="height:' + heights[i] + 'px;background:' + bgColors[i] + ';">' +
      '<span style="font-size:2rem;">' + medalEmoji[i] + '</span></div>';
    podiumEl.appendChild(c);
  });

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
    data.sort((a,b) => sortDir * (a[valKeys[currentSort]] - b[valKeys[currentSort]]));
    const tbody = document.getElementById('leaderboardBody');
    tbody.innerHTML = '';
    data.forEach(s => {
      const maxScore = high || 300;
      const phyPct  = Math.max(0, (s.phy_m  / maxScore) * 100);
      const chemPct = Math.max(0, (s.chem_m / maxScore) * 100);
      const mathPct = Math.max(0, (s.math_m / maxScore) * 100);
      const localRank = sorted.indexOf(s) + 1;
      const rankClass = localRank===1?'rank-1':localRank===2?'rank-2':localRank===3?'rank-3':'rank-other';
      const scoreColor = s.total>=high*0.75?'var(--accent2)':s.total>=high*0.5?'var(--accent)':s.total>=high*0.25?'var(--math)':'var(--accent3)';
      const accColor = s.accuracy>=60?'var(--accent2)':s.accuracy>=40?'var(--accent)':'var(--accent3)';
      const tr = document.createElement('tr');
      tr.className = 'row ' + getTier(s.total);
      tr.innerHTML =
        '<td><span class="rank-badge ' + rankClass + '">' + localRank + '</span></td>' +
        '<td><div class="name-cell"><a href="/student?student=' + encodeURIComponent(s.name) + '">' + s.name + '</a></div></td>' +
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

  function subjectStats(marks, correct, wrong, attempt) {
    const avg  = (marks.reduce((a,b)=>a+b,0)/marks.length).toFixed(1);
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

  const phyAvg  = raw.reduce((a,r)=>a+r.phy_m,0)/raw.length;
  const chemAvg = raw.reduce((a,r)=>a+r.chem_m,0)/raw.length;
  const mathAvg = raw.reduce((a,r)=>a+r.math_m,0)/raw.length;
  if(radarInst) radarInst.destroy();
  radarInst = new Chart(document.getElementById('radarChart'), {
    type:'radar',
    data:{labels:['Physics','Chemistry','Mathematics'],datasets:[{label:'Avg Marks',data:[phyAvg.toFixed(1),chemAvg.toFixed(1),mathAvg.toFixed(1)],borderColor:'#e8c547',backgroundColor:'rgba(232,197,71,0.1)',pointBackgroundColor:['#4fc3f7','#a78bfa','#fb923c'],pointRadius:6,borderWidth:2}]},
    options:{scales:{r:{grid:{color:'#1e1e2e'},ticks:{display:false},pointLabels:{color:'#e8e8f0',font:{family:'JetBrains Mono',size:11}}}},plugins:{legend:{display:false}}}
  });

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

  const accSorted = [...raw].sort((a,b)=>b.accuracy-a.accuracy);
  if(accuracyInst) accuracyInst.destroy();
  accuracyInst = new Chart(document.getElementById('accuracyChart'), {
    type:'bar',
    data:{labels:accSorted.map(s=>firstMeaningfulName(s.name)),datasets:[{label:'Accuracy %',data:accSorted.map(s=>s.accuracy),backgroundColor:accSorted.map(s=>s.accuracy>=70?'#47e8c5aa':s.accuracy>=50?'#e8c547aa':s.accuracy>=35?'#fb923caa':'#e847a0aa'),borderRadius:2}]},
    options:{indexAxis:'y',scales:{x:{ticks:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}},grid:{color:'#1e1e2e'},max:100},y:{ticks:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}},grid:{color:'transparent'}}},plugins:{legend:{display:false}}}
  });

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

function showError(msg) {
  const el = document.getElementById('uploadError');
  el.textContent = msg;
  el.style.display = 'block';
}

function hideOverlay() {
  const overlay = document.getElementById('uploadOverlay');
  overlay.style.opacity = '0';
  setTimeout(() => { overlay.style.display = 'none'; }, 500);
}

async function loadCSVByName(filename) {
  try {
    const res = await fetch('/static/' + filename);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const text = await res.text();
    const rows = parseCSV(text);
    if (rows.length === 0) { showError('CSV appears empty or malformed'); return; }
    hideOverlay();
    buildDashboard(rows.map(mapRow), filename);
  } catch(err) {
    showError('Error loading file: ' + err.message);
  }
}

async function populatePickerMenu() {
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
      btn.addEventListener('click', () => {
        const url = new URL(window.location);
        url.searchParams.set('file', filename);
        history.replaceState(null, '', url.toString());
        loadCSVByName(filename);
      });
      menu.appendChild(btn);
    });
  } catch(err) {
    menu.innerHTML = '<div style="color:#e847a0;font-size:0.7rem;">Failed to load file list: ' + err.message + '</div>';
  }
}

(async function boot() {
  const params = new URLSearchParams(window.location.search);
  const fileParam = params.get('file');

  if (fileParam) {
    document.getElementById('heroSub').textContent = 'LOADING ' + fileParam.toUpperCase() + '…';
    await loadCSVByName(fileParam);
  } else {
    document.getElementById('heroSub').textContent = 'SELECT A TEST TO BEGIN';
    const overlay = document.getElementById('uploadOverlay');
    overlay.style.display = 'flex';
    overlay.style.opacity = '1';
    await populatePickerMenu();
  }
})();
</script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(debug=True)
