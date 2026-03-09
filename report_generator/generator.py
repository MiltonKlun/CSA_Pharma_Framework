"""
CSA Step 4b: Report Generator

Aggregates System Inventory, ALCOA+ Validation Results, and Exploratory Sessions
to dynamically build a comprehensive Validation Summary Report HTML file, and
then prints it to PDF using Playwright (bypassing WeasyPrint OS dependencies).
"""
import os
import sys
import yaml
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from evidence_capture.integrity import write_sha256_sidecar

console = Console()

# We use playwright for PDF rendering since it's already installed and works natively on Windows
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    console.print("[bold red]Playwright is required to generate the PDF.[/bold red]")
    console.print("Please ensure it is installed: pip install playwright && playwright install chromium")
    exit(1)

def load_system_inventory(base_dir: str) -> dict:
    inventory_path = os.path.join(base_dir, "system_inventory", "config", "qms_system.yaml")
    if os.path.exists(inventory_path):
        with open(inventory_path, "r") as f:
            return yaml.safe_load(f)
    return {"system": {"name": "Unknown", "vendor": "Unknown", "version": "Unknown", "gamp_category": "Unknown"}, "features": []}

def load_unscripted_sessions(base_dir: str) -> list:
    sessions = []
    sessions_dir = os.path.join(base_dir, "test_suites", "unscripted", "sessions")
    if os.path.exists(sessions_dir):
        for filename in os.listdir(sessions_dir):
            if filename.endswith(".yaml"):
                with open(os.path.join(sessions_dir, filename), "r") as f:
                    sessions.append(yaml.safe_load(f))
    return sessions

def parse_junit_xml(xml_path: str) -> dict:
    """
    Parse a pytest --junitxml output file into a structured dict suitable
    for Jinja2 template rendering.
    Returns a dict with: total, passed, failed, errors, skipped, duration, testcases[]
    """
    if not os.path.exists(xml_path):
        return None

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # JUnit XML may have <testsuite> as root or wrapped in <testsuites>
    suites = root.findall('testsuite') if root.tag == 'testsuites' else [root]

    total = failed = errors = skipped = 0
    duration = 0.0
    testcases = []

    for suite in suites:
        total    += int(suite.get('tests', 0))
        failed   += int(suite.get('failures', 0))
        errors   += int(suite.get('errors', 0))
        skipped  += int(suite.get('skipped', 0))
        duration += float(suite.get('time', 0.0))

        for tc in suite.findall('testcase'):
            failure = tc.find('failure')
            error   = tc.find('error')
            skip    = tc.find('skipped')

            if failure is not None:
                status = 'FAIL'
                message = failure.get('message', '')
            elif error is not None:
                status = 'ERROR'
                message = error.get('message', '')
            elif skip is not None:
                status = 'SKIP'
                message = skip.get('message', '')
            else:
                status = 'PASS'
                message = ''

            # Build a human-readable test name from classname + name
            classname = tc.get('classname', '').split('.')[-1]  # Keep only the class, not full module path
            name = tc.get('name', '')
            testcases.append({
                'classname': classname,
                'name': name,
                'status': status,
                'duration': round(float(tc.get('time', 0.0)), 3),
                'message': message,
            })

    passed = total - failed - errors - skipped
    return {
        'total': total,
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'skipped': skipped,
        'duration': round(duration, 2),
        'all_passed': failed == 0 and errors == 0,
        'testcases': testcases,
    }


def run_scripted_tests(base_dir: str, xml_path: str) -> dict:
    """
    Execute the scripted test suite via subprocess and save results as JUnit XML.
    Returns the parsed results dict.
    """
    python_exec = sys.executable
    test_dir = os.path.join(base_dir, 'test_suites', 'scripted')

    console.print("[cyan]Running scripted test suite to capture live results...[/cyan]")
    result = subprocess.run(
        [python_exec, '-m', 'pytest', test_dir, f'--junitxml={xml_path}', '-q', '--tb=no'],
        capture_output=True,
        text=True,
        cwd=base_dir
    )
    if result.returncode not in (0, 1):  # 0=all pass, 1=some fail; anything else is a crash
        console.print(f"[bold red]Pytest crashed (exit {result.returncode}):[/bold red] {result.stderr}")
        sys.exit(1)

    return parse_junit_xml(xml_path)


