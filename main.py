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
  --bg:#0a0a0f; --surface:#111118; --surface2:#16161f; --border:#1e1e2e;
  --accent:#e8c547; --accent2:#47e8c5; --accent3:#e847a0;
  --text:#e8e8f0; --muted:#6b6b8a;
  --phy:#4fc3f7; --chem:#a78bfa; --math:#fb923c;
  --gold:#fbbf24; --silver:#94a3b8; --bronze:#cd7f32;
  --green:#4ade80; --red:#f87171;
}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;overflow-x:hidden;}
body::after{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");pointer-events:none;z-index:9999;opacity:0.4;}


/* SCROLLABLE CHART CONTAINER */
.chart-scroll-outer{overflow-x:auto;overflow-y:hidden;}
.chart-scroll-outer::-webkit-scrollbar{height:3px;}
.chart-scroll-outer::-webkit-scrollbar-track{background:transparent;}
.chart-scroll-outer::-webkit-scrollbar-thumb{background:rgba(232,197,71,0.2);border-radius:2px;}
.chart-scroll-outer{scrollbar-width:thin;scrollbar-color:rgba(232,197,71,0.2) transparent;}
.chart-scroll-inner{position:relative;height:280px;min-width:600px;}
.chart-scroll-inner.tall{height:340px;}
.chart-scroll-inner.short{height:220px;}
/* min-width scales with number of data points */
.chart-scroll-inner canvas{position:absolute;inset:0;width:100%!important;height:100%!important;}


/* SCROLLABLE CHART CONTAINER */
.chart-scroll-outer{overflow-x:auto;overflow-y:hidden;}
.chart-scroll-outer::-webkit-scrollbar{height:3px;}
.chart-scroll-outer::-webkit-scrollbar-track{background:transparent;}
.chart-scroll-outer::-webkit-scrollbar-thumb{background:rgba(232,197,71,0.2);border-radius:2px;}
.chart-scroll-outer{scrollbar-width:thin;scrollbar-color:rgba(232,197,71,0.2) transparent;}
.chart-scroll-inner{position:relative;height:280px;min-width:600px;}
.chart-scroll-inner.tall{height:340px;}
.chart-scroll-inner.short{height:220px;}
/* min-width scales with number of data points */
.chart-scroll-inner canvas{position:absolute;inset:0;width:100%!important;height:100%!important;}

/* NAV */
.topnav{position:fixed;top:0;left:0;right:0;z-index:500;background:rgba(10,10,15,0.9);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0.9rem 2rem;}
.topnav-logo{font-family:'Bebas Neue',sans-serif;font-size:1.4rem;letter-spacing:0.08em;color:var(--text);text-decoration:none;}
.topnav-logo span{color:var(--accent);}
.topnav-back{font-size:0.6rem;letter-spacing:0.25em;text-transform:uppercase;color:var(--muted);text-decoration:none;transition:color 0.2s;}
.topnav-back:hover{color:var(--accent);}
.nav-breadcrumb{font-size:0.58rem;letter-spacing:0.18em;color:var(--accent2);text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:220px;}

/* HERO */
.hero{min-height:100vh;display:flex;flex-direction:column;justify-content:flex-end;align-items:flex-start;padding:7rem 4rem 4rem;position:relative;overflow:hidden;}
.hero-bg{position:absolute;inset:0;background:radial-gradient(ellipse 100% 70% at 80% 20%,rgba(232,197,71,0.07) 0%,transparent 60%),radial-gradient(ellipse 60% 80% at 0% 80%,rgba(71,232,197,0.05) 0%,transparent 60%);}
.hero-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,0.018) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.018) 1px,transparent 1px);background-size:80px 80px;animation:gridDrift 40s linear infinite;}
@keyframes gridDrift{0%{background-position:0 0}100%{background-position:80px 80px}}
.hero-rank-bg{position:absolute;right:3rem;top:50%;transform:translateY(-50%);font-family:'Bebas Neue',sans-serif;font-size:clamp(10rem,22vw,20rem);line-height:1;-webkit-text-stroke:1px rgba(232,197,71,0.08);color:transparent;user-select:none;pointer-events:none;opacity:0;animation:fadeIn 1.2s 0.5s forwards;}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.hero-content{position:relative;z-index:5;}
.hero-eyebrow{font-size:0.62rem;letter-spacing:0.4em;color:var(--accent2);text-transform:uppercase;margin-bottom:1rem;opacity:0;animation:slideUp 0.6s 0.2s forwards;display:flex;align-items:center;gap:0.8rem;}
.hero-eyebrow::before{content:'';display:block;width:36px;height:1px;background:var(--accent2);}
.hero-name{font-family:'Bebas Neue',sans-serif;font-size:clamp(3.5rem,11vw,8.5rem);line-height:0.88;letter-spacing:0.02em;opacity:0;animation:slideUp 0.8s 0.35s forwards;}
.hero-name .outline{-webkit-text-stroke:1.5px var(--accent);color:transparent;display:block;}
.hero-tagline{font-size:0.7rem;color:var(--muted);letter-spacing:0.18em;margin-top:1.2rem;opacity:0;animation:slideUp 0.7s 0.55s forwards;}
.hero-metrics{display:flex;gap:2.5rem;margin-top:2.5rem;opacity:0;animation:slideUp 0.7s 0.7s forwards;flex-wrap:wrap;}
.hero-metric-val{font-family:'Bebas Neue',sans-serif;font-size:3.2rem;color:var(--accent);line-height:1;}
.hero-metric-label{font-size:0.52rem;letter-spacing:0.28em;color:var(--muted);text-transform:uppercase;margin-top:0.2rem;}
@keyframes slideUp{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:translateY(0)}}

/* RINGS */
.ring-cluster{position:absolute;right:3rem;bottom:3.5rem;z-index:5;display:flex;gap:1.5rem;align-items:flex-end;opacity:0;animation:fadeIn 1s 1.1s forwards;flex-wrap:wrap;justify-content:flex-end;}
.ring-wrap{text-align:center;}
.ring-label{font-size:0.52rem;letter-spacing:0.18em;color:var(--muted);text-transform:uppercase;margin-top:0.4rem;}
svg.ring{transform:rotate(-90deg);}
.ring-fill{fill:none;stroke-width:6;stroke-linecap:round;transition:stroke-dashoffset 1.6s cubic-bezier(0.4,0,0.2,1);}
.ring-text{font-family:'Bebas Neue',sans-serif;font-size:1.05rem;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);}
.ring-container{position:relative;display:inline-block;}

/* LAYOUT */
.main-wrap{max-width:1500px;margin:0 auto;padding:0 2.5rem 6rem;}
section{padding:4.5rem 0;}
.sec-label{font-size:0.6rem;letter-spacing:0.42em;color:var(--accent);text-transform:uppercase;margin-bottom:0.7rem;display:flex;align-items:center;gap:0.8rem;}
.sec-label::before{content:'';display:block;width:28px;height:1px;background:var(--accent);}
.sec-title{font-family:'DM Serif Display',serif;font-size:clamp(1.8rem,4.5vw,3rem);margin-bottom:2rem;}
.divider{height:1px;background:linear-gradient(90deg,transparent,var(--border) 20%,var(--border) 80%,transparent);}
.reveal{opacity:0;transform:translateY(28px);transition:opacity 0.7s,transform 0.7s;}
.reveal.vis{opacity:1;transform:translateY(0);}

/* PROFILE STRIP */
.profile-strip{display:flex;gap:2rem;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:2rem;align-items:center;flex-wrap:wrap;position:relative;overflow:hidden;}
.profile-strip::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--accent),var(--accent2),var(--accent3));}
.profile-avatar{width:76px;height:76px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;font-family:'Bebas Neue',sans-serif;font-size:2.4rem;color:var(--bg);flex-shrink:0;}
.profile-info h1{font-family:'DM Serif Display',serif;font-size:1.9rem;margin-bottom:0.2rem;}
.profile-info p{font-size:0.62rem;color:var(--muted);letter-spacing:0.18em;}
.ppills{display:flex;gap:0.5rem;margin-top:0.6rem;flex-wrap:wrap;}
.ppill{font-size:0.52rem;letter-spacing:0.15em;padding:0.22rem 0.65rem;border-radius:20px;text-transform:uppercase;}
.ppill-y{background:rgba(232,197,71,0.12);color:var(--accent);}
.ppill-g{background:rgba(251,191,36,0.12);color:var(--gold);}
.ppill-t{background:rgba(71,232,197,0.1);color:var(--accent2);}
.ppill-p{background:rgba(232,71,160,0.1);color:var(--accent3);}
.ppill-b{background:rgba(79,195,247,0.1);color:var(--phy);}

/* STAT CARDS */
.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem;margin-top:1.5rem;}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.6rem;position:relative;overflow:hidden;transition:transform 0.3s,border-color 0.3s;}
.stat-card:hover{transform:translateY(-4px);border-color:rgba(232,197,71,0.3);}
.stat-card::after{content:'';position:absolute;top:0;left:0;right:0;height:2px;}
.sc-y::after{background:linear-gradient(90deg,var(--accent),var(--accent2));}
.sc-p::after{background:var(--phy);}
.sc-c::after{background:var(--chem);}
.sc-m::after{background:var(--math);}
.sc-a::after{background:var(--accent3);}
.sc-r::after{background:var(--gold);}
.sc-n::after{background:var(--green);}
.sc-label{font-size:0.55rem;letter-spacing:0.28em;color:var(--muted);text-transform:uppercase;margin-bottom:0.7rem;}
.sc-val{font-family:'Bebas Neue',sans-serif;font-size:3rem;line-height:1;}
.sc-sub{font-size:0.58rem;color:var(--muted);margin-top:0.35rem;letter-spacing:0.08em;}
.sc-trend{font-size:0.6rem;margin-top:0.7rem;padding:0.25rem 0.55rem;display:inline-block;border-radius:2px;}
.tr-up{background:rgba(74,222,128,0.1);color:#4ade80;}
.tr-dn{background:rgba(248,113,113,0.1);color:#f87171;}
.tr-fl{background:rgba(107,107,138,0.1);color:var(--muted);}

/* REPUTATION BADGE */
.rep-badge{display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:1.5rem;}
.rep-card{flex:1;min-width:180px;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.5rem;text-align:center;transition:transform 0.3s;}
.rep-card:hover{transform:translateY(-4px);}
.rep-icon{font-size:2.2rem;margin-bottom:0.6rem;}
.rep-title{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;margin-bottom:0.3rem;}
.rep-desc{font-size:0.58rem;color:var(--muted);letter-spacing:0.1em;line-height:1.6;}

/* PERCENTILE BAR */
.percentile-section{margin-top:1.5rem;}
.pct-row{display:flex;align-items:center;gap:1rem;margin-bottom:0.9rem;}
.pct-label{font-size:0.62rem;color:var(--muted);width:80px;flex-shrink:0;letter-spacing:0.1em;}
.pct-bar-outer{flex:1;height:28px;background:var(--border);border-radius:3px;overflow:hidden;position:relative;}
.pct-bar-inner{height:100%;border-radius:3px;display:flex;align-items:center;padding-left:10px;font-size:0.6rem;font-weight:600;color:rgba(0,0,0,0.75);transition:width 1.5s cubic-bezier(0.4,0,0.2,1);}
.pct-val{font-size:0.7rem;width:50px;text-align:right;flex-shrink:0;font-family:'Bebas Neue',sans-serif;font-size:1.2rem;}

/* TIMELINE */
.timeline{position:relative;padding-left:2.8rem;margin-top:1.5rem;}
.timeline::before{content:'';position:absolute;left:10px;top:0;bottom:0;width:1px;background:linear-gradient(to bottom,var(--accent),var(--border));}
.tl-item{position:relative;margin-bottom:1.8rem;opacity:0;transform:translateX(-18px);transition:opacity 0.55s,transform 0.55s;}
.tl-item.vis{opacity:1;transform:translateX(0);}
.tl-dot{position:absolute;left:-2.15rem;top:1.1rem;width:11px;height:11px;border-radius:50%;border:2px solid var(--accent);background:var(--bg);box-shadow:0 0 10px rgba(232,197,71,0.4);}
.tl-dot.abs{border-color:var(--muted);box-shadow:none;background:var(--muted);}
.tl-dot.best{border-color:var(--accent2);box-shadow:0 0 14px rgba(71,232,197,0.6);}
.tl-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.4rem 1.8rem;position:relative;overflow:hidden;transition:transform 0.3s,border-color 0.3s;}
.tl-card:hover{transform:translateX(8px);border-color:rgba(232,197,71,0.4);}
.tl-card::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(to bottom,var(--accent),var(--accent2));}
.tl-card.abs::before{background:var(--muted);}
.tl-card.best-ever::before{background:linear-gradient(to bottom,var(--accent2),#4ade80);}
.tl-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.8rem;flex-wrap:wrap;gap:0.5rem;}
.tl-test-name{font-family:'DM Serif Display',serif;font-size:1.15rem;}
.tl-score{font-family:'Bebas Neue',sans-serif;font-size:2.4rem;line-height:1;}
.tl-badge{font-size:0.52rem;letter-spacing:0.18em;padding:0.2rem 0.65rem;border-radius:20px;text-transform:uppercase;}
.b-abs{background:rgba(107,107,138,0.15);color:var(--muted);}
.b-best{background:rgba(71,232,197,0.15);color:var(--accent2);}
.b-good{background:rgba(232,197,71,0.12);color:var(--accent);}
.b-avg{background:rgba(251,146,60,0.12);color:var(--math);}
.b-low{background:rgba(232,71,160,0.1);color:var(--accent3);}
.tl-subjs{display:flex;gap:1.2rem;flex-wrap:wrap;font-size:0.68rem;margin-top:0.3rem;}
.tl-rank-line{font-size:0.62rem;color:var(--muted);margin-top:0.5rem;letter-spacing:0.1em;}
.tl-mini-bars{margin-top:0.8rem;display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.6rem;}
.mini-bar-block{}
.mini-bar-lbl{display:flex;justify-content:space-between;font-size:0.55rem;color:var(--muted);margin-bottom:3px;}
.mini-bar-outer{height:4px;background:var(--border);border-radius:2px;overflow:hidden;}
.mini-bar-fill{height:100%;border-radius:2px;transition:width 1.2s cubic-bezier(0.4,0,0.2,1);}
.abs-notice{background:rgba(107,107,138,0.06);border:1px solid rgba(107,107,138,0.2);border-radius:4px;padding:1rem;text-align:center;font-size:0.65rem;letter-spacing:0.15em;color:var(--muted);text-transform:uppercase;}

/* CHARTS */
.charts-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-top:1.5rem;}
.chart-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.8rem;position:relative;overflow:hidden;}
.chart-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--accent),var(--accent2));}
.chart-card.full-w{grid-column:1/-1;}
.chart-title{font-size:0.6rem;letter-spacing:0.28em;color:var(--muted);text-transform:uppercase;margin-bottom:1.2rem;}
/* Fixed height on the canvas wrapper — Chart.js respects this when maintainAspectRatio:false */
.chart-card .chart-wrap{position:relative;height:280px;}
.chart-card.full-w .chart-wrap{height:260px;}
.chart-card canvas{position:absolute;inset:0;width:100%!important;height:100%!important;}

/* SW GRID */
.sw-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-top:1.5rem;}
.sw-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.8rem;}
.sw-title{font-family:'DM Serif Display',serif;font-size:1.35rem;margin-bottom:1.2rem;}
.sw-row{display:flex;align-items:center;gap:0.8rem;margin-bottom:0.9rem;}
.sw-name{font-size:0.65rem;width:85px;color:var(--muted);flex-shrink:0;}
.sw-outer{flex:1;height:22px;background:var(--border);border-radius:3px;overflow:hidden;}
.sw-inner{height:100%;border-radius:3px;display:flex;align-items:center;padding-left:8px;font-size:0.57rem;font-weight:600;color:rgba(0,0,0,0.7);transition:width 1.5s cubic-bezier(0.4,0,0.2,1);}
.sw-pct{font-size:0.68rem;width:40px;text-align:right;flex-shrink:0;}

/* IMP GRID */
.imp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:1rem;margin-top:1.5rem;}
.imp-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.4rem;text-align:center;}
.imp-arrow{font-size:2rem;margin-bottom:0.4rem;}
.imp-label{font-size:0.55rem;letter-spacing:0.18em;color:var(--muted);text-transform:uppercase;margin-bottom:0.4rem;}
.imp-val{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;}
.imp-sub{font-size:0.57rem;color:var(--muted);margin-top:0.25rem;}

