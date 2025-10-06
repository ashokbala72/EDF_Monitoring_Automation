import os
import streamlit as st
from helpers import (
    read_log_file,
    filter_logs_by_category,
    local_log_ai,
    init_learning_db,
    train_ml_classifier,
    load_ml_classifier,
    predict_subcategory
)

# ----------------------------------------------------------
#  INITIAL SETUP
# ----------------------------------------------------------
CATEGORY_TO_FILE = {
    "MS": "msdata_log.txt",
    "GIS": "gisdata_log.txt",
    "GM": "gmdata_log.txt",
    "Oracle": "oracle_log.txt",
    "Infra": "infra_log.txt",
    "CSP": "csp_log.txt",
    "iSmart": "ismart_large_log.log",
    "SolarWinds": "solarwinds_sql_large.txt",
    "WebOps": "webops_log.txt",
}

st.set_page_config(layout="wide")
st.title("🤖 Self-Learning ITSM & Non-ITSM Monitoring Assistant")

# DB + Model initialization
init_learning_db()
clf, vectorizer = load_ml_classifier()

if "results_cache" not in st.session_state:
    st.session_state["results_cache"] = {}

# ----------------------------------------------------------
#  DISPLAY FUNCTION
# ----------------------------------------------------------
def display_result(results):
    for issue in results:
        st.write(f"**{issue.get('Inference','')}**")
        if "Severity" in issue:
            st.write(f"Severity: {issue['Severity']}")
        if isinstance(issue.get("Reasons"), list) and issue["Reasons"]:
            st.write("**Issues Identified:**")
            for r in issue["Reasons"]:
                st.markdown(f"- {r}")
        if "Action" in issue:
            st.write(f"Action: {issue['Action']}")
        if "Why" in issue:
            st.write(f"Why: {issue['Why']}")
        if "BusinessImpact" in issue:
            st.write(f"Business Impact: {issue['BusinessImpact']}")
        st.markdown("---")

# ----------------------------------------------------------
#  PROCESS EACH CATEGORY
# ----------------------------------------------------------
def process_category(system_key, category):
    cache_key = f"{system_key}_{category}"
    if cache_key in st.session_state["results_cache"]:
        results = st.session_state["results_cache"][cache_key]
        display_result(results)
        return

    file_name = CATEGORY_TO_FILE.get(system_key)
    if not file_name:
        st.warning(f"⚠️ No log file for {system_key}")
        return
    file_path = os.path.join("logs", file_name)
    if not os.path.exists(file_path):
        st.warning(f"⚠️ Log file `{file_name}` not found in logs/")
        return

    log_text = read_log_file(file_path)
    filtered_text, matched_lines = filter_logs_by_category(log_text, category)

    # ML Prediction Section
    ml_preds = []
    for line in matched_lines:
        pred_subcat, prob = predict_subcategory(line, system_key, clf, vectorizer)
        if pred_subcat:
            ml_preds.append(f"{pred_subcat} ({prob:.2f})")

    if ml_preds:
        st.info(f"🧠 ML Predicted Subcategories: {', '.join(ml_preds)}")

    # Regular AI analysis
    results = local_log_ai("\n".join(matched_lines), category, matched_lines)
    st.session_state["results_cache"][cache_key] = results
    display_result(results)

# ----------------------------------------------------------
#  SUB-CATEGORY DEFINITIONS
# ----------------------------------------------------------
SYSTEM_CATEGORIES = {
    "MS": ["Application & Server Health Check", "Database Growth Trend", "Backup Monitoring"],
    "GIS": ["Server Certificate renewal", "ArcGIS Service Health"],
    "GM": ["Application & Server Health Checks", "Replication Monitoring"],
    "Oracle": ["ESB - real time transaction monitoring", "Tablespace Usage"],
    "Infra": ["Server Health Checks", "Disk Space Monitoring", "Network Latency Monitoring"],
    "CSP": ["Cloud Service Provider API Monitoring", "Cloud Security Events"],
    "iSmart": ["Site Cache Availability", "SQL Query Execution"],
    "SolarWinds": ["Query Performance", "High CPU Alerts"],
    "WebOps": ["Monitoring Reports", "Deployment Errors"],
}

# ----------------------------------------------------------
#  STREAMLIT UI TABS
# ----------------------------------------------------------
tabs = st.tabs(list(SYSTEM_CATEGORIES.keys()))

for idx, system in enumerate(SYSTEM_CATEGORIES.keys()):
    with tabs[idx]:
        st.header(f"{system} Logs")
        for category in SYSTEM_CATEGORIES[system]:
            with st.expander(category):
                process_category(system, category)
