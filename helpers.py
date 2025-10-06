import os, re, json, sqlite3
from datetime import datetime
from fpdf import FPDF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib

# ==========================================================
# ================  SELF-LEARNING DB SETUP  =================
# ==========================================================
DB_PATH = "learning_store.db"

def init_learning_db():
    """Create categories table if not exists."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_category TEXT,
            sub_category TEXT,
            keywords TEXT,
            last_seen TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_or_update_subcategory(parent, subcat, keywords):
    """Insert or update a sub-category entry with latest keywords."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id FROM categories WHERE parent_category=? AND sub_category=?;",
        (parent, subcat)
    )
    row = c.fetchone()
    now = datetime.now().isoformat()
    if row:
        c.execute(
            "UPDATE categories SET keywords=?, last_seen=? WHERE id=?;",
            (json.dumps(keywords), now, row[0])
        )
    else:
        c.execute(
            "INSERT INTO categories (parent_category, sub_category, keywords, last_seen) VALUES (?, ?, ?, ?);",
            (parent, subcat, json.dumps(keywords), now)
        )
    conn.commit()
    conn.close()

def get_all_training_data():
    """Return (text, subcat) pairs from DB."""
    conn = sqlite3.connect(DB_PATH)
    df = []
    for row in conn.execute("SELECT parent_category, sub_category, keywords FROM categories"):
        parent, subcat, keywords = row
        for kw in json.loads(keywords):
            df.append((kw, subcat))
    conn.close()
    return df


# ==========================================================
# ===================  ML MODEL SECTION  ====================
# ==========================================================
MODEL_PATH = "models/subcat_clf.pkl"
VEC_PATH = "models/subcat_vec.pkl"

def train_ml_classifier():
    """Train or reload classifier from DB."""
    os.makedirs("models", exist_ok=True)
    data = get_all_training_data()
    if not data:
        # bootstrap small model
        sample_logs = [
            "database connection failed",
            "cpu usage high",
            "disk full",
            "login failed",
            "backup failed"
        ]
        y = ["DB issue", "Infra issue", "Infra issue", "Security", "Backup"]
        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(sample_logs)
        clf = LogisticRegression(max_iter=200)
        clf.fit(X, y)
        joblib.dump(clf, MODEL_PATH)
        joblib.dump(vectorizer, VEC_PATH)
        return clf, vectorizer

    texts, labels = zip(*data)
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(texts)
    clf = LogisticRegression(max_iter=200)
    clf.fit(X, labels)
    joblib.dump(clf, MODEL_PATH)
    joblib.dump(vectorizer, VEC_PATH)
    return clf, vectorizer

def load_ml_classifier():
    if os.path.exists(MODEL_PATH) and os.path.exists(VEC_PATH):
        return joblib.load(MODEL_PATH), joblib.load(VEC_PATH)
    return train_ml_classifier()

def predict_subcategory(log_line, parent_category, clf, vectorizer, threshold=0.8):
    """Predict sub-category and update DB if confident."""
    if not log_line.strip():
        return None, 0.0
    X = vectorizer.transform([log_line])
    pred = clf.predict(X)[0]
    prob = clf.predict_proba(X).max()
    if prob >= threshold:
        add_or_update_subcategory(parent_category, pred, [log_line])
        return pred, prob
    return None, prob


# ==========================================================
# ===================  LOG CLASSIFIER  ======================
# ==========================================================
def read_log_file(file_path):
    try:
        with open(file_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def filter_logs_by_category(log_text: str, category: str):
    """Basic regex filter by category keywords."""
    filtered, matched = [], []
    for line in log_text.splitlines():
        lower_line = line.lower()
        if re.search(r"(error|fail|warn|exception|timeout)", lower_line):
            filtered.append(line)
            matched.append(line.strip())
    return "\n".join(filtered), matched


# ==========================================================
# ===================  ISSUE DETECTOR  ======================
# ==========================================================
def local_log_ai(log_text: str, category: str, matched_lines=None):
    """Classify lines as issue / no-issue."""
    if not log_text.strip():
        return [{"Inference": f"No issues found for {category}"}]

    issues = []
    vec_path, model_path = VEC_PATH, MODEL_PATH
    if os.path.exists(model_path):
        clf = joblib.load(model_path)
        vectorizer = joblib.load(vec_path)
    else:
        clf, vectorizer = train_ml_classifier()

    for line in log_text.splitlines():
        X = vectorizer.transform([line])
        pred = clf.predict(X)[0]
        prob = clf.predict_proba(X).max()
        if "issue" in pred.lower() or prob > 0.6:
            sev = "High" if prob > 0.8 else "Medium" if prob > 0.6 else "Low"
            issues.append({
                "Inference": f"Issue detected in {category}",
                "Severity": sev,
                "Reasons": [line.strip()],
                "Action": "Investigate the issue",
                "Why": "Detected unusual or problematic log behavior",
                "BusinessImpact": "Potential service degradation or outage"
            })

    if not issues:
        return [{"Inference": f"No issues found for {category}"}]
    return issues


# ==========================================================
# ===================  PDF REPORT  ==========================
# ==========================================================
def generate_pdf_report(report_type, content, output_path, only_high=True):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt=f"{report_type} Report", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=10)

    if isinstance(content, dict):
        for category, issues in content.items():
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(200, 8, txt=category, ln=True)
            pdf.set_font("Arial", size=10)
            if not issues or ("No issues" in issues[0].get("Inference", "")):
                pdf.multi_cell(0, 8, txt="✅ No Issues")
                pdf.ln(2)
                continue
            for issue in issues:
                sev = str(issue.get("Severity", "")).lower()
                if only_high and sev != "high":
                    continue
                pdf.multi_cell(0, 8, txt=json.dumps(issue, indent=2))
                pdf.ln(2)
    pdf.output(output_path)
    return output_path
