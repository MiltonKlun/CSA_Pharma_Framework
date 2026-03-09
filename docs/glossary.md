# Pharma-to-Code Glossary

> Mapping pharmaceutical quality concepts to their software QA equivalents in this framework.

---

## Core CSA Concepts

| Pharma Quality Concept | Definition | Software QA Equivalent | Framework Module |
|---|---|---|---|
| **Computer Software Assurance (CSA)** | FDA's risk-based approach for assuring software used in production/quality systems performs as intended (Sept 2025 guidance) | Risk-based test strategy with proportionate testing depth | Entire framework |
| **Computer System Validation (CSV)** | Legacy approach requiring extensive documentation (IQ/OQ/PQ) for every system regardless of risk | Full scripted test coverage with detailed protocols | *Replaced by CSA* |
| **Intended Use** | What a software feature/function is used for in the context of production or quality | Requirements specification / feature definition | `system_inventory/` |
| **Process Risk (HIGH)** | Feature failure could foreseeably lead to compromised patient safety | Critical test priority — full scripted automation | `risk_engine/` → `test_suites/scripted/` |
| **Process Risk (NOT HIGH)** | Feature failure would NOT foreseeably lead to compromised patient safety | Lower test priority — exploratory testing acceptable | `risk_engine/` → `test_suites/unscripted/` |

---

## Risk Management

| Pharma Concept | Definition | Software Equivalent | Module |
|---|---|---|---|
| **FMEA** (Failure Mode Effects Analysis) | Systematic method to identify potential failure modes, their effects, and causes | Risk scoring matrix (Severity × Occurrence × Detection = RPN) | `risk_engine/risk_assessor.py` |
| **Risk Priority Number (RPN)** | Quantified risk score from FMEA | Test priority score | `risk_engine/risk_matrix.py` |
| **GAMP Category 1** | Infrastructure software (OS, databases) | Platform/environment setup | `risk_engine/gamp_categorizer.py` |
| **GAMP Category 3** | Non-configurable COTS software | Third-party tools used as-is | `risk_engine/gamp_categorizer.py` |
| **GAMP Category 4** | Configurable software | Configured platforms (ERP, LIMS) | `risk_engine/gamp_categorizer.py` |
| **GAMP Category 5** | Custom-built software | Bespoke application code | `risk_engine/gamp_categorizer.py` |
| **ICH Q9 QRM** | Quality Risk Management framework | Risk-based testing decisions | `risk_engine/` |

---

## Testing & Validation

| Pharma Concept | Definition | Software Equivalent | Module |
|---|---|---|---|
| **Scripted Testing** | Pre-defined test procedures with step-by-step instructions and expected results | Automated test scripts with assertions (Playwright + pytest) | `test_suites/scripted/` |
| **Unscripted Testing** | Exploratory, scenario-based, or error-guessing testing with documented objectives | Exploratory test sessions with structured logging | `test_suites/unscripted/` |
| **IQ** (Installation Qualification) | Verify system is installed correctly per specifications | Environment setup verification / smoke tests | `test_suites/scripted/` |
| **OQ** (Operational Qualification) | Verify system operates as intended within defined ranges | Functional test automation | `test_suites/scripted/` |
| **PQ** (Performance Qualification) | Verify system performs consistently under real-world conditions | Performance/load testing | `test_suites/scripted/` |
| **Validation Protocol (VP)** | Formal plan for how validation will be conducted | Test plan / test strategy document | `docs/templates/validation_plan.md` |
| **Validation Summary Report (VSR)** | Final report documenting all validation activities and conclusions | Auto-generated test execution report | `report_generator/` |
| **Vendor Assessment** | Evaluating a software vendor's development and quality practices | Supplier qualification / third-party audit | Documentation task |

---

## Data Integrity (ALCOA+)

| Attribute | Definition | Software Implementation | Module |
|---|---|---|---|
| **Attributable** | Every action traced to who performed it and when | User identity + timestamp on all operations | `evidence_capture/` |
| **Legible** | Data is readable, unambiguous, and understandable | Structured, human-readable output formats | `report_generator/` |
| **Contemporaneous** | Data recorded at the time events occur | Real-time capture during test execution | `evidence_capture/` |
| **Original** | First-capture data preserved in original format | Source data retention, no lossy transformations | `evidence_capture/` |
| **Accurate** | Truthful representation of facts | Automated capture, validated against expected results | `evidence_capture/validators/` |
| **Complete** | All critical information present, nothing missing | Full metadata, no partial records | `evidence_capture/validators/` |
| **Consistent** | Standardized formats and logical data flow | Uniform date/ID/measurement formats | `evidence_capture/validators/` |
| **Enduring** | Data persists for entire retention period | Secure storage, immutable records | `evidence_capture/` |
| **Available** | Data accessible for review/audit at any time | Queryable, retrievable evidence archive | `evidence_capture/` |

---

## Compliance & Records

| Pharma Concept | Definition | Software Equivalent | Module |
|---|---|---|---|
| **Audit Trail** | Chronological record of all data changes (who, what, when, why) | Database change tracking middleware | `demo_app/app/audit_trail.py` |
| **Electronic Signature** | Authenticated action with legal equivalence to handwritten signature | Password-verified approval with user identity + timestamp + meaning | `demo_app/app/routes/auth.py` |
| **21 CFR Part 11** | FDA regulation for electronic records and electronic signatures | System controls: access, audit trails, e-signatures, validation | `demo_app/` |
| **Deviation** | Departure from an approved procedure or expected result | Test failure or unexpected system behavior | `demo_app/app/routes/deviations.py` |
| **CAPA** | Corrective and Preventive Action — systematic approach to fix root causes | Defect → root cause analysis → fix → regression test | `demo_app/app/routes/capa.py` |
| **Change Control** | Formal process for evaluating, approving, and documenting changes | Git version control + PR review workflow | Repository workflow |
| **Continuous Validation** | Maintaining validated state through ongoing monitoring | CI/CD pipeline running tests on every commit | `.github/workflows/` |

---

## Regulatory Bodies & Standards

| Abbreviation | Full Name | Relevance |
|---|---|---|
| **FDA** | U.S. Food and Drug Administration | Primary regulatory body; issued the CSA guidance |
| **EMA** | European Medicines Agency | EU regulatory body; EU GMP Annex 11 |
| **PIC/S** | Pharmaceutical Inspection Co-operation Scheme | Data integrity guidance (PI 041) |
| **ISPE** | International Society for Pharmaceutical Engineering | GAMP 5 publication |
| **ICH** | International Council for Harmonisation | Q9 Quality Risk Management guideline |
| **GMP** | Good Manufacturing Practice | Quality standards for pharmaceutical manufacturing |
| **GxP** | Good "x" Practice | Umbrella term for all regulatory good practices |
| **QMS** | Quality Management System | Organizational system for ensuring quality |
| **QMSR** | Quality Management System Regulation | Updated 21 CFR 820 (Feb 2026, harmonized with ISO 13485) |