def parse_alcoa_summary(base_dir: str) -> dict:
    summary_path = os.path.join(base_dir, "evidence_capture", "alcoa_validation_summary.txt")

    result = {
        "status": "UNKNOWN",
        "rules": {
            "Attributable": "FAIL",
            "Legible": "FAIL",
            "Contemporaneous": "FAIL",
            "Original": "FAIL",
            "Accurate": "FAIL"
        },
        "issues": []
    }
    
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            lines = f.readlines()
            
            for line in lines:
                if line.startswith("Overall Status:"):
                    result["status"] = line.split(":")[1].strip()
                elif line.startswith("[PASS]") or line.startswith("[FAIL]"):
                    status_text = "PASS" if "[PASS]" in line else "FAIL"
                    # Format: "[PASS] Attributable - description..."
                    rule_name = line.split("]")[1].split("-")[0].strip()
                    if rule_name in result["rules"]:
                        result["rules"][rule_name] = status_text
                elif line.strip().startswith("- "):
                    # Collect issues
                    result["issues"].append(line.strip()[2:])
                    
    return result

def generate_report():
    console.print("[cyan]Initializing Report Generator...[/cyan]")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Paths
    junit_xml_path = os.path.join(base_dir, 'test_suites', 'scripted_results.xml')
    outputs_dir = os.path.join(base_dir, 'report_generator', 'outputs')
    os.makedirs(outputs_dir, exist_ok=True)

    # 1. Run scripted tests and capture live results
    scripted_results = run_scripted_tests(base_dir, junit_xml_path)

    # 2. Gather all remaining data
    system_data = load_system_inventory(base_dir)
    sessions_data = load_unscripted_sessions(base_dir)
    alcoa_data = parse_alcoa_summary(base_dir)
    
    context = {
        "system": system_data.get("system", {}),
        "features": system_data.get("features", []),
        "unscripted_sessions": sessions_data,
        "scripted_results": scripted_results,
        "alcoa_status": alcoa_data.get("status"),
        "alcoa_rules": alcoa_data.get("rules"),
        "alcoa_issues": alcoa_data.get("issues"),
        "date": datetime.now().strftime("%B %d, %Y - %H:%M:%S")
    }

    # 3. Setup Jinja2 Environment
    templates_dir = os.path.join(base_dir, "report_generator", "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("validation_summary.html")
    
    # 3. Render HTML
    html_content = template.render(**context)
    
    # Ensure outputs directory exists
    outputs_dir = os.path.join(base_dir, "report_generator", "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    html_path = os.path.join(outputs_dir, "temp_report.html")
    pdf_path = os.path.join(outputs_dir, "Validation_Summary_Report.pdf")
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    console.print(f"[green]HTML template rendered.[/green]")
    console.print(f"[cyan]Converting to PDF via Playwright...[/cyan]")
    
    # 4. Generate PDF using Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Windows requires file:/// protocol for local files
        page.goto(f"file:///{html_path.replace(chr(92), '/')}")
        # Wait for any network idle just in case
        page.wait_for_load_state("networkidle")
        page.pdf(path=pdf_path, format="A4", print_background=True, margin={"top": "2cm", "bottom": "2cm", "left": "1.5cm", "right": "1.5cm"})
        browser.close()
        
    # Clean up the temp HTML
    if os.path.exists(html_path):
        os.remove(html_path)

    # SHA-256 hash the final PDF for evidence integrity (PIC/S PI 041 §6.9)
    digest = write_sha256_sidecar(pdf_path)
        
    console.print("\n[bold green]Report Generation Complete![/bold green]")
    console.print(f"Artifact Saved: {pdf_path}")
    console.print(f"Integrity Record: [dim]{pdf_path}.sha256[/dim]")
    console.print(f"SHA-256: [dim]{digest[:16]}...{digest[-8:]}[/dim]")

if __name__ == "__main__":
    generate_report()
