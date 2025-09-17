import os
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from helpers import (
    send_to_azure_openai,
    read_log_file,
    generate_pdf_report
)

load_dotenv()

st.set_page_config(layout="wide")
st.title("ITSM & Non-ITSM Monitoring Assistant")

# -----------------------------
# State
# -----------------------------
if "results_cache" not in st.session_state:
    st.session_state["results_cache"] = {
        "msdata_log.txt": [],
        "gisdata_log.txt": [],
        "gmdata_log.txt": [],
        "webops_log.txt": [],
        "oracle_log.txt": [],
        "infra_log.txt": [],
        "csp_log.txt": [],
    }

# -----------------------------
# Utilities
# -----------------------------
def normalize_for_table(data):
    normalized = []
    for issue in data:
        if isinstance(issue, dict) and "issues" in issue and isinstance(issue["issues"], list):
            for sub in issue["issues"]:
                flat = {k: "\n".join(v) if isinstance(v, list) else v for k, v in sub.items()}
                normalized.append(flat)
        else:
            flat = {k: "\n".join(v) if isinstance(v, list) else v for k, v in issue.items()}
            normalized.append(flat)
    return normalized

def display_result(result):
    try:
        if isinstance(result, list) and all(isinstance(i, dict) for i in result):
            df = pd.DataFrame(normalize_for_table(result))
            st.dataframe(df, use_container_width=True)
        elif isinstance(result, dict):
            df = pd.DataFrame(normalize_for_table([result]))
            st.dataframe(df, use_container_width=True)
        elif isinstance(result, str):
            parsed = json.loads(result)
            if isinstance(parsed, list):
                df = pd.DataFrame(normalize_for_table(parsed))
                st.dataframe(df, use_container_width=True)
            elif isinstance(parsed, dict):
                df = pd.DataFrame(normalize_for_table([parsed]))
                st.dataframe(df, use_container_width=True)
            else:
                st.write(parsed)
        else:
            st.write(result)
    except Exception as e:
        st.error(f"Could not render result: {e}")
        st.text(result)

def process_category(file_name, category):
    """Load full log file and analyze for a specific category."""
    log_text = read_log_file(os.path.join("logs", file_name))

    if log_text.strip():
        result = send_to_azure_openai(log_text, category)

        # ensure list form
        result_list = result if isinstance(result, list) else [result]

        # 🛠 Always clean "No issues..." if there are real issues
        real_issues = [r for r in result_list if isinstance(r, dict) and r.get("Inference") != "No issues in this category"]

        if real_issues:
            cleaned_results = real_issues
        else:
            cleaned_results = result_list  # could be just "No issues..."

        # cache results (overwrite instead of extend to avoid duplicates)
        st.session_state["results_cache"][file_name] = cleaned_results

    cached_results = st.session_state["results_cache"][file_name]

    def is_no_issue(entry):
        return (
            isinstance(entry, dict) and (
                not entry or entry.get("Inference") == "No issues in this category"
            )
        ) or entry == []

    if cached_results:
        if all(is_no_issue(i) for i in cached_results):
            st.info("✅ No Issues found")
        else:
            display_result(cached_results)
    else:
        st.info("✅ No Issues found")


# -----------------------------
# Tabs
# -----------------------------
tabs = [
    "MS+Data", "GIS Data", "GM Data",
    "WebOps Data", "Oracle Data",
    "Infra Data", "CSP Data", "Reports"
]
selected_tab = st.sidebar.radio("Select Tab", tabs)

# Global refresh button (clears cache so re-analysis happens)
if st.sidebar.button("🔄 Refresh Now"):
    for k in st.session_state["results_cache"]:
        st.session_state["results_cache"][k] = []

# -----------------------------
# MS+Data
# -----------------------------
if selected_tab == "MS+Data":
    checks = [
        "Morning Checks", "Application & Server Health Check",
        "Application log Monitoring", "Interface connectivity checking",
        "Periodic backup monitoring", "Night Checks",
        "File / Flow related alert handling", "User Audit report",
        "LLF Data Report", "MDD Data Load", "DTC Data Load",
        "CSS-Queue monitoring", "CSS - Incident Management",
        "Monthly Scheduled Jobs / Task Handling"
    ]
    for c in checks:
        with st.expander(c):
            with st.spinner("Analyzing logs..."):
                process_category("msdata_log.txt", c)
    if st.button("Create Service Now Incident"):
        st.success("ServiceNow Incident Created (Simulated)")

# -----------------------------
# GIS Data
# -----------------------------
if selected_tab == "GIS Data":
    checks = [
        "Application and Database Server Health Checks",
        "Interface Connectivity Checking",
        "Periodic Backup Monitoring",
        "Server Certificate renewal",
        "Legacy Mapinfo and Webmap health check",
        "Job failure handling",
        "L3 and L2 analysis",
        "Weekly scheduled jobs monitoring"
    ]
    for c in checks:
        with st.expander(c):
            with st.spinner("Analyzing logs..."):
                process_category("gisdata_log.txt", c)

