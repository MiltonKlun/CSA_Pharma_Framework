# Pharma CSA Framework Manual

This project automates the FDA's Computer Software Assurance (CSA) process for pharmaceutical software validation. Instead of writing hundreds of pages of manual testing documentation (CSV), it uses code to calculate risk, run automated tests, extract digital evidence, and generate a final PDF Validation Report.

## How to Run the Validation Process Manually

To run the full validation lifecycle step-by-step from your terminal, execute the following commands in order:

### 1. Initial Setup
Set up the virtual environment and install the required Python packages and Playwright browsers.
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
playwright install chromium
```

### 2. Seed the Database
Populates the system with dummy users and data, simulating a functioning Quality Management System (QMS).
```bash
./venv/Scripts/python -m demo_app.app.seed
```

### 3. Run the Risk Engine (CSA Steps 1 & 2)
Parses the system configuration (`qms_system.yaml`) to calculate the FMEA risk scores and automatically categorizes features as HIGH or NOT HIGH risk.
```bash
./venv/Scripts/python -m risk_engine.risk_matrix
```

### 4. Execute Automated Assurance (CSA Step 3)
Runs strict, automated Pytest integration tests against the **HIGH RISK** features (like Electronic Signatures and Audit Trails).
```bash
./venv/Scripts/pytest test_suites/scripted/ -v
```

### 5. Capture Digital Evidence (CSA Step 4a)
Extracts the immutable audit trail logs directly from the SQLite database into a JSON evidence file to prove who did what without needing screenshots.
```bash
./venv/Scripts/python -m evidence_capture.audit_trail_collector
```

### 6. Mathematically Assert Data Integrity (ALCOA+)
Validates the extracted JSON evidence against the 5 FDA Data Integrity principles (Attributable, Legible, Contemporaneous, Original, Accurate), outputting a summary report.
```bash
./venv/Scripts/python -m evidence_capture.validators.alcoa_validator
```

### 7. Generate the Final Report (CSA Step 4b)
Collects the Risk Matrix, the Pytest Results, and the ALCOA+ Audit Trail checks into an HTML template and prints it to a professionally formatted `Validation_Summary_Report.pdf`.
```bash
./venv/Scripts/python -m report_generator.generator
```

**Once finished, open `report_generator/outputs/Validation_Summary_Report.pdf` to see the final output!**

---

### Extra: Unscripted Exploratory Testing
For features that are **NOT HIGH risk** (like the CAPA module), CSA states you don't need heavy scripted automation. Instead, you can run an interactive Exploratory logger session.

To launch a session and log issues dynamically, use this command:
```bash
./venv/Scripts/python -m test_suites.unscripted.exploratory_logger --template test_suites/unscripted/session_template.yaml
```
It will guide you through logging `[A]`ctions, `[O]`bservations, and `[D]`efects. Once you press `[Q]` to quit, it will instantly generate an immutable evidence YAML file inside `test_suites/unscripted/sessions/`.
