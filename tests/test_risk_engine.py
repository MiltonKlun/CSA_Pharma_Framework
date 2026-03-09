import pytest
from risk_engine.risk_assessor import FMEACalculator
from risk_engine.risk_matrix import RiskMatrix
from risk_engine.gamp_categorizer import GampCategorizer
from system_inventory.inventory import SystemFeature

def test_fmea_calculation():
    calc = FMEACalculator()
    rpn = calc.calculate_rpn(severity_score=4, occurrence_score=3, detection_score=2)
    assert rpn == (4 * 3 * 2)

def test_fmea_invalid_score():
    calc = FMEACalculator()
    with pytest.raises(ValueError):
        # 10 is out of bounds (1-6 for severity)
        calc.calculate_rpn(severity_score=10, occurrence_score=1, detection_score=1)

def test_risk_matrix_thresholding():
    calc = FMEACalculator()
    matrix = RiskMatrix(calc)
    
    # Dummy Direct Use feature
    feature = SystemFeature(
        id="TEST-001",
        name="Test",
        description="Test feature",
        intended_use="direct",
        patient_safety_impact=True,
        data_integrity_impact=True,
        gamp_category=4
    )
    
    # Rule 1: High severity triggers HIGH risk regardless of RPN
    # 5 * 1 * 1 = 5 (RPN below 40 threshold, but severity >= 5)
    decision = matrix.evaluate_feature(feature, severity=5, occurrence=1, detection=1)
    assert decision.is_high_risk is True
    assert decision.rpn == 5
    
    # Rule 2: High RPN triggers HIGH risk
    # 4 * 4 * 3 = 48 (RPN >= 40)
    decision = matrix.evaluate_feature(feature, severity=4, occurrence=4, detection=3)
    assert decision.is_high_risk is True
    assert decision.rpn == 48
    
    # Not HIGH rule
    # 3 * 2 * 2 = 12 (Low severity, low RPN)
    decision = matrix.evaluate_feature(feature, severity=3, occurrence=2, detection=2)
    assert decision.is_high_risk is False
    assert decision.rpn == 12
    # Even though NOT HIGH, should flag that it is "Direct Use" for reviewer scrutiny
    assert "Direct Use" in decision.rationale

def test_gamp_categorizer():
    categorizer = GampCategorizer()
    cat4 = categorizer.get_category_info(4)
    assert cat4.name == "Configured Products"
    
    with pytest.raises(ValueError):
        categorizer.get_category_info(2) # Category 2 doesn't exist in GAMP 5 Second Edition