/* HEATMAP */
.hm-scroll{overflow-x:auto;margin-top:1.2rem;}
.hm-grid{display:grid;gap:3px;}
.hm-cell{width:38px;height:38px;border-radius:3px;position:relative;cursor:pointer;transition:transform 0.15s,box-shadow 0.15s;display:flex;align-items:center;justify-content:center;font-size:0.52rem;font-weight:600;color:rgba(255,255,255,0.75);}
.hm-cell:hover{transform:scale(1.3);z-index:20;box-shadow:0 4px 16px rgba(0,0,0,0.5);}
.hm-tip{position:absolute;bottom:calc(100% + 6px);left:50%;transform:translateX(-50%);background:#000;border:1px solid var(--border);padding:0.4rem 0.65rem;border-radius:3px;font-size:0.55rem;white-space:nowrap;pointer-events:none;opacity:0;transition:opacity 0.15s;z-index:100;color:var(--text);text-align:center;}
.hm-cell:hover .hm-tip{opacity:1;}

/* RANK TABLE */
.rtable{width:100%;border-collapse:separate;border-spacing:0 3px;margin-top:1.2rem;}
.rtable th{font-size:0.55rem;letter-spacing:0.22em;color:var(--muted);text-transform:uppercase;padding:0.4rem 0.8rem;text-align:left;font-weight:400;}
.rtable tr.rr{background:var(--surface);transition:all 0.2s;}
.rtable tr.rr:hover{background:var(--surface2);transform:translateX(4px);}
.rtable td{padding:0.7rem 0.8rem;font-size:0.7rem;border-top:1px solid transparent;border-bottom:1px solid transparent;}
.rtable tr.rr:hover td{border-color:var(--border);}
.rnk{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;}
.r1c{color:var(--gold);} .r2c{color:var(--silver);} .r3c{color:var(--bronze);} .roc{color:var(--muted);}

/* SELECTOR */
#selOverlay{position:fixed;inset:0;z-index:2000;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(10,10,15,0.98);backdrop-filter:blur(14px);}
.sel-title{font-family:'Bebas Neue',sans-serif;font-size:3.5rem;color:var(--accent);margin-bottom:0.5rem;text-align:center;}
.sel-sub{font-size:0.62rem;letter-spacing:0.35em;color:var(--muted);text-transform:uppercase;margin-bottom:1.8rem;text-align:center;}
.sel-search{background:var(--surface);border:1px solid var(--border);color:var(--text);padding:0.85rem 1.4rem;font-family:'JetBrains Mono',monospace;font-size:0.82rem;border-radius:4px;outline:none;width:90%;max-width:500px;transition:border-color 0.2s;margin-bottom:0.8rem;}
.sel-search:focus{border-color:var(--accent);}
.sel-search::placeholder{color:var(--muted);}
.sel-list{width:90%;max-width:500px;max-height:52vh;overflow-y:auto;display:flex;flex-direction:column;gap:3px;}
.sel-item{background:var(--surface);border:1px solid var(--border);color:var(--text);padding:0.85rem 1.4rem;font-family:'JetBrains Mono',monospace;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;border-radius:3px;display:flex;justify-content:space-between;align-items:center;transition:border-color 0.2s,background 0.2s,color 0.2s;}
.sel-item:hover{border-color:var(--accent);color:var(--accent);background:var(--surface2);}
.sel-item-sub{font-size:0.55rem;color:var(--muted);}
.sel-back{margin-top:1.2rem;font-size:0.58rem;letter-spacing:0.18em;color:var(--muted);text-decoration:none;text-transform:uppercase;transition:color 0.2s;}
.sel-back:hover{color:var(--accent);}

/* RESPONSIVE */
@media(max-width:900px){
  .charts-grid{grid-template-columns:1fr;}
  .chart-card.full-w{grid-column:auto;}
  .sw-grid{grid-template-columns:1fr;}
}
@media(max-width:680px){
  .hero{padding:7rem 1.5rem 3.5rem;}
  .hero-rank-bg{display:none;}
  .ring-cluster{position:static;margin-top:1.5rem;justify-content:flex-start;}
  .main-wrap{padding:0 1.2rem 4rem;}
  .hero-metrics{gap:1.2rem;}
  .imp-grid{grid-template-columns:1fr 1fr;}
}
</style>
</head>
<body>

<nav class="topnav">
  <a class="topnav-logo" href="/">JUT<span>·</span>HUB</a>
  <div class="nav-breadcrumb" id="navBc">Loading…</div>
  <a class="topnav-back" href="/">← All Tests</a>
</nav>

<div class="hero">
  <div class="hero-bg"></div>
  <div class="hero-grid"></div>
  <div class="hero-rank-bg" id="heroRankBg">#1</div>
  <div class="hero-content">
    <div class="hero-eyebrow" id="heroEyebrow">JUT · Student Profile</div>
    <div class="hero-name">
      <span id="heroFirst">Loading</span>
      <span class="outline" id="heroLast">Student</span>
    </div>
    <div class="hero-tagline" id="heroTagline">Physics · Chemistry · Mathematics</div>
    <div class="hero-metrics">
      <div><div class="hero-metric-val" id="hmBest">—</div><div class="hero-metric-label">Best Score</div></div>
      <div><div class="hero-metric-val" id="hmAvg">—</div><div class="hero-metric-label">Avg Score</div></div>
      <div><div class="hero-metric-val" id="hmTests">—</div><div class="hero-metric-label">Tests Attended</div></div>
      <div><div class="hero-metric-val" id="hmRank">—</div><div class="hero-metric-label">Overall Rank</div></div>
    </div>
  </div>
  <div class="ring-cluster" id="ringCluster"></div>
</div>

<div class="main-wrap">

<section>
  <div class="profile-strip reveal" id="profileStrip">
    <div class="profile-avatar" id="avatarEl">?</div>
    <div class="profile-info">
      <h1 id="fullNameEl">—</h1>
      <p id="testSummaryEl">Loading…</p>
      <div class="ppills" id="ppills"></div>
    </div>
  </div>
</section>

<div class="divider"></div>

<section>
  <div class="sec-label reveal">Performance Overview</div>
  <div class="sec-title reveal">Key Statistics</div>
  <div class="stat-grid reveal" id="statGrid"></div>
</section>

<div class="divider"></div>

<section>
  <div class="sec-label reveal">Rank & Percentile</div>
  <div class="sec-title reveal">Where You Stand</div>
  <div class="percentile-section reveal" id="pctSection"></div>
  <div class="rep-badge reveal" id="repBadge"></div>
</section>

<div class="divider"></div>

<section>
  <div class="sec-label reveal">Test History</div>
  <div class="sec-title reveal">JUT Timeline</div>
  <div class="timeline" id="timeline"></div>
</section>

<div class="divider"></div>

<section>
  <div class="sec-label reveal">Growth Analysis</div>
  <div class="sec-title reveal">Improvement Tracker</div>
  <div class="imp-grid reveal" id="impGrid"></div>
</section>

<div class="divider"></div>

<section>
  <div class="sec-label reveal">Visual Analytics</div>
  <div class="sec-title reveal">Score Intelligence</div>
  <div class="charts-grid">
    <div class="chart-card full-w reveal">
      <div class="chart-title">Score Across All JUTs vs Batch Average</div>
      <div class="chart-scroll-outer"><div class="chart-scroll-inner short" id="progressWrap"><canvas id="progressChart"></canvas></div></div>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Subject Breakdown — Average Marks</div>
      <div class="chart-wrap"><canvas id="radarChart"></canvas></div>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Correct · Wrong · Unattempted per JUT</div>
      <div class="chart-scroll-outer"><div class="chart-scroll-inner" id="stackedWrap"><canvas id="stackedChart"></canvas></div></div>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Accuracy % per JUT</div>
      <div class="chart-scroll-outer"><div class="chart-scroll-inner" id="accWrap"><canvas id="accChart"></canvas></div></div>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Subject Marks per JUT</div>
      <div class="chart-scroll-outer"><div class="chart-scroll-inner" id="subjWrap"><canvas id="subjChart"></canvas></div></div>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Your Rank per JUT (lower = better)</div>
      <div class="chart-scroll-outer"><div class="chart-scroll-inner" id="rankWrap"><canvas id="rankChart"></canvas></div></div>
    </div>
  </div>
</section>

<div class="divider"></div>

<section>
  <div class="sec-label reveal">Subject Intelligence</div>
  <div class="sec-title reveal">Strengths & Weaknesses</div>
  <div class="sw-grid reveal" id="swGrid">
    <div class="sw-card" id="swS"></div>
    <div class="sw-card" id="swW"></div>
  </div>
</section>

<div class="divider"></div>

<section>
  <div class="sec-label reveal">Micro Analysis</div>
  <div class="sec-title reveal">Per-JUT Heatmap</div>
  <p class="reveal" style="font-size:0.62rem;color:var(--muted);letter-spacing:0.12em;margin-bottom:0.8rem;">Each column = one JUT. Rows = Physics / Chemistry / Maths. Intensity = performance.</p>
  <div class="hm-scroll reveal"><div id="bigHm" class="hm-grid"></div></div>
</section>

<div class="divider"></div>

<section>
  <div class="sec-label reveal">Class Standing</div>
  <div class="sec-title reveal">JUT-wise Rank</div>
  <div class="reveal" style="overflow-x:auto;">
    <table class="rtable">
      <thead><tr>
        <th>JUT</th><th>Status</th><th>Score</th><th>Rank</th>
        <th>Batch Avg</th><th>vs Avg</th><th>Percentile</th><th>Accuracy</th>
      </tr></thead>
      <tbody id="rankBody"></tbody>
    </table>
  </div>
</section>

</div><!-- /main-wrap -->

<footer style="text-align:center;padding:2rem;color:var(--muted);font-size:0.58rem;letter-spacing:0.18em;border-top:1px solid var(--border);" id="footerEl">JUT INDIVIDUAL ANALYTICS</footer>

<div id="selOverlay">
  <div class="sel-title">WHOSE PROFILE?</div>
  <div class="sel-sub">Select a student to view their full analysis</div>
  <input class="sel-search" id="selSearch" type="text" placeholder="Search student name…" autocomplete="off">
  <div class="sel-list" id="selList"><div style="font-size:0.7rem;color:var(--muted);text-align:center;padding:2rem;">Loading…</div></div>
  <a class="sel-back" href="/">← Back to Hub</a>
</div>

<script>
/* ── utils ── */
const $ = id => document.getElementById(id);
const n = v => parseFloat(v)||0;
const pct = (a,b) => b>0?Math.round(a/b*100):0;
const avg = arr => arr.length?arr.reduce((a,b)=>a+b,0)/arr.length:0;
Chart.defaults.font.family = 'JetBrains Mono';
Chart.defaults.color = '#6b6b8a';

function shortLabel(s){
  // "Details of NEW JEE: 9164" → "JEE 9164"
  // "JUT_3" → "JUT 3"  etc
  s = s.replace(/_/g,' ').trim();
  // extract trailing number
  const m = s.match(/(\d+)\s*$/);
  if(m){
    // find keyword before the number
    const kws = ['JUT','JEE','TEST','EXAM'];
    for(const kw of kws){
      if(s.toUpperCase().includes(kw)) return kw+' '+m[1];
    }
    return '#'+m[1];
  }
  // shorten long strings
  if(s.length>10) return s.slice(0,10).trim()+'…';
  return s;
}

function initials(n){return n.trim().split(/\s+/).map(w=>w[0]?.toUpperCase()||'').join('').slice(0,2)||'?';}

function mapRow(r){
  const g=(...ks)=>{for(const k of ks){if(r[k]!==undefined&&r[k]!=='')return r[k];}return'0';};
  const gs=(...ks)=>{for(const k of ks){if(r[k]!==undefined&&r[k]!=='')return r[k];}return'';};
  return{
    name:gs('name')||'Unknown',
    test:gs('test','test_name','filename','jut','jut_name')||'Unknown',
    total:n(g('total_marks','total_score','total')),
    rank:n(g('rank')),
    phy_a:n(g('phy_attempt','physics_attempt')),chem_a:n(g('chem_attempt','chemistry_attempt')),math_a:n(g('math_attempt','maths_attempt')),
    tot_a:n(g('total_attempt')),
    phy_c:n(g('phy_correct','physics_correct')),chem_c:n(g('chem_correct','chemistry_correct')),math_c:n(g('math_correct','maths_correct')),
    tot_c:n(g('total_correct')),
    phy_w:n(g('phy_wrong','physics_wrong')),chem_w:n(g('chem_wrong','chemistry_wrong')),math_w:n(g('math_wrong','maths_wrong')),
    tot_w:n(g('total_wrong')),
    phy_m:n(g('phy_marks','physics_marks')),chem_m:n(g('chem_marks','chemistry_marks')),math_m:n(g('math_marks','maths_marks')),
  };
}

let charts={};
function destroyCharts(){Object.values(charts).forEach(c=>{try{c.destroy();}catch(e){}});charts={};}

/* ── selector ── */
let allRows=[], allStudents=[];
// Normalize name: trim, collapse internal whitespace, uppercase
// "Ayush  R  Mendon" and "AYUSH R MENDON" both become "AYUSH R MENDON"
function normName(n){ return n.trim().replace(/\s+/g,' ').toUpperCase(); }

async function loadSelector(){
  try{
    const res=await fetch('/api/master-data');
    if(!res.ok)throw new Error('HTTP '+res.status);
    const raw=await res.json();
    // Normalize all names on ingest so duplicates collapse
    allRows=raw.map(r=>{const m=mapRow(r);m.name=normName(m.name)||m.name;return m;});
    const ns={};
    allRows.forEach(r=>{const k=normName(r.name);if(!ns[k])ns[k]=r.name;});
    allStudents=Object.values(ns).sort();
    renderSelList(allStudents);
  }catch(e){
    $('selList').innerHTML=`<div style="color:var(--accent3);font-size:0.7rem;text-align:center;padding:1rem;">Error: ${e.message}</div>`;
  }
}

function renderSelList(students){
  const list=$('selList');list.innerHTML='';
  if(!students.length){list.innerHTML='<div style="font-size:0.7rem;color:var(--muted);text-align:center;padding:1rem;">No results</div>';return;}
  students.forEach(name=>{
    const rows=allRows.filter(r=>r.name.toLowerCase()===name.toLowerCase());
    const att=rows.filter(r=>r.total>0||r.tot_a>0).length;
    const best=Math.max(0,...rows.map(r=>r.total));
    const el=document.createElement('div');
    el.className='sel-item';
    el.innerHTML=`<span>${name}</span><span class="sel-item-sub">Best: ${best} · ${att} JUTs attended</span>`;
    el.addEventListener('click',()=>loadProfile(name));
    list.appendChild(el);
  });
}

$('selSearch').addEventListener('input',e=>{
  const q=e.target.value.toLowerCase();
  renderSelList(allStudents.filter(n=>normName(n).includes(q.toUpperCase())));
});

async function loadProfile(name){
  const url=new URL(window.location);url.searchParams.set('student',name);history.replaceState(null,'',url.toString());
  const ov=$('selOverlay');ov.style.opacity='0';setTimeout(()=>{ov.style.display='none';},500);
  destroyCharts();
  buildProfile(name,allRows);
}

/* ── PROFILE BUILDER ── */
function buildProfile(studentName,masterRows){
  const sRows=masterRows.filter(r=>normName(r.name)===normName(studentName));
  const testMap={};
  masterRows.forEach(r=>{if(!testMap[r.test])testMap[r.test]=[];testMap[r.test].push(r);});
  const allTests=Object.keys(testMap).sort();

  // per-test data
  const perTest=allTests.map(testName=>{
    const row=sRows.find(r=>r.test===testName);
    const batchRows=testMap[testName];
    const batchScores=batchRows.map(r=>r.total).sort((a,b)=>b-a);
    const batchAvg=avg(batchRows.map(r=>r.total));
    const batchMax=Math.max(...batchRows.map(r=>r.total));
    if(!row){
      return{testName,absent:true,batchAvg:Math.round(batchAvg),batchMax,batchSize:batchRows.length,rank:null,...nullEntry()};
    }
    const absent=(row.total===0&&row.tot_a===0);
    const scored=batchRows.map(r=>r.total).sort((a,b)=>b-a);
    const rankInTest=scored.indexOf(row.total)+1||null;
    // percentile: % of students scoring <= this student
    const below=scored.filter(s=>s<row.total).length;
    const percentile=Math.round((below/batchRows.length)*100);
    return{testName,absent,batchAvg:Math.round(batchAvg),batchMax,batchSize:batchRows.length,rank:rankInTest,percentile,...row};
  });

  const attended=perTest.filter(t=>!t.absent);
  const scores=attended.map(t=>t.total);
  const bestScore=scores.length?Math.max(...scores):0;
  const avgScore=scores.length?Math.round(avg(scores)):0;
  const bestRank=attended.filter(t=>t.rank).length?Math.min(...attended.filter(t=>t.rank).map(t=>t.rank)):'—';
  const overallAcc=attended.length?Math.round(avg(attended.map(t=>pct(t.tot_c,t.tot_a)))):0;

  // ── TRUE OVERALL RANK: rank by avg score across all students (matches overview) ──
  // Build every student's avg score from masterRows
  const _studentAvgs = {};
  masterRows.forEach(r => {
    if(!_studentAvgs[normName(r.name)]) _studentAvgs[normName(r.name)] = {scores:[], name:r.name};
    if(r.total > 0 || r.tot_a > 0) _studentAvgs[normName(r.name)].scores.push(r.total);
  });
  // Sort all students by their avg score descending
  const _allAvgs = Object.values(_studentAvgs)
    .filter(s => s.scores.length > 0)
    .map(s => ({name: s.name, avgScore: avg(s.scores)}))
    .sort((a, b) => b.avgScore - a.avgScore);
  // Find this student's position (1-based)
  const _myKey = normName(studentName);
  const _myIdx = _allAvgs.findIndex(s => normName(s.name) === _myKey);
  const avgRank = _myIdx >= 0 ? _myIdx + 1 : '—';
  // Best rank: best position achieved in any single JUT
  const avgPct=attended.filter(t=>t.percentile!=null).length?Math.round(avg(attended.filter(t=>!t.absent).map(t=>t.percentile))):'—';

  /* ── HERO ── */
  const parts=studentName.trim().split(/\s+/);
  $('heroFirst').textContent=parts[0]||studentName;
  $('heroLast').textContent=parts.slice(1).join(' ')||'';
  if(!parts[1])$('heroLast').style.display='none';
  $('heroRankBg').textContent='#'+(avgRank||'?');
  $('heroEyebrow').textContent=`JUT · Student Profile · ${attended.length}/${allTests.length} Tests`;
  $('hmBest').textContent=bestScore||'—';
  $('hmAvg').textContent=avgScore||'—';
  $('hmTests').textContent=attended.length;
  $('hmRank').textContent='#'+(avgRank||'—');
  $('heroTagline').textContent=`Physics · Chemistry · Mathematics · ${allTests.length} JUTs Total`;
  $('navBc').textContent=studentName.toUpperCase();
  document.title='JUT · '+studentName;
  $('footerEl').textContent='JUT INDIVIDUAL ANALYTICS · '+studentName.toUpperCase()+' · '+attended.length+' TESTS';

  /* ── RINGS ── */
  const rc=$('ringCluster');rc.innerHTML='';
  const phyA=attended.length?avg(attended.map(t=>t.phy_m)):0;
  const chemA=attended.length?avg(attended.map(t=>t.chem_m)):0;
  const mathA=attended.length?avg(attended.map(t=>t.math_m)):0;
  [
    {lbl:'Physics',val:Math.round(pct(phyA,100)),color:'var(--phy)',c:'79,195,247'},
    {lbl:'Chem',val:Math.round(pct(chemA,100)),color:'var(--chem)',c:'167,139,250'},
    {lbl:'Maths',val:Math.round(pct(mathA,100)),color:'var(--math)',c:'251,146,60'},
  ].forEach(({lbl,val,color,c})=>{
    const r=42,circ=2*Math.PI*r,offset=circ*(1-val/100);
    const d=document.createElement('div');d.className='ring-wrap';
    d.innerHTML=`<div class="ring-container" style="width:96px;height:96px;">
      <svg class="ring" width="96" height="96" viewBox="0 0 96 96">
        <circle fill="none" stroke="var(--border)" stroke-width="6" cx="48" cy="48" r="${r}"/>
        <circle class="ring-fill" cx="48" cy="48" r="${r}" stroke="${color}"
          stroke-dasharray="${circ}" stroke-dashoffset="${circ}" data-off="${offset}"/>
      </svg>
      <div class="ring-text" style="color:${color}">${val}%</div>
    </div>
    <div class="ring-label">${lbl}</div>`;
    rc.appendChild(d);
  });
  setTimeout(()=>{document.querySelectorAll('.ring-fill').forEach(c=>{c.style.strokeDashoffset=c.dataset.off;});},700);

  /* ── PROFILE STRIP ── */
  $('avatarEl').textContent=initials(studentName);
  $('fullNameEl').textContent=studentName;
  $('testSummaryEl').textContent=`${attended.length} of ${allTests.length} JUTs attended · ${perTest.filter(t=>t.absent).length} absences`;
  const pills=$('ppills');pills.innerHTML='';
  const pillData=[
    {cls:'ppill-y',t:`Best: ${bestScore}`},
    {cls:'ppill-g',t:`Overall Rank: #${avgRank}`},
    {cls:'ppill-t',t:`Avg Accuracy: ${overallAcc}%`},
    {cls:'ppill-p',t:`Avg Percentile: ${avgPct}%`},
    {cls:'ppill-b',t:`Attendance: ${Math.round(pct(attended.length,allTests.length))}%`},
  ];
  pillData.forEach(({cls,t})=>{const p=document.createElement('span');p.className=`ppill ${cls}`;p.textContent=t;pills.appendChild(p);});

  /* ── STAT CARDS ── */
  function trend(arr){
    if(arr.length<2)return'<span class="sc-trend tr-fl">— not enough data</span>';
    const d=arr[arr.length-1]-arr[arr.length-2];
    if(d>0)return`<span class="sc-trend tr-up">↑ +${d} from prev</span>`;
    if(d<0)return`<span class="sc-trend tr-dn">↓ ${d} from prev</span>`;
    return'<span class="sc-trend tr-fl">→ same as prev</span>';
  }
  const phyBest=attended.length?Math.max(...attended.map(t=>t.phy_m)):0;
  const chemBest=attended.length?Math.max(...attended.map(t=>t.chem_m)):0;
  const mathBest=attended.length?Math.max(...attended.map(t=>t.math_m)):0;
  $('statGrid').innerHTML=[
    {cls:'sc-y',lbl:'Best Total',val:bestScore,sub:`Avg: ${avgScore}`,tr:trend(attended.map(t=>t.total))},
    {cls:'sc-r',lbl:'Overall Rank',val:'#'+avgRank,sub:`Ranked by avg score · best in a test: #${bestRank}`,tr:''},
    {cls:'sc-n',lbl:'Avg Percentile',val:avgPct+'%',sub:`Based on ${attended.length} tests`,tr:''},
    {cls:'sc-p',lbl:'Avg Physics',val:Math.round(phyA),sub:`Best: ${phyBest}`,tr:trend(attended.map(t=>t.phy_m))},
    {cls:'sc-c',lbl:'Avg Chemistry',val:Math.round(chemA),sub:`Best: ${chemBest}`,tr:trend(attended.map(t=>t.chem_m))},
    {cls:'sc-m',lbl:'Avg Maths',val:Math.round(mathA),sub:`Best: ${mathBest}`,tr:trend(attended.map(t=>t.math_m))},
    {cls:'sc-a',lbl:'Avg Accuracy',val:overallAcc+'%',sub:`Best: ${attended.length?Math.max(...attended.map(t=>pct(t.tot_c,t.tot_a))):0}%`,tr:trend(attended.map(t=>pct(t.tot_c,t.tot_a)))},
    {cls:'sc-y',lbl:'Tests Attended',val:attended.length,sub:`of ${allTests.length} total · ${Math.round(pct(attended.length,allTests.length))}% attendance`,tr:''},
  ].map(({cls,lbl,val,sub,tr})=>`<div class="stat-card ${cls}"><div class="sc-label">${lbl}</div><div class="sc-val">${val}</div><div class="sc-sub">${sub}</div>${tr}</div>`).join('');

  /* ── PERCENTILE SECTION ── */
  const pctEl=$('pctSection');pctEl.innerHTML='';
  const subjectPcts=[
    {lbl:'Physics',val:attended.length?Math.round(avg(attended.map(t=>pct(t.phy_m,100)))):0,color:'#4fc3f7'},
    {lbl:'Chemistry',val:attended.length?Math.round(avg(attended.map(t=>pct(t.chem_m,100)))):0,color:'#a78bfa'},
    {lbl:'Maths',val:attended.length?Math.round(avg(attended.map(t=>pct(t.math_m,100)))):0,color:'#fb923c'},
    {lbl:'Overall',val:attended.length?Math.round(avg(attended.map(t=>pct(t.total,300)))):0,color:'#e8c547'},
    {lbl:'Accuracy',val:overallAcc,color:'#e847a0'},
  ];
  subjectPcts.forEach(({lbl,val,color})=>{
    const row=document.createElement('div');row.className='pct-row';
    row.innerHTML=`<div class="pct-label">${lbl}</div>
      <div class="pct-bar-outer"><div class="pct-bar-inner" style="background:${color};width:0%" data-pct="${val}">${val}%</div></div>
      <div class="pct-val" style="color:${color}">${val}%</div>`;
    pctEl.appendChild(row);
  });
  setTimeout(()=>{document.querySelectorAll('.pct-bar-inner').forEach(b=>{b.style.width=b.dataset.pct+'%';});},400);

  /* ── REPUTATION / MOTIVATION CARDS ── */
  function getReputation(){
    if(!attended.length)return{icon:'👻',title:'GHOST',desc:'No tests attended yet. Start your journey.',color:'var(--muted)'};
    const a=avgRank==='—'?999:avgRank;
    const batchSize=perTest.find(t=>!t.absent)?.batchSize||1;
    const topPct=Math.round((a/batchSize)*100);
    if(topPct<=10)return{icon:'🔱',title:'ELITE',desc:'Consistently in the top 10% of the batch.',color:'var(--accent2)'};
    if(topPct<=25)return{icon:'🌟',title:'STAR PERFORMER',desc:'Top quartile. The batch looks up to you.',color:'var(--gold)'};
    if(topPct<=50)return{icon:'⚡',title:'ABOVE AVERAGE',desc:'Performing better than half the batch.',color:'var(--accent)'};
    if(topPct<=75)return{icon:'📈',title:'IN PROGRESS',desc:'Room to grow — the climb has begun.',color:'var(--math)'};
    return{icon:'🎯',title:'CHALLENGER',desc:'Every attempt is a step toward the top.',color:'var(--accent3)'};
  }
  function getConsistencyRating(){
    if(scores.length<2)return{icon:'🎲',title:'SINGLE TEST',desc:'Attend more JUTs to gauge consistency.',color:'var(--muted)'};
    const mn=avg(scores),sd=Math.sqrt(avg(scores.map(x=>(x-mn)**2)));
    const cv=sd/mn;
    if(cv<0.05)return{icon:'🔒',title:'ROCK SOLID',desc:'Exceptional consistency. Virtually no variance.',color:'var(--accent2)'};
    if(cv<0.12)return{icon:'💎',title:'CONSISTENT',desc:'Very stable scores across all tests.',color:'var(--green)'};
    if(cv<0.2)return{icon:'🌊',title:'SOME VARIANCE',desc:'Mostly stable with occasional swings.',color:'var(--accent)'};
    return{icon:'🌪',title:'VOLATILE',desc:'High variance — focus on stability.',color:'var(--accent3)'};
  }
  function getMotivation(){
    if(!attended.length)return{icon:'🚀',title:'START NOW',desc:'Every JUT you attend builds your edge.',color:'var(--accent)'};
    const last3=attended.slice(-3).map(t=>t.total);
    if(last3.length>=2&&last3[last3.length-1]>last3[0])return{icon:'📊',title:'ON THE RISE',desc:'Your recent scores show an upward trend!',color:'var(--green)'};
    if(last3.length>=2&&last3[last3.length-1]<last3[0])return{icon:'🔧',title:'NEEDS WORK',desc:'Recent dip — review, reset, and rise.',color:'var(--math)'};
    return{icon:'⚖️',title:'HOLDING STEADY',desc:'Maintaining performance. Push for the next level.',color:'var(--accent2)'};
  }
  function getPhysicsTag(){
    if(!attended.length)return null;
    const pa=avg(attended.map(t=>pct(t.phy_m,100)));
    const ca=avg(attended.map(t=>pct(t.chem_m,100)));
    const ma=avg(attended.map(t=>pct(t.math_m,100)));
    const best=[['Physics',pa],['Chemistry',ca],['Maths',ma]].sort((a,b)=>b[1]-a[1])[0];
    return{icon:'🏆',title:`${best[0].toUpperCase()} ACE`,desc:`${best[0]} is your strongest subject at ${Math.round(best[1])}% avg.`,color:'var(--accent)'};
  }
  const badges=[getReputation(),getConsistencyRating(),getMotivation()];
  const phyTag=getPhysicsTag();if(phyTag)badges.push(phyTag);
  $('repBadge').innerHTML=badges.map(b=>`
    <div class="rep-card">
      <div class="rep-icon">${b.icon}</div>
      <div class="rep-title" style="color:${b.color}">${b.title}</div>
      <div class="rep-desc">${b.desc}</div>
    </div>`).join('');

  /* ── TIMELINE ── */
  const tl=$('timeline');tl.innerHTML='';
  perTest.forEach((t,i)=>{
    const isBest=!t.absent&&t.total===bestScore&&attended.length>0;
    const acc=t.absent?0:pct(t.tot_c,t.tot_a);
    let bc='b-avg',bl='Average';
    if(t.absent){bc='b-abs';bl='Absent';}
    else if(isBest){bc='b-best';bl='🏆 Personal Best';}
    else if(t.total>=t.batchMax*0.8){bc='b-best';bl='Excellent';}
    else if(t.total>=t.batchAvg*1.1){bc='b-good';bl='Above Avg';}
    else if(t.total<t.batchAvg*0.7){bc='b-low';bl='Below Avg';}
    const item=document.createElement('div');item.className='tl-item';item.style.transitionDelay=(i*0.06)+'s';
    item.innerHTML=`
      <div class="tl-dot${t.absent?' abs':isBest?' best':''}"></div>
      <div class="tl-card${t.absent?' abs':isBest?' best-ever':''}">
        <div class="tl-top">
          <div>
            <div class="tl-test-name">${t.testName.replace(/_/g,' ')}</div>
            <div class="tl-rank-line">${t.absent?'Absent':'Rank #'+(t.rank||'?')+' of '+t.batchSize+' · Percentile: '+(t.percentile!=null?t.percentile+'%':'—')}</div>
          </div>
          <div style="text-align:right">
            <div class="tl-score" style="color:${t.absent?'var(--muted)':isBest?'var(--accent2)':'var(--accent)'}">${t.absent?'ABS':t.total}</div>
            <span class="tl-badge ${bc}">${bl}</span>
          </div>
        </div>
        ${t.absent?`<div class="abs-notice">Absent — no data recorded</div>`:`
          <div class="tl-subjs">
            <span style="color:var(--phy)">P: ${t.phy_m}</span>
            <span style="color:var(--chem)">C: ${t.chem_m}</span>
            <span style="color:var(--math)">M: ${t.math_m}</span>
            <span style="color:var(--muted);margin-left:auto">vs avg: <span style="color:${t.total>=t.batchAvg?'var(--green)':'var(--red)'}">${t.total>=t.batchAvg?'+':''}${t.total-t.batchAvg}</span></span>
            <span style="color:var(--muted)">acc: <span style="color:${acc>=60?'var(--accent2)':acc>=40?'var(--accent)':'var(--accent3)'}">${acc}%</span></span>
          </div>
          <div class="tl-mini-bars">
            <div class="mini-bar-block"><div class="mini-bar-lbl"><span style="color:var(--phy)">Phy</span><span>${t.phy_m}</span></div><div class="mini-bar-outer"><div class="mini-bar-fill" style="width:${pct(t.phy_m,100)}%;background:var(--phy)"></div></div></div>
            <div class="mini-bar-block"><div class="mini-bar-lbl"><span style="color:var(--chem)">Chem</span><span>${t.chem_m}</span></div><div class="mini-bar-outer"><div class="mini-bar-fill" style="width:${pct(t.chem_m,100)}%;background:var(--chem)"></div></div></div>
            <div class="mini-bar-block"><div class="mini-bar-lbl"><span style="color:var(--math)">Math</span><span>${t.math_m}</span></div><div class="mini-bar-outer"><div class="mini-bar-fill" style="width:${pct(t.math_m,100)}%;background:var(--math)"></div></div></div>
          </div>`}
      </div>`;
    tl.appendChild(item);
  });

  /* ── IMPROVEMENT TRACKER ── */
  const first=attended[0],last=attended[attended.length-1];
  function impCard(lbl,val,sub,upGood=true){
    if(val===null)return`<div class="imp-card"><div class="imp-arrow" style="color:var(--muted)">—</div><div class="imp-label">${lbl}</div><div class="imp-val" style="color:var(--muted)">—</div><div class="imp-sub">${sub}</div></div>`;
    const pos=val>0,zero=val===0;
    const col=zero?'var(--muted)':((pos&&upGood)||(!pos&&!upGood))?'var(--green)':'var(--red)';
    return`<div class="imp-card"><div class="imp-arrow" style="color:${col}">${zero?'→':pos?'↑':'↓'}</div><div class="imp-label">${lbl}</div><div class="imp-val" style="color:${col}">${pos?'+':''}${val}</div><div class="imp-sub">${sub}</div></div>`;
  }
  const cons=scores.length>=2?Math.round(100-Math.sqrt(avg(scores.map(x=>(x-avg(scores))**2)))/avg(scores)*100):null;
  $('impGrid').innerHTML=
    impCard('Total Change',(first&&last&&first!==last)?last.total-first.total:null,'First → Last JUT')+
    impCard('Physics Trend',(first&&last&&first!==last)?last.phy_m-first.phy_m:null,'First → Last')+
    impCard('Chem Trend',(first&&last&&first!==last)?last.chem_m-first.chem_m:null,'First → Last')+
    impCard('Maths Trend',(first&&last&&first!==last)?last.math_m-first.math_m:null,'First → Last')+
    (cons!==null?`<div class="imp-card"><div class="imp-arrow" style="color:var(--accent2)">◎</div><div class="imp-label">Consistency</div><div class="imp-val" style="color:var(--accent2)">${cons}%</div><div class="imp-sub">Higher = stable</div></div>`:impCard('Consistency',null,''))+
    `<div class="imp-card"><div class="imp-arrow" style="color:var(--accent)">★</div><div class="imp-label">Attendance</div><div class="imp-val" style="color:var(--accent)">${attended.length}/${allTests.length}</div><div class="imp-sub">${Math.round(pct(attended.length,allTests.length))}% rate</div></div>`;

  /* ── CHARTS ── */
  // SHORT labels for x-axis — no rotation, no squashing
  const shortLabels=allTests.map(shortLabel);
  const dataPoints=perTest.map(t=>t.absent?null:t.total);
  const batchLine=perTest.map(t=>t.batchAvg);

  // Score progress
  // Set scroll widths proportional to number of JUTs
  const _jutCount=shortLabels.length;
  const _minW=Math.max(600, _jutCount*70);
  ['progressWrap','stackedWrap','accWrap','subjWrap','rankWrap'].forEach(id=>{
    const el=document.getElementById(id);
    if(el) el.style.minWidth=_minW+'px';
  });
  charts.prog=new Chart($('progressChart'),{
    type:'line',
    data:{labels:shortLabels,datasets:[
      {label:'Your Score',data:dataPoints,borderColor:'#e8c547',backgroundColor:'rgba(232,197,71,0.07)',borderWidth:2.5,pointRadius:6,pointBackgroundColor:dataPoints.map(v=>v===null?'transparent':'#e8c547'),tension:0.3,spanGaps:false},
      {label:'Batch Avg',data:batchLine,borderColor:'rgba(107,107,138,0.5)',borderDash:[6,4],borderWidth:1.5,pointRadius:3,tension:0.3},
    ]},
    options:{
      maintainAspectRatio:false,
      scales:{
        x:{grid:{color:'#1e1e2e'},ticks:{color:'#6b6b8a',maxRotation:0,font:{size:10}}},
        y:{grid:{color:'#1e1e2e'},ticks:{color:'#6b6b8a'},min:0}
      },
      plugins:{legend:{labels:{color:'#6b6b8a'}},tooltip:{callbacks:{label:ctx=>ctx.dataset.label+': '+(ctx.raw===null?'Absent':ctx.raw)}}}
    }
  });

  // Radar
  charts.radar=new Chart($('radarChart'),{
    type:'radar',
    data:{labels:['Physics','Chemistry','Maths'],datasets:[
      {label:'You (avg)',data:[phyA.toFixed(1),chemA.toFixed(1),mathA.toFixed(1)],borderColor:'#e8c547',backgroundColor:'rgba(232,197,71,0.1)',pointBackgroundColor:['#4fc3f7','#a78bfa','#fb923c'],pointRadius:6,borderWidth:2},
    ]},
    options:{maintainAspectRatio:false,scales:{r:{grid:{color:'#1e1e2e'},ticks:{display:false},pointLabels:{color:'#e8e8f0',font:{size:12}}}},plugins:{legend:{display:false}}}
  });

  // Stacked
  charts.stacked=new Chart($('stackedChart'),{
    type:'bar',
    data:{labels:shortLabels,datasets:[
      {label:'Correct',data:perTest.map(t=>t.absent?0:t.tot_c),backgroundColor:'#47e8c5bb',stack:'s'},
      {label:'Wrong',data:perTest.map(t=>t.absent?0:t.tot_w),backgroundColor:'#e847a0bb',stack:'s'},
      {label:'Unattempted',data:perTest.map(t=>t.absent?0:(75-t.tot_a)),backgroundColor:'#1e1e2e',stack:'s'},
      {label:'Absent',data:perTest.map(t=>t.absent?75:0),backgroundColor:'rgba(107,107,138,0.15)',stack:'s'},
    ]},
    options:{maintainAspectRatio:false,scales:{x:{ticks:{color:'#6b6b8a',maxRotation:0,font:{size:10}},grid:{color:'#1e1e2e'}},y:{ticks:{color:'#6b6b8a'},grid:{color:'#1e1e2e'},max:75,stacked:true}},plugins:{legend:{labels:{color:'#6b6b8a',font:{size:9}}}}}
  });

  // Accuracy
  charts.acc=new Chart($('accChart'),{
    type:'line',
    data:{labels:shortLabels,datasets:[{label:'Accuracy %',data:perTest.map(t=>t.absent?null:pct(t.tot_c,t.tot_a)),borderColor:'#e847a0',backgroundColor:'rgba(232,71,160,0.07)',borderWidth:2,pointRadius:5,tension:0.35,spanGaps:false,fill:true}]},
    options:{maintainAspectRatio:false,scales:{x:{ticks:{color:'#6b6b8a',maxRotation:0,font:{size:10}},grid:{color:'#1e1e2e'}},y:{ticks:{color:'#6b6b8a',callback:v=>v+'%'},grid:{color:'#1e1e2e'},min:0,max:100}},plugins:{legend:{display:false}}}
  });

  // Subject trends
  charts.subj=new Chart($('subjChart'),{
    type:'line',
    data:{labels:shortLabels,datasets:[
      {label:'Physics',data:perTest.map(t=>t.absent?null:t.phy_m),borderColor:'#4fc3f7',backgroundColor:'rgba(79,195,247,0.05)',borderWidth:2,tension:0.3,pointRadius:4,spanGaps:false},
      {label:'Chemistry',data:perTest.map(t=>t.absent?null:t.chem_m),borderColor:'#a78bfa',backgroundColor:'rgba(167,139,250,0.05)',borderWidth:2,tension:0.3,pointRadius:4,spanGaps:false},
      {label:'Maths',data:perTest.map(t=>t.absent?null:t.math_m),borderColor:'#fb923c',backgroundColor:'rgba(251,146,60,0.05)',borderWidth:2,tension:0.3,pointRadius:4,spanGaps:false},
    ]},
    options:{maintainAspectRatio:false,scales:{x:{ticks:{color:'#6b6b8a',maxRotation:0,font:{size:10}},grid:{color:'#1e1e2e'}},y:{ticks:{color:'#6b6b8a'},grid:{color:'#1e1e2e'},min:0}},plugins:{legend:{labels:{color:'#6b6b8a',font:{size:9}}}}}
  });

  // Rank chart
  charts.rank=new Chart($('rankChart'),{
    type:'bar',
    data:{labels:shortLabels,datasets:[{label:'Rank',data:perTest.map(t=>t.absent?null:t.rank),backgroundColor:perTest.map(t=>{if(t.absent||t.rank===null)return'transparent';const r=t.rank,bs=t.batchSize;const p=r/bs;return p<=0.1?'#47e8c5aa':p<=0.25?'#e8c547aa':p<=0.5?'#fb923caa':'#e847a0aa';}),borderRadius:3}]},
    options:{maintainAspectRatio:false,scales:{x:{ticks:{color:'#6b6b8a',maxRotation:0,font:{size:10}},grid:{color:'#1e1e2e'}},y:{ticks:{color:'#6b6b8a'},grid:{color:'#1e1e2e'},reverse:true,min:0}},plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>'Rank #'+(ctx.raw===null?'Absent':ctx.raw)}}}}
  });

  /* ── STRENGTHS / WEAKNESSES ── */
  const subjData=[
    {name:'Physics',avgMark:phyA,avgAcc:attended.length?avg(attended.map(t=>pct(t.phy_c,25))):0,color:'var(--phy)'},
    {name:'Chemistry',avgMark:chemA,avgAcc:attended.length?avg(attended.map(t=>pct(t.chem_c,25))):0,color:'var(--chem)'},
    {name:'Maths',avgMark:mathA,avgAcc:attended.length?avg(attended.map(t=>pct(t.math_c,25))):0,color:'var(--math)'},
  ];
  const sortedS=[...subjData].sort((a,b)=>b.avgMark-a.avgMark);
  const maxMark=Math.max(...subjData.map(s=>s.avgMark),1);
  function swBar(item){
    const p=(item.avgMark/maxMark*100).toFixed(1);
    return`<div class="sw-row"><div class="sw-name">${item.name}</div><div class="sw-outer"><div class="sw-inner" style="background:${item.color};width:0%" data-pct="${p}">${Math.round(item.avgMark)} marks</div></div><div class="sw-pct" style="color:${item.color}">${Math.round(item.avgAcc)}%</div></div>`;
  }
  $('swS').innerHTML=`<div class="sw-title">💪 Strengths</div>${sortedS.slice(0,2).map(swBar).join('')}<p style="font-size:0.58rem;color:var(--muted);margin-top:0.8rem;letter-spacing:0.1em;">Best: <span style="color:${sortedS[0].color}">${sortedS[0].name}</span> at avg ${sortedS[0].avgMark.toFixed(1)} marks</p>`;
  $('swW').innerHTML=`<div class="sw-title">🎯 Focus Areas</div>${[...sortedS].reverse().slice(0,2).map(swBar).join('')}<p style="font-size:0.58rem;color:var(--muted);margin-top:0.8rem;letter-spacing:0.1em;">Weakest: <span style="color:${sortedS[2].color}">${sortedS[2].name}</span> at avg ${sortedS[2].avgMark.toFixed(1)} marks</p>`;
  setTimeout(()=>{document.querySelectorAll('.sw-inner').forEach(b=>{b.style.width=b.dataset.pct+'%';});},600);

  /* ── HEATMAP ── */
  const hm=$('bigHm');hm.innerHTML='';
  hm.style.gridTemplateColumns=`100px repeat(${allTests.length},40px)`;
  const hmSubjs=[{name:'Physics',key:'phy_m',max:100,color:'79,195,247'},{name:'Chemistry',key:'chem_m',max:100,color:'167,139,250'},{name:'Maths',key:'math_m',max:100,color:'251,146,60'}];

  // Header row
  const hdr=document.createElement('div');hdr.style.cssText='font-size:0.5rem;color:var(--muted);display:flex;align-items:flex-end;';hdr.textContent='Subject';hm.appendChild(hdr);
  allTests.forEach((t,i)=>{
    const c=document.createElement('div');
    c.style.cssText='font-size:0.48rem;color:var(--muted);text-align:center;padding-bottom:4px;display:flex;align-items:flex-end;justify-content:center;line-height:1.3;';
    c.textContent=shortLabels[i];
    hm.appendChild(c);
  });
  hmSubjs.forEach(({name,key,max,color})=>{
    const rl=document.createElement('div');rl.style.cssText=`font-size:0.58rem;color:rgba(${color},0.9);display:flex;align-items:center;letter-spacing:0.08em;`;rl.textContent=name;hm.appendChild(rl);
    perTest.forEach(t=>{
      const val=t.absent?null:t[key];
      const cell=document.createElement('div');cell.className='hm-cell';
      if(val===null){cell.style.background='rgba(107,107,138,0.1)';cell.style.color='var(--muted)';cell.style.fontSize='0.4rem';cell.textContent='ABS';}
      else{const intensity=0.12+(val/max)*0.72;cell.style.background=`rgba(${color},${intensity})`;cell.textContent=val;}
      cell.innerHTML+=`<div class="hm-tip">${shortLabel(t.testName)}<br>${name}: ${val===null?'Absent':val+'/'+max}</div>`;
      hm.appendChild(cell);
    });
  });

  /* ── RANK TABLE ── */
  const tbody=$('rankBody');tbody.innerHTML='';
  perTest.forEach(t=>{
    const acc=t.absent?'—':pct(t.tot_c,t.tot_a)+'%';
    const diff=t.absent?null:t.total-t.batchAvg;
    const diffStr=t.absent?'—':(diff>=0?`<span style="color:var(--green)">+${diff}</span>`:`<span style="color:var(--red)">${diff}</span>`);
    const pctStr=t.absent?'—':(t.percentile!=null?`<span style="color:${t.percentile>=75?'var(--accent2)':t.percentile>=50?'var(--accent)':'var(--accent3)'}">${t.percentile}%</span>`:'—');
    const rankBadge=t.absent?'<span style="color:var(--muted)">ABS</span>':(t.rank===1?`<span class="rnk r1c">1</span>`:t.rank===2?`<span class="rnk r2c">2</span>`:t.rank===3?`<span class="rnk r3c">3</span>`:`<span class="rnk roc">${t.rank||'?'}</span>`);
    const sc=t.absent?'var(--muted)':t.total>=t.batchMax*0.8?'var(--accent2)':t.total>=t.batchAvg?'var(--accent)':'var(--accent3)';
    const tr=document.createElement('tr');tr.className='rr';
    tr.innerHTML=`
      <td style="font-family:'DM Serif Display',serif;font-size:0.78rem;">${shortLabel(t.testName)}</td>
      <td>${t.absent?`<span class="tl-badge b-abs">Absent</span>`:`<span class="tl-badge b-good">✓Present</span>`}</td>
      <td><span style="font-family:'Bebas Neue',sans-serif;font-size:1.4rem;color:${sc}">${t.absent?'—':t.total}</span></td>
      <td>${rankBadge}${!t.absent&&t.rank?`<span style="font-size:0.58rem;color:var(--muted)"> / ${t.batchSize}</span>`:''}</td>
      <td style="color:var(--muted)">${t.batchAvg}</td>
      <td>${diffStr}</td>
      <td>${pctStr}</td>
      <td style="color:${t.absent?'var(--muted)':pct(t.tot_c,t.tot_a)>=60?'var(--green)':'var(--accent3)'}">${acc}</td>`;
    tbody.appendChild(tr);
  });

  /* ── REVEAL ── */
  const io=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('vis');});},{threshold:0.06});
  document.querySelectorAll('.reveal,.tl-item').forEach(el=>{el.classList.remove('vis');io.observe(el);});
}

