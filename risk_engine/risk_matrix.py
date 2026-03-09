from pydantic import BaseModel
from typing import Optional
from system_inventory.inventory import SystemFeature
from .risk_assessor import FMEACalculator

class RiskDecision(BaseModel):
    feature_id: str
    feature_name: str
    rpn: int
    severity: int
    occurrence: int
    detection: int
    is_high_risk: bool
    rationale: str

class RiskMatrix:
    """
    Applies the FDA CSA threshold logical checks to determine if a 
    software feature poses a HIGH or NOT HIGH risk.
    """
    def __init__(self, fmea_calc: Optional[FMEACalculator] = None):
        self.fmea = fmea_calc or FMEACalculator()
        self.thresholds = self.fmea.criteria.thresholds

    def evaluate_feature(self, feature: SystemFeature, severity: int, occurrence: int, detection: int) -> RiskDecision:
        rpn = self.fmea.calculate_rpn(severity, occurrence, detection)
        
        is_high_risk = False
        rationales = []
        
        # Rule 1: Does it have a critical severity?
        if severity >= self.thresholds.get("critical_severity_trigger", 5):
            is_high_risk = True
            rationales.append(f"Severity ({severity}) meets or exceeds critical threshold")
            
        # Rule 2: Does the RPN exceed the accepted high risk minimum?
        if rpn >= self.thresholds.get("high_risk_min_rpn", 40):
            is_high_risk = True
            rationales.append(f"Calculated RPN ({rpn}) exceeds threshold ({self.thresholds.get('high_risk_min_rpn', 40)})")
        
        # Rule 3: Direct use with patient safety / data integrity impact is always scrutinized higher.
        if feature.is_direct_use and not is_high_risk:
            # We add a warning narrative or manual decision point if it technically scored low but is a direct impact
            rationales.append("Scored as NOT HIGH, but flagged as Direct Use - Review carefully")
            
        if not rationales:
            rationales.append("Scored below all HIGH risk thresholds")
        
        return RiskDecision(
            feature_id=feature.id,
            feature_name=feature.name,
            rpn=rpn,
            severity=severity,
            occurrence=occurrence,
            detection=detection,
            is_high_risk=is_high_risk,
            rationale="; ".join(rationales)
        )


def derive_fmea_scores(feature) -> tuple[int, int, int]:
    """
    Derive defensible FMEA scores from a feature's own metadata.

    Scoring rationale (documented for auditor review):
      Severity:
        6 → patient_safety_impact=True (critical: potential patient harm)
        4 → data_integrity_impact=True only (major: quality event required)
        2 → neither (negligible: operational inconvenience at most)
      Occurrence:
        3 → intended_use='direct' (feature is actively used in quality decisions)
        2 → intended_use='supporting' (feature supports decisions indirectly)
      Detection:
        1 → gamp_category=5 (COTS, well-tested, high detection confidence)
        2 → gamp_category=4 (configured product, moderate detection)
        3 → gamp_category=3 (standard functionality, lower detection assurance)
        4 → gamp_category<3 (custom code, detection hardest)
    """
    # Severity
    if feature.patient_safety_impact:
        severity = 6
    elif feature.data_integrity_impact:
        severity = 4
    else:
        severity = 2

    # Occurrence
    occurrence = 3 if feature.is_direct_use else 2

    # Detection (inverse of GAMP category confidence)
    gamp = feature.gamp_category
    if gamp >= 5:
        detection = 1
    elif gamp == 4:
        detection = 2
    elif gamp == 3:
        detection = 3
    else:
        detection = 4

    return severity, occurrence, detection


if __name__ == "__main__":
    import json
    import os
    import sys
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from system_inventory.inventory import load_inventory

    console = Console()
    console.print(Panel.fit(
        "[bold cyan]CSA Risk Engine — Steps 1 & 2[/bold cyan]\n"
        "FMEA Risk Assessment via ICH Q9 methodology",
        title="Risk Matrix"
    ))

    # Load system inventory
    try:
        inventory = load_inventory()
    except FileNotFoundError as e:
        console.print(f"[bold red]Error loading inventory:[/bold red] {e}")
        sys.exit(1)

    console.print(f"[dim]System:[/dim] [bold]{inventory.system.name}[/bold] v{inventory.system.version}")
    console.print(f"[dim]GAMP Category:[/dim] {inventory.system.gamp_category}\n")

    matrix = RiskMatrix()
    decisions = []

    for feature in inventory.features:
        severity, occurrence, detection = derive_fmea_scores(feature)
        decision = matrix.evaluate_feature(feature, severity, occurrence, detection)
        decisions.append(decision)

    # Build Rich table
    table = Table(title=f"Risk Assessment Results — {len(decisions)} Features", show_lines=True)
    table.add_column("ID",         style="dim",    no_wrap=True)
    table.add_column("Feature",    style="bold")
    table.add_column("S",          justify="center")
    table.add_column("O",          justify="center")
    table.add_column("D",          justify="center")
    table.add_column("RPN",        justify="center", style="bold")
    table.add_column("CSA Risk",   justify="center", no_wrap=True)
    table.add_column("Assurance Required", style="italic")

    for d in decisions:
        risk_label = "[bold red]HIGH[/bold red]" if d.is_high_risk else "[bold green]NOT HIGH[/bold green]"
        assurance  = "Scripted Pytest Automation" if d.is_high_risk else "Unscripted Exploratory"
        table.add_row(
            d.feature_id,
            d.feature_name,
            str(d.severity),
            str(d.occurrence),
            str(d.detection),
            str(d.rpn),
            risk_label,
            assurance,
        )

    console.print(table)

    high_count     = sum(1 for d in decisions if d.is_high_risk)
    not_high_count = len(decisions) - high_count
    console.print(f"\n[bold]Summary:[/bold] {high_count} HIGH risk feature(s), {not_high_count} NOT HIGH feature(s).")

    # Export JSON for report generator
    base_dir    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(base_dir, "risk_engine", "risk_assessment_results.json")
    export_data = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "system": inventory.system.model_dump(),
        "decisions": [d.model_dump() for d in decisions],
    }
    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=2)

    console.print(f"[dim]Results exported to:[/dim] {output_path}")

