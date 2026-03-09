# CSA Methodology — How This Framework Implements the FDA's Four-Step Process

> This document explains how each module in the `pharma-csa-framework` maps to the FDA's Computer Software Assurance (CSA) guidance (September 2025).

---

## Overview

The FDA's final CSA guidance establishes a four-step, risk-based framework for assuring that computer software used in production or quality management systems performs as intended. This framework automates all four steps through purpose-built Python modules.

```
Input                    Framework                        Output
─────                    ─────────                        ──────

System features    ──►  Step 1: system_inventory/    ──►  Feature catalog
                           │                              (intended use classification)
                           ▼
Risk criteria      ──►  Step 2: risk_engine/         ──►  Risk assessment matrix
                           │                              (HIGH / NOT HIGH per feature)
                           ▼
Demo app (SUT)     ──►  Step 3: test_suites/         ──►  Test results
                           │   ├── scripted/              (Playwright reports)
                           │   └── unscripted/            (exploratory session logs)
                           ▼
Test data + logs   ──►  Step 4: evidence_capture/    ──►  Validation Summary Report
                              + report_generator/         (HTML / PDF, audit-ready)
```

---

## Step 1: Identify Intended Use → `system_inventory/`

### What the FDA Requires

> _"For each software feature, function, or operation used as part of production or the quality system, identify its intended use."_

### How We Implement It

**Module:** `system_inventory/`

| Component | Purpose |
|---|---|
| `config/qms_system.yaml` | YAML configuration file listing every feature of the system under validation, including its name, description, and intended use classification |
| `inventory.py` | Parses the YAML config, creates structured Feature objects |
| `classifier.py` | Classifies each feature as **direct** use (production/quality impact) or **supporting** use (administrative/informational) |

**Configuration Schema:**

```yaml
system:
  name: "PharmaQMS Demo"
  gamp_category: 4
  vendor: "Milton Klun (demo)"
  version: "1.0.0"

features:
  - id: "AUTH-001"
    name: "User Authentication"
    intended_use: "direct"      # direct | supporting
    quality_impact: true
    patient_safety_impact: true
    data_integrity_impact: true
```

**Output:** A structured feature catalog documenting every feature's intended use — directly satisfying the FDA's Step 1 record requirement.

---

## Step 2: Determine Risk-Based Approach → `risk_engine/`

### What the FDA Requires

> _"Determine whether each software feature, function, or operation is associated with HIGH process risk or NOT HIGH process risk."_

The key question: **"If this feature fails, could it foreseeably lead to compromised patient safety?"**

### How We Implement It

**Module:** `risk_engine/`

| Component | Purpose |
|---|---|
| `risk_assessor.py` | Performs FMEA calculation: **Severity × Occurrence × Detection = RPN** (per ICH Q9 methodology) |
| `risk_matrix.py` | Maps RPN scores to FDA's binary classification: **HIGH** or **NOT HIGH** process risk |
| `gamp_categorizer.py` | Assigns GAMP 5 software categories (1/3/4/5) to inform testing depth |
| `config/risk_criteria.yaml` | Configurable severity, occurrence, and detection scales |
| `config/gamp_categories.yaml` | GAMP category definitions and thresholds |

**Risk Classification Logic:**

```
RPN = Severity × Occurrence × Detection

HIGH Process Risk:
  - RPN ≥ threshold (configurable, default: 40)
  - OR patient_safety_impact == true AND severity ≥ 7
  - OR data_integrity_impact == true AND severity ≥ 8

NOT HIGH Process Risk:
  - All other features
```

**Output:** A risk assessment matrix documenting the classification of every feature — directly satisfying the FDA's Step 2 record requirement.

---

## Step 3: Select Assurance Activities → `test_suites/`

### What the FDA Requires

**For HIGH process risk:** Scripted testing — step-by-step test procedures with expected results, independent review, and detailed documentation.

**For NOT HIGH process risk:** Unscripted testing — exploratory, scenario-based, or error-guessing testing with documented objectives and pass/fail criteria.

### How We Implement It

#### Step 3a: Scripted Testing → `test_suites/scripted/`

For features classified as **HIGH process risk**, we use automated Playwright tests with pytest:

| Component | Purpose |
|---|---|
| `conftest.py` | Playwright fixtures, test data setup, browser configuration |
| `pages/` | Page Object Model classes for each demo app page |
| `test_audit_trail.py` | Validates audit trail compliance (21 CFR Part 11 §11.10(e)) |
| `test_electronic_signatures.py` | Validates e-signature requirements (§11.50, §11.70) |
| `test_access_control.py` | Validates role-based access (§11.10(d)) |
| `test_data_integrity.py` | Validates ALCOA+ data integrity (PIC/S PI 041) |
| `test_deviation_workflow.py` | Validates deviation management workflow |
| `test_capa_workflow.py` | Validates CAPA lifecycle |