function nullEntry(){return{total:0,rank:null,percentile:0,phy_a:0,chem_a:0,math_a:0,tot_a:0,phy_c:0,chem_c:0,math_c:0,tot_c:0,phy_w:0,chem_w:0,math_w:0,tot_w:0,phy_m:0,chem_m:0,math_m:0};}

/* ── BOOT ── */
(async function boot(){
  const ov=$('selOverlay');ov.style.display='flex';ov.style.opacity='1';
  await loadSelector();
  const params=new URLSearchParams(window.location.search);
  const sp=params.get('student');
  if(sp){
    const matched=allStudents.find(n=>normName(n)===normName(sp));
    if(matched)await loadProfile(matched);
    else{$('selSearch').value=sp;$('selSearch').dispatchEvent(new Event('input'));}
  }
})();
</script>
</body>
</html>
"""


@app.get("/student")
def student_page():
    return app.response_class(INDIVIDUAL_HTML, mimetype='text/html')


OVERVIEW_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JUT · Master Overview</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@300;400;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
:root{
  --bg:#0a0a0f;--surface:#111118;--surface2:#16161f;--border:#1e1e2e;
  --accent:#e8c547;--accent2:#47e8c5;--accent3:#e847a0;
  --text:#e8e8f0;--muted:#6b6b8a;
  --phy:#4fc3f7;--chem:#a78bfa;--math:#fb923c;
  --gold:#fbbf24;--silver:#94a3b8;--bronze:#cd7f32;
  --green:#4ade80;--red:#f87171;
}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;overflow-x:hidden;}
body::after{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");pointer-events:none;z-index:9999;opacity:0.4;}


/* SCROLLABLE CHART CONTAINER */
.chart-scroll-outer{overflow-x:auto;overflow-y:hidden;}
.chart-scroll-outer::-webkit-scrollbar{height:3px;}
.chart-scroll-outer::-webkit-scrollbar-track{background:transparent;}
.chart-scroll-outer::-webkit-scrollbar-thumb{background:rgba(232,197,71,0.2);border-radius:2px;}
.chart-scroll-outer{scrollbar-width:thin;scrollbar-color:rgba(232,197,71,0.2) transparent;}
.chart-scroll-inner{position:relative;height:280px;min-width:600px;}
.chart-scroll-inner.tall{height:340px;}
.chart-scroll-inner.short{height:220px;}
/* min-width scales with number of data points */
.chart-scroll-inner canvas{position:absolute;inset:0;width:100%!important;height:100%!important;}


/* SCROLLABLE CHART CONTAINER */
.chart-scroll-outer{overflow-x:auto;overflow-y:hidden;}
.chart-scroll-outer::-webkit-scrollbar{height:3px;}
.chart-scroll-outer::-webkit-scrollbar-track{background:transparent;}
.chart-scroll-outer::-webkit-scrollbar-thumb{background:rgba(232,197,71,0.2);border-radius:2px;}
.chart-scroll-outer{scrollbar-width:thin;scrollbar-color:rgba(232,197,71,0.2) transparent;}
.chart-scroll-inner{position:relative;height:280px;min-width:600px;}
.chart-scroll-inner.tall{height:340px;}
.chart-scroll-inner.short{height:220px;}
/* min-width scales with number of data points */
.chart-scroll-inner canvas{position:absolute;inset:0;width:100%!important;height:100%!important;}

/* NAV */
.topnav{position:fixed;top:0;left:0;right:0;z-index:500;background:rgba(10,10,15,0.9);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0.9rem 2rem;gap:1rem;}
.topnav-logo{font-family:'Bebas Neue',sans-serif;font-size:1.4rem;letter-spacing:0.08em;color:var(--text);text-decoration:none;flex-shrink:0;}
.topnav-logo span{color:var(--accent);}
.topnav-links{display:flex;gap:1.2rem;align-items:center;}
.topnav-link{font-size:0.58rem;letter-spacing:0.22em;text-transform:uppercase;color:var(--muted);text-decoration:none;transition:color 0.2s;padding:0.3rem 0;}
.topnav-link:hover,.topnav-link.active{color:var(--accent);}
.topnav-link.active{border-bottom:1px solid var(--accent);}

/* HERO */
.hero{min-height:100vh;display:flex;flex-direction:column;justify-content:flex-end;padding:7rem 4rem 5rem;position:relative;overflow:hidden;}
.hero-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,0.018) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.018) 1px,transparent 1px);background-size:80px 80px;animation:gridDrift 40s linear infinite;}
@keyframes gridDrift{0%{background-position:0 0}100%{background-position:80px 80px}}
.hero-glow{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 70% 30%,rgba(232,197,71,0.07) 0%,transparent 60%),radial-gradient(ellipse 50% 50% at 10% 80%,rgba(71,232,197,0.05) 0%,transparent 60%);}
.hero-content{position:relative;z-index:5;}
.hero-eyebrow{font-size:0.62rem;letter-spacing:0.42em;color:var(--accent2);text-transform:uppercase;margin-bottom:1rem;opacity:0;animation:slideUp 0.6s 0.2s forwards;display:flex;align-items:center;gap:0.8rem;}
.hero-eyebrow::before{content:'';display:block;width:36px;height:1px;background:var(--accent2);}
.hero-title{font-family:'Bebas Neue',sans-serif;font-size:clamp(4rem,12vw,10rem);line-height:0.86;letter-spacing:0.02em;opacity:0;animation:slideUp 0.8s 0.35s forwards;}
.hero-title .outline{-webkit-text-stroke:1.5px var(--accent);color:transparent;display:block;}
.hero-sub{font-size:0.72rem;color:var(--muted);letter-spacing:0.18em;margin-top:1.5rem;opacity:0;animation:slideUp 0.7s 0.55s forwards;}
.hero-kpis{display:flex;gap:3rem;margin-top:3rem;opacity:0;animation:slideUp 0.7s 0.7s forwards;flex-wrap:wrap;}
.kpi-val{font-family:'Bebas Neue',sans-serif;font-size:3.5rem;color:var(--accent);line-height:1;}
.kpi-label{font-size:0.52rem;letter-spacing:0.28em;color:var(--muted);text-transform:uppercase;margin-top:0.2rem;}
@keyframes slideUp{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:translateY(0)}}

/* JUT SELECTOR BAR */
.jut-bar{position:sticky;top:57px;z-index:400;background:rgba(10,10,15,0.95);backdrop-filter:blur(16px);border-bottom:1px solid var(--border);padding:0.7rem 2rem;display:flex;gap:0.5rem;overflow-x:auto;align-items:center;}
.jut-tab{font-size:0.58rem;letter-spacing:0.18em;text-transform:uppercase;padding:0.4rem 1rem;border:1px solid var(--border);border-radius:2px;cursor:pointer;background:transparent;color:var(--muted);font-family:'JetBrains Mono',monospace;transition:all 0.2s;white-space:nowrap;flex-shrink:0;}
.jut-tab:hover{border-color:var(--accent);color:var(--accent);}
.jut-tab.active{background:var(--accent);color:var(--bg);border-color:var(--accent);}
.jut-bar-label{font-size:0.55rem;letter-spacing:0.2em;color:var(--muted);text-transform:uppercase;flex-shrink:0;margin-right:0.5rem;}

/* LAYOUT */
.main-wrap{max-width:1600px;margin:0 auto;padding:0 2.5rem 6rem;}
section{padding:4rem 0;}
.sec-label{font-size:0.6rem;letter-spacing:0.42em;color:var(--accent);text-transform:uppercase;margin-bottom:0.7rem;display:flex;align-items:center;gap:0.8rem;}
.sec-label::before{content:'';display:block;width:28px;height:1px;background:var(--accent);}
.sec-title{font-family:'DM Serif Display',serif;font-size:clamp(1.8rem,4vw,2.8rem);margin-bottom:2rem;}
.divider{height:1px;background:linear-gradient(90deg,transparent,var(--border) 20%,var(--border) 80%,transparent);}
.reveal{opacity:0;transform:translateY(24px);transition:opacity 0.6s,transform 0.6s;}
.reveal.vis{opacity:1;transform:translateY(0);}

/* STAT STRIP */
.stat-strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1px;background:var(--border);border:1px solid var(--border);border-radius:4px;overflow:hidden;margin-bottom:3rem;}
.ss-item{background:var(--surface);padding:1.5rem;text-align:center;}
.ss-val{font-family:'Bebas Neue',sans-serif;font-size:2.5rem;color:var(--accent);line-height:1;}
.ss-label{font-size:0.52rem;letter-spacing:0.22em;color:var(--muted);text-transform:uppercase;margin-top:0.3rem;}

/* PODIUM */
.podium-wrap{display:flex;align-items:flex-end;justify-content:center;gap:0;margin:2rem 0 1rem;}
.pod-card{flex:1;max-width:280px;text-align:center;cursor:pointer;transition:transform 0.3s;text-decoration:none;display:block;}
.pod-card:hover{transform:translateY(-8px);}
.pod-name{font-family:'DM Serif Display',serif;font-size:1rem;margin-bottom:0.25rem;color:var(--text);}
.pod-score{font-family:'Bebas Neue',sans-serif;font-size:3.2rem;line-height:1;}
.pod-sub{font-size:0.55rem;letter-spacing:0.18em;color:var(--muted);text-transform:uppercase;margin-top:0.2rem;}
.pod-block{margin-top:0.8rem;border-radius:4px 4px 0 0;display:flex;align-items:center;justify-content:center;font-size:2rem;}
.pod-1 .pod-score{color:var(--gold);}
.pod-1 .pod-block{background:linear-gradient(135deg,#fbbf24,#f59e0b);height:150px;}
.pod-2 .pod-score{color:var(--silver);}
.pod-2 .pod-block{background:linear-gradient(135deg,#94a3b8,#64748b);height:115px;}
.pod-3 .pod-score{color:var(--bronze);}
.pod-3 .pod-block{background:linear-gradient(135deg,#cd7f32,#a0632a);height:88px;}

/* LEADERBOARD */
.lb-controls{display:flex;gap:0.8rem;margin-bottom:1.2rem;flex-wrap:wrap;align-items:center;}
.lb-search{background:var(--surface);border:1px solid var(--border);color:var(--text);padding:0.6rem 1rem;font-family:'JetBrains Mono',monospace;font-size:0.72rem;border-radius:2px;outline:none;flex:1;min-width:180px;transition:border-color 0.2s;}
.lb-search:focus{border-color:var(--accent);}
.lb-search::placeholder{color:var(--muted);}
.sort-btn{background:var(--surface);border:1px solid var(--border);color:var(--muted);padding:0.5rem 0.9rem;font-family:'JetBrains Mono',monospace;font-size:0.58rem;letter-spacing:0.12em;text-transform:uppercase;cursor:pointer;border-radius:2px;transition:all 0.2s;white-space:nowrap;}
.sort-btn:hover,.sort-btn.active{border-color:var(--accent);color:var(--accent);}
.lb-table{width:100%;border-collapse:separate;border-spacing:0 3px;}
.lb-table th{font-size:0.55rem;letter-spacing:0.2em;color:var(--muted);text-transform:uppercase;padding:0.4rem 0.8rem;text-align:left;font-weight:400;}
.lb-table tr.lbr{background:var(--surface);transition:all 0.2s;cursor:pointer;}
.lb-table tr.lbr:hover{background:var(--surface2);transform:translateX(4px);}
.lb-table td{padding:0.65rem 0.8rem;font-size:0.7rem;border-top:1px solid transparent;border-bottom:1px solid transparent;}
.lb-table tr.lbr:hover td{border-color:var(--border);}
.lb-table tr.lbr.top1{background:rgba(251,191,36,0.06);}
.lb-table tr.lbr.top3{background:rgba(232,197,71,0.04);}
.lb-table tr.lbr.top10{background:rgba(71,232,197,0.03);}
.rnk{font-family:'Bebas Neue',sans-serif;font-size:1.4rem;}
.r1{color:var(--gold);}.r2{color:var(--silver);}.r3{color:var(--bronze);}.rn{color:var(--muted);}
.name-link{color:var(--text);text-decoration:none;border-bottom:1px dashed var(--muted);font-family:'DM Serif Display',serif;font-size:0.88rem;transition:color 0.2s,border-color 0.2s;}
.name-link:hover{color:var(--accent);border-color:var(--accent);}
.score-chip{display:inline-block;padding:0.18rem 0.7rem;border-radius:2px;font-family:'Bebas Neue',sans-serif;font-size:1.2rem;}
.mini-bars{display:flex;gap:2px;align-items:center;}
.mini-bar{height:5px;border-radius:1px;}
.trend-up{color:var(--green);font-size:0.65rem;}
.trend-dn{color:var(--red);font-size:0.65rem;}
.trend-fl{color:var(--muted);font-size:0.65rem;}

/* TIER ROWS */
.tier-s{background:rgba(71,232,197,0.06)!important;}
.tier-a{background:rgba(232,197,71,0.05)!important;}
.tier-b{background:rgba(251,146,60,0.04)!important;}
.tier-c{background:rgba(232,71,160,0.03)!important;}

/* CHARTS */
.charts-2{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-top:1.5rem;}
.charts-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.5rem;margin-top:1.5rem;}
.chart-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.8rem;position:relative;overflow:hidden;}
.chart-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--accent),var(--accent2));}
.chart-card.full{grid-column:1/-1;}
.chart-title{font-size:0.58rem;letter-spacing:0.26em;color:var(--muted);text-transform:uppercase;margin-bottom:1.2rem;}
.chart-wrap{position:relative;height:280px;}
.chart-wrap.tall{height:340px;}
.chart-wrap.short{height:220px;}
.chart-card canvas{position:absolute;inset:0;width:100%!important;height:100%!important;}

/* SUBJECT CARDS */
.subj-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2rem;margin-top:1.5rem;}
.subj-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.8rem;position:relative;overflow:hidden;}
.subj-card.phy{border-top:3px solid var(--phy);}
.subj-card.chem{border-top:3px solid var(--chem);}
.subj-card.math{border-top:3px solid var(--math);}
.subj-name{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;margin-bottom:1rem;}
.subj-card.phy .subj-name{color:var(--phy);}
.subj-card.chem .subj-name{color:var(--chem);}
.subj-card.math .subj-name{color:var(--math);}
.subj-row{display:flex;justify-content:space-between;padding:0.38rem 0;border-bottom:1px solid var(--border);font-size:0.68rem;}
.subj-row:last-child{border-bottom:none;}
.subj-key{color:var(--muted);}
.subj-val{color:var(--text);font-weight:600;}

/* CONSISTENCY TABLE */
.cons-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;margin-top:1.5rem;}
.cons-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.4rem;display:flex;align-items:center;gap:1rem;cursor:pointer;text-decoration:none;transition:transform 0.25s,border-color 0.25s;}
.cons-card:hover{transform:translateY(-3px);border-color:rgba(232,197,71,0.4);}
.cons-rank{font-family:'Bebas Neue',sans-serif;font-size:2rem;width:36px;text-align:center;flex-shrink:0;}
.cons-info{flex:1;min-width:0;}
.cons-name{font-family:'DM Serif Display',serif;font-size:0.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:0.2rem;}
.cons-bar-outer{height:4px;background:var(--border);border-radius:2px;overflow:hidden;margin-top:0.4rem;}
.cons-bar-inner{height:100%;border-radius:2px;transition:width 1.5s cubic-bezier(0.4,0,0.2,1);}
.cons-score{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;flex-shrink:0;}

/* DIST BARS */
.dist-wrap{margin-top:1.2rem;}
.dist-row{display:flex;align-items:center;gap:0.8rem;margin-bottom:0.6rem;}
.dist-lbl{font-size:0.6rem;color:var(--muted);width:70px;flex-shrink:0;letter-spacing:0.08em;}
.dist-outer{flex:1;height:26px;background:var(--border);border-radius:2px;overflow:hidden;}
.dist-inner{height:100%;border-radius:2px;display:flex;align-items:center;padding-left:8px;font-size:0.6rem;font-weight:600;color:rgba(0,0,0,0.7);transition:width 1.5s cubic-bezier(0.4,0,0.2,1);}
.dist-cnt{font-size:0.68rem;color:var(--muted);width:22px;text-align:right;flex-shrink:0;}

/* JUT TREND TABLE */
.jut-trend-table{width:100%;border-collapse:separate;border-spacing:0 3px;margin-top:1.2rem;}
.jut-trend-table th{font-size:0.52rem;letter-spacing:0.2em;color:var(--muted);text-transform:uppercase;padding:0.35rem 0.7rem;text-align:left;font-weight:400;}
.jut-trend-table tr.jtr{background:var(--surface);transition:all 0.18s;}
.jut-trend-table tr.jtr:hover{background:var(--surface2);}
.jut-trend-table td{padding:0.6rem 0.7rem;font-size:0.68rem;}


/* INSTITUTION CHIP */
.inst-chip{display:inline-block;font-size:0.5rem;letter-spacing:0.15em;padding:0.18rem 0.5rem;border-radius:2px;font-weight:600;text-transform:uppercase;flex-shrink:0;}
.inst-kjs{background:rgba(79,195,247,0.15);color:#4fc3f7;}
.inst-mjs{background:rgba(167,139,250,0.15);color:#a78bfa;}
.inst-ujs{background:rgba(251,146,60,0.15);color:#fb923c;}
.inst-unk{background:rgba(107,107,138,0.1);color:var(--muted);}

/* LOADING */
.loading-screen{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:60vh;gap:1rem;}
.loading-dots{display:flex;gap:6px;}
.ld{width:8px;height:8px;border-radius:50%;background:var(--accent);animation:blink 1.2s infinite;}
.ld:nth-child(2){animation-delay:0.2s;}
.ld:nth-child(3){animation-delay:0.4s;}
@keyframes blink{0%,100%{opacity:0.15}50%{opacity:1}}
.loading-text{font-size:0.65rem;letter-spacing:0.3em;color:var(--muted);text-transform:uppercase;}

@media(max-width:1024px){.charts-3{grid-template-columns:1fr 1fr;}.subj-cards{grid-template-columns:1fr 1fr 1fr;}}
@media(max-width:768px){
  .hero{padding:7rem 1.5rem 4rem;}
  .charts-2,.charts-3{grid-template-columns:1fr;}
  .subj-cards{grid-template-columns:1fr;}
  .main-wrap{padding:0 1.2rem 4rem;}
  .hero-kpis{gap:1.5rem;}
  .topnav-links .topnav-link:not(.always){display:none;}
}
</style>
</head>
<body>

<nav class="topnav">
  <a class="topnav-logo" href="/">JUT<span>·</span>HUB</a>
  <div class="topnav-links">
    <a class="topnav-link always" href="/">Home</a>
    <a class="topnav-link" href="/analysis">Per-Test</a>
    <a class="topnav-link active always" href="/overview">Overview</a>
    <a class="topnav-link" href="/student">Student</a>
  </div>
</nav>

<!-- HERO -->
<div class="hero">
  <div class="hero-glow"></div>
  <div class="hero-grid"></div>
  <div class="hero-content">
    <div class="hero-eyebrow">JUT · Master Analytics</div>
    <div class="hero-title">BATCH<br><span class="outline">OVERVIEW</span></div>
    <div class="hero-sub" id="heroSub">Loading all JUT data…</div>
    <div class="hero-kpis">
      <div><div class="kpi-val" id="kpiStudents">—</div><div class="kpi-label">Students</div></div>
      <div><div class="kpi-val" id="kpiJuts">—</div><div class="kpi-label">JUTs</div></div>
      <div><div class="kpi-val" id="kpiBatchAvg">—</div><div class="kpi-label">Overall Avg</div></div>
      <div><div class="kpi-val" id="kpiTopScore">—</div><div class="kpi-label">Highest Ever</div></div>
    </div>
  </div>
</div>

<!-- JUT FILTER BAR -->
<div class="jut-bar" id="jutBar">
  <span class="jut-bar-label">Filter:</span>
  <button class="jut-tab active" data-jut="ALL">All JUTs</button>
</div>

<!-- LOADING -->
<div class="main-wrap" id="mainWrap" style="display:none;">

<section>
  <div class="stat-strip reveal" id="statStrip"></div>

  <!-- PODIUM -->
  <div class="sec-label reveal">All-Time Top 3</div>
  <div class="sec-title reveal">Overall Podium</div>
  <div class="podium-wrap reveal" id="podium"></div>
</section>

<div class="divider"></div>

<!-- LEADERBOARD -->
<section>
  <div class="sec-label reveal">Ranked by Average Score</div>
  <div class="sec-title reveal">Master Leaderboard</div>
  <div class="lb-controls reveal">
    <input class="lb-search" id="lbSearch" type="text" placeholder="Search student…" autocomplete="off">
    <button class="sort-btn active" data-sort="avg">Avg ↕</button>
    <button class="sort-btn" data-sort="best">Best ↕</button>
    <button class="sort-btn" data-sort="phy">Physics ↕</button>
    <button class="sort-btn" data-sort="chem">Chem ↕</button>
    <button class="sort-btn" data-sort="math">Maths ↕</button>
    <button class="sort-btn" data-sort="acc">Accuracy ↕</button>
    <button class="sort-btn" data-sort="cons">Consistency ↕</button>
    <button class="sort-btn" data-sort="att">Attendance ↕</button>
  </div>
  <div class="reveal" style="overflow-x:auto;">
    <table class="lb-table">
      <thead><tr>
        <th>#</th><th>Student</th><th>Inst</th><th>Avg Score</th><th>Best</th>
        <th>Subjects (avg P·C·M)</th><th>Avg Acc</th><th>Consistency</th><th>Trend</th><th>Attended</th>
      </tr></thead>
      <tbody id="lbBody"></tbody>
    </table>
  </div>
</section>

<div class="divider"></div>

<!-- SUBJECT DEEP DIVE -->
<section>
  <div class="sec-label reveal">Subject Analysis</div>
  <div class="sec-title reveal">Batch Subject Stats</div>
  <div class="subj-cards">
    <div class="subj-card phy reveal" id="sPhysics"></div>
    <div class="subj-card chem reveal" id="sChem"></div>
    <div class="subj-card math reveal" id="sMath"></div>
  </div>
</section>

<div class="divider"></div>

<!-- CHARTS -->
<section>
  <div class="sec-label reveal">Visual Analytics</div>
  <div class="sec-title reveal">Batch Intelligence</div>
  <div class="charts-2">
    <div class="chart-card full reveal">
      <div class="chart-title">Batch Average Score per JUT</div>
      <div class="chart-scroll-outer"><div class="chart-scroll-inner short" id="batchTrendWrap"><canvas id="chartBatchTrend"></canvas></div></div>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Score Distribution (selected JUT / all)</div>
      <div class="dist-wrap" id="distWrap"></div>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Subject Avg Comparison (selected JUT / all)</div>
      <div class="chart-wrap"><canvas id="chartRadar"></canvas></div>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Top 15 Students — Avg Score</div>
      <div class="chart-wrap tall"><canvas id="chartTopBar"></canvas></div>
    </div>
    <div class="chart-card reveal">
      <div class="chart-title">Accuracy Distribution across Students</div>
      <div class="chart-wrap"><canvas id="chartAccDist"></canvas></div>
    </div>
  </div>
</section>

<div class="divider"></div>

<!-- JUT SUMMARY TABLE -->
<section>
  <div class="sec-label reveal">Test-by-Test Summary</div>
  <div class="sec-title reveal">JUT Performance Table</div>
  <div class="reveal" style="overflow-x:auto;">
    <table class="jut-trend-table">
      <thead><tr>
        <th>JUT</th><th>Students</th><th>Avg Score</th><th>Top Score</th><th>Lowest</th>
        <th>Avg Physics</th><th>Avg Chem</th><th>Avg Maths</th><th>Avg Accuracy</th>
      </tr></thead>
      <tbody id="jutSummaryBody"></tbody>
    </table>
  </div>
</section>

<div class="divider"></div>

<!-- CONSISTENCY RANKINGS -->
<section>
  <div class="sec-label reveal">Reliability Index</div>
  <div class="sec-title reveal">Most Consistent Students</div>
  <p class="reveal" style="font-size:0.62rem;color:var(--muted);letter-spacing:0.12em;margin-bottom:1.5rem;">Consistency = low variance relative to personal average. Min 3 JUTs required.</p>
  <div class="cons-grid reveal" id="consGrid"></div>
</section>

</div><!-- /main-wrap -->

<div id="loadingScreen" class="loading-screen main-wrap" style="max-width:1600px;margin:0 auto;padding:0 2.5rem;">
  <div class="loading-dots"><div class="ld"></div><div class="ld"></div><div class="ld"></div></div>
  <div class="loading-text">Loading master data…</div>
</div>

<footer style="text-align:center;padding:2rem;color:var(--muted);font-size:0.58rem;letter-spacing:0.18em;border-top:1px solid var(--border);" id="footerEl">JUT MASTER OVERVIEW</footer>

<script>
/* ── utils ── */
const $ = id => document.getElementById(id);
const n = v => parseFloat(v)||0;
const pct = (a,b) => b>0?Math.round(a/b*100):0;
const avg = arr => arr.length?arr.reduce((a,b)=>a+b,0)/arr.length:0;
const rnd = v => Math.round(v*10)/10;
Chart.defaults.font.family='JetBrains Mono';
Chart.defaults.color='#6b6b8a';

function normName(s){return s.trim().replace(/\s+/g,' ').toUpperCase();}
function shortLabel(s){
  s=s.replace(/_/g,' ').trim();
  const m=s.match(/(\d+)\s*$/);
  if(m){const kws=['JUT','JEE','TEST','EXAM'];for(const k of kws){if(s.toUpperCase().includes(k))return k+' '+m[1];}return '#'+m[1];}
  return s.length>12?s.slice(0,12)+'…':s;
}

function getInstitution(fileVal){
  if(!fileVal) return '';
  const f=fileVal.trim().toUpperCase();
  if(f.startsWith('K')) return 'KJS';
  if(f.startsWith('U')) return 'UJS';
  if(f.startsWith('M')) return 'MJS';
  return '';
}
function mapRow(r){
  const g=(...ks)=>{for(const k of ks){if(r[k]!==undefined&&r[k]!=='')return r[k];}return'0';};
  const gs=(...ks)=>{for(const k of ks){if(r[k]!==undefined&&r[k]!=='')return r[k];}return'';};
  const fileVal=gs('file','filename');
  return{
    name:normName(gs('name')||'Unknown'),
    test:gs('test','test_name','jut','jut_name')||'Unknown',
    inst:getInstitution(fileVal),
    total:n(g('total_marks','total_score','total')),
    tot_a:n(g('total_attempt')),
    tot_c:n(g('total_correct')),
    tot_w:n(g('total_wrong')),
    phy_m:n(g('phy_marks','physics_marks')),
    chem_m:n(g('chem_marks','chemistry_marks')),
    math_m:n(g('math_marks','maths_marks')),
    phy_c:n(g('phy_correct','physics_correct')),
    chem_c:n(g('chem_correct','chemistry_correct')),
    math_c:n(g('math_correct','maths_correct')),
  };
}

let charts={};
function destroyChart(id){if(charts[id]){try{charts[id].destroy();}catch(e){}delete charts[id];}}

/* ── data model ── */
let allRows=[], allTests=[], allStudentNames=[];
let studentMap={};  // normName → {name, rows[], stats}
let testMap={};     // testName → rows[]
let activeJut='ALL';

/* ── build student stats ── */
function buildStudentStats(rows){
  const attended=rows.filter(r=>r.total>0||r.tot_a>0);
  const scores=attended.map(r=>r.total);
  const avgScore=scores.length?avg(scores):0;
  const bestScore=scores.length?Math.max(...scores):0;
  const avgPhy=attended.length?avg(attended.map(r=>r.phy_m)):0;
  const avgChem=attended.length?avg(attended.map(r=>r.chem_m)):0;
  const avgMath=attended.length?avg(attended.map(r=>r.math_m)):0;
  const avgAcc=attended.length?avg(attended.map(r=>pct(r.tot_c,r.tot_a))):0;
  let consistency=null;
  if(scores.length>=3){
    const mn=avg(scores),sd=Math.sqrt(avg(scores.map(x=>(x-mn)**2)));
    consistency=mn>0?Math.max(0,Math.round(100-sd/mn*100)):0;
  }
  // trend: slope of linear regression on scores
  let trend=0;
  if(scores.length>=2){
    const xs=scores.map((_,i)=>i),ym=avg(scores),xm=avg(xs);
    const num=xs.reduce((s,x,i)=>s+(x-xm)*(scores[i]-ym),0);
    const den=xs.reduce((s,x)=>s+(x-xm)**2,0);
    trend=den?num/den:0;
  }
  return{avgScore,bestScore,avgPhy,avgChem,avgMath,avgAcc,consistency,trend,attended:attended.length,total:rows.length};
}

/* ── fetch & build ── */
async function loadData(){
  try{
    const res=await fetch('/api/master-data');
    if(!res.ok)throw new Error('HTTP '+res.status);
    const raw=await res.json();
    allRows=raw.map(mapRow);

    // group by test
    allRows.forEach(r=>{
      if(!testMap[r.test])testMap[r.test]=[];
      testMap[r.test].push(r);
    });
    allTests=Object.keys(testMap).sort();

    // group by student
    allRows.forEach(r=>{
      const k=r.name;
      if(!studentMap[k])studentMap[k]={name:r.name,rows:[],inst:r.inst||''};
      studentMap[k].rows.push(r);
      // keep inst if not already set
      if(!studentMap[k].inst && r.inst) studentMap[k].inst=r.inst;
    });
    // compute stats for each student
    Object.values(studentMap).forEach(s=>{s.stats=buildStudentStats(s.rows);});
    allStudentNames=Object.keys(studentMap).sort();

    // wire the static All JUTs button
    const allBtn=document.querySelector('.jut-tab[data-jut="ALL"]');
    if(allBtn) allBtn.addEventListener('click',()=>setActiveJut('ALL'));
    // populate JUT tabs
    const bar=$('jutBar');
    allTests.forEach(t=>{
      const btn=document.createElement('button');
      btn.className='jut-tab';btn.dataset.jut=t;
      btn.textContent=shortLabel(t);
      btn.addEventListener('click',()=>setActiveJut(t));
      bar.appendChild(btn);
    });

    // hero KPIs
    const allAttended=Object.values(studentMap).flatMap(s=>s.rows.filter(r=>r.total>0||r.tot_a>0));
    const allScores=allAttended.map(r=>r.total);
    $('kpiStudents').textContent=allStudentNames.length;
    $('kpiJuts').textContent=allTests.length;
    $('kpiBatchAvg').textContent=allScores.length?Math.round(avg(allScores)):'—';
    $('kpiTopScore').textContent=allScores.length?Math.max(...allScores):'—';
    $('heroSub').textContent=allStudentNames.length+' STUDENTS · '+allTests.length+' JUTs · PHYSICS · CHEMISTRY · MATHEMATICS';
    $('footerEl').textContent='JUT MASTER OVERVIEW · '+allStudentNames.length+' STUDENTS · '+allTests.length+' JUTs';
    document.title='JUT · Batch Overview';

    $('loadingScreen').style.display='none';
    $('mainWrap').style.display='block';

    buildAll('ALL');
    initReveal();

  }catch(e){
    $('loadingScreen').innerHTML=`<div style="color:var(--accent3);font-size:0.75rem;letter-spacing:0.2em;text-align:center;">Error loading data:<br>${e.message}</div>`;
  }
}

function setActiveJut(jut){
  activeJut=jut;
  document.querySelectorAll('.jut-tab').forEach(b=>{b.classList.toggle('active',b.dataset.jut===jut);});
  buildAll(jut);
}

/* ── MAIN BUILD ── */
function buildAll(jut){
  const rows=(jut==='ALL')?allRows:allRows.filter(r=>r.test===jut);
  const attended=rows.filter(r=>r.total>0||r.tot_a>0);

  buildStatStrip(jut,attended);
  buildPodium(jut);
  buildLeaderboard(jut);
  buildSubjectCards(attended);
  buildCharts(jut,attended);
  buildJutSummary();
  buildConsistency();
}

/* ── STAT STRIP ── */
function buildStatStrip(jut,attended){
  const scores=attended.map(r=>r.total);
  const batchAvg=scores.length?Math.round(avg(scores)):0;
  const topScore=scores.length?Math.max(...scores):0;
  const lowScore=scores.length?Math.min(...scores):0;
  const above=scores.filter(s=>s>batchAvg).length;
  const avgAcc=attended.length?Math.round(avg(attended.map(r=>pct(r.tot_c,r.tot_a)))):0;
  const phyAvg=attended.length?Math.round(avg(attended.map(r=>r.phy_m))):0;
  const chemAvg=attended.length?Math.round(avg(attended.map(r=>r.chem_m))):0;
  const mathAvg=attended.length?Math.round(avg(attended.map(r=>r.math_m))):0;
  $('statStrip').innerHTML=[
    {v:new Set(attended.map(r=>r.name)).size,l:'Students'},
    {v:batchAvg,l:'Batch Avg'},
    {v:topScore,l:'Top Score'},
    {v:lowScore,l:'Lowest'},
    {v:above,l:'Above Avg'},
    {v:avgAcc+'%',l:'Avg Accuracy'},
    {v:phyAvg,l:'Avg Physics'},
    {v:chemAvg,l:'Avg Chem'},
    {v:mathAvg,l:'Avg Maths'},
  ].map(({v,l})=>`<div class="ss-item"><div class="ss-val">${v}</div><div class="ss-label">${l}</div></div>`).join('');
}

/* ── PODIUM ── */
function buildPodium(jut){
  // Rank students: if specific JUT, by score in that JUT; if ALL, by avg score
  let ranked;
  if(jut==='ALL'){
    ranked=Object.values(studentMap)
      .filter(s=>s.stats.attended>=1)
      .sort((a,b)=>b.stats.avgScore-a.stats.avgScore)
      .slice(0,3);
  } else {
    const jutRows=testMap[jut]||[];
    const byStudent={};
    jutRows.filter(r=>r.total>0||r.tot_a>0).forEach(r=>{byStudent[r.name]=r;});
    ranked=Object.values(byStudent)
      .sort((a,b)=>b.total-a.total)
      .slice(0,3)
      .map(r=>({name:r.name,score:r.total,label:jut==='ALL'?r.total.toFixed(0):r.total}));
  }
  const pod=$('podium');pod.innerHTML='';
  if(!ranked.length){pod.innerHTML='<div style="color:var(--muted);font-size:0.7rem;letter-spacing:0.2em;text-align:center;padding:2rem;">No data</div>';return;}
  const order=[ranked[1],ranked[0],ranked[2]].filter(Boolean);
  const classes=['pod-2','pod-1','pod-3'];
  const heights=[115,150,88];
  const colors=['var(--silver)','var(--gold)','var(--bronze)'];
  const bgs=['linear-gradient(135deg,#94a3b8,#64748b)','linear-gradient(135deg,#fbbf24,#f59e0b)','linear-gradient(135deg,#cd7f32,#a0632a)'];
  const medals=['\u{1F948}','\u{1F947}','\u{1F949}'];
  order.forEach((s,i)=>{
    const score=jut==='ALL'?Math.round(s.stats.avgScore):(s.score||s.total||0);
    const subLabel=jut==='ALL'?`avg · best: ${s.stats.bestScore}`:`score in ${shortLabel(jut)}`;
    const card=document.createElement('a');
    card.className=`pod-card ${classes[i]}`;
    card.href=`/student?student=${encodeURIComponent(s.name)}`;
    card.innerHTML=`
      <div class="pod-name">${s.name}</div>
      <div class="pod-score" style="color:${colors[i]}">${score}</div>
      <div class="pod-sub">${subLabel}</div>
      <div class="pod-block" style="height:${heights[i]}px;background:${bgs[i]}">${medals[i]}</div>`;
    pod.appendChild(card);
  });
}

/* ── LEADERBOARD ── */
let lbData=[], lbSort='avg', lbDir=-1, lbFilter='';

function buildLeaderboard(jut){
  // Build per-student data for the selected JUT context
  if(jut==='ALL'){
    lbData=Object.values(studentMap).map(s=>({
      name:s.name,
      inst:s.inst||'',
      avg:s.stats.avgScore,
      best:s.stats.bestScore,
      phy:s.stats.avgPhy,
      chem:s.stats.avgChem,
      math:s.stats.avgMath,
      acc:s.stats.avgAcc,
      cons:s.stats.consistency,
      trend:s.stats.trend,
      att:s.stats.attended,
      total:s.stats.total,
    }));
  } else {
    const jutRows=testMap[jut]||[];
    const byStudent={};
    jutRows.filter(r=>r.total>0||r.tot_a>0).forEach(r=>{
      byStudent[r.name]={
        name:r.name,inst:r.inst||studentMap[r.name]?.inst||'',avg:r.total,best:r.total,
        phy:r.phy_m,chem:r.chem_m,math:r.math_m,
        acc:pct(r.tot_c,r.tot_a),cons:null,trend:0,att:1,total:1,
      };
    });
    lbData=Object.values(byStudent);
  }
  renderLeaderboard();
}

function renderLeaderboard(){
  let data=[...lbData];
  if(lbFilter)data=data.filter(s=>s.name.includes(lbFilter.toUpperCase()));
  const sortKey={avg:'avg',best:'best',phy:'phy',chem:'chem',math:'math',acc:'acc',cons:'cons',att:'att'};
  data.sort((a,b)=>{
    const av=a[sortKey[lbSort]]??-1,bv=b[sortKey[lbSort]]??-1;
    return lbDir*(av-bv);
  });
  // assign display ranks by avg (or score)
  const ranked=[...lbData].sort((a,b)=>b.avg-a.avg);
  const rankMap={};ranked.forEach((s,i)=>{rankMap[s.name]=i+1;});
  const maxAvg=ranked.length?ranked[0].avg:300;

  const tbody=$('lbBody');tbody.innerHTML='';
  data.forEach((s)=>{
    const r=rankMap[s.name]||'—';
    const rc=r===1?'r1':r===2?'r2':r===3?'r3':'rn';
    const sc=s.avg>=maxAvg*0.8?'var(--accent2)':s.avg>=maxAvg*0.6?'var(--accent)':s.avg>=maxAvg*0.4?'var(--math)':'var(--accent3)';
    const tierClass=r===1?'top1':r<=3?'top3':r<=10?'top10':'';
    const trendStr=s.trend>1?`<span class="trend-up">↑ ${s.trend.toFixed(1)}/test</span>`:s.trend<-1?`<span class="trend-dn">↓ ${Math.abs(s.trend).toFixed(1)}/test</span>`:`<span class="trend-fl">→ stable</span>`;
    const consStr=s.cons!==null?s.cons+'%':'—';
    const consColor=s.cons===null?'var(--muted)':s.cons>=70?'var(--green)':s.cons>=50?'var(--accent)':'var(--accent3)';
    const phyW=(s.phy/100*80).toFixed(0),chemW=(s.chem/100*80).toFixed(0),mathW=(s.math/100*80).toFixed(0);
    const instKey=(s.inst||'').toLowerCase();
    const instCls=instKey==='kjs'?'inst-kjs':instKey==='mjs'?'inst-mjs':instKey==='ujs'?'inst-ujs':'inst-unk';
    const tr=document.createElement('tr');tr.className=`lbr ${tierClass}`;
    tr.innerHTML=`
      <td><span class="rnk ${rc}">${r}</span></td>
      <td><a class="name-link" href="/student?student=${encodeURIComponent(s.name)}">${s.name}</a></td>
      <td>${s.inst?`<span class="inst-chip ${instCls}">${s.inst}</span>`:''}</td>
      <td><span class="score-chip" style="background:${sc}22;color:${sc}">${Math.round(s.avg)}</span></td>
      <td style="color:var(--accent);font-family:'Bebas Neue',sans-serif;font-size:1.2rem;">${s.best}</td>
      <td>
        <div class="mini-bars">
          <div class="mini-bar" style="width:${phyW}px;background:var(--phy)"></div>
          <div class="mini-bar" style="width:${chemW}px;background:var(--chem)"></div>
          <div class="mini-bar" style="width:${mathW}px;background:var(--math)"></div>
        </div>
        <div style="font-size:0.57rem;color:var(--muted);margin-top:2px;">P:${Math.round(s.phy)} · C:${Math.round(s.chem)} · M:${Math.round(s.math)}</div>
      </td>
      <td style="color:${s.acc>=60?'var(--accent2)':s.acc>=40?'var(--accent)':'var(--accent3)'}">${Math.round(s.acc)}%</td>
      <td style="color:${consColor}">${consStr}</td>
      <td>${trendStr}</td>
      <td style="color:var(--muted)">${s.att}${s.total>s.att?'/<span style="color:var(--muted)">'+s.total+'</span>':''}</td>`;
    tbody.appendChild(tr);
  });
}

// sort buttons
document.querySelectorAll('.sort-btn').forEach(btn=>{
  btn.addEventListener('click',()=>{
    const sv=btn.dataset.sort;
    if(sv===lbSort)lbDir*=-1;else{lbSort=sv;lbDir=-1;}
    document.querySelectorAll('.sort-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    renderLeaderboard();
  });
});
$('lbSearch').addEventListener('input',e=>{
  lbFilter=e.target.value.trim().toUpperCase();
  renderLeaderboard();
});

/* ── SUBJECT CARDS ── */
function buildSubjectCards(attended){
  function card(id,label,key,max){
    const vals=attended.map(r=>r[key]);
    if(!vals.length){$(`s${id}`).innerHTML=`<div class="subj-name">${label}</div><div style="color:var(--muted);font-size:0.65rem;">No data</div>`;return;}
    const a=avg(vals),mx=Math.max(...vals),mn=Math.min(...vals);
    const above=vals.filter(v=>v>a).length;
    const pctAbove=Math.round(above/vals.length*100);
    $(`s${id}`).innerHTML=`<div class="subj-name">${label}</div>
      ${[
        ['Batch Average',rnd(a)],
        ['Highest',mx],
        ['Lowest',mn],
        ['Above Avg',`${above} (${pctAbove}%)`],
        ['Std Dev',rnd(Math.sqrt(avg(vals.map(v=>(v-a)**2))))],
        ['Median',vals.sort((a,b)=>a-b)[Math.floor(vals.length/2)]],
      ].map(([k,v])=>`<div class="subj-row"><span class="subj-key">${k}</span><span class="subj-val">${v}</span></div>`).join('')}`;
  }
  card('Physics','Physics','phy_m',100);
  card('Chem','Chemistry','chem_m',100);
  card('Math','Maths','math_m',100);
}

/* ── CHARTS ── */
function buildCharts(jut,attended){
  buildBatchTrend();
  buildDistBars(attended);
  buildRadar(attended);
  buildTopBar(jut);
  buildAccDist(attended);
}

function buildBatchTrend(){
  destroyChart('batchTrend');
  const labels=allTests.map(shortLabel);
  const _minW=Math.max(600,allTests.length*80);
  const wrap=document.getElementById('batchTrendWrap');
  if(wrap) wrap.style.minWidth=_minW+'px';
  const data=allTests.map(t=>{
    const rows=(testMap[t]||[]).filter(r=>r.total>0||r.tot_a>0);
    return rows.length?Math.round(avg(rows.map(r=>r.total))):null;
  });
  const phyD=allTests.map(t=>{const rows=(testMap[t]||[]).filter(r=>r.total>0||r.tot_a>0);return rows.length?Math.round(avg(rows.map(r=>r.phy_m))):null;});
  const chemD=allTests.map(t=>{const rows=(testMap[t]||[]).filter(r=>r.total>0||r.tot_a>0);return rows.length?Math.round(avg(rows.map(r=>r.chem_m))):null;});
  const mathD=allTests.map(t=>{const rows=(testMap[t]||[]).filter(r=>r.total>0||r.tot_a>0);return rows.length?Math.round(avg(rows.map(r=>r.math_m))):null;});
  charts.batchTrend=new Chart($('chartBatchTrend'),{
    type:'line',
    data:{labels,datasets:[
      {label:'Total Avg',data,borderColor:'#e8c547',backgroundColor:'rgba(232,197,71,0.07)',borderWidth:2.5,pointRadius:5,tension:0.35,spanGaps:true},
      {label:'Physics Avg',data:phyD,borderColor:'#4fc3f7',borderWidth:1.5,pointRadius:3,tension:0.35,spanGaps:true,borderDash:[4,3]},
      {label:'Chem Avg',data:chemD,borderColor:'#a78bfa',borderWidth:1.5,pointRadius:3,tension:0.35,spanGaps:true,borderDash:[4,3]},
      {label:'Maths Avg',data:mathD,borderColor:'#fb923c',borderWidth:1.5,pointRadius:3,tension:0.35,spanGaps:true,borderDash:[4,3]},
    ]},
    options:{maintainAspectRatio:false,scales:{x:{ticks:{color:'#6b6b8a',maxRotation:0,font:{size:9}},grid:{color:'#1e1e2e'}},y:{ticks:{color:'#6b6b8a'},grid:{color:'#1e1e2e'},min:0}},plugins:{legend:{labels:{color:'#6b6b8a',font:{size:9}}}}}
  });
}

function buildDistBars(attended){
  // Use ONE average score per student, not one row per test-entry
  const studentScoreMap={};
  attended.forEach(r=>{
    const k=r.name||normName(r.name||'');
    if(!studentScoreMap[k])studentScoreMap[k]=[];
    studentScoreMap[k].push(r.total);
  });
  const scores=Object.values(studentScoreMap).map(arr=>Math.round(avg(arr)));
  const wrap=$('distWrap');wrap.innerHTML='';
  if(!scores.length){wrap.innerHTML='<div style="color:var(--muted);font-size:0.65rem;">No data</div>';return;}
  const mx=Math.max(...scores);
  const step=Math.ceil(mx/6)||50;
  const ranges=[];
  for(let i=5;i>=0;i--)ranges.push([i*step,(i+1)*step-1]);
  const colors=['#47e8c5','#e8c547','#fb923c','#a78bfa','#e847a0','#4fc3f7'];
  const counts=ranges.map(([lo,hi])=>scores.filter(s=>s>=lo&&s<=hi).length);
  const maxC=Math.max(...counts,1);
  ranges.forEach(([lo,hi],i)=>{
    const p=(counts[i]/maxC*100).toFixed(1);
    const row=document.createElement('div');row.className='dist-row';
    row.innerHTML=`<div class="dist-lbl">${lo}–${hi}</div>
      <div class="dist-outer"><div class="dist-inner" style="background:${colors[i]};width:0%" data-pct="${p}">${counts[i]>0?counts[i]+' students':''}</div></div>
      <div class="dist-cnt">${counts[i]}</div>`;
    wrap.appendChild(row);
  });
  setTimeout(()=>{document.querySelectorAll('.dist-inner').forEach(b=>{b.style.width=b.dataset.pct+'%';});},300);
}

function buildRadar(attended){
  destroyChart('radar');
  const phyA=attended.length?avg(attended.map(r=>r.phy_m)):0;
  const chemA=attended.length?avg(attended.map(r=>r.chem_m)):0;
  const mathA=attended.length?avg(attended.map(r=>r.math_m)):0;
  charts.radar=new Chart($('chartRadar'),{
    type:'radar',
    data:{labels:['Physics','Chemistry','Maths'],datasets:[{label:'Batch Avg',data:[rnd(phyA),rnd(chemA),rnd(mathA)],borderColor:'#e8c547',backgroundColor:'rgba(232,197,71,0.1)',pointBackgroundColor:['#4fc3f7','#a78bfa','#fb923c'],pointRadius:6,borderWidth:2}]},
    options:{maintainAspectRatio:false,scales:{r:{grid:{color:'#1e1e2e'},ticks:{display:false},pointLabels:{color:'#e8e8f0',font:{size:11}}}},plugins:{legend:{display:false}}}
  });
}

function buildTopBar(jut){
  destroyChart('topBar');
  let top;
  if(jut==='ALL'){
    top=Object.values(studentMap)
      .filter(s=>s.stats.attended>=1)
      .sort((a,b)=>b.stats.avgScore-a.stats.avgScore)
      .slice(0,15);
  } else {
    const jutRows=(testMap[jut]||[]).filter(r=>r.total>0||r.tot_a>0).sort((a,b)=>b.total-a.total).slice(0,15);
    top=jutRows.map(r=>({name:r.name,stats:{avgScore:r.total,avgPhy:r.phy_m,avgChem:r.chem_m,avgMath:r.math_m}}));
  }
  const labels=top.map(s=>s.name.split(' ')[0]);
  const avgs=top.map(s=>Math.round(s.stats.avgScore));
  charts.topBar=new Chart($('chartTopBar'),{
    type:'bar',
    data:{labels,datasets:[
      {label:'Avg Score',data:avgs,backgroundColor:avgs.map((_,i)=>i===0?'#fbbf24aa':i<3?'#e8c547aa':'#47e8c5aa'),borderRadius:3},
    ]},
    options:{maintainAspectRatio:false,indexAxis:'y',scales:{x:{ticks:{color:'#6b6b8a',font:{size:9}},grid:{color:'#1e1e2e'},min:0},y:{ticks:{color:'#6b6b8a',font:{size:9}},grid:{color:'transparent'}}},plugins:{legend:{display:false}}}
  });
}

function buildAccDist(attended){
  destroyChart('accDist');
  const accs=attended.map(r=>pct(r.tot_c,r.tot_a)).filter(a=>a>0);
  const buckets=[0,10,20,30,40,50,60,70,80,90,100];
  const counts=buckets.slice(0,-1).map((lo,i)=>accs.filter(a=>a>=lo&&a<buckets[i+1]).length);
  const labels=buckets.slice(0,-1).map((lo,i)=>`${lo}-${buckets[i+1]}%`);
  charts.accDist=new Chart($('chartAccDist'),{
    type:'bar',
    data:{labels,datasets:[{label:'Students',data:counts,backgroundColor:counts.map((_,i)=>i>=6?'#47e8c5aa':i>=4?'#e8c547aa':i>=2?'#fb923caa':'#e847a0aa'),borderRadius:2}]},
    options:{maintainAspectRatio:false,scales:{x:{ticks:{color:'#6b6b8a',font:{size:9},maxRotation:30},grid:{color:'#1e1e2e'}},y:{ticks:{color:'#6b6b8a'},grid:{color:'#1e1e2e'},min:0}},plugins:{legend:{display:false}}}
  });
}

/* ── JUT SUMMARY TABLE ── */
function buildJutSummary(){
  const tbody=$('jutSummaryBody');tbody.innerHTML='';
  allTests.forEach(t=>{
    const rows=(testMap[t]||[]).filter(r=>r.total>0||r.tot_a>0);
    if(!rows.length){
      const tr=document.createElement('tr');tr.className='jtr';
      tr.innerHTML=`<td style="font-family:'DM Serif Display',serif">${shortLabel(t)}</td><td colspan="8" style="color:var(--muted)">No data</td>`;
      tbody.appendChild(tr);return;
    }
    const scores=rows.map(r=>r.total);
    const bAvg=Math.round(avg(scores)),bMax=Math.max(...scores),bMin=Math.min(...scores);
    const phyA=rnd(avg(rows.map(r=>r.phy_m)));
    const chemA=rnd(avg(rows.map(r=>r.chem_m)));
    const mathA=rnd(avg(rows.map(r=>r.math_m)));
    const accA=Math.round(avg(rows.map(r=>pct(r.tot_c,r.tot_a))));
    const tr=document.createElement('tr');tr.className='jtr';
    tr.style.cursor='pointer';
    tr.addEventListener('click',()=>setActiveJut(t));
    tr.innerHTML=`
      <td style="font-family:'DM Serif Display',serif;color:var(--accent)">${shortLabel(t)}</td>
      <td style="color:var(--muted)">${rows.length}</td>
      <td style="font-family:'Bebas Neue',sans-serif;font-size:1.2rem;color:var(--accent)">${bAvg}</td>
      <td style="color:var(--green)">${bMax}</td>
      <td style="color:var(--red)">${bMin}</td>
      <td style="color:var(--phy)">${phyA}</td>
      <td style="color:var(--chem)">${chemA}</td>
      <td style="color:var(--math)">${mathA}</td>
      <td style="color:${accA>=60?'var(--accent2)':accA>=40?'var(--accent)':'var(--accent3)'}">${accA}%</td>`;
    tbody.appendChild(tr);
  });
}

/* ── CONSISTENCY ── */
function buildConsistency(){
  const eligible=Object.values(studentMap)
    .filter(s=>s.stats.consistency!==null&&s.stats.attended>=3)
    .sort((a,b)=>b.stats.consistency-a.stats.consistency)
    .slice(0,24);
  const grid=$('consGrid');grid.innerHTML='';
  const colors=['#fbbf24','#94a3b8','#cd7f32'];
  eligible.forEach((s,i)=>{
    const c=s.stats.consistency;
    const color=c>=70?'var(--green)':c>=50?'var(--accent)':'var(--accent3)';
    const rankColor=i<3?colors[i]:'var(--muted)';
    const card=document.createElement('a');
    card.className='cons-card';
    card.href=`/student?student=${encodeURIComponent(s.name)}`;
    card.innerHTML=`
      <div class="cons-rank" style="color:${rankColor}">${i+1}</div>
      <div class="cons-info">
        <div class="cons-name">${s.name}</div>
        <div style="font-size:0.55rem;color:var(--muted);letter-spacing:0.1em;">${s.stats.attended} JUTs · avg ${Math.round(s.stats.avgScore)}</div>
        <div class="cons-bar-outer"><div class="cons-bar-inner" style="background:${color};width:0%" data-pct="${c}"></div></div>
      </div>
      <div class="cons-score" style="color:${color}">${c}%</div>`;
    grid.appendChild(card);
  });
  setTimeout(()=>{document.querySelectorAll('.cons-bar-inner').forEach(b=>{b.style.width=b.dataset.pct+'%';});},400);
}

/* ── REVEAL ── */
function initReveal(){
  const io=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('vis');});},{threshold:0.05});
  document.querySelectorAll('.reveal').forEach(el=>{el.classList.remove('vis');io.observe(el);});
}

loadData();
</script>
</body>
</html>
"""