# -----------------------------
# GM Data
# -----------------------------
if selected_tab == "GM Data":
    checks = [
        "Morning Server Checks",
        "Application & Server Health Checks for any issues",
        "Interface connectivity Checks",
        "Periodic Backup Monitoring",
        "PI application system (PI DA, PI AF, PI int) monitoring",
        "Monthly scheduled jobs / task handling",
        "Application log monitoring",
        "Daily Scheduled jobs / task monitoring",
        "Night Server Checks",
        "PI interface connectivity checking",
        "Data flow checks, data sync and investigations",
        "Event Monitoring",
        "Version and configuration tracking and assess vulnerabilities",
        "Report Preparation",
        "License Monitoring Activities",
        "Capacity Monitoring and Management"
    ]
    for c in checks:
        with st.expander(c):
            with st.spinner("Analyzing logs..."):
                process_category("gmdata_log.txt", c)

# -----------------------------
# WebOps Data
# -----------------------------
if selected_tab == "WebOps Data":
    checks = [
        "Monitoring Reports",
        "Email Queries / Tasks",
        "Meetings",
        "Infrastructure Support (AWS)",
        "Data Management",
        "Application Support (SDLC Status)",
        "Google Analytics Management",
        "Analysis for Cloudflare maintenance",
        "Documentation: SOP documentation and control"
    ]
    for c in checks:
        with st.expander(c):
            with st.spinner("Analyzing logs..."):
                process_category("webops_log.txt", c)

# -----------------------------
# Oracle Data
# -----------------------------
if selected_tab == "Oracle Data":
    checks = [
        "Morning / Night Checks",
        "ESB - real time transaction monitoring",
        "ESB - Queue Monitoring",
        "ESB - Server Health Monitoring",
        "ESB - Log Monitoring",
        "ESB - File System storage checks",
        "Hubble - Daily Hubble Check",
        "Apps DBA monitoring",
        "Apps DBA - CFM and HCM Database user details report",
        "OPA Maintenance Monitoring"
    ]
    for c in checks:
        with st.expander(c):
            with st.spinner("Analyzing logs..."):
                process_category("oracle_log.txt", c)

# -----------------------------
# Infra Data
# -----------------------------
if selected_tab == "Infra Data":
    checks = [
        "Server Health Checks",
        "Disk Space Monitoring",
        "Cluster Monitoring",
        "Network Latency Monitoring",
        "Security Patch Compliance",
        "Data Center Cooling / Power Monitoring"
    ]
    for c in checks:
        with st.expander(c):
            with st.spinner("Analyzing logs..."):
                process_category("infra_log.txt", c)

# -----------------------------
# CSP Data
# -----------------------------
if selected_tab == "CSP Data":
    checks = [
        "Cloud Service Provider API Monitoring",
        "Latency and Performance Monitoring",
        "Cloud Resource Scaling",
        "Cloud Security Events",
        "Billing and Cost Anomaly Detection",
        "Disaster Recovery Simulation"
    ]
    for c in checks:
        with st.expander(c):
            with st.spinner("Analyzing logs..."):
                process_category("csp_log.txt", c)

# -----------------------------
# Reports
# -----------------------------
elif selected_tab == "Reports":
    st.subheader("Generate Reports (High Severity Only)")
    categories = {
        "MS+Data Report": "msdata_log.txt",
        "GIS Data Report": "gisdata_log.txt",
        "GM Data Report": "gmdata_log.txt",
        "WebOps Data Report": "webops_log.txt",
        "Oracle Data Report": "oracle_log.txt",
        "Infra Data Report": "infra_log.txt",
        "CSP Data Report": "csp_log.txt",
    }
    for label, file in categories.items():
        if st.button(f"Generate {label}"):
            all_results = st.session_state["results_cache"].get(file, [])
            if not all_results:
                st.warning(f"No results cached for {label}")
            else:
                filename = f"{label.replace(' ', '_').lower()}.pdf"
                path = os.path.join("reports", filename)
                generate_pdf_report(label, all_results, path, only_high=True)
                st.success(f"Generated {label} at {path}")

    # -----------------------------
    # Executive Summary Report (Plain Text)
    # -----------------------------
    if st.button("Generate Executive Summary"):
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt="Executive Summary - System Health Overview", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Arial", size=12)
        for label, file in categories.items():
            all_results = st.session_state["results_cache"].get(file, [])

            # Default health = HEALTHY
            health = "HEALTHY"
            if not all_results or (
                len(all_results) == 1 and all_results[0].get("Inference") == "No issues in this category"
            ):
                health = "HEALTHY"
            else:
                severities = [str(i.get("Severity", "")).lower() for i in all_results if "Severity" in i]
                if "high" in severities:
                    health = "CRITICAL"
                elif "medium" in severities:
                    health = "WARNING"
                elif "low" in severities:
                    health = "MINOR"

            # Write to PDF
            pdf.set_font("Arial", "B", 12)
            pdf.cell(200, 8, txt=label, ln=True)
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 8, txt=f"Health Status: {health}")
            pdf.ln(4)

        os.makedirs("reports", exist_ok=True)
        summary_path = os.path.join("reports", "executive_summary.pdf")
        pdf.output(summary_path)
        st.success(f"Generated Executive Summary at {summary_path}")


