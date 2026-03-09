import yaml
import os
from pydantic import BaseModel
from typing import Dict

class RiskCriteria(BaseModel):
    severity: Dict[int, str]
    occurrence: Dict[int, str]
    detection: Dict[int, str]
    thresholds: Dict[str, int]

def load_risk_criteria(config_path: str = None) -> RiskCriteria:
    if not config_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config", "risk_criteria.yaml")
        
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
        
    return RiskCriteria.model_validate(data)

class FMEACalculator:
    """
    Calculates the Risk Priority Number (RPN) based on ICH Q9 methodologies.
    RPN = Severity x Occurrence x Detection
    """
    def __init__(self, criteria: RiskCriteria = None):
        if not criteria:
            criteria = load_risk_criteria()
        self.criteria = criteria
        
    def calculate_rpn(self, severity_score: int, occurrence_score: int, detection_score: int) -> int:
        if severity_score not in self.criteria.severity:
            raise ValueError(f"Invalid severity score: {severity_score}")
        if occurrence_score not in self.criteria.occurrence:
            raise ValueError(f"Invalid occurrence score: {occurrence_score}")
        if detection_score not in self.criteria.detection:
            raise ValueError(f"Invalid detection score: {detection_score}")
            
        return severity_score * occurrence_score * detection_score