@app.get("/overview")
def overview_page():
    return app.response_class(OVERVIEW_HTML, mimetype='text/html')


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
  .inst-chip{display:inline-block;font-size:0.5rem;letter-spacing:0.15em;padding:0.18rem 0.5rem;border-radius:2px;font-weight:600;text-transform:uppercase;}
  .inst-kjs{background:rgba(79,195,247,0.15);color:#4fc3f7;}
  .inst-mjs{background:rgba(167,139,250,0.15);color:#a78bfa;}
  .inst-ujs{background:rgba(251,146,60,0.15);color:#fb923c;}

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
          <th>#</th><th>Student</th><th>Inst</th><th>Score</th><th>Subject Breakdown</th><th>Accuracy</th><th>Attempted</th>
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
const lines = csvText.trim().split('\n');
const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/\s+/g,'_'));
  return lines.slice(1).map(line => {
    const vals = line.split(',');
    const obj = {};
    headers.forEach((h,i) => { obj[h] = vals[i] !== undefined ? vals[i].trim() : ''; });
    return obj;
  }).filter(r => r[headers[0]]);
}

function n(v) { return parseFloat(v) || 0; }

function getInstA(fileVal){
  if(!fileVal) return '';
  const f=(fileVal+'').trim().toUpperCase();
  if(f.startsWith('K')) return 'KJS';
  if(f.startsWith('U')) return 'UJS';
  if(f.startsWith('M')) return 'MJS';
  return '';
}
function mapRow(r) {
  const get = (...keys) => { for(const k of keys){ if(r[k]!==undefined) return r[k]; } return '0'; };
  const getS = (...keys) => { for(const k of keys){ if(r[k]!==undefined) return r[k]; } return ''; };
  return {
    name:   getS('name') || 'Unknown',
    inst:   getInstA(getS('file','filename')),
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
        '<td>' + (s.inst ? '<span class="inst-chip inst-'+(s.inst||'').toLowerCase()+'">' + s.inst + '</span>' : '') + '</td>' +
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

@app.route("/annual")
def annual():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ANNUAL EXAM ANALYSIS</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@300;400;600;800&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
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
    --bio: #2ecc71;
    --eng: #f1c40f;
    --lang: #e84393;
    --gold: #fbbf24;
    --silver: #94a3b8;
    --bronze: #cd7f32;
    --green: #4ade80;
    --red: #f87171;
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

  .insight-desc {
    white-space: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .grid-bg {
    position: fixed;
    z-index: -1;
    inset: 0;
    background-image: linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
    background-size: 60px 60px;
    animation: gridDrift 30s linear infinite;
  }
  @keyframes gridDrift { 0% { background-position: 0 0; } 100% { background-position: 60px 60px; } }

  .glow-1, .glow-2, .glow-3 {
    position: fixed;
    border-radius: 50%;
    pointer-events: none;
  }
  .glow-1 { width: 700px; height: 700px; background: radial-gradient(circle, rgba(232,197,71,0.07) 0%, transparent 70%); top: -200px; left: -200px; animation: floatA 18s ease-in-out infinite; }
  .glow-2 { width: 500px; height: 500px; background: radial-gradient(circle, rgba(71,232,197,0.05) 0%, transparent 70%); bottom: -100px; right: -100px; animation: floatB 22s ease-in-out infinite; }
  .glow-3 { width: 400px; height: 400px; background: radial-gradient(circle, rgba(232,71,160,0.04) 0%, transparent 70%); top: 50%; right: 20%; animation: floatC 26s ease-in-out infinite; }
  @keyframes floatA { 0%,100%{transform:translate(0,0)} 50%{transform:translate(60px,40px)} }
  @keyframes floatB { 0%,100%{transform:translate(0,0)} 50%{transform:translate(-50px,-30px)} }
  @keyframes floatC { 0%,100%{transform:translate(0,0)} 50%{transform:translate(30px,-50px)} }

  .topnav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 500;
    background: rgba(10,10,15,0.95); backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.9rem 2rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .topnav-logo { font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; letter-spacing: 0.08em; color: var(--text); text-decoration: none; }
  .topnav-logo span { color: var(--accent); }
  .topnav-badge { font-size: 0.55rem; letter-spacing: 0.2em; color: var(--accent2); text-transform: uppercase; background: rgba(71,232,197,0.12); padding: 0.3rem 0.8rem; border-radius: 20px; }
  .data-status { font-size: 0.5rem; color: var(--muted); background: var(--surface); padding: 0.3rem 0.8rem; border-radius: 20px; }
  .topnav-back { font-size: 0.6rem; letter-spacing: 0.25em; color: var(--muted); text-decoration: none; cursor: pointer; }
  .topnav-back:hover { color: var(--accent); }

  .hero {
    min-height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center;
    text-align: center; position: relative; padding: 7rem 2rem 4rem;
  }
  .hero-bg { position: absolute; inset: 0; background: radial-gradient(ellipse 80% 50% at 20% 40%, rgba(232,197,71,0.08) 0%, transparent 60%), radial-gradient(ellipse 60% 60% at 80% 60%, rgba(71,232,197,0.06) 0%, transparent 60%); }
  .hero-tag { font-size: 0.7rem; letter-spacing: 0.3em; color: var(--accent); text-transform: uppercase; margin-bottom: 1.5rem; animation: fadeUp 0.6s 0.2s forwards; }
  .hero-title { font-family: 'Bebas Neue', sans-serif; font-size: clamp(4rem, 12vw, 10rem); line-height: 0.9; letter-spacing: 0.02em; animation: fadeUp 0.8s 0.4s forwards; }
  .hero-title span { -webkit-text-stroke: 1px var(--accent); color: transparent; }
  .hero-sub { font-size: 0.85rem; color: var(--muted); letter-spacing: 0.15em; margin-top: 1.5rem; animation: fadeUp 0.8s 0.6s forwards; }
  .hero-stats { display: flex; gap: 3rem; margin-top: 3rem; flex-wrap: wrap; justify-content: center; animation: fadeUp 0.8s 0.8s forwards; }
  .hero-stat { text-align: center; }
  .hero-stat-val { font-family: 'Bebas Neue', sans-serif; font-size: 3rem; color: var(--accent); line-height: 1; }
  .hero-stat-label { font-size: 0.6rem; color: var(--muted); letter-spacing: 0.2em; text-transform: uppercase; margin-top: 0.3rem; }
  @keyframes fadeUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }

  section { padding: 5rem 2rem; max-width: 1600px; margin: 0 auto; }
  .section-label { font-size: 0.65rem; letter-spacing: 0.4em; color: var(--accent); text-transform: uppercase; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.8rem; }
  .section-label::before { content: ''; display: block; width: 28px; height: 1px; background: var(--accent); }
  .section-title { font-family: 'DM Serif Display', serif; font-size: clamp(2rem, 5vw, 3.5rem); line-height: 1.1; margin-bottom: 3rem; }

  .podium-section { background: var(--surface); position: relative; overflow: hidden; padding: 4rem 2rem; }
  .podium { display: flex; align-items: flex-end; justify-content: center; gap: 0; margin-top: 2rem; flex-wrap: wrap; }
  .podium-card { flex: 1; max-width: 280px; text-align: center; transition: transform 0.3s; }
  .podium-card:hover { transform: translateY(-8px); }
  .podium-name { font-family: 'DM Serif Display', serif; font-size: 1.1rem; margin-bottom: 0.3rem; }
  .podium-score { font-family: 'Bebas Neue', sans-serif; font-size: 3.5rem; line-height: 1; }
  .podium-rank-label { font-size: 0.6rem; letter-spacing: 0.3em; color: var(--muted); text-transform: uppercase; margin-top: 0.3rem; }
  .podium-block { margin-top: 1rem; border-radius: 4px 4px 0 0; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; }
  .p1 .podium-score { color: var(--gold); } .p1 .podium-block { background: linear-gradient(135deg, #fbbf24, #f59e0b); height: 160px; }
  .p2 .podium-score { color: var(--silver); } .p2 .podium-block { background: linear-gradient(135deg, #94a3b8, #64748b); height: 120px; }
  .p3 .podium-score { color: var(--bronze); } .p3 .podium-block { background: linear-gradient(135deg, #cd7f32, #a0632a); height: 90px; }

  .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-top: 2rem; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 1.5rem; transition: transform 0.2s; }
  .stat-card:hover { transform: translateY(-4px); border-color: rgba(232,197,71,0.4); }
  .stat-card::after { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, var(--accent), var(--accent2)); }
  .stat-card { position: relative; }
  .stat-label-sm { font-size: 0.55rem; letter-spacing: 0.28em; color: var(--muted); text-transform: uppercase; margin-bottom: 0.7rem; }
  .stat-value { font-family: 'Bebas Neue', sans-serif; font-size: 2.8rem; line-height: 1; color: var(--accent); }
  .stat-sub { font-size: 0.58rem; color: var(--muted); margin-top: 0.3rem; }

  .charts-grid-2, .charts-grid-3 { display: grid; gap: 1.5rem; margin-top: 2rem; }
  .charts-grid-2 { grid-template-columns: 1fr 1fr; }
  .charts-grid-3 { grid-template-columns: repeat(3, 1fr); }
  .chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 1.5rem; position: relative; overflow: hidden; }
  .chart-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, var(--accent), var(--accent2)); }
  .chart-title { font-size: 0.6rem; letter-spacing: 0.3em; color: var(--muted); text-transform: uppercase; margin-bottom: 1rem; }
  canvas { max-height: 280px; width: 100% !important; }

  .subject-grid-6 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 2rem; }
  .subj-card { background: var(--surface); border: 1px solid var(--border); padding: 1.2rem; border-radius: 6px; transition: transform 0.2s; }
  .subj-card:hover { transform: translateY(-4px); }
  .subj-name { font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; margin-bottom: 0.5rem; }
  .subj-row { display: flex; justify-content: space-between; padding: 0.3rem 0; border-bottom: 1px solid var(--border); font-size: 0.65rem; }

  .filter-bar { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; align-items: center; }
  .search-input { background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 0.6rem 1rem; font-family: monospace; font-size: 0.72rem; border-radius: 2px; flex: 1; min-width: 200px; outline: none; }
  .search-input:focus { border-color: var(--accent); }
  .sort-btn { background: var(--surface); border: 1px solid var(--border); color: var(--muted); padding: 0.5rem 1rem; font-size: 0.6rem; letter-spacing: 0.15em; text-transform: uppercase; cursor: pointer; border-radius: 2px; transition: all 0.2s; }
  .sort-btn:hover, .sort-btn.active { border-color: var(--accent); color: var(--accent); }

  .leaderboard-table { width: 100%; border-collapse: separate; border-spacing: 0 4px; }
  .leaderboard-table th { font-size: 0.55rem; letter-spacing: 0.2em; color: var(--muted); padding: 0.5rem 0.8rem; text-align: left; }
  .leaderboard-table tr.row { background: var(--surface); transition: all 0.2s; }
  .leaderboard-table tr.row:hover { background: var(--surface2); transform: translateX(4px); }
  .leaderboard-table td { padding: 0.7rem 0.8rem; font-size: 0.7rem; }
  .rank-badge { font-family: 'Bebas Neue', sans-serif; font-size: 1.1rem; width: 32px; display: inline-block; }
  .rank-1 { color: var(--gold); } .rank-2 { color: var(--silver); } .rank-3 { color: var(--bronze); }
  .score-pill { display: inline-block; padding: 0.1rem 0.6rem; border-radius: 2px; font-family: 'Bebas Neue', sans-serif; font-size: 1rem; }

  .dist-bar-row { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.6rem; }
  .dist-range { font-size: 0.65rem; color: var(--muted); width: 80px; }
  .dist-bar-outer { flex: 1; height: 28px; background: var(--surface2); border-radius: 2px; overflow: hidden; }
  .dist-bar-inner { height: 100%; border-radius: 2px; display: flex; align-items: center; padding-left: 8px; font-size: 0.6rem; font-weight: 600; color: rgba(0,0,0,0.7); transition: width 1.2s; width: 0; }
  .dist-count { font-size: 0.7rem; color: var(--muted); width: 30px; text-align: right; }

  .insight-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; margin-top: 2rem; }
  .insight-card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 1.5rem; text-align: center; transition: transform 0.2s; }
  .insight-card:hover { transform: translateY(-3px); border-color: var(--accent2); }
  .insight-icon { font-size: 2rem; margin-bottom: 0.5rem; }
  .insight-title { font-family: 'Bebas Neue', sans-serif; font-size: 1.3rem; color: var(--accent); }
  .insight-desc { font-size: 0.6rem; color: var(--muted); margin-top: 0.3rem; }

  .csv-input-area { background: var(--surface); border: 2px dashed var(--border); border-radius: 12px; padding: 2rem; margin: 2rem auto; text-align: center; max-width: 1000px; }
  .csv-textarea { width: 100%; min-height: 350px; background: var(--bg); border: 1px solid var(--border); color: var(--text); font-family: monospace; font-size: 0.7rem; padding: 1rem; border-radius: 6px; margin-top: 1rem; resize: vertical; }
  .load-btn { background: var(--accent); color: var(--bg); border: none; padding: 0.8rem 2rem; font-family: 'Bebas Neue', sans-serif; font-size: 1.2rem; cursor: pointer; border-radius: 4px; margin-top: 1rem; transition: transform 0.2s; }
  .load-btn:hover { transform: scale(1.02); background: var(--accent2); }
  .sample-btn { background: transparent; border: 1px solid var(--border); color: var(--muted); padding: 0.5rem 1rem; margin-left: 1rem; cursor: pointer; font-size: 0.7rem; border-radius: 4px; }

  .reveal { opacity: 0; transform: translateY(30px); transition: opacity 0.7s, transform 0.7s; }
  .reveal.visible { opacity: 1; transform: translateY(0); }
  .divider { height: 1px; background: linear-gradient(90deg, transparent, var(--border), transparent); margin: 1rem 0; }
  footer { text-align: center; padding: 3rem; color: var(--muted); font-size: 0.6rem; letter-spacing: 0.2em; border-top: 1px solid var(--border); }

  @media (max-width: 1000px) { .charts-grid-2, .charts-grid-3, .subject-grid-6 { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="grid-bg"></div>
<div class="glow-1"></div><div class="glow-2"></div><div class="glow-3"></div>

<nav class="topnav">
  <a class="topnav-logo" href="#">ANNUAL<span>·</span>EXAM</a>
  <div class="topnav-badge">6 SUB · ANALYSIS</div>
  <a class="topnav-back" id="resetBtn">⟳ RESET</a>
</nav>

<div class="hero">
  <div class="hero-bg"></div>
  <div class="hero-tag">🔥 COMPLETE 6-SUBJECT ARMAGEDDON 🔥</div>
  <div class="hero-title">FULL <span>ANALYSIS</span><br>600 MARKS</div>
  <div class="hero-sub">Physics · Chemistry · Mathematics · Biology/CSC · English · Second Language</div>
  <div class="hero-stats" id="heroStats"></div>
</div>

<div class="csv-input-area" id="csvInputArea">
  <div class="section-label" style="justify-content: center;">📁 PASTE FULL CSV DATA (ALL 6 SUBJECTS + TOTAL)</div>
  <p style="color: var(--muted); font-size: 0.7rem;">Paste students.csv with columns: roll_no, name, combination, physics, chemistry, mathematics, subject4, english, language2, total</p>
  <textarea id="csvTextarea" class="csv-textarea" placeholder="roll_no,name,combination,physics,chemistry,mathematics,subject4,english,language2,total&#10;25001,ABHIJNA S SHETTY,PCMB,94,76,84,95,99,100,548&#10;..."></textarea>
  <div>
    <button class="load-btn" id="loadCsvBtn">⚡ ANALYZE ALL 6 SUBJECTS ⚡</button>
    <button class="sample-btn" id="loadSampleBtn">📋 Load Sample (20 Students)</button>
  </div>
</div>

<div id="mainContent" style="display: none;">
  <div class="podium-section">
    <div class="section-label reveal">🏆 LEGENDARY TOPPERS 🏆</div>
    <div class="section-title reveal">The Pantheon of 600</div>
    <div class="podium reveal" id="podium"></div>
  </div>

  <section>
    <div class="section-label reveal">📊 6-SUBJECT MASTER STATS</div>
    <div class="section-title reveal">Complete Academic Metrics</div>
    <div class="stat-grid reveal" id="statGrid"></div>
  </section>

  <section>
    <div class="section-label reveal">🧠 PER-SUBJECT DOMINATION (ALL 6)</div>
    <div class="section-title reveal">Subject-wise Hellscape</div>
    <div class="subject-grid-6 reveal" id="subjectGrid"></div>
  </section>

  <section>
    <div class="section-label reveal">📈 10+ VISUAL INSANITY CHARTS</div>
    <div class="section-title reveal">Analytics Overload</div>
    <div class="charts-grid-2">
      <div class="chart-card reveal"><div class="chart-title">🎯 Total Score Distribution (600 max)</div><div id="distBars"></div></div>
      <div class="chart-card reveal"><div class="chart-title">⚔️ All 6 Subjects Average Comparison</div><canvas id="radarChart6"></canvas></div>
      <div class="chart-card reveal"><div class="chart-title">📊 PCMB vs PCMC Domination</div><canvas id="comboChart"></canvas></div>
      <div class="chart-card reveal"><div class="chart-title">🏅 Top 15 Academic Gods</div><canvas id="top15Chart"></canvas></div>
      <div class="chart-card reveal"><div class="chart-title">📈 Subject-wise Performance Heat (Avg Marks)</div><canvas id="barChart6"></canvas></div>
      <div class="chart-card reveal"><div class="chart-title">🎓 Grade Distribution (A+, A, B, C, D, F)</div><canvas id="gradeChart"></canvas></div>
    </div>
  </section>

  <section>
    <div class="section-label reveal">📊 FULL LEADERBOARD</div>
    <div class="section-title reveal">Ranked by Total (600 max)</div>
    <div class="filter-bar reveal">
      <input class="search-input" id="searchInput" type="text" placeholder="Search student...">
      <button class="sort-btn active" data-sort="total">Total ↕</button>
      <button class="sort-btn" data-sort="phy">Physics ↕</button>
      <button class="sort-btn" data-sort="chem">Chemistry ↕</button>
      <button class="sort-btn" data-sort="math">Maths ↕</button>
      <button class="sort-btn" data-sort="sub4">Bio/CSC ↕</button>
      <button class="sort-btn" data-sort="eng">English ↕</button>
      <button class="sort-btn" data-sort="lang">Lang2 ↕</button>
    </div>
    <div style="overflow-x:auto" class="reveal">
      <table class="leaderboard-table">
        <thead><tr><th>#</th><th>Student</th><th>Comb</th><th>Total</th><th>P</th><th>C</th><th>M</th><th>4th</th><th>Eng</th><th>Lang</th><th>%</th></tr></thead>
        <tbody id="leaderboardBody"></tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="section-label reveal">💀 15+ CRAZY INSIGHTS</div>
    <div class="section-title reveal">Mind-Blowing Facts</div>
    <div class="insight-grid reveal" id="insightGrid"></div>
  </section>

  <footer>🔥 GOD MODE · 6 SUBJECTS · 600 MARKS · FULL CHAOS ANALYSIS 🔥</footer>
</div>

<script>
let students = [];
let charts = {};

function parseCSV(csvText) {
const lines = csvText.trim().split(new RegExp('\r?\n'));
if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/\s+/g, '_'));
  return lines.slice(1).map(line => {
    const vals = line.split(',');
    const obj = {};
    headers.forEach((h, i) => { obj[h] = vals[i] !== undefined ? vals[i].trim() : ''; });
    return obj;
  }).filter(r => r.total && !isNaN(parseFloat(r.total)));
}