**Test Naming Convention:**
```
test_<feature>_<scenario>_<expected_behavior>
Example: test_audit_trail_record_creation_generates_log_entry
```

#### Step 3b: Unscripted Testing → `test_suites/unscripted/`

For features classified as **NOT HIGH process risk**, we use a structured exploratory testing approach:

| Component | Purpose |
|---|---|
| `exploratory_logger.py` | Interactive CLI tool that guides testers through exploratory sessions |
| `session_template.yaml` | Charter template defining session structure |
| `sessions/` | Stored session logs (YAML format) |

**Session Output includes:** Charter, observations, findings, duration, conclusion (pass/fail), tester identity.

---

## Step 4: Establish Record → `evidence_capture/` + `report_generator/`

### What the FDA Requires

Every assurance activity must produce a record containing:
1. Intended use statement
2. Risk-based analysis result and rationale
3. Testing description
4. Test results (pass/fail)
5. Issues found and disposition
6. Conclusion of acceptability
7. Tester identity and date

### How We Implement It

#### Step 4a: Evidence Capture → `evidence_capture/`

| Component | Purpose |
|---|---|
| `audit_trail_collector.py` | Extracts audit trail entries from the demo app database for each test run |
| `system_log_collector.py` | Collects application logs from Docker containers |
| `screenshot_capture.py` | Captures screenshots on test failure (not for every step — per CSA digital evidence recommendation) |
| `validators/alcoa_validator.py` | Validates all collected evidence against ALCOA+ principles |

**ALCOA+ Validation Checks:**

| Principle | Automated Check |
|---|---|
| Attributable | Every audit entry has user_id + timestamp |
| Legible | Data renders correctly, no encoding issues |
| Contemporaneous | Timestamps within acceptable range of execution time |
| Original | Source records unmodified |
| Accurate | Data matches expected values |
| Complete | No gaps in audit trail sequence |
| Consistent | Cross-referenced data between tables |
| Enduring | Records persist after system restart |
| Available | Records queryable and retrievable |

#### Step 4b: Report Generation → `report_generator/`

| Component | Purpose |
|---|---|
| `generator.py` | Aggregates data from all modules into a structured report |
| `templates/validation_summary.html` | Jinja2 template for the Validation Summary Report |
| `outputs/` | Generated HTML/PDF reports |

**Report Structure (Validation Summary Report):**

1. Document Information (system, version, date, author)
2. Executive Summary (overall pass/fail, key metrics)
3. System Description (from `system_inventory/`)
4. Risk Assessment Summary (from `risk_engine/`)
5. Assurance Activities Performed
   - 5a. Scripted Testing Results (per test case)
   - 5b. Unscripted Testing Results (per session)
6. Evidence Summary (ALCOA+ validation results)
7. Issues & Deviations Found
8. Conclusion Statement
9. Appendices

---

## Continuous Validation → `.github/workflows/`

### Concept

The CSA guidance emphasizes maintaining a **validated state** — not just achieving it once. The CI/CD pipeline runs the entire four-step framework on every code change:

```yaml
# Pipeline Flow:
# 1. Spin up demo app (docker-compose)
# 2. Run system inventory → risk assessment
# 3. Execute scripted tests (HIGH risk features)
# 4. Collect evidence (audit trails, logs)
# 5. Validate evidence (ALCOA+)
# 6. Generate Validation Summary Report
# 7. Upload report as pipeline artifact
```

This demonstrates the pharma concept of **continuous validation** — every commit maintains the system's validated state.

---

## Regulatory Traceability

Every element in this framework traces back to a specific regulatory requirement:

| Framework Element | FDA CSA Reference | Additional Standards |
|---|---|---|
| Feature catalog | Step 1: Intended Use | GAMP 5 system description |
| Risk matrix | Step 2: Risk classification | ICH Q9 FMEA, GAMP 5 categories |
| Scripted tests | Step 3: HIGH risk assurance | 21 CFR Part 11, EU GMP Annex 11 |
| Exploratory logger | Step 3: NOT HIGH risk assurance | CSA unscripted testing guidance |
| Audit trail collection | Step 4: Digital evidence | 21 CFR Part 11 §11.10(e) |
| ALCOA+ validator | Step 4: Data integrity | PIC/S PI 041 |
| Validation report | Step 4: Establish Record | FDA record requirements |
| CI/CD pipeline | Continuous validation | GAMP 5 lifecycle maintenance |
