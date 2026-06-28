from flask import Flask, Blueprint, jsonify, request, render_template, session, redirect, url_for, abort, send_from_directory, render_template_string
import os
import csv
from functools import wraps
import json
import re
import base64
import json
import re
import urllib.request
import urllib.error

# ── Hardcoded password ──
PASSWORD = "jut2025"

# ── GitHub configuration ──
# Set these as environment variables for security
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO = 'Dheeraj-Nayak-2009/60.jut.analysis'
GITHUB_PATH = 'master/subject_swaps.json'
GITHUB_BRANCH = 'main'

app = Flask(__name__)
app.secret_key = 'supersecretkey-change-in-production'  # Use env var in production

# ── Login required decorator ──
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def get_github_file_sha():
    """Get the SHA of the current file on GitHub."""
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}'
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('sha')
    except urllib.error.HTTPError as e:
        print(f"GitHub API error: {e.code} {e.reason}")
        return None

def update_github_file(content, commit_message):
    """Update the file on GitHub with new content."""
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}'
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
    }
    
    sha = get_github_file_sha()
    if not sha:
        return {'error': 'Could not get file SHA'}, 500

    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {
        'message': commit_message,
        'content': content_b64,
        'sha': sha,
        'branch': GITHUB_BRANCH
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method='PUT'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8')), resp.status
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return {'error': f'{e.code} {e.reason}: {error_body}'}, e.code

@app.route("/api/swaps")
@login_required
def get_swaps():
    """Get current swaps from GitHub."""
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}'
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            content = base64.b64decode(data['content']).decode('utf-8')
            swaps = json.loads(content)
            return jsonify(swaps)
    except Exception as e:
        print(f"Error fetching swaps: {e}")
        return jsonify({}), 200

@app.route("/api/swaps", methods=['POST'])
@login_required
def update_swaps():
    """Update swaps on GitHub."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate structure
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid format'}), 400
    
    for key, value in data.items():
        if not isinstance(value, dict) or 'swap' not in value:
            return jsonify({'error': f'Invalid entry for {key}'}), 400
        if not isinstance(value['swap'], dict):
            return jsonify({'error': f'Invalid swap for {key}'}), 400
    
    # Format as pretty JSON
    content = json.dumps(data, indent=2, sort_keys=True)
    result, status = update_github_file(content, 'Update subject swaps via UI')
    
    if status == 200:
        return jsonify({'success': True, 'message': 'Swaps updated successfully'})
    else:
        return jsonify({'error': result.get('error', 'Update failed')}), status


# ── Login / Logout routes ──
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == PASSWORD:
            session['logged_in'] = True
            next_url = request.args.get('next') or url_for('read_root')
            return redirect(next_url)
        else:
            return render_template_string(LOGIN_HTML, error="Incorrect password. Try again.")
    return render_template_string(LOGIN_HTML, error=None)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ── Halving correction ──
def halve_row_if_needed(row):
    """If any attempt field > 75, halve all relevant numeric fields in place."""
    attempt_keys = ['total_attempt', 'phy_attempt', 'chem_attempt', 'math_attempt']
    for k in attempt_keys:
        if k in row and row[k].strip():
            try:
                val = float(row[k])
                if val > 75:
                    fields_to_halve = [
                        'total_score', 'phy_attempt', 'chem_attempt', 'math_attempt', 'total_attempt',
                        'phy_correct', 'chem_correct', 'math_correct', 'total_correct',
                        'phy_wrong', 'chem_wrong', 'math_wrong', 'total_wrong',
                        'phy_marks', 'chem_marks', 'math_marks', 'total_marks'
                    ]
                    for f in fields_to_halve:
                        if f in row and row[f].strip():
                            try:
                                row[f] = str(float(row[f]) / 2.0)
                            except ValueError:
                                pass
                    break  # only halve once per row
            except ValueError:
                pass
    return row

# ── API blueprint ──
api_bp = Blueprint('api', __name__)

@api_bp.before_request
def api_login_required():
    if not session.get('logged_in'):
        return jsonify({"error": "Authentication required"}), 401

@api_bp.get("/api/csv-files")
def list_csv_files():
    static_dir = app.static_folder
    files = [f for f in os.listdir(static_dir) if f.endswith('.csv')]
    return jsonify(sorted(files))

@api_bp.get("/api/master-data")
def get_master_data():
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    rows = []
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
            apply_subject_swaps(clean)
            halve_row_if_needed(clean)
            rows.append(clean)
    return jsonify(rows)

@api_bp.get("/api/student/<path:student_name>")
def get_student_data(student_name):
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    results = []
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
            if clean.get('name', '').strip().lower() == student_name.strip().lower():
                apply_subject_swaps(clean)
                halve_row_if_needed(clean)
                results.append(clean)
    return jsonify(results)

@api_bp.get("/api/elites")
def get_elites():
    import json, math
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    rows = []
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
            apply_subject_swaps(clean)
            halve_row_if_needed(clean)
            rows.append(clean)
    students = {}
    for r in rows:
        name = r.get('name','').strip()
        if not name: continue
        key = name.upper().replace('  ',' ')
        file_val = r.get('file','') or r.get('filename','')
        inst = 'KJS' if file_val.upper().startswith('K') else 'UJS' if file_val.upper().startswith('U') else 'MJS' if file_val.upper().startswith('M') else ''
        if key not in students:
            students[key] = {'name': name, 'inst': inst, 'rows': [], 'file': file_val}
        students[key]['rows'].append(r)
        if not students[key]['inst'] and inst:
            students[key]['inst'] = inst
        if not students[key]['file'] and file_val:
            students[key]['file'] = file_val
    result = []
    all_avgs = []
    for key, s in students.items():
        attended = [r for r in s['rows'] if (float(r.get('total_marks',0) or r.get('total_score',0) or 0)) > 0 or float(r.get('total_attempt',0) or 0) > 0]
        scores = [float(r.get('total_marks',0) or r.get('total_score',0) or 0) for r in attended]
        if not scores: continue
        avg_score = sum(scores)/len(scores)
        all_avgs.append((key, avg_score))
    all_avgs.sort(key=lambda x: -x[1])
    rank_map = {k: i+1 for i,(k,_) in enumerate(all_avgs)}
    total_students = len(all_avgs)
    for key, s in students.items():
        attended = [r for r in s['rows'] if (float(r.get('total_marks',0) or r.get('total_score',0) or 0)) > 0 or float(r.get('total_attempt',0) or 0) > 0]
        if not attended: continue
        scores = [float(r.get('total_marks',0) or r.get('total_score',0) or 0) for r in attended]
        phy   = [float(r.get('phy_marks',0) or r.get('physics_marks',0) or 0) for r in attended]
        chem  = [float(r.get('chem_marks',0) or r.get('chemistry_marks',0) or 0) for r in attended]
        math  = [float(r.get('math_marks',0) or r.get('maths_marks',0) or 0) for r in attended]
        tc    = [float(r.get('total_correct',0) or 0) for r in attended]
        ta    = [float(r.get('total_attempt',0) or 0) for r in attended]
        avg_score = sum(scores)/len(scores)
        best_score = max(scores)
        avg_phy = sum(phy)/len(phy) if phy else 0
        avg_chem = sum(chem)/len(chem) if chem else 0
        avg_math = sum(math)/len(math) if math else 0
        overall_acc = round(sum(tc)/sum(ta)*100) if sum(ta) > 0 else 0
        rank = rank_map.get(key, 9999)
        pct_rank = round(rank/total_students*100) if total_students else 100
        sd = math_module_sd(scores)
        consistency = max(0, round(100 - sd/avg_score*100)) if avg_score > 0 and len(scores) >= 3 else None
        subj_avgs = {'Physics': avg_phy, 'Chemistry': avg_chem, 'Maths': avg_math}
        dominant = max(subj_avgs, key=subj_avgs.get)
        badges = []
        if rank == 1: badges.append({'id':'rank1','label':'#1 Overall','tier':'legendary','icon':'👑'})
        if rank <= 3: badges.append({'id':'podium','label':'Podium','tier':'gold','icon':'🏅'})
        if rank <= 10: badges.append({'id':'top10','label':'Top 10','tier':'gold','icon':'⭐'})
        if pct_rank <= 10: badges.append({'id':'elite10','label':'Top 10%','tier':'silver','icon':'🔱'})
        if pct_rank <= 25: badges.append({'id':'top25','label':'Top 25%','tier':'silver','icon':'💎'})
        if best_score >= 300: badges.append({'id':'perfect','label':'Perfect Score','tier':'legendary','icon':'✨'})
        if best_score >= 280: badges.append({'id':'near_perfect','label':'Near Perfect','tier':'gold','icon':'🌟'})
        if overall_acc >= 80: badges.append({'id':'sharpshooter','label':'Sharpshooter','tier':'gold','icon':'🎯'})
        if overall_acc >= 70: badges.append({'id':'precise','label':'Precision','tier':'silver','icon':'🔬'})
        if consistency is not None and consistency >= 85: badges.append({'id':'ironwall','label':'Iron Wall','tier':'gold','icon':'🔒'})
        if consistency is not None and consistency >= 70: badges.append({'id':'consistent','label':'Consistent','tier':'silver','icon':'📐'})
        if len(attended) == len(set(r.get('test','') for r in s['rows'])): badges.append({'id':'perfect_att','label':'Perfect Attendance','tier':'silver','icon':'📅'})
        if avg_phy >= 80: badges.append({'id':'phy_ace','label':'Physics Ace','tier':'silver','icon':'⚛️'})
        if avg_chem >= 80: badges.append({'id':'chem_ace','label':'Chemistry Ace','tier':'silver','icon':'🧪'})
        if avg_math >= 80: badges.append({'id':'math_ace','label':'Maths Ace','tier':'silver','icon':'∑'})
        if avg_phy >= 90: badges.append({'id':'phy_god','label':'Physics God','tier':'gold','icon':'⚡'})
        if avg_chem >= 90: badges.append({'id':'chem_god','label':'Chem Genius','tier':'gold','icon':'🔭'})
        if avg_math >= 90: badges.append({'id':'math_god','label':'Math Wizard','tier':'gold','icon':'🌀'})
        if len(scores) >= 3 and all(scores[i] < scores[i+1] for i in range(len(scores)-3, len(scores)-1)):
            badges.append({'id':'rising','label':'Rising Star','tier':'silver','icon':'📈'})
        if not badges and pct_rank > 50: continue
        file_base = os.path.splitext(os.path.basename(s['file']))[0] if s['file'] else ''
        result.append({
            'name': s['name'],
            'inst': s['inst'],
            'rank': rank,
            'avg_score': round(avg_score, 1),
            'best_score': best_score,
            'avg_phy': round(avg_phy, 1),
            'avg_chem': round(avg_chem, 1),
            'avg_math': round(avg_math, 1),
            'accuracy': overall_acc,
            'attended': len(attended),
            'consistency': consistency,
            'dominant_subject': dominant,
            'pct_rank': pct_rank,
            'badges': badges,
            'photo': f'/img/{file_base}.jpg' if file_base else '',
        })
    result.sort(key=lambda x: x['rank'])
    return jsonify(result)

def math_module_sd(scores):
    import math
    if len(scores) < 2: return 0
    m = sum(scores)/len(scores)
    return math.sqrt(sum((x-m)**2 for x in scores)/len(scores))

@api_bp.get("/api/subject-swaps")
def get_subject_swaps():
    return jsonify(load_subject_swaps())

@api_bp.get("/api/anomalies")
def get_anomalies():
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    rows = []
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
            apply_subject_swaps(clean)
            # Check if any attempt > 75
            attempt_keys = ['total_attempt', 'phy_attempt', 'chem_attempt', 'math_attempt']
            is_anomaly = False
            for k in attempt_keys:
                if k in clean and clean[k].strip():
                    try:
                        if float(clean[k]) > 75:
                            is_anomaly = True
                            break
                    except ValueError:
                        pass
            if is_anomaly:
                rows.append(clean)
    # Group by test
    grouped = {}
    for r in rows:
        test = r.get('test', 'Unknown')
        if test not in grouped:
            grouped[test] = []
        grouped[test].append(r)
    # Sort tests
    sorted_tests = sorted(grouped.keys())
    result = {t: grouped[t] for t in sorted_tests}
    return jsonify(result)

#______SWAP______#

SWAPS_FILE = os.path.join(os.path.dirname(app.static_folder), 'master', 'subject_swaps.json')
_subject_swaps = None

def load_subject_swaps():
    global _subject_swaps
    if _subject_swaps is not None:
        return _subject_swaps
    if os.path.exists(SWAPS_FILE):
        with open(SWAPS_FILE, 'r', encoding='utf-8') as f:
            _subject_swaps = json.load(f)
    else:
        _subject_swaps = {}
    return _subject_swaps

def extract_test_code(test_field):
    """Extract numeric code from test field, e.g. 'Details of NEW JEE: 9488' -> '9488'"""
    if not test_field:
        return None
    # Try to find a number after a colon or at the end
    m = re.search(r':\s*(\d+)', test_field)
    if m:
        return m.group(1)
    # Fallback: any number in the string
    m = re.search(r'\b(\d+)\b', test_field)
    if m:
        return m.group(1)
    return test_field.strip()  # fallback to the whole string

def apply_subject_swaps(row):
    """Swap subject data in place if the test code has a swap mapping."""
    test_field = row.get('test', '')
    test_code = extract_test_code(test_field)
    if not test_code:
        return row
    swaps = load_subject_swaps()
    if test_code not in swaps:
        return row
    swap_map = swaps[test_code].get('swap', {})
    if not swap_map:
        return row

    subjects = ['phy', 'chem', 'math']
    suffixes = ['_marks', '_correct', '_wrong', '_attempt']
    # Save original values for involved subjects
    involved = set(swap_map.keys()) | set(swap_map.values())
    original = {}
    for subj in involved:
        for suff in suffixes:
            key = subj + suff
            if key in row:
                original[key] = row[key]
    # Apply swaps
    for subj in involved:
        target = swap_map.get(subj, subj)
        if target == subj:
            continue
        for suff in suffixes:
            src_key = subj + suff
            dst_key = target + suff
            if src_key in original:
                row[dst_key] = original[src_key]
    return row
    
########### BLUEPRINT REG ##############
app.register_blueprint(api_bp)

# ── Protected HTML pages ──
@app.route("/")
@login_required
def read_root():
    return app.response_class(HOME_HTML, mimetype='text/html')

@app.route("/analysis")
@login_required
def analysis():
    return app.response_class(ANALYSIS_HTML, mimetype='text/html')

@app.route("/student")
@login_required
def student_page():
    return app.response_class(INDIVIDUAL_HTML, mimetype='text/html')

@app.route("/overview")
@login_required
def overview_page():
    return app.response_class(OVERVIEW_HTML, mimetype='text/html')

@app.route("/elites")
@login_required
def elites_page():
    return app.response_class(ELITES_HTML, mimetype='text/html')

@app.route("/annual")
@login_required
def annual():
    return render_template("annual.html")

@app.route("/kcet")
@login_required
def kcet_page():
    return app.response_class(KCET_HTML, mimetype='text/html')

@app.route("/neet")
@login_required
def neet_page():
    return app.response_class(NEET_HTML, mimetype='text/html')
    
@app.route("/anomaly")
@login_required
def anomaly_page():
    return app.response_class(ANOMALY_HTML, mimetype='text/html')

@app.route("/swap-manager")
@login_required
def swap_manager():
    return app.response_class(SWAP_MANAGER_HTML, mimetype='text/html')

# ── Static image serving (also protected) ──
@app.route("/img/<path:filename>")
@login_required
def serve_img(filename):
    img_dir = os.path.join(os.path.dirname(app.static_folder), 'img')
    if not os.path.exists(img_dir):
        abort(404)
    return send_from_directory(img_dir, filename)

@app.route('/public/<path:filename>')
@login_required
def public_files(filename):
    return send_from_directory('public', filename)

# ── Login page HTML ──
LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login · JUT Hub</title>
    <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Serif+Display&family=JetBrains+Mono:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            background: #0a0a0f;
            color: #e8e8f0;
            font-family: 'JetBrains Mono', monospace;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background-image: radial-gradient(ellipse at 30% 40%, rgba(232,197,71,0.06) 0%, transparent 60%),
                              radial-gradient(ellipse at 70% 60%, rgba(71,232,197,0.05) 0%, transparent 60%);
        }
        .login-box {
            background: #111118;
            border: 1px solid #1e1e2e;
            border-radius: 12px;
            padding: 3rem 2.5rem;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.6);
        }
        .login-box h1 {
            font-family: 'Bebas Neue', sans-serif;
            font-size: 2.8rem;
            letter-spacing: 0.02em;
            color: #e8c547;
            margin-bottom: 0.3rem;
        }
        .login-box .sub {
            font-size: 0.65rem;
            letter-spacing: 0.3em;
            color: #6b6b8a;
            text-transform: uppercase;
            margin-bottom: 2rem;
            border-bottom: 1px solid #1e1e2e;
            padding-bottom: 0.8rem;
        }
        .login-box form {
            display: flex;
            flex-direction: column;
            gap: 1.2rem;
        }
        .login-box label {
            font-size: 0.6rem;
            letter-spacing: 0.2em;
            color: #6b6b8a;
            text-transform: uppercase;
        }
        .login-box input[type="password"] {
            background: #0a0a0f;
            border: 1px solid #1e1e2e;
            color: #e8e8f0;
            padding: 0.8rem 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 1rem;
            border-radius: 6px;
            outline: none;
            transition: border-color 0.2s;
        }
        .login-box input[type="password"]:focus {
            border-color: #e8c547;
        }
        .login-box .error {
            color: #e847a0;
            font-size: 0.65rem;
            letter-spacing: 0.1em;
            min-height: 1.5rem;
        }
        .login-box button {
            background: #e8c547;
            border: none;
            color: #0a0a0f;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 1.4rem;
            padding: 0.6rem;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s, transform 0.1s;
            width: 100%;
            letter-spacing: 0.1em;
        }
        .login-box button:hover {
            background: #d4b03a;
        }
        .login-box button:active {
            transform: scale(0.97);
        }
        .login-box .hint {
            font-size: 0.55rem;
            color: #6b6b8a;
            text-align: center;
            margin-top: 1rem;
            letter-spacing: 0.15em;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🔐 JUT HUB</h1>
        <div class="sub">Authentication Required</div>
        <form method="post">
            <label for="password">Enter Password</label>
            <input type="password" id="password" name="password" placeholder="••••••••" autofocus>
            <div class="error">{{ error if error else '' }}</div>
            <button type="submit">Unlock</button>
        </form>
        <div class="hint">Contact admin if you don't have the password.</div>
    </div>
</body>
</html>"""

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
.reveal{opacity:1;transform:translateY(28px);transition:opacity 0.7s,transform 0.7s;}
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
      <td>${t.absent?`<span class="tl-badge b-abs">Absent</span>`:`<span class="tl-badge b-good">✓ Present</span>`}</td>
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
.reveal{opacity:1;transform:translateY(24px);transition:opacity 0.6s,transform 0.6s;}
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