function n(v) { return parseFloat(v) || 0; }

function mapStudent(row) {
  return {
    name: row.name || 'Unknown',
    roll: row.roll_no || '',
    combination: row.combination || '',
    total: n(row.total),
    physics: n(row.physics),
    chemistry: n(row.chemistry),
    mathematics: n(row.mathematics),
    subject4: n(row.subject4),
    subject4_name: row.subject4_name || (row.combination === 'PCMB' ? 'BIOLOGY' : 'CSC'),
    english: n(row.english),
    language2: n(row.language2),
    language2_name: row.language2_name || 'HINDI',
  };
}

function destroyCharts() {
  Object.values(charts).forEach(chart => { if (chart) try { chart.destroy(); } catch(e) {} });
  charts = {};
}

function getGrade(percentage) {
  if (percentage >= 90) return 'A+';
  if (percentage >= 75) return 'A';
  if (percentage >= 60) return 'B';
  if (percentage >= 45) return 'C';
  if (percentage >= 35) return 'D';
  return 'F';
}

function renderDashboard(data) {
  destroyCharts();
  students = data.map(s => ({ ...s, percentage: (s.total / 600 * 100).toFixed(1), grade: getGrade(s.total / 600 * 100) }));
  
  const total = students.length;
  const avgTotal = (students.reduce((a,b)=>a+b.total,0)/total).toFixed(1);
  const maxTotal = Math.max(...students.map(s=>s.total));
  const minTotal = Math.min(...students.map(s=>s.total));
  const pcmb = students.filter(s=>s.combination === 'PCMB').length;
  const pcmc = students.filter(s=>s.combination === 'PCMC').length;
  const topStudent = students.find(s=>s.total === maxTotal);
  const median = students.sort((a,b)=>a.total-b.total)[Math.floor(total/2)].total;
  
  document.getElementById('heroStats').innerHTML = `
    <div class="hero-stat"><div class="hero-stat-val">${total}</div><div class="hero-stat-label">Students</div></div>
    <div class="hero-stat"><div class="hero-stat-val">${avgTotal}</div><div class="hero-stat-label">Avg /600</div></div>
    <div class="hero-stat"><div class="hero-stat-val">${maxTotal}</div><div class="hero-stat-label">🏆 Top</div></div>
    <div class="hero-stat"><div class="hero-stat-val">${minTotal}</div><div class="hero-stat-label">💀 Bottom</div></div>
    <div class="hero-stat"><div class="hero-stat-val">${pcmb}</div><div class="hero-stat-label">PCMB</div></div>
    <div class="hero-stat"><div class="hero-stat-val">${pcmc}</div><div class="hero-stat-label">PCMC</div></div>
  `;
  
  document.getElementById('statGrid').innerHTML = `
    <div class="stat-card"><div class="stat-label-sm">Total Warriors</div><div class="stat-value">${total}</div><div class="stat-sub">PCMB:${pcmb} · PCMC:${pcmc}</div></div>
    <div class="stat-card"><div class="stat-label-sm">Mean Total</div><div class="stat-value">${avgTotal}</div><div class="stat-sub">out of 600</div></div>
    <div class="stat-card"><div class="stat-label-sm">Highest Scorer</div><div class="stat-value">${maxTotal}</div><div class="stat-sub">${topStudent?.name || ''}</div></div>
    <div class="stat-card"><div class="stat-label-sm">Median Total</div><div class="stat-value">${median}</div><div class="stat-sub">Middle Warrior</div></div>
    <div class="stat-card"><div class="stat-label-sm">Std Deviation</div><div class="stat-value">${Math.sqrt(students.reduce((a,b)=>a+Math.pow(b.total-avgTotal,2),0)/total).toFixed(1)}</div><div class="stat-sub">Volatility</div></div>
    <div class="stat-card"><div class="stat-label-sm">Perfect 100s</div><div class="stat-value">${students.filter(s=>s.physics===100||s.chemistry===100||s.mathematics===100||s.subject4===100||s.english===100||s.language2===100).length}</div><div class="stat-sub">Subject Gods</div></div>
  `;
  
  const sorted = [...students].sort((a,b)=>b.total - a.total);
  const top3 = sorted.slice(0,3);
  const podium = document.getElementById('podium');
  podium.innerHTML = '';
  const order = [top3[1], top3[0], top3[2]].filter(Boolean);
  const classes = ['p2','p1','p3'];
  const heights = [120,160,90];
  const medal = ['🥈','🥇','🥉'];
  order.forEach((s,i) => {
    const div = document.createElement('div');
    div.className = `podium-card ${classes[i]}`;
    div.innerHTML = `<div class="podium-name">${s.name}</div><div class="podium-score">${s.total}</div><div class="podium-rank-label">${s.combination}</div><div class="podium-block" style="height:${heights[i]}px;">${medal[i]}</div>`;
    podium.appendChild(div);
  });
  
  // 6 Subject Cards
  const subjects = [
    { key: 'physics', name: 'Physics', color: 'var(--phy)' },
    { key: 'chemistry', name: 'Chemistry', color: 'var(--chem)' },
    { key: 'mathematics', name: 'Mathematics', color: 'var(--math)' },
    { key: 'subject4', name: 'Bio/CSC', color: 'var(--bio)' },
    { key: 'english', name: 'English', color: 'var(--eng)' },
    { key: 'language2', name: 'Lang2', color: 'var(--lang)' }
  ];
  const subjStats = subjects.map(sub => {
    const vals = students.map(s=>s[sub.key]);
    return { ...sub, avg: (vals.reduce((a,b)=>a+b,0)/total).toFixed(1), max: Math.max(...vals), min: Math.min(...vals) };
  });
  document.getElementById('subjectGrid').innerHTML = subjStats.map(s => `
    <div class="subj-card"><div class="subj-name" style="color:${s.color}">${s.name}</div>
    <div class="subj-row"><span>Avg</span><span>${s.avg}</span></div>
    <div class="subj-row"><span>Highest</span><span>${s.max}</span></div>
    <div class="subj-row"><span>Lowest</span><span>${s.min}</span></div>
    <div class="subj-row"><span>Above 90</span><span>${students.filter(st=>st[s.key]>=90).length}</span></div>
    <div class="subj-row"><span>Below 35</span><span>${students.filter(st=>st[s.key]<35).length}</span></div></div>
  `).join('');
  
  // Score Distribution
  const buckets = [{min:0,max:299,label:'<300'},{min:300,max:349,label:'300-349'},{min:350,max:399,label:'350-399'},{min:400,max:449,label:'400-449'},{min:450,max:499,label:'450-499'},{min:500,max:549,label:'500-549'},{min:550,max:599,label:'550-599'},{min:600,max:600,label:'600'}];
  const counts = buckets.map(b => students.filter(s=>s.total>=b.min && s.total<=b.max).length);
  const maxCount = Math.max(...counts,1);
  const distDiv = document.getElementById('distBars');
  distDiv.innerHTML = '';
  const colors = ['#e847a0','#fb923c','#e8c547','#a78bfa','#47e8c5','#4fc3f7','#fbbf24','#2ecc71'];
  buckets.forEach((b,i) => {
    const pct = (counts[i]/maxCount)*100;
    const row = document.createElement('div'); row.className = 'dist-bar-row';
    row.innerHTML = `<div class="dist-range">${b.label}</div><div class="dist-bar-outer"><div class="dist-bar-inner" data-pct="${pct}" style="background:${colors[i]};width:0%">${counts[i]} students</div></div><div class="dist-count">${counts[i]}</div>`;
    distDiv.appendChild(row);
  });
  setTimeout(()=>{ document.querySelectorAll('.dist-bar-inner').forEach(b=>{ b.style.width = b.dataset.pct+'%'; }); }, 200);
  
  // Charts
  const comboCounts = [pcmb, pcmc];
  charts.combo = new Chart(document.getElementById('comboChart'), { type:'pie', data:{ labels:['PCMB','PCMC'], datasets:[{ data:comboCounts, backgroundColor:['#e8c547','#47e8c5'], borderWidth:0 }] }, options:{ responsive:true, plugins:{ legend:{ labels:{ color:'#fff' } } } } });
  
  const top15 = sorted.slice(0,15);
  charts.top15 = new Chart(document.getElementById('top15Chart'), { type:'bar', data:{ labels:top15.map(s=>s.name.split(' ')[0]), datasets:[{ label:'Total /600', data:top15.map(s=>s.total), backgroundColor:'#facc15', borderRadius:6 }] }, options:{ responsive:true, maintainAspectRatio:true, plugins:{ legend:{ labels:{ color:'#fff' } } } } });
  
  charts.radar6 = new Chart(document.getElementById('radarChart6'), { type:'radar', data:{ labels:subjStats.map(s=>s.name), datasets:[{ label:'Avg Marks', data:subjStats.map(s=>s.avg), borderColor:'#e8c547', backgroundColor:'rgba(232,197,71,0.1)', pointBackgroundColor:['#4fc3f7','#a78bfa','#fb923c','#2ecc71','#f1c40f','#e84393'], pointRadius:5 }] }, options:{ responsive:true, scales:{ r:{ grid:{ color:'#1e1e2e' }, ticks:{ display:false }, pointLabels:{ color:'#e8e8f0', font:{ size:10 } } } }, plugins:{ legend:{ display:false } } } });
  
  charts.bar6 = new Chart(document.getElementById('barChart6'), { type:'bar', data:{ labels:subjStats.map(s=>s.name), datasets:[{ label:'Average Marks', data:subjStats.map(s=>s.avg), backgroundColor:['#4fc3f7','#a78bfa','#fb923c','#2ecc71','#f1c40f','#e84393'], borderRadius:6 }] }, options:{ responsive:true, plugins:{ legend:{ display:false } }, scales:{ y:{ beginAtZero:true, max:100 } } } });
  
  const gradeDist = { 'A+':0, 'A':0, 'B':0, 'C':0, 'D':0, 'F':0 };
  students.forEach(s => gradeDist[s.grade]++);
  charts.grade = new Chart(document.getElementById('gradeChart'), { type:'bar', data:{ labels:['A+ (90%+)','A (75-89)','B (60-74)','C (45-59)','D (35-44)','F (<35)'], datasets:[{ label:'Students', data:Object.values(gradeDist), backgroundColor:'#e8c547', borderRadius:6 }] }, options:{ responsive:true } });
  
  // Leaderboard
  let currentSort = 'total', sortDir = -1, filterText = '';
  function renderLeaderboard() {
    let data = [...students];
    if (filterText) data = data.filter(s => s.name.toLowerCase().includes(filterText.toLowerCase()));
    const sortKey = { total:'total', phy:'physics', chem:'chemistry', math:'mathematics', sub4:'subject4', eng:'english', lang:'language2' };
    data.sort((a,b) => sortDir * (a[sortKey[currentSort]] - b[sortKey[currentSort]]));
    const tbody = document.getElementById('leaderboardBody');
    tbody.innerHTML = '';
    const rankMap = {};
    [...students].sort((a,b)=>b.total - a.total).forEach((s,idx)=> rankMap[s.name] = idx+1);
    data.forEach(s => {
      const rank = rankMap[s.name];
      const rankClass = rank===1?'rank-1':rank===2?'rank-2':rank===3?'rank-3':'';
      const scoreColor = s.total>=550?'var(--accent2)':s.total>=500?'var(--accent)':s.total>=450?'var(--math)':'var(--accent3)';
      const tr = document.createElement('tr'); tr.className = 'row';
      tr.innerHTML = `<td><span class="rank-badge ${rankClass}">${rank}</span></td>
        <td style="font-family:'DM Serif Display';">${s.name}</td>
        <td><span class="inst-chip" style="background:rgba(232,197,71,0.12);padding:2px 6px;">${s.combination}</span></td>
        <td><span class="score-pill" style="background:${scoreColor}22;color:${scoreColor}">${s.total}</span></td>
        <td>${s.physics}</td><td>${s.chemistry}</td><td>${s.mathematics}</td>
        <td>${s.subject4}</td><td>${s.english}</td><td>${s.language2}</td>
        <td>${s.percentage}%</td>`;
      tbody.appendChild(tr);
    });
  }
  renderLeaderboard();
  document.getElementById('searchInput').oninput = e => { filterText = e.target.value; renderLeaderboard(); };
  document.querySelectorAll('.sort-btn').forEach(btn => {
    btn.onclick = () => {
      const sv = btn.dataset.sort;
      if (sv === currentSort) sortDir *= -1; else { currentSort = sv; sortDir = -1; }
      document.querySelectorAll('.sort-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      renderLeaderboard();
    };
  });
  
  // Crazy Insights
  const perfectAny = students.filter(s=>s.physics===100||s.chemistry===100||s.mathematics===100||s.subject4===100||s.english===100||s.language2===100).length;
  const above540 = students.filter(s=>s.total>=540).length;
  const below300 = students.filter(s=>s.total<300).length;
  const langAvg = students.reduce((a,b)=>a+b.language2,0)/total;
  const engAvg = students.reduce((a,b)=>a+b.english,0)/total;
  const highestSub = subjStats.reduce((a,b)=> parseFloat(a.avg) > parseFloat(b.avg) ? a : b);
  const lowestSub = subjStats.reduce((a,b)=> parseFloat(a.avg) < parseFloat(b.avg) ? a : b);
  const toppersList = sorted.slice(0,5).map((s,i)=>`${i+1}. ${s.name.split(' ')[0]} (${s.total})`).join(' · ');
  
  document.getElementById('insightGrid').innerHTML = `
    <div class="insight-card"><div class="insight-icon">🏆</div><div class="insight-title">${perfectAny}</div><div class="insight-desc">Students with 100 in any subject</div></div>
    <div class="insight-card"><div class="insight-icon">⚡</div><div class="insight-title">${above540}</div><div class="insight-desc">Above 540 marks (90%+)</div></div>
    <div class="insight-card"><div class="insight-icon">💀</div><div class="insight-title">${below300}</div><div class="insight-desc">Below 300 marks (critical zone)</div></div>
    <div class="insight-card"><div class="insight-icon">📈</div><div class="insight-title">${highestSub.name}</div><div class="insight-desc">Highest avg: ${highestSub.avg}</div></div>
    <div class="insight-card"><div class="insight-icon">📉</div><div class="insight-title">${lowestSub.name}</div><div class="insight-desc">Lowest avg: ${lowestSub.avg}</div></div>
    <div class="insight-card"><div class="insight-icon">🇬🇧</div><div class="insight-title">${engAvg.toFixed(1)}</div><div class="insight-desc">English Average</div></div>
    <div class="insight-card"><div class="insight-icon">🗣️</div><div class="insight-title">${langAvg.toFixed(1)}</div><div class="insight-desc">Second Language Avg</div></div>
    <div class="insight-card"><div class="insight-icon">🎯</div><div class="insight-title">${students.filter(s=>s.physics>=90).length}</div><div class="insight-desc">Physics 90+ scorers</div></div>
    <div class="insight-card"><div class="insight-icon">🧪</div><div class="insight-title">${students.filter(s=>s.chemistry>=90).length}</div><div class="insight-desc">Chemistry 90+ scorers</div></div>
    <div class="insight-card"><div class="insight-icon">📐</div><div class="insight-title">${students.filter(s=>s.mathematics>=90).length}</div><div class="insight-desc">Maths 90+ scorers</div></div>
    <div class="insight-card"><div class="insight-icon">🔬</div><div class="insight-title">${students.filter(s=>s.subject4>=90).length}</div><div class="insight-desc">Bio/CSC 90+ scorers</div></div>
    <div class="insight-card"><div class="insight-icon">👑</div><div class="insight-title">Top 5</div><div class="insight-desc">${toppersList}</div></div>
    <div class="insight-card"><div class="insight-icon">📊</div><div class="insight-title">${pcmb > pcmc ? 'PCMB' : 'PCMC'}</div><div class="insight-desc">Dominant Combination</div></div>
    <div class="insight-card"><div class="insight-icon">⭐</div><div class="insight-title">${students.filter(s=>s.grade === 'A+').length}</div><div class="insight-desc">A+ Grade (90%+) Warriors</div></div>
  `;
  
  const observer = new IntersectionObserver(entries=>{ entries.forEach(e=>{ if(e.isIntersecting) e.target.classList.add('visible'); }); }, { threshold:0.05 });
  document.querySelectorAll('.reveal').forEach(el=>{ el.classList.remove('visible'); observer.observe(el); });
}

function loadCSVAndAnalyze(csvText) {
  const parsed = parseCSV(csvText);
  if (parsed.length === 0) { alert("No valid data! Ensure CSV has total column."); return false; }
  const mapped = parsed.map(mapStudent);
  document.getElementById('csvInputArea').style.display = 'none';
  document.getElementById('mainContent').style.display = 'block';
  renderDashboard(mapped);
  return true;
}



// click loadsample on entering page:
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('loadCsvBtn').onclick = () => {
        const csvText = document.getElementById('csvTextarea').value;
        if (!csvText.trim()) { alert("Please paste CSV data first!"); return; }
        loadCSVAndAnalyze(csvText);
};
  document.getElementById('loadSampleBtn').click();
});

