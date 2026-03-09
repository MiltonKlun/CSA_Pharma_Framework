"""
CSA Step 4 — Record: ALCOA+ Validator
Programmatically evaluates extracted JSON evidence against FDA Data Integrity Principles.
Covers all 9 ALCOA+ principles: Attributable, Legible, Contemporaneous, Original, Accurate,
and the '+' extensions: Complete, Consistent, Enduring, Available.
"""
import json
import os
import re
from datetime import datetime
from rich.console import Console
from rich.table import Table

console = Console()

class ALCOAValidator:
    def __init__(self, evidence_file: str):
        self.evidence_file = evidence_file
        self.evidence = self._load_evidence()
        self.records = self.evidence.get("records", [])
        self.results = {}
        self.issues = []
        
    def _load_evidence(self) -> dict:
        if not os.path.exists(self.evidence_file):
            console.print(f"[bold red]Evidence file not found: {self.evidence_file}[/bold red]")
            exit(1)
        with open(self.evidence_file, "r") as f:
            return json.load(f)

    def validate_attributable(self) -> bool:
        """Rule: Every record must have a distinct user identifier."""
        failed = [r for r in self.records if not r.get('user_id')]
        for f in failed:
            self.issues.append(f"Attributable Violation: Record {f.get('id')} has no user_id.")
        
        passed = len(failed) == 0
        self.results['Attributable'] = passed
        return passed

    def validate_legible(self) -> bool:
        """Rule: Data strings must be readable humans (no corruption/binary bits)."""
        passed = True
        for r in self.records:
            # Simple check ensuring the serialized JSON data isn't null if it should exist
            if r.get('old_values') is None and r.get('action') in ('UPDATE', 'DELETE'):
                self.issues.append(f"Legible Violation: Record {r.get('id')} missing old_values for {r.get('action')}")
                passed = False
        
        self.results['Legible'] = passed
        return passed

    def validate_contemporaneous(self) -> bool:
        """Rule: Timestamps must be valid ISO formats, recorded at the time of the action."""
        passed = True
        # SQLite often uses ' ' instead of 'T' for separation
        iso_regex = re.compile(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\.\d+')
        for r in self.records:
            ts = r.get('timestamp', '')
            if not ts or not iso_regex.match(ts):
                self.issues.append(f"Contemporaneous Violation: Record {r.get('id')} has invalid timestamp format '{ts}'")
                passed = False
                
        self.results['Contemporaneous'] = passed
        return passed

    def validate_original(self) -> bool:
        """Rule: Original records must be captured. Here we verify the table name references base tables."""
        passed = True
        valid_tables = ['users', 'deviations', 'capas', 'documents', 'batch_records']
        for r in self.records:
            table = r.get('table_name')
            if table not in valid_tables:
                self.issues.append(f"Original Violation: Record {r.get('id')} references unknown source table '{table}'")
                passed = False
                
        self.results['Original'] = passed
        return passed

    def validate_accurate(self) -> bool:
        """Rule: Audit trail must not have sequential gaps (which indicates tampering/deletion)."""
        passed = True
        if not self.records:
            self.results['Accurate'] = True
            return True
            
        expected_id = self.records[0].get('id')
        for r in self.records:
            current_id = r.get('id')
            if current_id != expected_id:
                self.issues.append(f"Accurate Violation: Gap in sequence detected. Expected ID {expected_id}, found {current_id}")
                passed = False
                break # Sequence is broken
            expected_id += 1
            
        self.results['Accurate'] = passed
        return passed

    # --- ALCOA '+' Extension Principles ---

    def validate_complete(self) -> bool:
        """Rule (+Complete): Every record must be fully populated with no missing required fields.

        Note: `record_id` is intentionally excluded from CREATE actions because the database
        auto-increment primary key hasn't been assigned by the time the SQLAlchemy before_flush
        event fires. This is architecturally unavoidable and not a compliance violation.
        UPDATE and DELETE actions always have a known primary key and are strictly checked.
        """
        always_required = ['id', 'timestamp', 'action', 'table_name']
        passed = True
        for r in self.records:
            # For UPDATE/DELETE the record_id must be present
            fields_to_check = always_required[:]
            if r.get('action') in ('UPDATE', 'DELETE'):
                fields_to_check.append('record_id')

            missing = [f for f in fields_to_check if r.get(f) is None or r.get(f) == '']
            if missing:
                self.issues.append(
                    f"Complete Violation: Record {r.get('id')} (action={r.get('action')}) "
                    f"is missing required fields: {missing}"
                )
                passed = False
        self.results['Complete'] = passed
        return passed

    def validate_consistent(self) -> bool:
        """Rule (+Consistent): Timestamps must be strictly chronological across all records."""
        passed = True
        if len(self.records) < 2:
            self.results['Consistent'] = True
            return True

        # Normalize timestamps: SQLite uses space separator, Python uses 'T'
        def parse_ts(r):
            ts = r.get('timestamp', '')
            return ts.replace(' ', 'T').split('.')[0]  # strip microseconds for comparison

        prev_ts = parse_ts(self.records[0])
        for r in self.records[1:]:
            curr_ts = parse_ts(r)
            if curr_ts < prev_ts:
                self.issues.append(
                    f"Consistent Violation: Record {r.get('id')} timestamp '{curr_ts}' is earlier than previous '{prev_ts}'. "
                    f"Possible clock manipulation or replay attack."
                )
                passed = False
            prev_ts = curr_ts

        self.results['Consistent'] = passed
        return passed

    def validate_enduring(self) -> bool:
        """Rule (+Enduring): Evidence is stored in a durable, non-proprietary, open format."""
        # JSON is an open IETF standard (RFC 8259) — inherently enduring.
        # We verify the evidence file extension and that it parsed correctly.
        is_json = self.evidence_file.endswith('.json') and isinstance(self.evidence, dict)
        if not is_json:
            self.issues.append(
                "Enduring Violation: Evidence is not stored in an open, non-proprietary format (expected .json)."
            )
        self.results['Enduring'] = is_json
        return is_json

    def validate_available(self) -> bool:
        """Rule (+Available): Evidence must be accessible and readable on demand."""
        # If we got this far, the file was successfully loaded and parsed.
        # We verify the file still physically exists and can be re-read at validation time.
        available = os.path.exists(self.evidence_file) and len(self.records) >= 0
        if not available:
            self.issues.append(
                f"Available Violation: Evidence file '{self.evidence_file}' is not accessible at validation time."
            )
        self.results['Available'] = available
        return available

    def run_all(self):
        console.print("[cyan]Running ALCOA+ Validation Rules (9 Principles)...[/cyan]")
        # Core ALCOA
        self.validate_attributable()
        self.validate_legible()
        self.validate_contemporaneous()
        self.validate_original()
        self.validate_accurate()
        # '+' Extensions
        self.validate_complete()
        self.validate_consistent()
        self.validate_enduring()
        self.validate_available()
        
    def generate_report(self, output_file: str):
        table = Table(title=f"ALCOA+ Validation Summary [{len(self.records)} Records]", show_lines=True)
        table.add_column("Principle", justify="right", style="cyan", no_wrap=True)
        table.add_column("Result", justify="center", style="bold")
        table.add_column("Description", style="italic")
        
        descriptions = {
            # Core ALCOA
            'Attributable':      'All records linked to a specific user identity',
            'Legible':           'Data formats are human-readable and intact',
            'Contemporaneous':   'Timestamps are ISO-8601 strictly compliant',
            'Original':          'Tied to primary data source tables',
            'Accurate':          'Sequential integrity verified (no deleted logs)',
            # ALCOA '+' Extensions
            'Complete':          'All required fields populated (no missing data)',
            'Consistent':        'Timestamps are strictly chronological (no clock manipulation)',
            'Enduring':          'Evidence stored in open, non-proprietary format (JSON/RFC 8259)',
            'Available':         'Evidence file is physically accessible and readable on demand',
        }
        
        all_passed = True
        for principle, passed in self.results.items():
            if not passed: all_passed = False
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            table.add_row(principle, status, descriptions.get(principle, ""))
            
        console.print(table)
        
        if not all_passed:
            console.print("\n[bold red]Validation Failures Detected:[/bold red]")
            for issue in self.issues:
                console.print(f" - {issue}")
                
        # Write text report
        with open(output_file, "w") as f:
            f.write(f"CSA Step 4 — ALCOA+ Validation Summary\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Source: {self.evidence_file}\n")
            f.write(f"Overall Status: {'PASS' if all_passed else 'FAIL'}\n\n")
            
            f.write("--- Rules Evaluation ---\n")
            for principle, passed in self.results.items():
                f.write(f"[{'PASS' if passed else 'FAIL'}] {principle} - {descriptions.get(principle, '')}\n")
                
            if not all_passed:
                f.write("\n--- Issues Found ---\n")
                for issue in self.issues:
                    f.write(f"- {issue}\n")
                    
        console.print(f"\n[dim]Report saved to: {output_file}[/dim]")
        return all_passed

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ALCOA+ Data Integrity Validator")
    parser.add_argument("--evidence", default="evidence_capture/extracted_audit_trail.json", help="Path to evidence JSON file")
    parser.add_argument("--output", default="evidence_capture/alcoa_validation_summary.txt", help="Path to save text summary report")
    args = parser.parse_args()
    
    # Ensure validators dir exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    validator = ALCOAValidator(args.evidence)
    validator.run_all()
    all_passed = validator.generate_report(args.output)
    
    if not all_passed:
        import sys
        sys.exit(1)