/* INSTITUTION FILTER */
.inst-filter-bar{display:flex;gap:0.5rem;align-items:center;padding:0.6rem 2rem;background:rgba(10,10,15,0.8);border-bottom:1px solid var(--border);flex-wrap:wrap;}
.inst-filter-label{font-size:0.52rem;letter-spacing:0.22em;color:var(--muted);text-transform:uppercase;flex-shrink:0;}
.inst-btn{font-size:0.55rem;letter-spacing:0.15em;text-transform:uppercase;padding:0.35rem 0.85rem;border:1px solid var(--border);border-radius:2px;cursor:pointer;background:transparent;color:var(--muted);font-family:'JetBrains Mono',monospace;transition:all 0.2s;white-space:nowrap;}
.inst-btn:hover{border-color:var(--accent);color:var(--accent);}
.inst-btn.active{background:var(--accent);color:var(--bg);border-color:var(--accent);}
.inst-btn.ib-kjs.active{background:#4fc3f7;border-color:#4fc3f7;color:var(--bg);}
.inst-btn.ib-mjs.active{background:#a78bfa;border-color:#a78bfa;color:var(--bg);}
.inst-btn.ib-ujs.active{background:#fb923c;border-color:#fb923c;color:var(--bg);}

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

.avg-dec{
  font-size:0.65em;
  opacity:0.7;
  margin-left:1px;
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

<div class="inst-filter-bar" id="instFilterBarOv">
  <span class="inst-filter-label">Institution:</span>
  <button class="inst-btn active" data-inst="ALL">All</button>
  <button class="inst-btn ib-kjs" data-inst="KJS">KJS</button>
  <button class="inst-btn ib-mjs" data-inst="MJS">MJS</button>
  <button class="inst-btn ib-ujs" data-inst="UJS">UJS</button>
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

function formatAvg(v){
  const intPart = Math.floor(v);
  const decPart = (v - intPart).toFixed(2).slice(2); // 2 digits
  return `${intPart}<span class="avg-dec">.${decPart}</span>`;
}

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
let activeJut='ALL', instFilterOv='ALL';

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

    // Wire institution filter buttons
    document.querySelectorAll('#instFilterBarOv .inst-btn').forEach(btn=>{
      btn.addEventListener('click',()=>{
        instFilterOv=btn.dataset.inst;
        document.querySelectorAll('#instFilterBarOv .inst-btn').forEach(b=>b.classList.remove('active'));
        btn.classList.add('active');
        buildAll(activeJut);
      });
    });

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
  let rows=(jut==='ALL')?allRows:allRows.filter(r=>r.test===jut);
  if(instFilterOv!=='ALL') rows=rows.filter(r=>(r.inst||'').toUpperCase()===instFilterOv);
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
      .filter(s=>s.stats.attended>=1&&(instFilterOv==='ALL'||(s.inst||'').toUpperCase()===instFilterOv))
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
  // Apply institution filter to student list
  const filteredStudents=Object.values(studentMap).filter(s=>instFilterOv==='ALL'||(s.inst||'').toUpperCase()===instFilterOv);
  if(jut==='ALL'){
    lbData=filteredStudents.map(s=>({
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
    const diff=lbDir*(av-bv);
    if(diff!==0)return diff;
    // Tiebreakers always direction-neutral: accuracy desc → name asc
    if((b.acc||0)!==(a.acc||0))return (b.acc||0)-(a.acc||0);
    return a.name.localeCompare(b.name);
  });
  // assign display ranks by avg (or score) — tiebreaker: acc desc → name asc
  const ranked=[...lbData].sort((a,b)=>{
    if(b.avg!==a.avg)return b.avg-a.avg;
    if((b.acc||0)!==(a.acc||0))return (b.acc||0)-(a.acc||0);
    return a.name.localeCompare(b.name);
  });
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
      <td><span class="score-chip" style="background:${sc}22;color:${sc}">${formatAvg(s.avg)}</span></td>
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
      .filter(s=>s.stats.attended>=1&&(instFilterOv==='ALL'||(s.inst||'').toUpperCase()===instFilterOv))
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
    .filter(s=>s.stats.consistency!==null&&s.stats.attended>=3&&(instFilterOv==='ALL'||(s.inst||'').toUpperCase()===instFilterOv))
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

# ══════════════════════════════════════════════════════════════════════════════
#  HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════
HOME_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FLOODING IN PROGRESS</title>
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

  /* NAV GRID */
  .nav-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1rem;
    margin-bottom: 1rem;
  }
  .nav-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1.8rem;
    text-decoration: none;
    display: block;
    position: relative;
    overflow: hidden;
    transition: transform 0.25s, border-color 0.25s, background 0.25s;
  }
  .nav-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.35s;
  }
  .nc-analysis::before { background: linear-gradient(90deg, #47e8c5, #4fc3f7); }
  .nc-overview::before { background: linear-gradient(90deg, #e8c547, #fb923c); }
  .nc-student::before  { background: linear-gradient(90deg, #a78bfa, #e847a0); }
  .nc-elites::before   { background: linear-gradient(90deg, #fbbf24, #e8c547); }
  .nav-card:hover { transform: translateY(-5px); background: var(--surface2); }
  .nc-analysis:hover { border-color: #47e8c5; }
  .nc-overview:hover  { border-color: #e8c547; }
  .nc-student:hover   { border-color: #a78bfa; }
  .nc-elites:hover    { border-color: #fbbf24; }
  .nav-card:hover::before { transform: scaleX(1); }
  .nc-icon { font-size: 1.8rem; margin-bottom: 0.8rem; }
  .nc-label { font-size: 0.52rem; letter-spacing: 0.3em; color: var(--muted); text-transform: uppercase; margin-bottom: 0.3rem; }
  .nc-title { font-family: 'DM Serif Display', serif; font-size: 1.5rem; margin-bottom: 0.6rem; color: var(--text); }
  .nc-desc { font-size: 0.62rem; color: var(--muted); line-height: 1.7; letter-spacing: 0.05em; }
  .nc-arrow { position: absolute; bottom: 1.4rem; right: 1.4rem; font-size: 1.2rem; color: var(--muted); transition: transform 0.2s, color 0.2s; }
  .nav-card:hover .nc-arrow { transform: translate(3px,-3px); }
  .nc-analysis:hover .nc-arrow { color: #47e8c5; }
  .nc-overview:hover .nc-arrow { color: #e8c547; }
  .nc-student:hover .nc-arrow  { color: #a78bfa; }
  .nc-elites:hover .nc-arrow   { color: #fbbf24; }

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
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Bodoni+Moda:ital,opsz,wght@0,6..96,400..900;1,6..96,400..900&family=Forum&family=Lexend:wght@100..900&family=Special+Gothic+Condensed+One&display=swap');
    *{
        user-select: none;
    }
    .tapoverlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgb(194, 149, 0);
        display: flex;
        flex-direction: column;
        z-index: 9999;
    }
    .tapoverlay h1 {
        font-size: 7em;
        color: #fff;
        margin: 30px 40px 0 40px;
        font-family: "Bebas Neue", sans-serif;
    }
    .tapoverlay img {
        width: 400px;
        height: auto;
        position: absolute;
        bottom: 0;
        right:0;
    }
    @media only screen and (max-width: 450px) {
        .tapoverlay h1 {
            font-size: 5em;
            margin: 20px 20px 0 20px;
        }
    }
</style>
</head>
<body>

    <div class="tapoverlay">
        <h1>TWO TAPS ARE ENOUGH<br> TO FLOOD YOUR ROOM</h1>
        <img src="static/tap.gif" alt="WATERTAP">
    </div>
    <script>
        document.title = "FLOODING IN PROGRESS";
        document.body.style.overflow = "hidden";
        // quick double tap to remove the overlay
        let tapCount = 0;
        let tapTimeout;
        document.querySelector('.tapoverlay').addEventListener('click', () => {
            tapCount++;
            if (tapCount === 2) {
                document.querySelector('.tapoverlay').style.display = 'none';
                    // change title to "TAPOVERLAY"
                    document.title = "JUT · Analytics Hub"
                    document.body.style.overflow = "auto";
                clearTimeout(tapTimeout);
                tapCount = 0;
            } else {
                tapTimeout = setTimeout(() => {
                    tapCount = 0;
                }, 200); // reset tap count after 200ms
            }
        });
    </script>

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

  <!-- NAV SECTION -->
  <div class="section-label" style="animation:fadeUp 0.6s 0.8s both;">Navigate</div>
  <div class="section-title" style="animation:fadeUp 0.7s 0.9s both;">All Sections</div>
  <div class="nav-grid" id="navGrid" style="animation:fadeUp 0.8s 1.0s both;">
    <a href="/analysis" class="nav-card nc-analysis">
      <div class="nc-icon">📊</div>
      <div class="nc-label">PER-TEST</div>
      <div class="nc-title">Analysis</div>
      <div class="nc-desc">Deep-dive into any single JUT — leaderboard, subject stats, charts, heatmap.</div>
      <div class="nc-arrow">→</div>
    </a>
    <a href="/overview" class="nav-card nc-overview">
      <div class="nc-icon">🌐</div>
      <div class="nc-label">MASTER</div>
      <div class="nc-title">Overview</div>
      <div class="nc-desc">Cross-JUT batch analytics — trends, rankings, distribution, consistency.</div>
      <div class="nc-arrow">→</div>
    </a>
    <a href="/student" class="nav-card nc-student">
      <div class="nc-icon">👤</div>
      <div class="nc-label">INDIVIDUAL</div>
      <div class="nc-title">Student Profile</div>
      <div class="nc-desc">Full personal analytics — score history, strengths, percentile, rank.</div>
      <div class="nc-arrow">→</div>
    </a>
    <a href="/elites" class="nav-card nc-elites">
      <div class="nc-icon">🏆</div>
      <div class="nc-label">HALL OF FAME</div>
      <div class="nc-title">JUT Elites</div>
      <div class="nc-desc">Wall of fame — achievement badges, elite performers, remarkable scorers.</div>
      <div class="nc-arrow">→</div>
    </a>
    <a href="/annual" class="nav-card nc-analysis">
      <div class="nc-icon">📝</div>
      <div class="nc-label">EXAM</div>
      <div class="nc-title">Annual Exam</div>
      <div class="nc-desc">I PUC Annual Exam.</div>
      <div class="nc-arrow">→</div>
    </a>
    <a href="/kcet" class="nav-card nc-overview">
      <div class="nc-icon">🚀</div>
      <div class="nc-label">BATCH SELECTION</div>
      <div class="nc-title">KCET Analysis</div>
      <div class="nc-desc">KCET Mock Test - Batch Selection.</div>
      <div class="nc-arrow">→</div>
    </a>
    <a href="/neet" class="nav-card nc-student">
      <div class="nc-icon">🧬</div>
      <div class="nc-label">BATCH SELECTION</div>
      <div class="nc-title">NEET Analysis</div>
      <div class="nc-desc">NEET Mock Test - Batch Selection.</div>
      <div class="nc-arrow">→</div>
    </a>
    <a href="/anomaly" class="nav-card nc-analysis">
      <div class="nc-icon">🔍</div>
      <div class="nc-label">ANOMALY</div>
      <div class="nc-title">Check Attempts</div>
      <div class="nc-desc">Find rows with attempt > 75 across all JUTs – flagged before halving.</div>
      <div class="nc-arrow">→</div>
    </a>
  </div>

  <div class="divider" style="margin:3rem 0;"></div>

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
    
    // Filter only files matching pattern: 60jut{num}.csv (case insensitive)
    const jutFiles = files.filter(f => {
      const match = f.toLowerCase().match(/^60jut(\d+)\.csv$/);
      return match !== null;
    });
    
    // Sort by number (extract the number from filename)
    jutFiles.sort((a, b) => {
      const numA = parseInt(a.match(/60jut(\d+)\.csv/i)[1]);
      const numB = parseInt(b.match(/60jut(\d+)\.csv/i)[1]);
      return numA - numB;
    });

    document.getElementById('strip-files').textContent = jutFiles.length || '0';

    if (jutFiles.length === 0) {
      grid.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">NO JUT FILES</div>
        <p>No files matching pattern <code>60jut{num}.csv</code> found in /static folder.<br>Example: 60jut1.csv, 60jut2.csv, ... 60jut30.csv</p>
      </div>`;
      return;
    }

    grid.innerHTML = '';
    jutFiles.forEach((filename, idx) => {
      // Extract number for display
      const numMatch = filename.match(/60jut(\d+)\.csv/i);
      const jutNum = numMatch ? numMatch[1] : '';
      const label = `JUT ${jutNum}`;
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
#  ANALYSIS PAGE (with halving correction in mapRow)
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
    opacity: 1;
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

  /* INSTITUTION FILTER BAR */
  .inst-filter-bar{display:flex;gap:0.5rem;align-items:center;margin-bottom:1rem;flex-wrap:wrap;}
  .inst-filter-label{font-size:0.55rem;letter-spacing:0.22em;color:var(--muted);text-transform:uppercase;}
  .inst-btn{font-size:0.55rem;letter-spacing:0.15em;text-transform:uppercase;padding:0.35rem 0.8rem;border:1px solid var(--border);border-radius:2px;cursor:pointer;background:transparent;color:var(--muted);font-family:'JetBrains Mono',monospace;transition:all 0.2s;white-space:nowrap;}
  .inst-btn:hover{border-color:var(--accent);color:var(--accent);}
  .inst-btn.active{background:var(--accent);color:var(--bg);border-color:var(--accent);}
  .inst-btn.ib-kjs.active{background:#4fc3f7;border-color:#4fc3f7;color:var(--bg);}
  .inst-btn.ib-mjs.active{background:#a78bfa;border-color:#a78bfa;color:var(--bg);}
  .inst-btn.ib-ujs.active{background:#fb923c;border-color:#fb923c;color:var(--bg);}
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
  <div class="inst-filter-bar reveal" id="instFilterBar">
    <span class="inst-filter-label">Institution:</span>
    <button class="inst-btn active" data-inst="ALL">All</button>
    <button class="inst-btn ib-kjs" data-inst="KJS">KJS</button>
    <button class="inst-btn ib-mjs" data-inst="MJS">MJS</button>
    <button class="inst-btn ib-ujs" data-inst="UJS">UJS</button>
  </div>
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
          <th>SL</th><th>CSV Rank</th><th>#</th><th>Student</th><th>Inst</th><th>Score</th><th>Subject Breakdown</th><th>Accuracy</th><th>Attempted</th>
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
let subjectSwaps = {};

async function loadSubjectSwaps() {
    try {
        const res = await fetch('/api/subject-swaps');
        if (res.ok) {
            subjectSwaps = await res.json();
            console.log('✅ Subject swaps loaded:', subjectSwaps);
        }
    } catch(e) {
        console.warn('⚠️ Could not load subject swaps', e);
    }
}

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

function getInstA(fileVal){
  if(!fileVal) return '';
  const f=(fileVal+'').trim().toUpperCase();
  if(f.startsWith('K')) return 'KJS';
  if(f.startsWith('U')) return 'UJS';
  if(f.startsWith('M')) return 'MJS';
  return '';
}

function extractTestCode(testField) {
    if (!testField) return null;
    const m = testField.match(/:\s*(\d+)/);
    if (m) return m[1];
    const m2 = testField.match(/\b(\d+)\b/);
    if (m2) return m2[1];
    return testField.trim();
}

function mapRow(r) {
  const get = (...ks) => { for (const k of ks) { if (r[k] !== undefined && r[k] !== '') return r[k]; } return '0'; };
  const getS = (...ks) => { for (const k of ks) { if (r[k] !== undefined && r[k] !== '') return r[k]; } return ''; };

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
    test:   getS('test','test_name','filename','jut','jut_name') || 'Unknown'
  };
}

// Apply subject swaps to an entire array of rows using a test code
function applySwapsToData(rows, testCode) {
    if (!testCode || !subjectSwaps[testCode]) return rows;
    console.log(`🔄 Applying swap for test code: ${testCode}`);
    const swapMap = subjectSwaps[testCode].swap || {};
    const suffixMap = {
        '_marks':   '_m',
        '_correct': '_c',
        '_wrong':   '_w',
        '_attempt': '_a'
    };
    const subjects = ['phy', 'chem', 'math'];

    rows.forEach(row => {
        // Save originals
        const original = {};
        subjects.forEach(subj => {
            Object.values(suffixMap).forEach(suff => {
                const key = subj + suff;
                if (row[key] !== undefined) original[key] = row[key];
            });
        });
        // Apply swaps
        subjects.forEach(subj => {
            const target = swapMap[subj] || subj;
            if (target === subj) return;
            Object.values(suffixMap).forEach(suff => {
                const srcKey = subj + suff;
                const dstKey = target + suff;
                if (srcKey in original) {
                    row[dstKey] = original[srcKey];
                }
            });
        });
    });
    console.log('✅ Swap applied to', rows.length, 'rows');
    return rows;
}

// Halving correction (unchanged)
function applyHalving(rows) {
    rows.forEach(row => {
        const attemptVals = [row.phy_a, row.chem_a, row.math_a, row.tot_a];
        if (attemptVals.some(v => v > 75)) {
            const fields = ['phy_a','chem_a','math_a','tot_a','phy_c','chem_c','math_c','tot_c',
                            'phy_w','chem_w','math_w','tot_w','phy_m','chem_m','math_m','total'];
            fields.forEach(f => {
                if (f === 'total') row.total = row.total / 2;
                else row[f] = row[f] / 2;
            });
        }
    });
    return rows;
}

let radarInst, stackedInst, accuracyInst;

function buildDashboard(raw, filename) {
  raw.forEach(s => { s.accuracy = s.tot_a > 0 ? Math.round((s.tot_c / s.tot_a) * 100) : 0; });
  const sorted = [...raw].sort((a,b) => {
    if (b.total !== a.total) return b.total - a.total;
    if (b.tot_c !== a.tot_c) return b.tot_c - a.tot_c;
    return a.name.localeCompare(b.name);
  });
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

  let currentSort = 'total', sortDir = -1, filterText = '', instFilterA = 'ALL';

  function getTier(score) {
    if (score >= high * 0.75) return 'tier-excellent';
    if (score >= high * 0.5)  return 'tier-good';
    if (score >= high * 0.25) return 'tier-average';
    return 'tier-poor';
  }

  function renderLeaderboard() {
    let data = [...raw];
    if (instFilterA !== 'ALL') data = data.filter(s => (s.inst||'').toUpperCase() === instFilterA);
    if (filterText) data = data.filter(s => s.name.toLowerCase().includes(filterText.toLowerCase()));
    const valKeys = {total:'total',phy:'phy_m',chem:'chem_m',math:'math_m',acc:'accuracy'};
    data.sort((a,b) => {
      const diff = sortDir * (a[valKeys[currentSort]] - b[valKeys[currentSort]]);
      if (diff !== 0) return diff;
      if (b.tot_c !== a.tot_c) return b.tot_c - a.tot_c;
      return a.name.localeCompare(b.name);
    });
    const tbody = document.getElementById('leaderboardBody');
    tbody.innerHTML = '';
    data.forEach((s, slIdx) => {
      const maxScore = high || 300;
      const phyPct  = Math.max(0, (s.phy_m  / maxScore) * 100);
      const chemPct = Math.max(0, (s.chem_m / maxScore) * 100);
      const mathPct = Math.max(0, (s.math_m / maxScore) * 100);
      const localRank = sorted.indexOf(s) + 1;
      const rankClass = localRank===1?'rank-1':localRank===2?'rank-2':localRank===3?'rank-3':'rank-other';
      const scoreColor = s.total>=high*0.75?'var(--accent2)':s.total>=high*0.5?'var(--accent)':s.total>=high*0.25?'var(--math)':'var(--accent3)';
      const accColor = s.accuracy>=60?'var(--accent2)':s.accuracy>=40?'var(--accent)':'var(--accent3)';
      const csvRank = s.rank ? s.rank : '\u2014';
      const tr = document.createElement('tr');
      tr.className = 'row ' + getTier(s.total);
      tr.innerHTML =
        '<td style="color:var(--muted);font-size:0.65rem;min-width:32px;">' + (slIdx+1) + '</td>' +
        '<td style="color:var(--muted);font-family:\'Bebas Neue\',sans-serif;font-size:1.1rem;min-width:48px;">' + csvRank + '</td>' +
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
  document.querySelectorAll('#instFilterBar .inst-btn').forEach(btn => {
    btn.onclick = () => {
      instFilterA = btn.dataset.inst;
      document.querySelectorAll('#instFilterBar .inst-btn').forEach(b => b.classList.remove('active'));
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

    // Map rows
    let data = rows.map(mapRow);

    // Apply halving
    data = applyHalving(data);

    // Apply subject swaps using filename (take the last number)
    const allNums = filename.match(/\d+/g);
    const testCode = allNums ? allNums[allNums.length - 1] : null;
    if (testCode && subjectSwaps[testCode]) {
        data = applySwapsToData(data, testCode);
    }

    hideOverlay();
    buildDashboard(data, filename);
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
  await loadSubjectSwaps();
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

# ══════════════════════════════════════════════════════════════════════════════
#  ELITES PAGE (unchanged, uses backend corrected data)
# ══════════════════════════════════════════════════════════════════════════════
ELITES_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JUT · Elites — Wall of Fame</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@300;400;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0a0a0f;--surface:#111118;--surface2:#16161f;--border:#1e1e2e;
  --accent:#e8c547;--accent2:#47e8c5;--accent3:#e847a0;
  --text:#e8e8f0;--muted:#6b6b8a;
  --phy:#4fc3f7;--chem:#a78bfa;--math:#fb923c;
  --gold:#fbbf24;--silver:#94a3b8;--bronze:#cd7f32;--legendary:#e8c547;
  --green:#4ade80;--red:#f87171;
}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;overflow-x:hidden;}

/* ── noise grain ── */
body::after{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");pointer-events:none;z-index:9999;opacity:0.4;}

/* ── animated grid bg ── */
.grid-bg{position:fixed;inset:0;background-image:linear-gradient(rgba(255,255,255,0.015) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.015) 1px,transparent 1px);background-size:80px 80px;animation:gridDrift 50s linear infinite;z-index:0;}
@keyframes gridDrift{0%{background-position:0 0}100%{background-position:80px 80px}}

/* ── ambient glows ── */
.glow-gold{position:fixed;width:900px;height:900px;border-radius:50%;background:radial-gradient(circle,rgba(232,197,71,0.06) 0%,transparent 65%);top:-300px;right:-200px;pointer-events:none;animation:floatGold 22s ease-in-out infinite;}
.glow-teal{position:fixed;width:600px;height:600px;border-radius:50%;background:radial-gradient(circle,rgba(71,232,197,0.05) 0%,transparent 65%);bottom:-150px;left:-100px;pointer-events:none;animation:floatTeal 28s ease-in-out infinite;}
.glow-pink{position:fixed;width:500px;height:500px;border-radius:50%;background:radial-gradient(circle,rgba(232,71,160,0.04) 0%,transparent 65%);top:40%;left:40%;pointer-events:none;animation:floatPink 34s ease-in-out infinite;}
@keyframes floatGold{0%,100%{transform:translate(0,0)}50%{transform:translate(-40px,60px)}}
@keyframes floatTeal{0%,100%{transform:translate(0,0)}50%{transform:translate(60px,-40px)}}
@keyframes floatPink{0%,100%{transform:translate(0,0)}50%{transform:translate(-50px,30px)}}

/* ── nav ── */
.topnav{position:fixed;top:0;left:0;right:0;z-index:500;background:rgba(10,10,15,0.88);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0.9rem 2rem;gap:1rem;}
.topnav-logo{font-family:'Bebas Neue',sans-serif;font-size:1.4rem;letter-spacing:0.08em;color:var(--text);text-decoration:none;}
.topnav-logo span{color:var(--accent);}
.topnav-links{display:flex;gap:1.2rem;align-items:center;}
.topnav-link{font-size:0.58rem;letter-spacing:0.22em;text-transform:uppercase;color:var(--muted);text-decoration:none;transition:color 0.2s;padding:0.3rem 0;}
.topnav-link:hover,.topnav-link.active{color:var(--accent);}
.topnav-link.active{border-bottom:1px solid var(--accent);}

/* ── hero ── */
.hero{position:relative;z-index:1;min-height:100vh;display:flex;flex-direction:column;justify-content:flex-end;padding:8rem 4rem 5rem;overflow:hidden;}
.hero-scanline{position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(232,197,71,0.012) 3px,rgba(232,197,71,0.012) 4px);pointer-events:none;}
.hero-content{position:relative;z-index:2;}
.hero-eyebrow{font-size:0.62rem;letter-spacing:0.5em;color:var(--accent2);text-transform:uppercase;margin-bottom:1rem;opacity:0;animation:slideUp 0.6s 0.2s forwards;display:flex;align-items:center;gap:0.8rem;}
.hero-eyebrow::before{content:'';display:block;width:42px;height:1px;background:var(--accent2);}
.hero-title{font-family:'Bebas Neue',sans-serif;font-size:clamp(5rem,16vw,14rem);line-height:0.84;letter-spacing:0.01em;opacity:0;animation:slideUp 0.9s 0.35s forwards;}
.hero-title .gold{color:var(--accent);-webkit-text-stroke:0px;display:block;}
.hero-title .stroke{-webkit-text-stroke:1.5px rgba(232,197,71,0.5);color:transparent;display:block;}
.hero-sub{font-size:0.75rem;color:var(--muted);letter-spacing:0.18em;margin-top:1.5rem;max-width:560px;line-height:1.8;opacity:0;animation:slideUp 0.7s 0.6s forwards;}
.hero-kpis{display:flex;gap:3rem;margin-top:3rem;opacity:0;animation:slideUp 0.7s 0.75s forwards;flex-wrap:wrap;}
.kpi{text-align:left;}
.kpi-val{font-family:'Bebas Neue',sans-serif;font-size:3.8rem;color:var(--accent);line-height:1;}
.kpi-label{font-size:0.52rem;letter-spacing:0.28em;color:var(--muted);text-transform:uppercase;margin-top:0.2rem;}
@keyframes slideUp{from{opacity:0;transform:translateY(32px)}to{opacity:1;transform:translateY(0)}}

/* ── scrolling ticker ── */
.ticker-wrap{position:absolute;bottom:0;left:0;right:0;z-index:3;overflow:hidden;border-top:1px solid rgba(232,197,71,0.12);height:36px;background:rgba(10,10,15,0.7);backdrop-filter:blur(8px);}
.ticker{display:flex;align-items:center;white-space:nowrap;animation:tickerScroll 40s linear infinite;height:100%;}
.ticker-item{font-size:0.55rem;letter-spacing:0.22em;color:rgba(232,197,71,0.5);text-transform:uppercase;padding:0 2rem;}
.ticker-sep{color:rgba(232,197,71,0.25);padding:0 0.5rem;}
@keyframes tickerScroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* ── main layout ── */
.main{position:relative;z-index:1;max-width:1600px;margin:0 auto;padding:0 2.5rem 8rem;}
section{padding:5rem 0;}
.sec-label{font-size:0.6rem;letter-spacing:0.45em;color:var(--accent);text-transform:uppercase;margin-bottom:0.7rem;display:flex;align-items:center;gap:0.8rem;}
.sec-label::before{content:'';display:block;width:28px;height:1px;background:var(--accent);}
.sec-title{font-family:'DM Serif Display',serif;font-size:clamp(2rem,5vw,3.5rem);margin-bottom:2.5rem;}
.divider{height:1px;background:linear-gradient(90deg,transparent,var(--border) 20%,var(--border) 80%,transparent);}
.reveal{opacity:1;transform:translateY(28px);transition:opacity 0.7s,transform 0.7s;}
.reveal.vis{opacity:1;transform:translateY(0);}

/* ── filter bar ── */
.filter-strip{display:flex;gap:0.6rem;align-items:center;flex-wrap:wrap;margin-bottom:2.5rem;padding:1rem 1.4rem;background:var(--surface);border:1px solid var(--border);border-radius:6px;}
.filter-label{font-size:0.52rem;letter-spacing:0.25em;color:var(--muted);text-transform:uppercase;flex-shrink:0;}
.filter-sep{width:1px;height:18px;background:var(--border);flex-shrink:0;}
.flt-btn{font-size:0.55rem;letter-spacing:0.15em;text-transform:uppercase;padding:0.35rem 0.9rem;border:1px solid var(--border);border-radius:2px;cursor:pointer;background:transparent;color:var(--muted);font-family:'JetBrains Mono',monospace;transition:all 0.2s;white-space:nowrap;}
.flt-btn:hover{border-color:var(--accent);color:var(--accent);}
.flt-btn.active{background:var(--accent);color:var(--bg);border-color:var(--accent);}
.flt-btn.ib-kjs.active{background:#4fc3f7;border-color:#4fc3f7;}
.flt-btn.ib-mjs.active{background:#a78bfa;border-color:#a78bfa;}
.flt-btn.ib-ujs.active{background:#fb923c;border-color:#fb923c;}
.search-elite{background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:0.4rem 0.9rem;font-family:'JetBrains Mono',monospace;font-size:0.68rem;border-radius:2px;outline:none;min-width:220px;transition:border-color 0.2s;margin-left:auto;}
.search-elite:focus{border-color:var(--accent);}
.search-elite::placeholder{color:var(--muted);}

/* ── badge tier colors ── */
.tier-legendary{background:linear-gradient(135deg,rgba(232,197,71,0.18),rgba(251,191,36,0.08));border-color:rgba(232,197,71,0.5)!important;color:var(--gold);}
.tier-gold{background:rgba(251,191,36,0.08);border-color:rgba(251,191,36,0.3)!important;color:#fbbf24;}
.tier-silver{background:rgba(148,163,184,0.08);border-color:rgba(148,163,184,0.25)!important;color:var(--silver);}
.tier-bronze{background:rgba(205,127,50,0.08);border-color:rgba(205,127,50,0.2)!important;color:var(--bronze);}

/* ── elite card ── */
.elites-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1.5rem;}
.elite-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden;position:relative;transition:transform 0.3s,border-color 0.3s,box-shadow 0.3s;cursor:pointer;text-decoration:none;display:block;}
.elite-card:hover{transform:translateY(-6px);border-color:rgba(232,197,71,0.35);box-shadow:0 20px 60px rgba(0,0,0,0.4);}
.elite-card.legendary-card{border-color:rgba(232,197,71,0.3);box-shadow:0 0 30px rgba(232,197,71,0.06);}
.elite-card.legendary-card:hover{border-color:rgba(232,197,71,0.6);box-shadow:0 20px 60px rgba(232,197,71,0.12);}

/* card top band */
.card-band{height:3px;}
.band-legendary{background:linear-gradient(90deg,#fbbf24,#e8c547,#47e8c5);}
.band-gold{background:linear-gradient(90deg,#fbbf24,#fb923c);}
.band-silver{background:linear-gradient(90deg,#94a3b8,#4fc3f7);}
.band-default{background:linear-gradient(90deg,var(--accent),var(--accent2));}

/* rank badge absolute top-right */
.card-rank{position:absolute;top:0.8rem;right:0.9rem;font-family:'Bebas Neue',sans-serif;font-size:1.8rem;line-height:1;opacity:0.55;}
.rank-1-c{color:var(--gold);}
.rank-2-c{color:var(--silver);}
.rank-3-c{color:var(--bronze);}
.rank-n-c{color:var(--muted);}

/* photo area */
.card-photo-wrap{width:100%;aspect-ratio:3/4;overflow:hidden;position:relative;background:var(--surface2);}
.card-photo{width:100%;height:100%;object-fit:cover;display:block;transition:transform 0.5s;}
.elite-card:hover .card-photo{transform:scale(1.04);}
.card-photo-fallback{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-family:'Bebas Neue',sans-serif;font-size:4rem;color:rgba(232,197,71,0.15);}
.card-photo-overlay{position:absolute;inset:0;background:linear-gradient(to top,rgba(10,10,15,0.9) 0%,rgba(10,10,15,0.3) 50%,transparent 100%);}
.card-photo-score{position:absolute;bottom:0.9rem;left:1rem;font-family:'Bebas Neue',sans-serif;font-size:2.8rem;line-height:1;color:var(--accent);}
.card-photo-avg-label{font-size:0.48rem;letter-spacing:0.22em;color:rgba(232,197,71,0.6);text-transform:uppercase;margin-bottom:1px;}

/* card body */
.card-body{padding:1.2rem 1.3rem 1.4rem;}
.card-inst{display:inline-block;font-size:0.48rem;letter-spacing:0.2em;padding:0.16rem 0.5rem;border-radius:2px;text-transform:uppercase;margin-bottom:0.5rem;font-weight:600;}
.inst-kjs{background:rgba(79,195,247,0.12);color:#4fc3f7;}
.inst-mjs{background:rgba(167,139,250,0.12);color:#a78bfa;}
.inst-ujs{background:rgba(251,146,60,0.12);color:#fb923c;}
.card-name{font-family:'DM Serif Display',serif;font-size:1.2rem;line-height:1.2;margin-bottom:0.6rem;color:var(--text);}
.card-stats{display:flex;gap:1.2rem;margin-bottom:1rem;flex-wrap:wrap;}
.card-stat-item{text-align:center;}
.cs-val{font-family:'Bebas Neue',sans-serif;font-size:1.4rem;line-height:1;}
.cs-lbl{font-size:0.44rem;letter-spacing:0.18em;color:var(--muted);text-transform:uppercase;}
.card-subj-bars{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;margin-bottom:1rem;}
.csb-row{}
.csb-label{font-size:0.48rem;color:var(--muted);letter-spacing:0.1em;margin-bottom:3px;display:flex;justify-content:space-between;}
.csb-outer{height:3px;background:var(--border);border-radius:2px;overflow:hidden;}
.csb-inner{height:100%;border-radius:2px;}

/* badges strip */
.card-badges{display:flex;flex-wrap:wrap;gap:0.35rem;}
.badge{display:inline-flex;align-items:center;gap:0.3rem;font-size:0.48rem;letter-spacing:0.12em;padding:0.22rem 0.55rem;border-radius:20px;border:1px solid;text-transform:uppercase;white-space:nowrap;}
.badge .badge-icon{font-size:0.7rem;}

/* ── podium section ── */
.podium-trio{display:flex;align-items:flex-end;justify-content:center;gap:0;margin:2rem 0 3rem;}
.ptop{flex:1;max-width:320px;text-align:center;position:relative;}
.ptop-photo{width:120px;height:120px;border-radius:50%;overflow:hidden;margin:0 auto 1rem;border:3px solid var(--border);position:relative;}
.ptop-photo img{width:100%;height:100%;object-fit:cover;}
.ptop-photo-fb{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-family:'Bebas Neue',sans-serif;font-size:2.5rem;color:rgba(232,197,71,0.2);}
.ptop-medal{position:absolute;top:-8px;right:-8px;font-size:1.5rem;}
.ptop-name{font-family:'DM Serif Display',serif;font-size:1.05rem;margin-bottom:0.25rem;}
.ptop-score{font-family:'Bebas Neue',sans-serif;font-size:3rem;line-height:1;}
.ptop-sub{font-size:0.52rem;letter-spacing:0.18em;color:var(--muted);text-transform:uppercase;}
.ptop-block{margin-top:0.8rem;border-radius:4px 4px 0 0;height:120px;display:flex;align-items:center;justify-content:center;font-size:2.5rem;}
.ptop-1 .ptop-score{color:var(--gold);}
.ptop-1 .ptop-photo{border-color:var(--gold);box-shadow:0 0 20px rgba(251,191,36,0.25);}
.ptop-1 .ptop-block{background:linear-gradient(135deg,#fbbf24,#f59e0b);height:150px;}
.ptop-2 .ptop-score{color:var(--silver);}
.ptop-2 .ptop-photo{border-color:var(--silver);}
.ptop-2 .ptop-block{background:linear-gradient(135deg,#94a3b8,#64748b);}
.ptop-3 .ptop-score{color:var(--bronze);}
.ptop-3 .ptop-photo{border-color:var(--bronze);}
.ptop-3 .ptop-block{background:linear-gradient(135deg,#cd7f32,#a0632a);height:88px;}

/* ── badge legend ── */
.badge-legend{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:0.8rem;margin-top:1.5rem;}
.bl-item{display:flex;align-items:center;gap:0.8rem;background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:0.8rem 1rem;}
.bl-icon{font-size:1.5rem;flex-shrink:0;}
.bl-name{font-size:0.62rem;margin-bottom:0.15rem;}
.bl-desc{font-size:0.52rem;color:var(--muted);letter-spacing:0.05em;line-height:1.5;}

/* ── loading ── */
.loading-wrap{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:50vh;gap:1rem;}
.ld-dots{display:flex;gap:8px;}
.ld-dot{width:10px;height:10px;border-radius:50%;background:var(--accent);animation:blink 1.2s infinite;}
.ld-dot:nth-child(2){animation-delay:0.2s;}
.ld-dot:nth-child(3){animation-delay:0.4s;}
@keyframes blink{0%,100%{opacity:0.15}50%{opacity:1}}
.ld-text{font-size:0.65rem;letter-spacing:0.3em;color:var(--muted);text-transform:uppercase;}

/* ── empty state ── */
.empty-msg{text-align:center;padding:4rem;color:var(--muted);font-size:0.7rem;letter-spacing:0.2em;}

@media(max-width:900px){
  .hero{padding:7rem 1.5rem 4rem;}
  .podium-trio{flex-direction:column;align-items:center;gap:1.5rem;}
  .ptop{max-width:260px;}
  .ptop-block{display:none;}
  .main{padding:0 1.2rem 6rem;}
  .elites-grid{grid-template-columns:1fr;}
}
</style>
</head>
<body>
<div class="grid-bg"></div>
<div class="glow-gold"></div>
<div class="glow-teal"></div>
<div class="glow-pink"></div>

<nav class="topnav">
  <a class="topnav-logo" href="/">JUT<span>·</span>HUB</a>
  <div class="topnav-links">
    <a class="topnav-link" href="/">Home</a>
    <a class="topnav-link" href="/analysis">Per-Test</a>
    <a class="topnav-link" href="/overview">Overview</a>
    <a class="topnav-link" href="/student">Student</a>
    <a class="topnav-link active" href="/elites">Elites</a>
  </div>
</nav>

<!-- HERO -->
<div class="hero">
  <div class="hero-scanline"></div>
  <div class="hero-content">
    <div class="hero-eyebrow">JUT · Wall of Fame</div>
    <div class="hero-title">
      <span class="gold">JUT</span>
      <span class="stroke">ELITES</span>
    </div>
    <div class="hero-sub" id="heroSub">Loading elite performers…</div>
    <div class="hero-kpis">
      <div class="kpi"><div class="kpi-val" id="kpiElites">—</div><div class="kpi-label">Elites Listed</div></div>
      <div class="kpi"><div class="kpi-val" id="kpiBadges">—</div><div class="kpi-label">Badges Awarded</div></div>
      <div class="kpi"><div class="kpi-val" id="kpiLegendary">—</div><div class="kpi-label">Legendary</div></div>
    </div>
  </div>
  <div class="ticker-wrap"><div class="ticker" id="ticker"></div></div>
</div>

<div class="main">

<!-- PODIUM -->
<section>
  <div class="sec-label reveal">All-Time Top 3</div>
  <div class="sec-title reveal">The Immortal Podium</div>
  <div class="podium-trio reveal" id="podiumTrio"></div>
</section>

<div class="divider"></div>

<!-- WALL OF FAME -->
<section>
  <div class="sec-label reveal">Achievement Wall</div>
  <div class="sec-title reveal">Elite Performers</div>

  <div class="filter-strip reveal" id="filterStrip">
    <span class="filter-label">Filter:</span>
    <button class="flt-btn active" data-filter="all">All</button>
    <div class="filter-sep"></div>
    <span class="filter-label">Inst:</span>
    <button class="flt-btn ib-kjs" data-inst="KJS">KJS</button>
    <button class="flt-btn ib-mjs" data-inst="MJS">MJS</button>
    <button class="flt-btn ib-ujs" data-inst="UJS">UJS</button>
    <div class="filter-sep"></div>
    <span class="filter-label">Badge:</span>
    <button class="flt-btn" data-badge="rank1">👑 #1</button>
    <button class="flt-btn" data-badge="top10">⭐ Top10</button>
    <button class="flt-btn" data-badge="sharpshooter">🎯 Sharp</button>
    <button class="flt-btn" data-badge="ironwall">🔒 Consistent</button>
    <button class="flt-btn" data-badge="rising">📈 Rising</button>
    <input class="search-elite" id="eliteSearch" type="text" placeholder="Search name…">
  </div>

  <div id="wallGrid" class="elites-grid"></div>
  <div id="wallEmpty" class="empty-msg" style="display:none;">No elites match the current filter.</div>
</section>

<div class="divider"></div>

<!-- BADGE LEGEND -->
<section>
  <div class="sec-label reveal">Achievement Guide</div>
  <div class="sec-title reveal">Badge Glossary</div>
  <div class="badge-legend reveal" id="badgeLegend"></div>
</section>

</div><!-- /main -->

<div id="loadingWrap" class="loading-wrap main" style="max-width:1600px;margin:0 auto;padding:0 2.5rem;">
  <div class="ld-dots"><div class="ld-dot"></div><div class="ld-dot"></div><div class="ld-dot"></div></div>
  <div class="ld-text">Scanning achievements…</div>
</div>

<footer style="text-align:center;padding:2rem;color:var(--muted);font-size:0.58rem;letter-spacing:0.18em;border-top:1px solid var(--border);position:relative;z-index:1;">JUT ELITES · WALL OF FAME · ACHIEVEMENT SYSTEM</footer>

<script>
const BADGE_META = {
  rank1:       { icon:'👑', label:'#1 Overall',        tier:'legendary', desc:'Highest avg score across all JUTs in the batch.' },
  podium:      { icon:'🏅', label:'Podium',             tier:'gold',      desc:'Among the top 3 students by average score.' },
  top10:       { icon:'⭐', label:'Top 10',             tier:'gold',      desc:'Within the top 10 students overall.' },
  elite10:     { icon:'🔱', label:'Top 10%',            tier:'silver',    desc:'Ranks in the top 10% of the entire batch.' },
  top25:       { icon:'💎', label:'Top 25%',            tier:'silver',    desc:'Ranks in the top 25% of the batch.' },
  perfect:     { icon:'✨', label:'Perfect Score',      tier:'legendary', desc:'Achieved a flawless 300/300 in a JUT.' },
  near_perfect:{ icon:'🌟', label:'Near Perfect',       tier:'gold',      desc:'Scored 280 or above in a single JUT.' },
  sharpshooter:{ icon:'🎯', label:'Sharpshooter',       tier:'gold',      desc:'80%+ overall accuracy across all attempts.' },
  precise:     { icon:'🔬', label:'Precision',          tier:'silver',    desc:'70%+ overall accuracy across all attempts.' },
  ironwall:    { icon:'🔒', label:'Iron Wall',          tier:'gold',      desc:'85%+ consistency score (very low variance).' },
  consistent:  { icon:'📐', label:'Consistent',         tier:'silver',    desc:'70%+ consistency score across tests.' },
  perfect_att: { icon:'📅', label:'Perfect Attendance', tier:'silver',    desc:'Attended every single JUT without absence.' },
  phy_ace:     { icon:'⚛️', label:'Physics Ace',        tier:'silver',    desc:'Average Physics score ≥ 80 marks.' },
  chem_ace:    { icon:'🧪', label:'Chemistry Ace',      tier:'silver',    desc:'Average Chemistry score ≥ 80 marks.' },
  math_ace:    { icon:'∑',  label:'Maths Ace',          tier:'silver',    desc:'Average Maths score ≥ 80 marks.' },
  phy_god:     { icon:'⚡', label:'Physics God',        tier:'gold',      desc:'Average Physics score ≥ 90 marks.' },
  chem_god:    { icon:'🔭', label:'Chem Genius',        tier:'gold',      desc:'Average Chemistry score ≥ 90 marks.' },
  math_god:    { icon:'🌀', label:'Math Wizard',        tier:'gold',      desc:'Average Maths score ≥ 90 marks.' },
  rising:      { icon:'📈', label:'Rising Star',        tier:'silver',    desc:'Last 3 JUT scores show continuous improvement.' },
};

let allData = [], filteredData = [];
let activeInst = null, activeBadge = null, searchText = '';

function normName(n){ return n.trim().replace(/\s+/g,' ').toUpperCase(); }

function instChip(inst){
  if(!inst) return '';
  const cls = inst==='KJS'?'inst-kjs':inst==='MJS'?'inst-mjs':'inst-ujs';
  return `<span class="card-inst ${cls}">${inst}</span>`;
}

function tierOrder(t){ return {legendary:0,gold:1,silver:2,bronze:3}[t]??4; }

function highestTier(badges){
  if(!badges.length) return 'default';
  return badges.slice().sort((a,b)=>tierOrder(a.tier)-tierOrder(b.tier))[0].tier;
}

function bandClass(tier){
  return {legendary:'band-legendary',gold:'band-gold',silver:'band-silver'}[tier]||'band-default';
}

function rankClass(r){
  return r===1?'rank-1-c':r===2?'rank-2-c':r===3?'rank-3-c':'rank-n-c';
}

function buildCard(s){
  const tier = highestTier(s.badges);
  const isLeg = tier==='legendary';
  const top3 = s.rank<=3;
  const instC = s.inst?`inst-${s.inst.toLowerCase()}`:'';

  // photo
  let photoHtml = '';
  if(s.photo){
    photoHtml = `<img class="card-photo" src="${s.photo}" alt="${s.name}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
      <div class="card-photo-fallback" style="display:none;">${s.name.split(' ').map(w=>w[0]).join('').slice(0,2)}</div>`;
  } else {
    photoHtml = `<div class="card-photo-fallback">${s.name.split(' ').map(w=>w[0]).join('').slice(0,2)}</div>`;
  }

  // subject bars
  const maxSubj = Math.max(s.avg_phy, s.avg_chem, s.avg_math, 1);
  const subjBars = [
    {lbl:'Phy', val:s.avg_phy, color:'var(--phy)'},
    {lbl:'Che', val:s.avg_chem, color:'var(--chem)'},
    {lbl:'Mat', val:s.avg_math, color:'var(--math)'},
  ].map(x=>`<div class="csb-row">
    <div class="csb-label"><span style="color:${x.color}">${x.lbl}</span><span>${Math.round(x.val)}</span></div>
    <div class="csb-outer"><div class="csb-inner" style="background:${x.color};width:${(x.val/100*100).toFixed(1)}%"></div></div>
  </div>`).join('');

  // badges (up to 5 shown)
  const badgesHtml = s.badges.slice(0,6).map(b=>{
    const meta = BADGE_META[b.id]||{icon:'🏷️',label:b.label,tier:b.tier};
    return `<span class="badge tier-${meta.tier}" title="${(BADGE_META[b.id]||{}).desc||''}"><span class="badge-icon">${meta.icon}</span>${meta.label}</span>`;
  }).join('');

  const accColor = s.accuracy>=80?'var(--accent2)':s.accuracy>=60?'var(--accent)':'var(--math)';

  return `<a class="elite-card${isLeg?' legendary-card':''}" href="/student?student=${encodeURIComponent(s.name)}">
  <div class="card-band ${bandClass(tier)}"></div>
  <div class="card-rank ${rankClass(s.rank)}">#${s.rank}</div>
  <div class="card-photo-wrap">
    ${photoHtml}
    <div class="card-photo-overlay"></div>
    <div class="card-photo-score">
      <div class="card-photo-avg-label">Avg Score</div>
      ${Math.round(s.avg_score)}
    </div>
  </div>
  <div class="card-body">
    ${instChip(s.inst)}
    <div class="card-name">${s.name}</div>
    <div class="card-stats">
      <div class="card-stat-item"><div class="cs-val" style="color:var(--accent)">${Math.round(s.avg_score)}</div><div class="cs-lbl">Avg</div></div>
      <div class="card-stat-item"><div class="cs-val" style="color:var(--gold)">${s.best_score}</div><div class="cs-lbl">Best</div></div>
      <div class="card-stat-item"><div class="cs-val" style="color:${accColor}">${s.accuracy}%</div><div class="cs-lbl">Acc</div></div>
      <div class="card-stat-item"><div class="cs-val" style="color:var(--accent2)">${s.attended}</div><div class="cs-lbl">JUTs</div></div>
      ${s.consistency!==null?`<div class="card-stat-item"><div class="cs-val" style="color:var(--silver)">${s.consistency}%</div><div class="cs-lbl">Cons.</div></div>`:''}
    </div>
    <div class="card-subj-bars">${subjBars}</div>
    <div class="card-badges">${badgesHtml}</div>
  </div>
</a>`;
}

function applyFilters(){
  let d = [...allData];
  if(activeInst) d = d.filter(s=>s.inst===activeInst);
  if(activeBadge) d = d.filter(s=>s.badges.some(b=>b.id===activeBadge));
  if(searchText) d = d.filter(s=>normName(s.name).includes(searchText.toUpperCase()));
  filteredData = d;
  const wall = document.getElementById('wallGrid');
  const empty = document.getElementById('wallEmpty');
  if(!d.length){ wall.innerHTML=''; empty.style.display='block'; return; }
  empty.style.display='none';
  wall.innerHTML = d.map(buildCard).join('');
}

function buildPodium(data){
  const top3 = data.slice(0,3);
  const order = [top3[1], top3[0], top3[2]].filter(Boolean);
  const classes = ['ptop ptop-2','ptop ptop-1','ptop ptop-3'];
  const medals = ['🥈','🥇','🥉'];
  const heights = [120,150,88];
  const trio = document.getElementById('podiumTrio');
  trio.innerHTML = order.map((s,i)=>{
    const photoInner = s.photo
      ? `<img src="${s.photo}" alt="${s.name}" style="width:100%;height:100%;object-fit:cover;" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';"><div class="ptop-photo-fb" style="display:none;">${s.name.split(' ').map(w=>w[0]).join('').slice(0,2)}</div>`
      : `<div class="ptop-photo-fb">${s.name.split(' ').map(w=>w[0]).join('').slice(0,2)}</div>`;
    return `<a class="${classes[i]}" href="/student?student=${encodeURIComponent(s.name)}" style="text-decoration:none;color:inherit;">
      <div class="ptop-photo"><span class="ptop-medal">${medals[i]}</span>${photoInner}</div>
      <div class="ptop-name">${s.name}</div>
      <div class="ptop-score">${Math.round(s.avg_score)}</div>
      <div class="ptop-sub">avg · best: ${s.best_score}</div>
      <div class="ptop-block" style="background:${['linear-gradient(135deg,#94a3b8,#64748b)','linear-gradient(135deg,#fbbf24,#f59e0b)','linear-gradient(135deg,#cd7f32,#a0632a)'][i]};height:${heights[i]}px">${medals[i]}</div>
    </a>`;
  }).join('');
}

function buildBadgeLegend(){
  const leg = document.getElementById('badgeLegend');
  leg.innerHTML = Object.entries(BADGE_META).map(([id,b])=>`
    <div class="bl-item">
      <div class="bl-icon">${b.icon}</div>
      <div>
        <div class="bl-name"><span class="badge tier-${b.tier}" style="font-size:0.52rem;">${b.label}</span></div>
        <div class="bl-desc">${b.desc}</div>
      </div>
    </div>`).join('');
}

function buildTicker(data){
  const items = data.slice(0,20).map(s=>`<span class="ticker-item">${s.name}<span class="ticker-sep">·</span>#${s.rank}<span class="ticker-sep">·</span>${Math.round(s.avg_score)} avg</span>`).join('');
  const t = document.getElementById('ticker');
  t.innerHTML = items + items; // double for seamless loop
}

async function loadElites(){
  try{
    const res = await fetch('/api/elites');
    if(!res.ok) throw new Error('HTTP '+res.status);
    allData = await res.json();

    // Hero KPIs
    const totalBadges = allData.reduce((s,e)=>s+e.badges.length,0);
    const legendaryCount = allData.filter(e=>e.badges.some(b=>b.tier==='legendary')).length;
    document.getElementById('kpiElites').textContent = allData.length;
    document.getElementById('kpiBadges').textContent = totalBadges;
    document.getElementById('kpiLegendary').textContent = legendaryCount;
    document.getElementById('heroSub').textContent = allData.length + ' ELITE PERFORMERS · ' + totalBadges + ' BADGES AWARDED · ' + legendaryCount + ' LEGENDARY';

    document.getElementById('loadingWrap').style.display='none';
    document.getElementById('wallGrid').closest('section').style.display='block';

    buildPodium(allData);
    buildTicker(allData);
    buildBadgeLegend();
    applyFilters();

    // Reveal
    const io = new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('vis');});},{threshold:0.05});
    document.querySelectorAll('.reveal').forEach(el=>{el.classList.remove('vis');io.observe(el);});

  } catch(e){
    document.getElementById('loadingWrap').innerHTML=`<div style="color:var(--accent3);font-size:0.75rem;letter-spacing:0.2em;text-align:center;">Error: ${e.message}</div>`;
  }
}

// Filter buttons
document.querySelectorAll('[data-inst]').forEach(btn=>{
  btn.addEventListener('click',()=>{
    const inst = btn.dataset.inst;
    activeInst = activeInst===inst ? null : inst;
    document.querySelectorAll('[data-inst]').forEach(b=>b.classList.remove('active'));
    if(activeInst) btn.classList.add('active');
    applyFilters();
  });
});
document.querySelectorAll('[data-badge]').forEach(btn=>{
  btn.addEventListener('click',()=>{
    const badge = btn.dataset.badge;
    activeBadge = activeBadge===badge ? null : badge;
    document.querySelectorAll('[data-badge]').forEach(b=>b.classList.remove('active'));
    if(activeBadge) btn.classList.add('active');
    applyFilters();
  });
});
document.querySelector('[data-filter="all"]').addEventListener('click',()=>{
  activeInst=null; activeBadge=null;
  document.querySelectorAll('[data-inst],[data-badge]').forEach(b=>b.classList.remove('active'));
  document.querySelector('[data-filter="all"]').classList.add('active');
  applyFilters();
});
document.getElementById('eliteSearch').addEventListener('input',e=>{
  searchText=e.target.value.trim();
  applyFilters();
});

loadElites();
</script>
</body>
</html>"""

# ══════════════════════════════════════════════════════════════════════════════
#  NEET ANALYSIS PAGE (with halving correction in mapRow)
# ══════════════════════════════════════════════════════════════════════════════

NEET_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NEET Performance Analysis</title>
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
    --bio: #4ade80;
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
  .subj-card.bio { border-top: 3px solid var(--bio); }

  .subj-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
  }

  .subj-card.phy .subj-name { color: var(--phy); }
  .subj-card.chem .subj-name { color: var(--chem); }
  .subj-card.bio .subj-name { color: var(--bio); }

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
    opacity: 1;
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

  .inst-filter-bar{display:flex;gap:0.5rem;align-items:center;margin-bottom:1rem;flex-wrap:wrap;}
  .inst-filter-label{font-size:0.55rem;letter-spacing:0.22em;color:var(--muted);text-transform:uppercase;}
  .inst-btn{font-size:0.55rem;letter-spacing:0.15em;text-transform:uppercase;padding:0.35rem 0.8rem;border:1px solid var(--border);border-radius:2px;cursor:pointer;background:transparent;color:var(--muted);font-family:'JetBrains Mono',monospace;transition:all 0.2s;white-space:nowrap;}
  .inst-btn:hover{border-color:var(--accent);color:var(--accent);}
  .inst-btn.active{background:var(--accent);color:var(--bg);border-color:var(--accent);}
  .inst-btn.ib-kjs.active{background:#4fc3f7;border-color:#4fc3f7;color:var(--bg);}
  .inst-btn.ib-mjs.active{background:#a78bfa;border-color:#a78bfa;color:var(--bg);}
  .inst-btn.ib-ujs.active{background:#fb923c;border-color:#fb923c;color:var(--bg);}
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
  <a class="topnav-back" href="/">← Back</a>
</nav>

<div class="hero">
  <div class="hero-bg"></div>
  <div class="hero-grid"></div>
  <div style="position:relative;z-index:2;">
    <div class="hero-tag" id="heroTag">NEET · Batch Analysis</div>
    <div class="hero-title">NEET<span>PERFOR</span>MANCE</div>
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
  <div class="inst-filter-bar reveal" id="instFilterBar">
    <span class="inst-filter-label">Institution:</span>
    <button class="inst-btn active" data-inst="ALL">All</button>
    <button class="inst-btn ib-kjs" data-inst="KJS">KJS</button>
    <button class="inst-btn ib-mjs" data-inst="MJS">MJS</button>
    <button class="inst-btn ib-ujs" data-inst="UJS">UJS</button>
  </div>
  <div class="filter-bar reveal">
    <input class="search-input" id="searchInput" type="text" placeholder="Search student…">
    <button class="sort-btn active" data-sort="total">Total ↕</button>
    <button class="sort-btn" data-sort="phy">Physics ↕</button>
    <button class="sort-btn" data-sort="chem">Chemistry ↕</button>
    <button class="sort-btn" data-sort="bio">Biology ↕</button>
    <button class="sort-btn" data-sort="acc">Accuracy ↕</button>
  </div>
  <div style="overflow-x:auto">
    <table class="leaderboard-table">
      <thead>
        <tr>
          <th>SL</th><th>CSV Rank</th><th>#</th><th>Student</th><th>Inst</th><th>Score</th><th>Subject Breakdown</th><th>Accuracy</th><th>Attempted</th>
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
    <div class="subj-card bio reveal" id="bioCard"></div>
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
      <div class="chart-title">Correct vs Wrong vs Unattempted (Top 10)</div>
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
      <span style="font-size:0.65rem;color:var(--bio);">&#9632; Biology</span>
    </div>
    <div id="heatmapGrid" class="matrix-grid"></div>
  </div>
</section>

<footer id="footerBar">NEET ANALYSIS DASHBOARD</footer>

<div id="uploadOverlay" style="display:none;">
  <div class="picker-title">SELECT NEET TEST</div>
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

function getInstA(fileVal){
  if(!fileVal) return '';
  const f=(fileVal+'').trim().toUpperCase();
  if(f.startsWith('K')) return 'KJS';
  if(f.startsWith('U')) return 'UJS';
  if(f.startsWith('M')) return 'MJS';
  return '';
}

function mapRow(r, filename) {
  const get = (...ks) => { for (const k of ks) { if (r[k] !== undefined && r[k] !== '') return r[k]; } return '0'; };
  const getS = (...ks) => { for (const k of ks) { if (r[k] !== undefined && r[k] !== '') return r[k]; } return ''; };

  // Base row
  const row = {
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
    test:   getS('test','test_name','filename','jut','jut_name') || 'Unknown'
  };

  // ── Extract test code ──
  let testCode = extractTestCode(row.test);
  // Fallback: extract the LAST number from the filename (e.g. "60jut9722.csv" → "9722")
  if (!testCode && filename) {
    const allNums = filename.match(/\d+/g);
    if (allNums && allNums.length > 0) {
      testCode = allNums[allNums.length - 1];
    }
  }

  // ── Subject swap correction ──
  if (testCode && subjectSwaps[testCode]) {
    console.log(`🔄 Applying swap for test code: ${testCode}`);
    const swapMap = subjectSwaps[testCode].swap || {};

    // Map short suffixes (_m, _c, _w, _a) used by the row object
    const suffixMap = {
      '_marks':   '_m',
      '_correct': '_c',
      '_wrong':   '_w',
      '_attempt': '_a'
    };

    const subjects = ['phy', 'chem', 'math'];
    const original = {};

    // Save original values
    subjects.forEach(subj => {
      Object.values(suffixMap).forEach(suff => {
        const key = subj + suff;
        if (row[key] !== undefined) original[key] = row[key];
      });
    });

    // Apply swaps
    subjects.forEach(subj => {
      const target = swapMap[subj] || subj;
      if (target === subj) return;
      Object.values(suffixMap).forEach(suff => {
        const srcKey = subj + suff;
        const dstKey = target + suff;
        if (srcKey in original) {
          row[dstKey] = original[srcKey];
        }
      });
    });
  }

  // ── Halving correction ──
  const attemptVals = [row.phy_a, row.chem_a, row.math_a, row.tot_a];
  if (attemptVals.some(v => v > 75)) {
    const fields = ['phy_a','chem_a','math_a','tot_a','phy_c','chem_c','math_c','tot_c',
                    'phy_w','chem_w','math_w','tot_w','phy_m','chem_m','math_m','total'];
    fields.forEach(f => {
      if (f === 'total') row.total = row.total / 2;
      else row[f] = row[f] / 2;
    });
  }
  return row;
}

let radarInst, stackedInst, accuracyInst;

function buildDashboard(raw, filename) {
  raw.forEach(s => { s.accuracy = s.tot_a > 0 ? Math.round((s.tot_c / s.tot_a) * 100) : 0; });
  const sorted = [...raw].sort((a,b) => {
    if (b.total !== a.total) return b.total - a.total;
    if (b.tot_c !== a.tot_c) return b.tot_c - a.tot_c;
    return a.name.localeCompare(b.name);
  });
  const avg  = Math.round(raw.reduce((s,r) => s+r.total, 0) / raw.length);
  const high = Math.max(...raw.map(r => r.total));
  const avgAcc = Math.round(raw.reduce((s,r) => s+r.accuracy, 0) / raw.length);
  const maxPossible = 720;

  document.getElementById('hs-avg').textContent   = avg;
  document.getElementById('hs-high').textContent  = high;
  document.getElementById('hs-acc').textContent   = avgAcc + '%';
  document.getElementById('hs-count').textContent = raw.length;
  document.getElementById('heroSub').textContent  = raw.length + ' STUDENTS · PHYSICS · CHEMISTRY · BIOLOGY';
  const label = filename.replace('.csv','').replace(/_/g,' ').toUpperCase();
  document.getElementById('heroTag').textContent  = 'NEET · ' + label + ' · BATCH ANALYSIS';
  document.getElementById('topnavFile').textContent = label;
  document.getElementById('footerBar').textContent = 'NEET ANALYSIS DASHBOARD · ' + raw.length + ' STUDENTS · ' + label;
  document.title = 'NEET · ' + label;

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

  let currentSort = 'total', sortDir = -1, filterText = '', instFilterA = 'ALL';

  function getTier(score) {
    if (score >= high * 0.75) return 'tier-excellent';
    if (score >= high * 0.5)  return 'tier-good';
    if (score >= high * 0.25) return 'tier-average';
    return 'tier-poor';
  }

  function renderLeaderboard() {
    let data = [...raw];
    if (instFilterA !== 'ALL') data = data.filter(s => (s.inst||'').toUpperCase() === instFilterA);
    if (filterText) data = data.filter(s => s.name.toLowerCase().includes(filterText.toLowerCase()));
    const valKeys = {total:'total',phy:'phy_m',chem:'chem_m',bio:'bio_m',acc:'accuracy'};
    data.sort((a,b) => {
      const diff = sortDir * (a[valKeys[currentSort]] - b[valKeys[currentSort]]);
      if (diff !== 0) return diff;
      if (b.tot_c !== a.tot_c) return b.tot_c - a.tot_c;
      return a.name.localeCompare(b.name);
    });
    const tbody = document.getElementById('leaderboardBody');
    tbody.innerHTML = '';
    data.forEach((s, slIdx) => {
      const phyPct  = Math.max(0, (s.phy_m  / maxPossible) * 100);
      const chemPct = Math.max(0, (s.chem_m / maxPossible) * 100);
      const bioPct  = Math.max(0, (s.bio_m  / maxPossible) * 100);
      const localRank = sorted.indexOf(s) + 1;
      const rankClass = localRank===1?'rank-1':localRank===2?'rank-2':localRank===3?'rank-3':'rank-other';
      const scoreColor = s.total>=high*0.75?'var(--accent2)':s.total>=high*0.5?'var(--accent)':s.total>=high*0.25?'var(--math)':'var(--accent3)';
      const accColor = s.accuracy>=60?'var(--accent2)':s.accuracy>=40?'var(--accent)':'var(--accent3)';
      const csvRank = s.rank ? s.rank : '\u2014';
      const tr = document.createElement('tr');
      tr.className = 'row ' + getTier(s.total);
      tr.innerHTML =
        '<td style="color:var(--muted);font-size:0.65rem;min-width:32px;">' + (slIdx+1) + '</td>' +
        '<td style="color:var(--muted);font-family:\'Bebas Neue\',sans-serif;font-size:1.1rem;min-width:48px;">' + csvRank + '</td>' +
        '<td><span class="rank-badge ' + rankClass + '">' + localRank + '</span></td>' +
        '<td><div class="name-cell"><a href="/student?student=' + encodeURIComponent(s.name) + '">' + s.name + '</a></div></td>' +
        '<td>' + (s.inst ? '<span class="inst-chip inst-'+(s.inst||'').toLowerCase()+'">' + s.inst + '</span>' : '') + '</td>' +
        '<td><span class="score-pill" style="background:' + scoreColor + '22;color:' + scoreColor + '">' + s.total + '</span></td>' +
        '<td><div class="mini-bar-wrap">' +
          '<div class="mini-bar" style="width:' + (phyPct*1.5) + 'px;background:var(--phy)"></div>' +
          '<div class="mini-bar" style="width:' + (chemPct*1.5) + 'px;background:var(--chem)"></div>' +
          '<div class="mini-bar" style="width:' + (bioPct*1.5) + 'px;background:var(--bio)"></div>' +
        '</div><div style="font-size:0.6rem;color:var(--muted);margin-top:3px;">P:' + s.phy_m + ' \u00b7 C:' + s.chem_m + ' \u00b7 B:' + s.bio_m + '</div></td>' +
        '<td style="color:' + accColor + '">' + s.accuracy + '%</td>' +
        '<td style="color:var(--muted)">' + s.tot_a + '/180</td>';
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
  document.querySelectorAll('#instFilterBar .inst-btn').forEach(btn => {
    btn.onclick = () => {
      instFilterA = btn.dataset.inst;
      document.querySelectorAll('#instFilterBar .inst-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderLeaderboard();
    };
  });

  function subjectStats(marks, correct, wrong, attempt, maxPerQ=4) {
    const avg  = (marks.reduce((a,b)=>a+b,0)/marks.length).toFixed(1);
    const best = Math.max(...marks), worst = Math.min(...marks);
    const avgC = (correct.reduce((a,b)=>a+b,0)/correct.length).toFixed(1);
    const avgW = (wrong.reduce((a,b)=>a+b,0)/wrong.length).toFixed(1);
    const totalC = correct.reduce((a,b)=>a+b,0), totalA = attempt.reduce((a,b)=>a+b,0);
    const acc = totalA > 0 ? Math.round((totalC/totalA)*100) : 0;
    return {avg, best, worst, avgC, avgW, acc};
  }
  
  function makeSubjectCard(id, label, color, marks, correct, wrong, attempt, qCount) {
    const s = subjectStats(marks, correct, wrong, attempt);
    document.getElementById(id).innerHTML =
      '<div class="subj-name">' + label + '</div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Avg Marks</span><span class="subj-stat-val" style="color:' + color + '">' + s.avg + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Highest</span><span class="subj-stat-val">' + s.best + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Lowest</span><span class="subj-stat-val">' + s.worst + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Avg Correct</span><span class="subj-stat-val">' + s.avgC + ' / ' + qCount + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Avg Wrong</span><span class="subj-stat-val">' + s.avgW + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Accuracy</span><span class="subj-stat-val">' + s.acc + '%</span></div>';
  }
  
  makeSubjectCard('physCard','Physics','var(--phy)',raw.map(r=>r.phy_m),raw.map(r=>r.phy_c),raw.map(r=>r.phy_w),raw.map(r=>r.phy_a), 45);
  makeSubjectCard('chemCard','Chemistry','var(--chem)',raw.map(r=>r.chem_m),raw.map(r=>r.chem_c),raw.map(r=>r.chem_w),raw.map(r=>r.chem_a), 45);
  makeSubjectCard('bioCard','Biology','var(--bio)',raw.map(r=>r.bio_m),raw.map(r=>r.bio_c),raw.map(r=>r.bio_w),raw.map(r=>r.bio_a), 90);

  const distContainer = document.getElementById('distBars');
  distContainer.innerHTML = '';
  const step = high > 0 ? Math.ceil(high / 5) : 144;
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
  const bioAvg  = raw.reduce((a,r)=>a+r.bio_m,0)/raw.length;
  if(radarInst) radarInst.destroy();
  radarInst = new Chart(document.getElementById('radarChart'), {
    type:'radar',
    data:{labels:['Physics','Chemistry','Biology'],datasets:[{label:'Avg Marks',data:[phyAvg.toFixed(1),chemAvg.toFixed(1),bioAvg.toFixed(1)],borderColor:'#e8c547',backgroundColor:'rgba(232,197,71,0.1)',pointBackgroundColor:['#4fc3f7','#a78bfa','#4ade80'],pointRadius:6,borderWidth:2}]},
    options:{scales:{r:{grid:{color:'#1e1e2e'},ticks:{display:false},pointLabels:{color:'#e8e8f0',font:{family:'JetBrains Mono',size:11}}}},plugins:{legend:{display:false}}}
  });

  const top10 = sorted.slice(0,10);
  if(stackedInst) stackedInst.destroy();
  stackedInst = new Chart(document.getElementById('stackedChart'), {
    type:'bar',
    data:{labels:top10.map(s=>firstMeaningfulName(s.name)),datasets:[
      {label:'Correct',data:top10.map(s=>s.tot_c),backgroundColor:'#47e8c5bb',stack:'s'},
      {label:'Wrong',data:top10.map(s=>s.tot_w),backgroundColor:'#e847a0bb',stack:'s'},
      {label:'Unattempted',data:top10.map(s=>180-s.tot_a),backgroundColor:'#1e1e2e',stack:'s'},
    ]},
    options:{scales:{x:{ticks:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}},grid:{color:'#1e1e2e'}},y:{ticks:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}},grid:{color:'#1e1e2e'},max:180}},plugins:{legend:{labels:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}}}}}
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
  const subjects = ['phy','chem','bio'];
  const subjColors = {'phy':'79,195,247','chem':'167,139,250','bio':'74,222,128'};
  hmGrid.style.gridTemplateColumns = 'repeat(' + (subjects.length * 3) + ', 28px)';
  ['P','C','B'].forEach(s => { ['C','W','%'].forEach(t => {
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
      const maxQ = subj === 'bio' ? 90 : 45;
      const mk = (bg, tip) => {
        const el = document.createElement('div');
        el.className = 'matrix-cell';
        el.style.cssText = 'background:' + bg + ';width:28px;height:28px;';
        el.innerHTML = '<div class="tooltip">' + dn + ' \u00b7 ' + subj.toUpperCase() + ' ' + tip + '</div>';
        hmGrid.appendChild(el);
      };
      mk('rgba('+rgb+','+(0.1+(c/maxQ)*0.7)+')', 'correct: '+c);
      mk('rgba(232,71,160,'+(0.05+(w/maxQ)*0.7)+')', 'wrong: '+w);
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
    const neetFiles = files.filter(f => f.toLowerCase().includes('neet'));
    if (neetFiles.length === 0) {
      menu.innerHTML = '<div style="color:#6b6b8a;font-size:0.75rem;letter-spacing:0.15em;text-align:center;padding:1rem;">NO NEET CSV FILES FOUND IN /static<br>Please add a file named like "neet.csv" or "neet_*.csv"</div>';
      return;
    }
    neetFiles.forEach(filename => {
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
    // Try to automatically load the first NEET file found
    try {
      const res = await fetch('/api/csv-files');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const files = await res.json();
      const neetFiles = files.filter(f => f.toLowerCase().includes('neet'));
      
      if (neetFiles.length === 1) {
        document.getElementById('heroSub').textContent = 'LOADING ' + neetFiles[0].toUpperCase() + '…';
        await loadCSVByName(neetFiles[0]);
      } else if (neetFiles.length > 1) {
        document.getElementById('heroSub').textContent = 'SELECT A NEET TEST TO BEGIN';
        const overlay = document.getElementById('uploadOverlay');
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
        await populatePickerMenu();
      } else {
        document.getElementById('heroSub').textContent = 'NO NEET CSV FILES FOUND';
        const overlay = document.getElementById('uploadOverlay');
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
        await populatePickerMenu();
      }
    } catch(err) {
      document.getElementById('heroSub').textContent = 'ERROR LOADING FILES';
      const overlay = document.getElementById('uploadOverlay');
      overlay.style.display = 'flex';
      overlay.style.opacity = '1';
      await populatePickerMenu();
    }
  }
})();
</script>
</body>
</html>"""

# ══════════════════════════════════════════════════════════════════════════════
#  KCET ANALYSIS PAGE (with halving correction in mapRow)
# ══════════════════════════════════════════════════════════════════════════════

KCET_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KCET Performance Analysis</title>
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
    opacity: 1;
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

  .inst-filter-bar{display:flex;gap:0.5rem;align-items:center;margin-bottom:1rem;flex-wrap:wrap;}
  .inst-filter-label{font-size:0.55rem;letter-spacing:0.22em;color:var(--muted);text-transform:uppercase;}
  .inst-btn{font-size:0.55rem;letter-spacing:0.15em;text-transform:uppercase;padding:0.35rem 0.8rem;border:1px solid var(--border);border-radius:2px;cursor:pointer;background:transparent;color:var(--muted);font-family:'JetBrains Mono',monospace;transition:all 0.2s;white-space:nowrap;}
  .inst-btn:hover{border-color:var(--accent);color:var(--accent);}
  .inst-btn.active{background:var(--accent);color:var(--bg);border-color:var(--accent);}
  .inst-btn.ib-kjs.active{background:#4fc3f7;border-color:#4fc3f7;color:var(--bg);}
  .inst-btn.ib-mjs.active{background:#a78bfa;border-color:#a78bfa;color:var(--bg);}
  .inst-btn.ib-ujs.active{background:#fb923c;border-color:#fb923c;color:var(--bg);}
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
  <a class="topnav-back" href="/">← Back</a>
</nav>

<div class="hero">
  <div class="hero-bg"></div>
  <div class="hero-grid"></div>
  <div style="position:relative;z-index:2;">
    <div class="hero-tag" id="heroTag">KCET · Batch Analysis</div>
    <div class="hero-title">KCET<span>PERFOR</span>MANCE</div>
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
  <div class="inst-filter-bar reveal" id="instFilterBar">
    <span class="inst-filter-label">Institution:</span>
    <button class="inst-btn active" data-inst="ALL">All</button>
    <button class="inst-btn ib-kjs" data-inst="KJS">KJS</button>
    <button class="inst-btn ib-mjs" data-inst="MJS">MJS</button>
    <button class="inst-btn ib-ujs" data-inst="UJS">UJS</button>
  </div>
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
          <th>SL</th><th>CSV Rank</th><th>#</th><th>Student</th><th>Inst</th><th>Score</th><th>Subject Breakdown</th><th>Accuracy</th><th>Attempted</th>
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
      <div class="chart-title">Correct vs Wrong vs Unattempted (Top 10)</div>
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
      <span style="font-size:0.65rem;color:var(--math);">&#9632; Mathematics</span>
    </div>
    <div id="heatmapGrid" class="matrix-grid"></div>
  </div>
</section>

<footer id="footerBar">KCET ANALYSIS DASHBOARD</footer>

<div id="uploadOverlay" style="display:none;">
  <div class="picker-title">SELECT KCET TEST</div>
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

function getInstA(fileVal){
  if(!fileVal) return '';
  const f=(fileVal+'').trim().toUpperCase();
  if(f.startsWith('K')) return 'KJS';
  if(f.startsWith('U')) return 'UJS';
  if(f.startsWith('M')) return 'MJS';
  return '';
}

function mapRow(r, filename) {
  const get = (...ks) => { for (const k of ks) { if (r[k] !== undefined && r[k] !== '') return r[k]; } return '0'; };
  const getS = (...ks) => { for (const k of ks) { if (r[k] !== undefined && r[k] !== '') return r[k]; } return ''; };

  // Base row
  const row = {
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
    test:   getS('test','test_name','filename','jut','jut_name') || 'Unknown'
  };

  // ── Extract test code ──
  let testCode = extractTestCode(row.test);
  console.log('🔍 row.test:', JSON.stringify(row.test));
  console.log('🔍 testCode from row.test:', testCode);

  if (!testCode && filename) {
    const allNums = filename.match(/\d+/g);
    if (allNums && allNums.length > 0) testCode = allNums[allNums.length - 1];
    console.log('🔍 testCode from filename:', testCode);
  }

  console.log('🔍 subjectSwaps object:', JSON.stringify(subjectSwaps));
  console.log('🔍 subjectSwaps[testCode]:', JSON.stringify(subjectSwaps[testCode]));
  console.log('🔍 row BEFORE swap - phy_m:', row.phy_m, 'math_m:', row.math_m);

  // ── Subject swap correction ──
  if (testCode && subjectSwaps[testCode]) {
    console.log(`🔄 Applying swap for test code: ${testCode}`);
    const swapMap = subjectSwaps[testCode].swap || {};

    const suffixMap = {
      '_marks':   '_m',
      '_correct': '_c',
      '_wrong':   '_w',
      '_attempt': '_a'
    };

    const subjects = ['phy', 'chem', 'math'];
    const original = {};

    subjects.forEach(subj => {
      Object.values(suffixMap).forEach(suff => {
        const key = subj + suff;
        if (row[key] !== undefined) original[key] = row[key];
      });
    });

    subjects.forEach(subj => {
      const target = swapMap[subj] || subj;
      if (target === subj) return;
      Object.values(suffixMap).forEach(suff => {
        const srcKey = subj + suff;
        const dstKey = target + suff;
        if (srcKey in original) {
          row[dstKey] = original[srcKey];
        }
      });
    });

    console.log('🔍 row AFTER swap - phy_m:', row.phy_m, 'math_m:', row.math_m);

  } else {
    console.log('⚠️ Swap NOT applied. testCode:', testCode, 'exists in swaps?', !!(testCode && subjectSwaps[testCode]));
  }

  // ── Halving correction ──
  const attemptVals = [row.phy_a, row.chem_a, row.math_a, row.tot_a];
  if (attemptVals.some(v => v > 75)) {
    const fields = ['phy_a','chem_a','math_a','tot_a','phy_c','chem_c','math_c','tot_c',
                    'phy_w','chem_w','math_w','tot_w','phy_m','chem_m','math_m','total'];
    fields.forEach(f => {
      if (f === 'total') row.total = row.total / 2;
      else row[f] = row[f] / 2;
    });
  }
  return row;
}

let radarInst, stackedInst, accuracyInst;

function buildDashboard(raw, filename) {
  raw.forEach(s => { s.accuracy = s.tot_a > 0 ? Math.round((s.tot_c / s.tot_a) * 100) : 0; });
  const sorted = [...raw].sort((a,b) => {
    if (b.total !== a.total) return b.total - a.total;
    if (b.tot_c !== a.tot_c) return b.tot_c - a.tot_c;
    return a.name.localeCompare(b.name);
  });
  const avg  = Math.round(raw.reduce((s,r) => s+r.total, 0) / raw.length);
  const high = Math.max(...raw.map(r => r.total));
  const avgAcc = Math.round(raw.reduce((s,r) => s+r.accuracy, 0) / raw.length);
  const maxPossible = 600;

  document.getElementById('hs-avg').textContent   = avg;
  document.getElementById('hs-high').textContent  = high;
  document.getElementById('hs-acc').textContent   = avgAcc + '%';
  document.getElementById('hs-count').textContent = raw.length;
  document.getElementById('heroSub').textContent  = raw.length + ' STUDENTS · PHYSICS · CHEMISTRY · MATHEMATICS';
  const label = filename.replace('.csv','').replace(/_/g,' ').toUpperCase();
  document.getElementById('heroTag').textContent  = 'KCET · ' + label + ' · BATCH ANALYSIS';
  document.getElementById('topnavFile').textContent = label;
  document.getElementById('footerBar').textContent = 'KCET ANALYSIS DASHBOARD · ' + raw.length + ' STUDENTS · ' + label;
  document.title = 'KCET · ' + label;

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

  let currentSort = 'total', sortDir = -1, filterText = '', instFilterA = 'ALL';

  function getTier(score) {
    if (score >= high * 0.75) return 'tier-excellent';
    if (score >= high * 0.5)  return 'tier-good';
    if (score >= high * 0.25) return 'tier-average';
    return 'tier-poor';
  }

  function renderLeaderboard() {
    let data = [...raw];
    if (instFilterA !== 'ALL') data = data.filter(s => (s.inst||'').toUpperCase() === instFilterA);
    if (filterText) data = data.filter(s => s.name.toLowerCase().includes(filterText.toLowerCase()));
    const valKeys = {total:'total',phy:'phy_m',chem:'chem_m',math:'math_m',acc:'accuracy'};
    data.sort((a,b) => {
      const diff = sortDir * (a[valKeys[currentSort]] - b[valKeys[currentSort]]);
      if (diff !== 0) return diff;
      if (b.tot_c !== a.tot_c) return b.tot_c - a.tot_c;
      return a.name.localeCompare(b.name);
    });
    const tbody = document.getElementById('leaderboardBody');
    tbody.innerHTML = '';
    data.forEach((s, slIdx) => {
      const phyPct  = Math.max(0, (s.phy_m  / maxPossible) * 100);
      const chemPct = Math.max(0, (s.chem_m / maxPossible) * 100);
      const mathPct = Math.max(0, (s.math_m / maxPossible) * 100);
      const localRank = sorted.indexOf(s) + 1;
      const rankClass = localRank===1?'rank-1':localRank===2?'rank-2':localRank===3?'rank-3':'rank-other';
      const scoreColor = s.total>=high*0.75?'var(--accent2)':s.total>=high*0.5?'var(--accent)':s.total>=high*0.25?'var(--math)':'var(--accent3)';
      const accColor = s.accuracy>=60?'var(--accent2)':s.accuracy>=40?'var(--accent)':'var(--accent3)';
      const csvRank = s.rank ? s.rank : '\u2014';
      const tr = document.createElement('tr');
      tr.className = 'row ' + getTier(s.total);
      tr.innerHTML =
        '<td style="color:var(--muted);font-size:0.65rem;min-width:32px;">' + (slIdx+1) + '</td>' +
        '<td style="color:var(--muted);font-family:\'Bebas Neue\',sans-serif;font-size:1.1rem;min-width:48px;">' + csvRank + '</td>' +
        '<td><span class="rank-badge ' + rankClass + '">' + localRank + '</span></td>' +
        '<td><div class="name-cell"><a href="/student?student=' + encodeURIComponent(s.name) + '">' + s.name + '</a></div></td>' +
        '<td>' + (s.inst ? '<span class="inst-chip inst-'+(s.inst||'').toLowerCase()+'">' + s.inst + '</span>' : '') + '</td>' +
        '<td><span class="score-pill" style="background:' + scoreColor + '22;color:' + scoreColor + '">' + s.total + '</span></td>' +
        '<td><div class="mini-bar-wrap">' +
          '<div class="mini-bar" style="width:' + (phyPct*1.2) + 'px;background:var(--phy)"></div>' +
          '<div class="mini-bar" style="width:' + (chemPct*1.2) + 'px;background:var(--chem)"></div>' +
          '<div class="mini-bar" style="width:' + (mathPct*1.2) + 'px;background:var(--math)"></div>' +
        '</div><div style="font-size:0.6rem;color:var(--muted);margin-top:3px;">P:' + s.phy_m + ' \u00b7 C:' + s.chem_m + ' \u00b7 M:' + s.math_m + '</div></td>' +
        '<td style="color:' + accColor + '">' + s.accuracy + '%</td>' +
        '<td style="color:var(--muted)">' + s.tot_a + '/180</td>';
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
  document.querySelectorAll('#instFilterBar .inst-btn').forEach(btn => {
    btn.onclick = () => {
      instFilterA = btn.dataset.inst;
      document.querySelectorAll('#instFilterBar .inst-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderLeaderboard();
    };
  });

  function subjectStats(marks, correct, wrong, attempt, maxQ=60) {
    const avg  = (marks.reduce((a,b)=>a+b,0)/marks.length).toFixed(1);
    const best = Math.max(...marks), worst = Math.min(...marks);
    const avgC = (correct.reduce((a,b)=>a+b,0)/correct.length).toFixed(1);
    const avgW = (wrong.reduce((a,b)=>a+b,0)/wrong.length).toFixed(1);
    const totalC = correct.reduce((a,b)=>a+b,0), totalA = attempt.reduce((a,b)=>a+b,0);
    const acc = totalA > 0 ? Math.round((totalC/totalA)*100) : 0;
    return {avg, best, worst, avgC, avgW, acc};
  }
  
  function makeSubjectCard(id, label, color, marks, correct, wrong, attempt, qCount) {
    const s = subjectStats(marks, correct, wrong, attempt, qCount);
    document.getElementById(id).innerHTML =
      '<div class="subj-name">' + label + '</div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Avg Marks</span><span class="subj-stat-val" style="color:' + color + '">' + s.avg + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Highest</span><span class="subj-stat-val">' + s.best + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Lowest</span><span class="subj-stat-val">' + s.worst + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Avg Correct</span><span class="subj-stat-val">' + s.avgC + ' / ' + qCount + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Avg Wrong</span><span class="subj-stat-val">' + s.avgW + '</span></div>' +
      '<div class="subj-stat-row"><span class="subj-stat-key">Accuracy</span><span class="subj-stat-val">' + s.acc + '%</span></div>';
  }
  
  makeSubjectCard('physCard','Physics','var(--phy)',raw.map(r=>r.phy_m),raw.map(r=>r.phy_c),raw.map(r=>r.phy_w),raw.map(r=>r.phy_a), 60);
  makeSubjectCard('chemCard','Chemistry','var(--chem)',raw.map(r=>r.chem_m),raw.map(r=>r.chem_c),raw.map(r=>r.chem_w),raw.map(r=>r.chem_a), 60);
  makeSubjectCard('mathCard','Mathematics','var(--math)',raw.map(r=>r.math_m),raw.map(r=>r.math_c),raw.map(r=>r.math_w),raw.map(r=>r.math_a), 60);

  const distContainer = document.getElementById('distBars');
  distContainer.innerHTML = '';
  const step = high > 0 ? Math.ceil(high / 5) : 100;
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
      {label:'Unattempted',data:top10.map(s=>180-s.tot_a),backgroundColor:'#1e1e2e',stack:'s'},
    ]},
    options:{scales:{x:{ticks:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}},grid:{color:'#1e1e2e'}},y:{ticks:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}},grid:{color:'#1e1e2e'},max:180}},plugins:{legend:{labels:{color:'#6b6b8a',font:{family:'JetBrains Mono',size:9}}}}}
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
      const maxQ = 60;
      const mk = (bg, tip) => {
        const el = document.createElement('div');
        el.className = 'matrix-cell';
        el.style.cssText = 'background:' + bg + ';width:28px;height:28px;';
        el.innerHTML = '<div class="tooltip">' + dn + ' \u00b7 ' + subj.toUpperCase() + ' ' + tip + '</div>';
        hmGrid.appendChild(el);
      };
      mk('rgba('+rgb+','+(0.1+(c/maxQ)*0.7)+')', 'correct: '+c);
      mk('rgba(232,71,160,'+(0.05+(w/maxQ)*0.7)+')', 'wrong: '+w);
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
    const kcetFiles = files.filter(f => f.toLowerCase().includes('kcet'));
    if (kcetFiles.length === 0) {
      menu.innerHTML = '<div style="color:#6b6b8a;font-size:0.75rem;letter-spacing:0.15em;text-align:center;padding:1rem;">NO KCET CSV FILES FOUND IN /static<br>Please add a file named like "kcet.csv" or "kcet_*.csv"</div>';
      return;
    }
    kcetFiles.forEach(filename => {
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
    try {
      const res = await fetch('/api/csv-files');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const files = await res.json();
      const kcetFiles = files.filter(f => f.toLowerCase().includes('kcet'));
      
      if (kcetFiles.length === 1) {
        document.getElementById('heroSub').textContent = 'LOADING ' + kcetFiles[0].toUpperCase() + '…';
        await loadCSVByName(kcetFiles[0]);
      } else if (kcetFiles.length > 1) {
        document.getElementById('heroSub').textContent = 'SELECT A KCET TEST TO BEGIN';
        const overlay = document.getElementById('uploadOverlay');
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
        await populatePickerMenu();
      } else {
        document.getElementById('heroSub').textContent = 'NO KCET CSV FILES FOUND';
        const overlay = document.getElementById('uploadOverlay');
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
        await populatePickerMenu();
      }
    } catch(err) {
      document.getElementById('heroSub').textContent = 'ERROR LOADING FILES';
      const overlay = document.getElementById('uploadOverlay');
      overlay.style.display = 'flex';
      overlay.style.opacity = '1';
      await populatePickerMenu();
    }
  }
})();
</script>
</body>
</html>"""

#__________ANOMALY___________#
ANOMALY_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JUT · Anomaly Check</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@300;400;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0a0a0f;--surface:#111118;--surface2:#16161f;--border:#1e1e2e;
  --accent:#e8c547;--accent2:#47e8c5;--accent3:#e847a0;
  --text:#e8e8f0;--muted:#6b6b8a;
  --red:#f87171;
}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;overflow-x:hidden;padding:2rem;}
body::after{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");pointer-events:none;z-index:9999;opacity:0.4;}
.topnav{position:sticky;top:0;z-index:10;background:rgba(10,10,15,0.9);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:1rem 2rem;margin:-2rem -2rem 2rem -2rem;}
.topnav-logo{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:0.08em;color:var(--text);text-decoration:none;}
.topnav-logo span{color:var(--accent);}
.topnav-back{font-size:0.6rem;letter-spacing:0.25em;text-transform:uppercase;color:var(--muted);text-decoration:none;transition:color 0.2s;}
.topnav-back:hover{color:var(--accent);}
h1{font-family:'Bebas Neue',sans-serif;font-size:4rem;margin-bottom:0.5rem;color:var(--accent);}
.sub{font-size:0.7rem;color:var(--muted);letter-spacing:0.2em;margin-bottom:2rem;}
.jut-block{margin-bottom:3rem;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.5rem;overflow-x:auto;}
.jut-title{font-family:'DM Serif Display',serif;font-size:1.8rem;margin-bottom:1rem;color:var(--accent2);}
table{width:100%;border-collapse:collapse;font-size:0.75rem;}
th{text-align:left;padding:0.5rem 0.8rem;color:var(--muted);font-weight:400;letter-spacing:0.15em;text-transform:uppercase;border-bottom:1px solid var(--border);}
td{padding:0.5rem 0.8rem;border-bottom:1px solid var(--border);}
.anomaly-highlight{background:rgba(248,113,113,0.08);}
.high-value{color:var(--red);font-weight:600;}
.empty-state{text-align:center;padding:4rem;color:var(--muted);font-size:0.8rem;letter-spacing:0.2em;}
</style>
</head>
<body>
<nav class="topnav">
  <a class="topnav-logo" href="/">JUT<span>·</span>HUB</a>
  <a class="topnav-back" href="/">← Back to Hub</a>
</nav>
<h1>⚠️ ANOMALY CHECK</h1>
<div class="sub">Rows where any attempt > 75 (before halving correction) – grouped by JUT</div>
<div id="content">
  <div style="text-align:center;padding:3rem;color:var(--muted);">Loading anomalies…</div>
</div>
<script>
async function loadAnomalies(){
  const container = document.getElementById('content');
  try{
    const res = await fetch('/api/anomalies');
    if(!res.ok) throw new Error('HTTP '+res.status);
    const data = await res.json();
    const tests = Object.keys(data);
    if(!tests.length){
      container.innerHTML = '<div class="empty-state">✅ No anomalies found – all attempt values ≤ 75.</div>';
      return;
    }
    let html = '';
    tests.forEach(test => {
      const rows = data[test];
      html += `<div class="jut-block"><div class="jut-title">📄 ${test}</div><table><thead><tr>
        <th>Student</th><th>Total Attempt</th><th>Physics Attempt</th><th>Chemistry Attempt</th><th>Maths Attempt</th><th>Total Marks</th>
      </tr></thead><tbody>`;
      rows.forEach(r => {
        const totalA = parseFloat(r.total_attempt) || 0;
        const phyA = parseFloat(r.phy_attempt) || 0;
        const chemA = parseFloat(r.chem_attempt) || 0;
        const mathA = parseFloat(r.math_attempt) || 0;
        const isAnomaly = totalA > 75 || phyA > 75 || chemA > 75 || mathA > 75;
        const cls = isAnomaly ? 'anomaly-highlight' : '';
        const highClass = (val) => val > 75 ? 'high-value' : '';
        html += `<tr class="${cls}">
          <td><strong>${r.name || 'Unknown'}</strong></td>
          <td><span class="${highClass(totalA)}">${totalA}</span></td>
          <td><span class="${highClass(phyA)}">${phyA}</span></td>
          <td><span class="${highClass(chemA)}">${chemA}</span></td>
          <td><span class="${highClass(mathA)}">${mathA}</span></td>
          <td>${r.total_marks || r.total_score || '—'}</td>
        </tr>`;
      });
      html += '</tbody></table></div>';
    });
    container.innerHTML = html;
  } catch(e){
    container.innerHTML = `<div class="empty-state" style="color:var(--red);">Error: ${e.message}</div>`;
  }
}
loadAnomalies();
</script>
</body>
</html>"""


SWAP_MANAGER_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Swap Manager · JUT Hub</title>
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
    --green: #4ade80;
    --red: #f87171;
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

  .hero {
    padding: 4rem 0 3rem;
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
    font-size: clamp(3rem, 8vw, 6rem);
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
    margin-top: 1.5rem;
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
  }
  .section-title {
    font-family: 'DM Serif Display', serif;
    font-size: clamp(1.6rem, 4vw, 2.5rem);
    margin-bottom: 2rem;
  }

  .topnav {
    position: fixed;
    top: 0; left: 0; right: 0;
    z-index: 500;
    background: rgba(10,10,15,0.9);
    backdrop-filter: blur(20px);
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
    transition: color 0.2s;
  }
  .topnav-back:hover { color: var(--accent); }

  .main-wrap {
    max-width: 1200px;
    margin: 0 auto;
    padding: 6rem 2rem 4rem;
  }

  /* ── Swap UI ── */
  .swap-form {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 2rem;
    margin-bottom: 3rem;
  }
  .swap-form-row {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    align-items: flex-end;
  }
  .swap-form-group {
    flex: 1;
    min-width: 180px;
  }
  .swap-form-group label {
    display: block;
    font-size: 0.55rem;
    letter-spacing: 0.2em;
    color: var(--muted);
    text-transform: uppercase;
    margin-bottom: 0.4rem;
  }
  .swap-form-group select,
  .swap-form-group input {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 0.6rem 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    border-radius: 4px;
    outline: none;
    transition: border-color 0.2s;
  }
  .swap-form-group select:focus,
  .swap-form-group input:focus {
    border-color: var(--accent);
  }
  .swap-form-group select option {
    background: var(--surface);
  }

  .swap-type-group {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .swap-type-btn {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 0.4rem 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .swap-type-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
  .swap-type-btn.active {
    border-color: var(--accent);
    background: rgba(232,197,71,0.1);
    color: var(--accent);
  }

  .btn {
    background: var(--accent);
    border: none;
    color: var(--bg);
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.2rem;
    padding: 0.6rem 2rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s, transform 0.1s;
    letter-spacing: 0.05em;
    min-width: 120px;
  }
  .btn:hover { background: #d4b03a; }
  .btn:active { transform: scale(0.97); }
  .btn-danger {
    background: var(--accent3);
  }
  .btn-danger:hover { background: #c73a8a; }
  .btn-success {
    background: var(--accent2);
    color: var(--bg);
  }
  .btn-success:hover { background: #3ad4b5; }
  .btn-outline {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
  }
  .btn-outline:hover {
    border-color: var(--accent);
    color: var(--accent);
  }

  /* ── Swap list ── */
  .swap-list {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
  }
  .swap-item {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1.2rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
    transition: border-color 0.2s;
  }
  .swap-item:hover { border-color: rgba(232,197,71,0.3); }
  .swap-item-left {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    flex-wrap: wrap;
  }
  .swap-item-id {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    color: var(--accent);
    min-width: 80px;
  }
  .swap-item-mapping {
    display: flex;
    gap: 0.8rem;
    align-items: center;
    flex-wrap: wrap;
  }
  .swap-subj {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.05em;
  }
  .swap-subj-phy { background: rgba(79,195,247,0.2); color: var(--phy); }
  .swap-subj-chem { background: rgba(167,139,250,0.2); color: var(--chem); }
  .swap-subj-math { background: rgba(251,146,60,0.2); color: var(--math); }
  .swap-arrow { color: var(--muted); font-size: 1.2rem; }
  .swap-item-actions {
    display: flex;
    gap: 0.5rem;
  }
  .swap-item-actions button {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 0.3rem 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.55rem;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .swap-item-actions button:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
  .swap-item-actions .delete-btn:hover {
    border-color: var(--accent3);
    color: var(--accent3);
  }

  .empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--muted);
  }
  .empty-state-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .toast {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 2rem;
    z-index: 1000;
    transform: translateY(100px);
    opacity: 0;
    transition: all 0.4s ease;
    max-width: 400px;
  }
  .toast.show {
    transform: translateY(0);
    opacity: 1;
  }
  .toast-success { border-color: var(--green); }
  .toast-success .toast-icon { color: var(--green); }
  .toast-error { border-color: var(--red); }
  .toast-error .toast-icon { color: var(--red); }
  .toast-message { font-size: 0.7rem; margin-top: 0.3rem; }

  .loading-spinner {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @keyframes fadeUp {
    from { opacity:0; transform:translateY(20px); }
    to   { opacity:1; transform:translateY(0); }
  }

  @media(max-width:600px) {
    .swap-form-row { flex-direction: column; }
    .swap-item { flex-direction: column; align-items: stretch; }
    .swap-item-left { flex-direction: column; align-items: flex-start; }
    .swap-item-actions { justify-content: flex-end; }
  }
</style>
</head>
<body>
<div class="grid-bg"></div>
<div class="glow-1"></div>
<div class="glow-2"></div>
<div class="glow-3"></div>

<nav class="topnav">
  <a class="topnav-logo" href="/">JUT<span>·</span>HUB</a>
  <a class="topnav-back" href="/">← Back to Hub</a>
</nav>

<div class="main-wrap">
  <div class="hero">
    <div class="hero-eyebrow">Subject Swap Manager</div>
    <div class="hero-title">SWAP<span class="outline">CONTROL</span></div>
    <div class="hero-desc">Add, edit, or remove subject swaps for any JUT. Changes are saved directly to GitHub.</div>
  </div>

  <div class="divider"></div>

  <!-- ── Add / Edit Form ── -->
  <div class="section-label">Manage Swap</div>
  <div class="section-title" id="formTitle">Add New Swap</div>
  <div class="swap-form" id="swapForm">
    <div class="swap-form-row">
      <div class="swap-form-group">
        <label>JUT ID</label>
        <select id="jutSelect"></select>
      </div>
      <div class="swap-form-group">
        <label>Swap Type</label>
        <div class="swap-type-group" id="swapTypeGroup">
          <button class="swap-type-btn" data-type="phy_math">P ↔ M</button>
          <button class="swap-type-btn" data-type="chem_math">C ↔ M</button>
          <button class="swap-type-btn" data-type="phy_chem">P ↔ C</button>
          <button class="swap-type-btn" data-type="phy_chem_math">P → C → M</button>
          <button class="swap-type-btn" data-type="custom">Custom</button>
        </div>
      </div>
    </div>
    <div class="swap-form-row" style="margin-top:1rem;" id="customSwapRow" style="display:none;">
      <div class="swap-form-group" style="flex:0 0 120px;">
        <label>From</label>
        <select id="swapFrom">
          <option value="phy">Physics</option>
          <option value="chem">Chemistry</option>
          <option value="math">Maths</option>
        </select>
      </div>
      <div class="swap-form-group" style="flex:0 0 60px;text-align:center;padding-top:1.5rem;">
        <span style="color:var(--muted);font-size:1.5rem;">→</span>
      </div>
      <div class="swap-form-group" style="flex:0 0 120px;">
        <label>To</label>
        <select id="swapTo">
          <option value="phy">Physics</option>
          <option value="chem">Chemistry</option>
          <option value="math">Maths</option>
        </select>
      </div>
    </div>
    <div class="swap-form-row" style="margin-top:1.5rem;">
      <button class="btn" id="saveBtn">Save Swap</button>
      <button class="btn btn-outline" id="cancelBtn" style="display:none;">Cancel</button>
      <span id="formStatus" style="font-size:0.65rem;color:var(--muted);margin-left:1rem;"></span>
    </div>
  </div>

  <div class="divider"></div>

  <!-- ── Existing Swaps ── -->
  <div class="section-label">Active Swaps</div>
  <div class="section-title">Current Mappings</div>
  <div id="swapListContainer">
    <div style="text-align:center;padding:2rem;color:var(--muted);">
      <div class="loading-spinner"></div>
      <div style="margin-top:0.5rem;font-size:0.7rem;">Loading swaps…</div>
    </div>
  </div>
</div>

<!-- ── Toast ── -->
<div class="toast" id="toast">
  <div style="display:flex;align-items:center;gap:0.8rem;">
    <span class="toast-icon" style="font-size:1.5rem;">✓</span>
    <div>
      <div style="font-weight:600;font-size:0.75rem;" id="toastTitle">Success</div>
      <div class="toast-message" id="toastMessage">Swaps updated.</div>
    </div>
  </div>
</div>

<script>
let currentSwaps = {};
let editingId = null;
let csvFiles = [];

// ── DOM refs ──
const jutSelect = document.getElementById('jutSelect');
const swapTypeGroup = document.getElementById('swapTypeGroup');
const customSwapRow = document.getElementById('customSwapRow');
const swapFrom = document.getElementById('swapFrom');
const swapTo = document.getElementById('swapTo');
const saveBtn = document.getElementById('saveBtn');
const cancelBtn = document.getElementById('cancelBtn');
const formStatus = document.getElementById('formStatus');
const formTitle = document.getElementById('formTitle');
const swapListContainer = document.getElementById('swapListContainer');
const toast = document.getElementById('toast');

// ── Toast ──
let toastTimeout;

function showToast(message, type = 'success') {
  toast.className = `toast toast-${type}`;
  document.getElementById('toastTitle').textContent = type === 'success' ? 'Success' : 'Error';
  document.getElementById('toastMessage').textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove('show'), 4000);
}

// ── Fetch CSV files ──
async function fetchCSVFiles() {
  try {
    const res = await fetch('/api/csv-files');
    if (!res.ok) throw new Error('Failed to fetch files');
    csvFiles = await res.json();
    const ids = csvFiles
      .map(f => {
        const match = f.match(/\d+/g);
        return match ? match[match.length - 1] : null;
      })
      .filter(id => id !== null);
    // Populate dropdown
    jutSelect.innerHTML = '';
    ids.forEach(id => {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = `JUT ${id}`;
      jutSelect.appendChild(opt);
    });
  } catch (e) {
    console.error('Error fetching CSV files:', e);
    showToast('Could not load JUT list', 'error');
  }
}

// ── Fetch swaps ──
async function fetchSwaps() {
  try {
    const res = await fetch('/api/swaps');
    if (!res.ok) throw new Error('Failed to fetch swaps');
    currentSwaps = await res.json();
    renderSwaps();
  } catch (e) {
    console.error('Error fetching swaps:', e);
    swapListContainer.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">⚠️</div>
      <p>Could not load swaps. Make sure GITHUB_TOKEN is set.</p>
    </div>`;
  }
}

// ── Render swaps ──
function renderSwaps() {
  const ids = Object.keys(currentSwaps);
  if (ids.length === 0) {
    swapListContainer.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">📭</div>
      <p>No swaps configured yet. Add one above.</p>
    </div>`;
    return;
  }

  let html = '<div class="swap-list">';
  ids.sort().forEach(id => {
    const swap = currentSwaps[id].swap || {};
    const entries = Object.entries(swap);
    const mappingHtml = entries.map(([from, to]) => {
      const fromLabel = {phy:'Physics',chem:'Chemistry',math:'Maths'}[from] || from;
      const toLabel = {phy:'Physics',chem:'Chemistry',math:'Maths'}[to] || to;
      const fromClass = {phy:'swap-subj-phy',chem:'swap-subj-chem',math:'swap-subj-math'}[from] || '';
      const toClass = {phy:'swap-subj-phy',chem:'swap-subj-chem',math:'swap-subj-math'}[to] || '';
      return `<span class="swap-subj ${fromClass}">${fromLabel}</span>
              <span class="swap-arrow">→</span>
              <span class="swap-subj ${toClass}">${toLabel}</span>`;
    }).join(' <span class="swap-arrow" style="margin:0 0.3rem;">·</span> ');

    html += `
      <div class="swap-item" data-id="${id}">
        <div class="swap-item-left">
          <div class="swap-item-id">#${id}</div>
          <div class="swap-item-mapping">${mappingHtml}</div>
        </div>
        <div class="swap-item-actions">
          <button class="edit-btn" onclick="editSwap('${id}')">✎ Edit</button>
          <button class="delete-btn" onclick="deleteSwap('${id}')">✕ Delete</button>
        </div>
      </div>
    `;
  });
  html += '</div>';
  swapListContainer.innerHTML = html;
}

// ── Swap type presets ──
function getSwapForType(type) {
  const presets = {
    'phy_math': { phy: 'math', math: 'phy' },
    'chem_math': { chem: 'math', math: 'chem' },
    'phy_chem': { phy: 'chem', chem: 'phy' },
    'phy_chem_math': { phy: 'chem', chem: 'math', math: 'phy' },
  };
  return presets[type] || null;
}

// ── Swap type button clicks ──
document.querySelectorAll('.swap-type-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.swap-type-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const type = btn.dataset.type;
    if (type === 'custom') {
      customSwapRow.style.display = 'flex';
      formStatus.textContent = 'Custom swap: select from → to';
    } else {
      customSwapRow.style.display = 'none';
      const preset = getSwapForType(type);
      if (preset) {
        const desc = Object.entries(preset).map(([f,t]) => {
          const labels = {phy:'P',chem:'C',math:'M'};
          return `${labels[f]}→${labels[t]}`;
        }).join(' · ');
        formStatus.textContent = `Preset: ${desc}`;
      }
    }
  });
});

// Default: select first preset
document.querySelector('.swap-type-btn')?.classList.add('active');

// ── Save / Update swap ──
saveBtn.addEventListener('click', async () => {
  const id = jutSelect.value;
  if (!id) {
    showToast('Please select a JUT ID', 'error');
    return;
  }

  // Get active swap type
  const activeBtn = document.querySelector('.swap-type-btn.active');
  const type = activeBtn ? activeBtn.dataset.type : 'custom';
  let swap = {};

  if (type === 'custom') {
    const from = swapFrom.value;
    const to = swapTo.value;
    if (from === to) {
      showToast('Cannot swap a subject with itself', 'error');
      return;
    }
    swap[from] = to;
  } else {
    const preset = getSwapForType(type);
    if (!preset) {
      showToast('Invalid swap type', 'error');
      return;
    }
    swap = { ...preset };
  }

  // Update currentSwaps
  currentSwaps[id] = { swap };

  try {
    const res = await fetch('/api/swaps', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentSwaps)
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`Swap for JUT ${id} saved successfully!`, 'success');
      renderSwaps();
      resetForm();
    } else {
      showToast(data.error || 'Failed to save', 'error');
    }
  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
  }
});

// ── Edit swap ──
function editSwap(id) {
  editingId = id;
  const swap = currentSwaps[id]?.swap || {};
  const entries = Object.entries(swap);

  // Select JUT
  jutSelect.value = id;

  // Try to match a preset
  const presetNames = {
    'phy_math': { phy: 'math', math: 'phy' },
    'chem_math': { chem: 'math', math: 'chem' },
    'phy_chem': { phy: 'chem', chem: 'phy' },
    'phy_chem_math': { phy: 'chem', chem: 'math', math: 'phy' },
  };

  let matched = false;
  for (const [name, preset] of Object.entries(presetNames)) {
    if (JSON.stringify(entries.sort()) === JSON.stringify(Object.entries(preset).sort())) {
      document.querySelectorAll('.swap-type-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.type === name);
      });
      matched = true;
      customSwapRow.style.display = 'none';
      formStatus.textContent = `Editing preset for JUT ${id}`;
      break;
    }
  }

  if (!matched) {
    // Custom
    document.querySelectorAll('.swap-type-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('[data-type="custom"]')?.classList.add('active');
    customSwapRow.style.display = 'flex';
    if (entries.length > 0) {
      swapFrom.value = entries[0][0];
      swapTo.value = entries[0][1];
    }
    formStatus.textContent = `Editing custom swap for JUT ${id}`;
  }

  formTitle.textContent = `Edit Swap for JUT ${id}`;
  saveBtn.textContent = 'Update Swap';
  cancelBtn.style.display = 'inline-block';
}

// ── Delete swap ──
async function deleteSwap(id) {
  if (!confirm(`Delete swap for JUT ${id}?`)) return;
  delete currentSwaps[id];

  try {
    const res = await fetch('/api/swaps', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentSwaps)
    });
    if (res.ok) {
      showToast(`Swap for JUT ${id} deleted`, 'success');
      renderSwaps();
    } else {
      const data = await res.json();
      showToast(data.error || 'Failed to delete', 'error');
    }
  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
  }
}

// ── Reset form ──
function resetForm() {
  editingId = null;
  formTitle.textContent = 'Add New Swap';
  saveBtn.textContent = 'Save Swap';
  cancelBtn.style.display = 'none';
  formStatus.textContent = '';
  customSwapRow.style.display = 'none';
  // Reset to first JUT
  if (jutSelect.options.length > 0) jutSelect.selectedIndex = 0;
  // Select first preset
  document.querySelectorAll('.swap-type-btn').forEach((b, i) => {
    b.classList.toggle('active', i === 0);
  });
  swapFrom.value = 'phy';
  swapTo.value = 'math';
}

cancelBtn.addEventListener('click', resetForm);

// ── Auto-fill JUT from dropdown ──
// When selecting a JUT that already has a swap, show its current mapping
jutSelect.addEventListener('change', () => {
  const id = jutSelect.value;
  if (id && currentSwaps[id]) {
    // We're viewing an existing swap - show its mapping but don't auto-edit
    const swap = currentSwaps[id].swap || {};
    const entries = Object.entries(swap);
    if (entries.length > 0) {
      // Try to match preset for display
      const presetNames = {
        'phy_math': { phy: 'math', math: 'phy' },
        'chem_math': { chem: 'math', math: 'chem' },
        'phy_chem': { phy: 'chem', chem: 'phy' },
        'phy_chem_math': { phy: 'chem', chem: 'math', math: 'phy' },
      };
      let matched = false;
      for (const [name, preset] of Object.entries(presetNames)) {
        if (JSON.stringify(entries.sort()) === JSON.stringify(Object.entries(preset).sort())) {
          document.querySelectorAll('.swap-type-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.type === name);
          });
          matched = true;
          customSwapRow.style.display = 'none';
          formStatus.textContent = `Existing: ${Object.entries(swap).map(([f,t]) => {
            const labels = {phy:'P',chem:'C',math:'M'};
            return `${labels[f]}→${labels[t]}`;
          }).join(' · ')}`;
          break;
        }
      }
      if (!matched) {
        document.querySelectorAll('.swap-type-btn').forEach(b => b.classList.remove('active'));
        document.querySelector('[data-type="custom"]')?.classList.add('active');
        customSwapRow.style.display = 'flex';
        swapFrom.value = entries[0][0];
        swapTo.value = entries[0][1];
        formStatus.textContent = `Existing custom: ${entries[0][0]} → ${entries[0][1]}`;
      }
    }
  } else {
    // Reset to default
    document.querySelectorAll('.swap-type-btn').forEach((b, i) => {
      b.classList.toggle('active', i === 0);
    });
    customSwapRow.style.display = 'none';
    formStatus.textContent = '';
  }
});

// ── Init ──
async function init() {
  await fetchCSVFiles();
  await fetchSwaps();
  // Set default JUT
  if (jutSelect.options.length > 0) {
    // Try to find the largest JUT number (most recent)
    let maxIdx = 0;
    let maxVal = 0;
    for (let i = 0; i < jutSelect.options.length; i++) {
      const val = parseInt(jutSelect.options[i].value);
      if (val > maxVal) { maxVal = val; maxIdx = i; }
    }
    jutSelect.selectedIndex = maxIdx;
  }
  // Trigger change to show existing swap if any
  jutSelect.dispatchEvent(new Event('change'));
}

init();
</script>
</body>
</html>"""


@app.route('/debug-swaps')
@login_required
def debug_swaps():
    return jsonify({
        'swaps_file': SWAPS_FILE,
        'exists': os.path.exists(SWAPS_FILE),
        'content': load_subject_swaps()
    })
    
from urllib.parse import unquote

@app.route("/debug-row/<student_name>")
@login_required
def debug_row(student_name):
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    
    # Decode URL‑encoded characters and normalize spaces
    decoded_name = unquote(student_name)
    normalized_input = ' '.join(decoded_name.strip().split())
    
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
            if 'name' not in clean or not clean['name']:
                continue
            stored_name = ' '.join(clean['name'].strip().split())
            if stored_name.lower() == normalized_input.lower():
                before = clean.copy()
                test_code = extract_test_code(clean.get('test', ''))
                apply_subject_swaps(clean)
                return jsonify({
                    'test_code': test_code,
                    'before': before,
                    'after': clean,
                    'swaps_loaded': load_subject_swaps(),
                    'matched_on': stored_name
                })
    
    # If not found, return the full list of names for debugging
    available = []
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
            if 'name' in clean and clean['name']:
                available.append(clean['name'])
    
    return jsonify({
        "error": "Student not found",
        "you_searched_for": normalized_input,
        "available_names": sorted(set(available)),
        "hint": "Copy one of these names exactly as shown"
    }), 404

@app.route("/debug-test-rows/<test_code>")
@login_required
def debug_test_rows(test_code):
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    rows = []
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
            tcode = extract_test_code(clean.get('test', ''))
            if tcode == test_code:
                before = clean.copy()
                apply_subject_swaps(clean)
                rows.append({
                    'name': clean.get('name'),
                    'test': clean.get('test'),
                    'before_phy_math': (before.get('phy_marks'), before.get('math_marks')),
                    'after_phy_math': (clean.get('phy_marks'), clean.get('math_marks'))
                })
    return jsonify(rows[:5])  # first 5 rows

@app.route("/debug-headers")
@login_required
def debug_headers():
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
    return jsonify({"headers": headers})

@app.route("/debug-students")
@login_required
def debug_students():
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    names = []
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
            if 'name' in clean and clean['name']:
                names.append(clean['name'])
    return jsonify(sorted(set(names)))

@app.route("/debug-students-by-test/<test_code>")
@login_required
def debug_students_by_test(test_code):
    master_path = os.path.join(os.path.dirname(app.static_folder), 'master', 'master.csv')
    if not os.path.exists(master_path):
        return jsonify({"error": "master.csv not found"}), 404
    students = []
    with open(master_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
            if 'name' in clean and clean['name']:
                tcode = extract_test_code(clean.get('test', ''))
                if tcode == test_code:
                    students.append(clean['name'])
    return jsonify(sorted(set(students)))


if __name__ == "__main__":
    app.run(debug=True)