document.getElementById('loadSampleBtn').onclick = () => {
  const sample = `roll_no,contact_no,name,class,combination,physics,chemistry,mathematics,subject4,subject4_name,english,language2,language2_name,total
25001,8310669725,ABHIJNA S SHETTY,I PUC - PCMB,PCMB,94,76,84,95,BIOLOGY,99,100,HINDI,548
25002,8073465428,ANVITHA N,I PUC - PCMB,PCMB,93,88,91,90,BIOLOGY,98,98,HINDI,558
25003,7022910180,AYESHA SAMRA,I PUC - PCMB,PCMB,95,98,94,97,BIOLOGY,99,98,HINDI,581
25004,9480579398,BHUVAN,I PUC - PCMB,PCMB,94,92,80,88,BIOLOGY,91,95,HINDI,540
25005,9029091231,CHARVI LAKSHMIKANT SALIAN,I PUC - PCMB,PCMB,79,71,79,67,BIOLOGY,88,89,HINDI,473
25006,8095924323,GAYATHRI M DEVADIGA,I PUC - PCMB,PCMB,94,96,96,98,BIOLOGY,98,100,HINDI,582
25007,6360537202,HARDHIKA SHETTY,I PUC - PCMB,PCMB,97,95,97,96,BIOLOGY,99,100,HINDI,584
25008,7219146397,ICCHA NIRANJAN SHETTY,I PUC - PCMB,PCMB,94,98,95,97,BIOLOGY,99,96,HINDI,579
25009,9845452133,KAPTHI MOHAMMED ATUF,I PUC - PCMB,PCMB,69,84,70,61,BIOLOGY,92,65,HINDI,441
25010,9742681144,KARAN VISHWAKARMA,I PUC - PCMB,PCMB,90,84,90,81,BIOLOGY,92,89,HINDI,526
25011,9741638256,KAUSHIKI S POOJARY,I PUC - PCMB,PCMB,94,74,91,87,BIOLOGY,97,98,HINDI,541
25012,7506705313,M POOJITHAKRISHNA,I PUC - PCMB,PCMB,98,100,95,98,BIOLOGY,99,100,HINDI,590
25013,8548010285,MANYA G SUVARNA,I PUC - PCMB,PCMB,78,72,68,90,BIOLOGY,99,99,HINDI,506
25014,8050025175,MOHAMMAD DANIYAL,I PUC - PCMB,PCMB,93,100,97,94,BIOLOGY,98,100,HINDI,582
25015,8747896067,MONISH B S,I PUC - PCMB,PCMB,87,91,80,89,BIOLOGY,99,81,HINDI,527
25016,9964142988,N G VIJAYALAKSHMI,I PUC - PCMB,PCMB,91,86,89,92,BIOLOGY,97,100,HINDI,555
25017,7760249403,NAITHIK SHETTY,I PUC - PCMB,PCMB,75,73,85,92,BIOLOGY,96,94,HINDI,515
25018,9448820346,NEHA CHETAN NAIK,I PUC - PCMB,PCMB,99,100,99,100,BIOLOGY,99,100,HINDI,597
25019,8884013973,NIDHI PAI M,I PUC - PCMB,PCMB,97,99,99,97,BIOLOGY,98,100,HINDI,590
25020,9448820346,NISHA CHETAN NAIK,I PUC - PCMB,PCMB,98,100,96,96,BIOLOGY,99,100,HINDI,589
25021,9731569614,NITHIKSHA D KANCHAN,I PUC - PCMB,PCMB,78,69,87,83,BIOLOGY,87,89,HINDI,493
25022,7019904869,PARNIKA V SHETTY,I PUC - PCMB,PCMB,74,79,70,81,BIOLOGY,96,93,HINDI,493
25023,9611186851,PAVITRA SHANKAR PRABHU,I PUC - PCMB,PCMB,92,83,76,90,BIOLOGY,96,99,HINDI,536
25024,9886474805,PRANAMYA K,I PUC - PCMB,PCMB,98,89,97,93,BIOLOGY,95,99,HINDI,571
25025,9008510021,PRANAV NARAYAN S M,I PUC - PCMB,PCMB,92,91,97,92,BIOLOGY,98,98,HINDI,568
25026,9448501043,PRAPTI MUKESH SHET,I PUC - PCMB,PCMB,97,99,98,95,BIOLOGY,99,100,HINDI,588
25027,8806360732,PRARTHANA,I PUC - PCMB,PCMB,74,79,78,81,BIOLOGY,93,82,HINDI,487
25028,8971955734,PRISHA P SHETTY,I PUC - PCMB,PCMB,91,89,99,83,BIOLOGY,98,92,HINDI,552
25029,9901657094,PRIYA,I PUC - PCMB,PCMB,98,96,94,95,BIOLOGY,98,100,HINDI,581
25030,7975340057,ALVA PUNYA CHANDRASHEKHAR,I PUC - PCMB,PCMB,80,72,82,83,BIOLOGY,94,95,HINDI,506
25031,9845247019,PUSHKARAN K,I PUC - PCMB,PCMB,88,80,87,82,BIOLOGY,94,93,HINDI,524
25032,9731488745,R SUDHANVA NAVADA,I PUC - PCMB,PCMB,77,86,83,80,BIOLOGY,91,92,HINDI,509
25033,9731434538,RANJANA N,I PUC - PCMB,PCMB,86,90,89,95,BIOLOGY,95,89,HINDI,544
25034,9886367003,RAUNAK MOHAN AMBERKAR,I PUC - PCMB,PCMB,93,87,93,93,BIOLOGY,95,91,HINDI,552
25035,9844897877,RISHA D RAI,I PUC - PCMB,PCMB,64,68,72,82,BIOLOGY,97,83,HINDI,466
25036,8660960117,SAANVI D KUNDER,I PUC - PCMB,PCMB,91,98,97,96,BIOLOGY,99,98,HINDI,579
25037,9486656059,SAANVI NITIN BILAGI,I PUC - PCMB,PCMB,92,96,99,93,BIOLOGY,95,96,HINDI,571
25038,9901659784,SAHANA R MENDON,I PUC - PCMB,PCMB,86,82,94,81,BIOLOGY,96,99,HINDI,538
25039,9986176634,SAI CHIRAG K N,I PUC - PCMB,PCMB,100,100,99,99,BIOLOGY,99,98,HINDI,595
25040,9448152139,SAMBRAM R KANJARPANE,I PUC - PCMB,PCMB,100,98,99,92,BIOLOGY,97,96,HINDI,582
25041,9900490696,SAMVITH RATHISH THANTRY,I PUC - PCMB,PCMB,70,68,76,80,BIOLOGY,95,97,HINDI,486
25042,8073959914,SANIKA SHETTY,I PUC - PCMB,PCMB,77,86,84,81,BIOLOGY,96,99,HINDI,523
25043,9740541812,SANVI A SHETTY,I PUC - PCMB,PCMB,58,50,46,69,BIOLOGY,94,88,HINDI,405
25044,9448094204,SANVI S SHETTY,I PUC - PCMB,PCMB,83,81,87,82,BIOLOGY,94,100,HINDI,527
25045,9480727992,SATHVIK BHAT A,I PUC - PCMB,PCMB,80,92,92,96,BIOLOGY,98,98,HINDI,556
25046,9886053977,SHARVARI RADHESH BEKAL,I PUC - PCMB,PCMB,96,94,92,92,BIOLOGY,99,92,HINDI,565
25047,9845370730,SHARVARI S S,I PUC - PCMB,PCMB,86,80,89,85,BIOLOGY,94,85,HINDI,519
25048,8861530531,SHRINIDHI V SHETTY,I PUC - PCMB,PCMB,54,65,63,59,BIOLOGY,91,85,HINDI,417
25049,7899491980,SNEHAL VENORA MENDONCA,I PUC - PCMB,PCMB,78,86,79,86,BIOLOGY,97,92,HINDI,518
25050,9686448802,SUDHANVA U MUNDKUR,I PUC - PCMB,PCMB,99,98,100,99,BIOLOGY,99,100,HINDI,595
25051,9738934943,SUMITH SHRIKANTH HUNALLI,I PUC - PCMB,PCMB,76,88,94,91,BIOLOGY,90,91,HINDI,530
25052,8197120018,SUMUKHA RAO B S,I PUC - PCMB,PCMB,98,93,98,98,BIOLOGY,96,100,HINDI,583
25053,9986566211,SUPRAJ U,I PUC - PCMB,PCMB,94,92,92,95,BIOLOGY,96,98,HINDI,567
25054,9831089289,SWAPNIL SEAL,I PUC - PCMB,PCMB,71,69,62,78,BIOLOGY,88,90,HINDI,458
25055,9980899168,TUSHARA SHANKARA,I PUC - PCMB,PCMB,88,88,92,89,BIOLOGY,99,86,HINDI,542
25056,9844773573,VAMSHI KRISHNA DEVARAMANE,I PUC - PCMB,PCMB,99,100,100,97,BIOLOGY,99,100,HINDI,595
25057,9844733847,VARSHINI S MOHARER,I PUC - PCMB,PCMB,99,97,92,97,BIOLOGY,99,99,HINDI,583
25058,7019001843,YASH SHETTY,I PUC - PCMB,PCMB,87,90,89,96,BIOLOGY,97,95,HINDI,554
25059,9481250027,AARNAV NIKIN SHETTY,I PUC - PCMB,PCMB,88,82,76,86,BIOLOGY,93,56,HINDI,481
25060,9482625925,ADARSH B R,I PUC - PCMB,PCMB,91,84,82,75,BIOLOGY,89,98,HINDI,519
25061,8884599266,ALAA TAYYABA SHEIKH,I PUC - PCMB,PCMB,88,91,81,90,BIOLOGY,93,99,HINDI,542
25062,9945797188,ALENA RITA FERNANDES,I PUC - PCMB,PCMB,99,98,100,99,BIOLOGY,99,99,HINDI,594
25063,8277615108,AMOGH RAVINDRA BABLESHWAR,I PUC - PCMB,PCMB,47,46,42,54,BIOLOGY,70,82,HINDI,341
25064,9448251515,AMRUTHA D,I PUC - PCMB,PCMB,93,83,87,91,BIOLOGY,92,100,HINDI,546
25065,8217308239,ANSHUL P BHANDARY,I PUC - PCMB,PCMB,91,86,94,85,BIOLOGY,92,95,HINDI,543
25066,9902378399,ANVESH SHETTY,I PUC - PCMB,PCMB,92,93,90,98,BIOLOGY,96,98,HINDI,567
25067,9448621930,ANVESH U SHETTY,I PUC - PCMB,PCMB,86,91,81,89,BIOLOGY,86,93,HINDI,526
25068,7411112345,ATHARV NAGARAJ RAO,I PUC - PCMB,PCMB,66,84,81,90,BIOLOGY,90,84,HINDI,495
25069,9845303053,AVILASH RAO B,I PUC - PCMB,PCMB,93,89,95,90,BIOLOGY,94,98,HINDI,559
25070,8147455647,AYAAN ASHFAQ AHMED,I PUC - PCMB,PCMB,92,91,94,98,BIOLOGY,94,86,HINDI,555
25071,9449390257,AYUSH SHETTY,I PUC - PCMB,PCMB,99,100,97,98,BIOLOGY,94,100,HINDI,588
25072,9110831417,BRINDA B SHETTY,I PUC - PCMB,PCMB,83,68,76,79,BIOLOGY,89,100,HINDI,495
25073,9663115151,CEDRIC SONY,I PUC - PCMB,PCMB,83,63,60,84,BIOLOGY,90,80,HINDI,460
25074,9686917725,CHINMAYI,I PUC - PCMB,PCMB,81,87,83,82,BIOLOGY,95,99,HINDI,527
25075,9964499939,CHIRAG G RAO,I PUC - PCMB,PCMB,91,85,71,91,BIOLOGY,88,82,HINDI,508
25076,7204087407,DANICE VICTORIA KARKADA,I PUC - PCMB,PCMB,87,83,90,90,BIOLOGY,97,100,HINDI,547
25077,9845383625,DELVIN ARYAN MUTHU,I PUC - PCMB,PCMB,74,79,72,90,BIOLOGY,93,94,HINDI,502
25078,8600663919,EIKYATA HARISH SHETTY,I PUC - PCMB,PCMB,91,85,80,94,BIOLOGY,95,96,HINDI,541
25079,9538653479,H MUHAMMED ZAYAAN,I PUC - PCMB,PCMB,72,62,48,78,BIOLOGY,90,59,HINDI,409
25080,6360657970,HARSHIT DEVANAGAON,I PUC - PCMB,PCMB,93,85,79,92,BIOLOGY,91,99,HINDI,539
25081,9972376612,HENCILA LORA DSOUZA,I PUC - PCMB,PCMB,90,89,83,89,BIOLOGY,94,98,HINDI,543
25082,9880783491,IMAN IHSAN AHMED,I PUC - PCMB,PCMB,78,64,51,75,BIOLOGY,94,97,HINDI,459
25083,6362782484,JELIN D ALMEIDA,I PUC - PCMB,PCMB,74,63,49,66,BIOLOGY,93,82,HINDI,427
25084,8310598950,K KRITHIKA SOMAYAJI,I PUC - PCMB,PCMB,80,66,77,66,BIOLOGY,86,98,HINDI,473
25085,9448953001,K PRABHAV UPADHYA,I PUC - PCMB,PCMB,98,96,100,96,BIOLOGY,96,100,HINDI,586
25086,8073770967,KRISHNA KEERTHI K,I PUC - PCMB,PCMB,97,91,94,93,BIOLOGY,98,100,HINDI,573
25087,9880202419,MAHIKA,I PUC - PCMB,PCMB,92,89,91,91,BIOLOGY,92,99,HINDI,554
25088,9741150087,MANDARA B SUVARNA,I PUC - PCMB,PCMB,89,92,98,91,BIOLOGY,94,100,HINDI,564
25089,9740070418,MANISHRI SHETTY,I PUC - PCMB,PCMB,91,85,90,92,BIOLOGY,91,98,HINDI,547
25090,8861912353,MANYA SHIVANANDA,I PUC - PCMB,PCMB,88,80,69,82,BIOLOGY,94,86,HINDI,499
25091,9741193462,NIKHIL RAMCHANDRA JOSHI,I PUC - PCMB,PCMB,86,81,80,82,BIOLOGY,82,94,HINDI,505
25092,9739404485,NIRUPRASAD SHETTY,I PUC - PCMB,PCMB,90,89,86,81,BIOLOGY,90,100,HINDI,536
25093,9901657817,NISHITA H SHETTY,I PUC - PCMB,PCMB,98,99,95,96,BIOLOGY,97,100,HINDI,585
25094,9740087287,NIYATHI P POOJARI,I PUC - PCMB,PCMB,95,96,96,99,BIOLOGY,94,99,HINDI,579
25095,9844219160,PARINITHA,I PUC - PCMB,PCMB,100,100,96,96,BIOLOGY,97,100,HINDI,589
25096,8380898068,POOJA D SHET,I PUC - PCMB,PCMB,90,83,84,92,BIOLOGY,95,94,HINDI,538
25097,9113613538,PRAJNA S NAIK,I PUC - PCMB,PCMB,93,87,99,77,BIOLOGY,97,100,HINDI,553
25098,9980880207,PRAKYATH R RAO,I PUC - PCMB,PCMB,98,96,100,94,BIOLOGY,95,99,HINDI,582
25099,9449454254,PRANAV R BHAT,I PUC - PCMB,PCMB,83,76,77,74,BIOLOGY,94,88,HINDI,492
25100,9234638777,PRANEETA SHARAN,I PUC - PCMB,PCMB,99,95,97,97,BIOLOGY,97,98,HINDI,583
25101,9535561731,PRARTHANA S POOJARY,I PUC - PCMB,PCMB,90,77,83,91,BIOLOGY,91,89,HINDI,521
25102,9110818485,RAGHAVI R JERE,I PUC - PCMB,PCMB,63,58,60,60,BIOLOGY,86,72,HINDI,399
25103,9986411497,REHAN S RON,I PUC - PCMB,PCMB,60,64,58,56,BIOLOGY,82,73,HINDI,393
25104,9632093136,ROSHNI PRAMOD KARKERA,I PUC - PCMB,PCMB,89,82,92,81,BIOLOGY,88,98,HINDI,530
25105,9686628592,S ANIRUDH,I PUC - PCMB,PCMB,94,91,94,91,BIOLOGY,95,87,HINDI,552
25106,9844627552,SAISPARSHA K,I PUC - PCMB,PCMB,96,98,98,99,BIOLOGY,98,100,HINDI,589
25107,9448723852,SAMHITA UPPOOR,I PUC - PCMB,PCMB,76,72,68,80,BIOLOGY,90,96,HINDI,482
25108,8197079049,SAMRAZ SARFRAZ KHADER,I PUC - PCMB,PCMB,90,89,93,88,BIOLOGY,94,83,HINDI,537
25109,8217520165,SANWI S RAO,I PUC - PCMB,PCMB,91,96,96,96,BIOLOGY,94,99,HINDI,572
25110,9448843911,SHRESHTA A,I PUC - PCMB,PCMB,96,100,98,98,BIOLOGY,96,100,HINDI,588
25111,9980272164,SOUHARDH R SHETTY,I PUC - PCMB,PCMB,90,87,95,87,BIOLOGY,93,86,HINDI,538
25112,8123600135,SUHAN R SHETTY,I PUC - PCMB,PCMB,88,72,74,86,BIOLOGY,89,86,HINDI,495
25113,9663642580,SUNAINA,I PUC - PCMB,PCMB,93,98,92,92,BIOLOGY,93,96,HINDI,564
25114,9243388835,TANISHKA S NAYAK,I PUC - PCMB,PCMB,83,74,71,83,BIOLOGY,89,96,HINDI,496
25115,9448282865,TANVI AMRTHESHA ARIGA,I PUC - PCMB,PCMB,97,99,97,98,BIOLOGY,99,100,HINDI,590
25116,9482502956,THASMAYI A KUNDAR,I PUC - PCMB,PCMB,86,80,73,85,BIOLOGY,87,79,HINDI,490
25117,9844993773,VARSHA SALIAN,I PUC - PCMB,PCMB,83,87,85,89,BIOLOGY,95,97,HINDI,536
25118,9945773128,VIJETH KRISHNA KUNTAR,I PUC - PCMB,PCMB,57,51,41,71,BIOLOGY,78,90,HINDI,388
25119,9945364820,VISHRTH,I PUC - PCMB,PCMB,99,99,99,99,BIOLOGY,97,99,HINDI,592
25120,9845136018,YUKTHA G,I PUC - PCMB,PCMB,88,89,94,93,BIOLOGY,95,95,HINDI,554
25201,7760950049,AADHYA S SHETTY,I PUC - PCMC,PCMC,93,72,85,95,CSC,97,95,SANSKRIT,537
25202,9945124225,AARUSH A SHETTY,I PUC - PCMC,PCMC,99,96,98,99,CSC,99,98,SANSKRIT,589
25203,6362266119,ACHINTHYA KRISHNA S R,I PUC - PCMC,PCMC,95,96,100,99,CSC,95,98,SANSKRIT,583
25204,9686472067,AKARSH CHANDRA M,I PUC - PCMC,PCMC,95,96,95,100,CSC,99,93,SANSKRIT,578
25205,9880935608,AMOGH M RAO,I PUC - PCMC,PCMC,84,76,93,99,CSC,97,99,SANSKRIT,548
25206,9731827833,ANANYA N HEGDE,I PUC - PCMC,PCMC,97,94,95,98,CSC,98,100,SANSKRIT,582
25207,9767789283,ASHISH U SHETTY,I PUC - PCMC,PCMC,75,69,69,94,CSC,82,81,SANSKRIT,470
25208,9449331837,C V MOULYA,I PUC - PCMC,PCMC,96,95,98,99,CSC,98,100,SANSKRIT,586
25209,9480159487,DHEERAJ D NAYAK,I PUC - PCMC,PCMC,98,100,99,99,CSC,98,100,SANSKRIT,594
25210,9686434105,DHRISHA D SHETTY,I PUC - PCMC,PCMC,91,91,97,98,CSC,96,90,SANSKRIT,563
25211,9902189585,JASHITH S SUVARNA,I PUC - PCMC,PCMC,73,76,65,94,CSC,78,88,SANSKRIT,474
25212,9036279077,JITHESH,I PUC - PCMC,PCMC,92,87,96,97,CSC,95,95,SANSKRIT,562
25213,9241660977,K RITHVIK KINI,I PUC - PCMC,PCMC,51,60,47,92,CSC,66,80,SANSKRIT,396
25214,7624840704,K SHREENITH S SHERIGAR,I PUC - PCMC,PCMC,99,98,100,100,CSC,97,100,SANSKRIT,594
25215,9035128666,K UTTAM BHAKTHA,I PUC - PCMC,PCMC,84,64,80,91,CSC,80,91,SANSKRIT,490
25216,9740374645,KARMIN H SHETTY,I PUC - PCMC,PCMC,84,81,84,94,CSC,96,93,SANSKRIT,532
25217,9980854016,KARTHIK G,I PUC - PCMC,PCMC,94,85,90,100,CSC,91,93,SANSKRIT,553
25218,7812961799,LAVANYA UDUPA,I PUC - PCMC,PCMC,94,99,94,99,CSC,98,100,SANSKRIT,584
25219,7406996947,MANYA S BALLAL,I PUC - PCMC,PCMC,94,99,98,100,CSC,97,99,SANSKRIT,587
25220,9731418787,MIHIR B SUVARNA,I PUC - PCMC,PCMC,75,60,85,96,CSC,93,91,SANSKRIT,500
25221,9740299360,NAGARAJA B SHETTY,I PUC - PCMC,PCMC,90,84,96,98,CSC,86,81,SANSKRIT,535
25222,8217855705,NAMAN BASAVARAJ DESAI,I PUC - PCMC,PCMC,98,99,99,100,CSC,98,99,SANSKRIT,593
25223,9480433743,NEHA U SALIAN,I PUC - PCMC,PCMC,93,82,90,98,CSC,96,97,SANSKRIT,556
25225,9964069416,PRANAV RAO,I PUC - PCMC,PCMC,96,99,97,99,CSC,100,100,SANSKRIT,591
25226,9844643293,PRATEEK,I PUC - PCMC,PCMC,,,,,,,,,
25227,9740085455,RITHWIK S HEGDE,I PUC - PCMC,PCMC,97,82,91,98,CSC,95,94,SANSKRIT,557
25228,8451085461,S HEMANTH,I PUC - PCMC,PCMC,95,95,98,99,CSC,97,99,SANSKRIT,583
25229,9844210310,SAMARTH B GOWDA,I PUC - PCMC,PCMC,61,58,53,83,CSC,92,68,SANSKRIT,415
25230,8884518789,SAMBHRAM PRASHANT MESTA,I PUC - PCMC,PCMC,71,55,60,86,CSC,84,53,SANSKRIT,409
25231,9980127849,SAMYAK S ACHARYA,I PUC - PCMC,PCMC,88,85,93,94,CSC,84,79,SANSKRIT,523
25232,9483862270,SANATH S KOTIAN,I PUC - PCMC,PCMC,97,100,100,100,CSC,97,100,SANSKRIT,594
25233,8310179844,SANJAY J ACHARYA,I PUC - PCMC,PCMC,84,77,83,95,CSC,92,55,SANSKRIT,486
25234,9611296623,SANVI SHETTY,I PUC - PCMC,PCMC,88,85,95,99,CSC,96,97,SANSKRIT,560
25235,8197681566,SHAMAN NAIK,I PUC - PCMC,PCMC,66,72,81,93,CSC,88,91,SANSKRIT,491
25236,9686925838,SHISHIR PRASHANTHA ACHAR,I PUC - PCMC,PCMC,66,61,58,88,CSC,86,91,SANSKRIT,450
25237,9741116783,SOHAM A SHRIYAN,I PUC - PCMC,PCMC,51,59,56,80,CSC,76,63,SANSKRIT,385
25238,8277766621,SRUSHTI J SHETTY,I PUC - PCMC,PCMC,59,66,60,90,CSC,88,86,SANSKRIT,449
25239,8217784029,SRUSHTI M R,I PUC - PCMC,PCMC,90,83,91,94,CSC,93,95,SANSKRIT,546
25240,9449464631,SUGHOSH BHARADWAJ,I PUC - PCMC,PCMC,99,100,100,99,CSC,99,100,SANSKRIT,597
25241,9902960411,SWARNALAKSHMI K MOODUBELLE,I PUC - PCMC,PCMC,89,91,96,95,CSC,93,90,SANSKRIT,554
25242,9731736013,TANVI SHETTY,I PUC - PCMC,PCMC,95,79,91,100,CSC,96,98,SANSKRIT,559
25243,9148726190,TUSHAR KHARVI,I PUC - PCMC,PCMC,95,89,99,98,CSC,96,100,SANSKRIT,577
25244,9481144853,VALLIKANTH BHAT,I PUC - PCMC,PCMC,93,83,75,95,CSC,81,92,SANSKRIT,519
25245,9900410511,VISHWAS S K,I PUC - PCMC,PCMC,90,84,89,97,CSC,97,97,SANSKRIT,554
25246,9972269480,ABHIMAN SHETTY,I PUC - PCMC,PCMC,88,83,69,98,CSC,82,92,SANSKRIT,512
25247,9740862116,ABIN S,I PUC - PCMC,PCMC,76,91,81,96,CSC,89,89,SANSKRIT,522
25248,8087629045,ADITI ARUNKUMAR CHANDAN,I PUC - PCMC,PCMC,61,76,56,90,CSC,93,88,SANSKRIT,464
25249,9844211835,AKASH RAVINDRA PRABHU,I PUC - PCMC,PCMC,95,100,99,99,CSC,96,99,SANSKRIT,588
25250,9900753843,AMRUTHA ASHOK,I PUC - PCMC,PCMC,58,67,53,91,CSC,86,90,SANSKRIT,445
25251,9740948907,ARYAN U ACHARYA,I PUC - PCMC,PCMC,68,81,76,93,CSC,86,80,SANSKRIT,484
25252,9964281312,BHAGAT RAJ M,I PUC - PCMC,PCMC,61,73,59,87,CSC,88,74,SANSKRIT,442
25253,9342136083,BHOOMIKA H PUTHRAN,I PUC - PCMC,PCMC,99,99,99,98,CSC,99,100,SANSKRIT,594
25254,8095577499,BRINDA J,I PUC - PCMC,PCMC,50,57,42,75,CSC,90,83,SANSKRIT,397
25255,6364144714,CHINMAYANANDA,I PUC - PCMC,PCMC,,,,,,,,,
25256,9740940700,DHRUTHI U S,I PUC - PCMC,PCMC,96,94,99,99,CSC,96,99,SANSKRIT,583
25257,9740934648,GREESHAN ASHWIN BANGERA,I PUC - PCMC,PCMC,77,88,67,90,CSC,89,91,SANSKRIT,502
25258,9632648871,HARSHITHA ASHOKA ACHARI,I PUC - PCMC,PCMC,95,95,96,98,CSC,96,98,SANSKRIT,578
25259,8496828117,JAYADEEP POOJARY,I PUC - PCMC,PCMC,99,100,100,99,CSC,93,98,SANSKRIT,589
25260,9845406657,K HEMANTH BHAT,I PUC - PCMC,PCMC,93,99,97,99,CSC,95,95,SANSKRIT,578
25261,9241297658,K KRISHNA PRANAV,I PUC - PCMC,PCMC,47,62,41,88,CSC,88,91,SANSKRIT,417
25262,9964477781,KRUTHIKA A SHETTY,I PUC - PCMC,PCMC,91,85,81,97,CSC,95,97,SANSKRIT,546
25263,9448428676,MELRIA FERNANDES,I PUC - PCMC,PCMC,87,85,80,99,CSC,95,96,SANSKRIT,542
25264,9901048688,MOHAMMED AFRAAZ,I PUC - PCMC,PCMC,100,100,97,98,CSC,92,97,SANSKRIT,584
25266,8971548576,MOHAMMED SAHIL,I PUC - PCMC,PCMC,70,65,68,86,CSC,83,70,SANSKRIT,442
25267,7899470543,NAMISH UDAYA BILLAVA,I PUC - PCMC,PCMC,100,99,100,98,CSC,98,98,SANSKRIT,593
25268,9606355149,NILSHIKA,I PUC - PCMC,PCMC,64,75,71,95,CSC,89,93,SANSKRIT,487
25269,9110895728,NITHIKA N KARKERA,I PUC - PCMC,PCMC,88,87,80,99,CSC,92,93,SANSKRIT,539
25270,9483732359,PRAJWAL PRASHANTHA ACHARYA,I PUC - PCMC,PCMC,74,82,58,94,CSC,86,89,SANSKRIT,483
25271,9945867616,PRATHVIN,I PUC - PCMC,PCMC,95,100,98,99,CSC,98,98,SANSKRIT,588
25272,8762246703,PREKSHANA DESHPANDE,I PUC - PCMC,PCMC,69,73,70,99,CSC,85,95,SANSKRIT,491
25273,9740059943,RAJATH PRABHU P,I PUC - PCMC,PCMC,93,86,84,96,CSC,90,98,SANSKRIT,547
25274,9482040402,RITHIN S SHETTY,I PUC - PCMC,PCMC,100,100,100,99,CSC,95,100,SANSKRIT,594
25275,9972130134,SAANVI JAGANNATHA SUVARNA,I PUC - PCMC,PCMC,95,93,98,98,CSC,96,99,SANSKRIT,579
25276,9611849261,SACHIN S MARALADINNI,I PUC - PCMC,PCMC,53,57,57,82,CSC,83,60,SANSKRIT,392
25277,9448108563,SATHWIK KUNDER,I PUC - PCMC,PCMC,71,79,78,98,CSC,86,61,SANSKRIT,473
25278,9448532940,SATHWIK R PATEL,I PUC - PCMC,PCMC,72,68,74,83,CSC,80,84,SANSKRIT,461
25279,9964451514,SHASHIDHARA R HEBBAR,I PUC - PCMC,PCMC,56,59,45,85,CSC,83,86,SANSKRIT,414
25280,9901207259,SHOURYA S SALIAN,I PUC - PCMC,PCMC,99,96,98,98,CSC,94,99,SANSKRIT,584
25281,9686126724,SHREESHA KRISHNA,I PUC - PCMC,PCMC,61,71,72,92,CSC,81,93,SANSKRIT,470
25282,9449547947,SHRI RAMANA V UPADHYAYA,I PUC - PCMC,PCMC,53,68,63,92,CSC,84,96,SANSKRIT,456
25283,9108052100,SOUMYA ABHISHIKTA ACHARY,I PUC - PCMC,PCMC,82,78,84,98,CSC,95,98,SANSKRIT,535
25284,9980253227,SPOORTHI S SUVARNA,I PUC - PCMC,PCMC,98,98,97,99,CSC,97,99,SANSKRIT,588
25285,7483549776,SRAJAN R KOTIAN,I PUC - PCMC,PCMC,65,62,65,78,CSC,85,69,SANSKRIT,424
25287,9980439109,TANISH SHETTY,I PUC - PCMC,PCMC,93,77,68,92,CSC,88,85,SANSKRIT,503
25288,9480758925,TANISHKA M KOTEGAR,I PUC - PCMC,PCMC,87,95,94,100,CSC,91,100,SANSKRIT,567
25289,9449450858,VISHRUTHA M SHETTY,I PUC - PCMC,PCMC,52,56,40,57,CSC,78,59,SANSKRIT,342
25290,8971524711,YASHIKA DEVADIGA,I PUC - PCMC,PCMC,92,91,96,99,CSC,90,97,SANSKRIT,565
25291,9964584864,YATHARTH PRASAD,I PUC - PCMC,PCMC,70,77,68,98,CSC,93,84,SANSKRIT,490
`;
  document.getElementById('csvTextarea').value = sample;
  loadCSVAndAnalyze(sample);
};

document.getElementById('resetBtn').onclick = () => {
  document.getElementById('csvInputArea').style.display = 'block';
  document.getElementById('mainContent').style.display = 'none';
  document.getElementById('csvTextarea').value = '';
  document.getElementById('dataStatus').innerHTML = '';
};
</script>
</body>
</html>
    """


if __name__ == "__main__":
    app.run(debug=True)
