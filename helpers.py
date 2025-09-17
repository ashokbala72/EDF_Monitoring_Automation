import os
import json
from fpdf import FPDF
from openai import AzureOpenAI
from dotenv import load_dotenv

try:
    import json5
    HAS_JSON5 = True
except ImportError:
    HAS_JSON5 = False

load_dotenv()

# -----------------------------
# Azure OpenAI client
# -----------------------------
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview",  # fixed to your version
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)
DEPLOYMENT_NAME = "gpt-4o-raj"  # fixed to your deployment

# -----------------------------
# Category → Log file mapping
# -----------------------------
CATEGORY_LOG_FILES = {
    "CSP Monitoring": "csp_log.txt",
    "GIS Data Monitoring": "gisdata_log.txt",
    "GM Data Monitoring": "gmdata_log.txt",
    "Infrastructure Health": "infra_log.txt",
    "MS Data Monitoring": "msdata_log.txt",
    "Oracle Monitoring": "oracle_log.txt",
    "WebOps Monitoring": "webops_log.txt",
}

# -----------------------------
# Read full log file
# -----------------------------
def read_log_file(file_path):
    """Read full log file contents."""
    try:
        with open(file_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

# -----------------------------
# Azure OpenAI call
# -----------------------------
def send_to_azure_openai(log_text: str, category: str):
    """
    GPT must return only issues specific to the category.
    If none exist, return { "issues": [ { "Inference": "No issues in this category" } ] }.
    """

    prompt = f"""
    You are an ITSM monitoring assistant.

    Task: Analyze the logs ONLY for the category: "{category}".

    Rules:
    - Search carefully for issues that match this category.
    - If you find relevant issues, return ONLY those issues.
    - If there are truly no relevant issues, return:
      {{ "issues": [ {{ "Inference": "No issues in this category" }} ] }}
    - Never output "No issues in this category" together with real issues.
    - Always output JSON with a top-level key "issues".
    - Each real issue must include:
      Inference, Severity (High/Medium/Low), Reasons (2–3 bullet points),
      Action, Why, BusinessImpact.
    - If no issues, return a single object with only:
      "Inference": "No issues in this category"

    Logs:
    {log_text}
    """

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a strict IT monitoring assistant. Only return issues relevant to the category. If none, output { 'issues': [ { 'Inference': 'No issues in this category' } ] }."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=800,
        )

        content = response.choices[0].message.content.strip()
        data = json.loads(content)

        issues = data.get("issues", [])

        # Safety net: if GPT mixes, drop "No issues"
        if any(i.get("Inference") == "No issues in this category" for i in issues) and len(issues) > 1:
            issues = [i for i in issues if i.get("Inference") != "No issues in this category"]

        # If GPT returns empty, force a fallback
        if not issues:
            return [{"Inference": "No issues in this category"}]

        return issues

    except Exception as e:
        return [{
            "Inference": "Error processing logs",
            "Severity": "High",
            "Reasons": [str(e)],
            "Action": "Check Azure OpenAI setup",
            "Why": "AI call failed",
            "BusinessImpact": "No monitoring results available",
        }]


# -----------------------------
# Analyze all categories
# -----------------------------
def analyze_all_logs(base_dir="./"):
    """Analyze all logs across categories and return dict {category: issues}."""
    results = {}
    for category, filename in CATEGORY_LOG_FILES.items():
        file_path = os.path.join(base_dir, filename)
        log_text = read_log_file(file_path)
        if not log_text.strip():
            results[category] = [{"Inference": "No issues in this category"}]
        else:
            results[category] = send_to_azure_openai(log_text, category=category)
    return results

# -----------------------------
# PDF Report
# -----------------------------
def generate_pdf_report(report_type, content, output_path, only_high=True):
    """Generate a PDF report. If only_high=True, include only High severity issues."""
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
            if not issues or (
                len(issues) == 1 and issues[0].get("Inference") == "No issues in this category"
            ):
                pdf.multi_cell(0, 8, txt="✅ No Issues in this category")
                pdf.ln(2)
                continue
            for issue in issues:
                severity = str(issue.get("Severity", "")).lower()
                if only_high and severity != "high":
                    continue
                pdf.multi_cell(0, 8, txt=json.dumps(issue, indent=2))
                pdf.ln(2)

    elif isinstance(content, list):
        for issue in content:
            severity = str(issue.get("Severity", "")).lower()
            if only_high and severity != "high":
                continue
            pdf.multi_cell(0, 8, txt=json.dumps(issue, indent=2))
            pdf.ln(2)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    return output_path
