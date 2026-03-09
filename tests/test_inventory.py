import pytest
from system_inventory.inventory import SystemInventory, SystemFeature, load_inventory
from system_inventory.classifier import FeatureClassifier

def test_inventory_loading():
    # Tests that the parser can load our demo system YAML
    inventory = load_inventory()
    
    assert inventory.system.name == "PharmaQMS Demo App"
    assert len(inventory.features) > 0
    
def test_direct_vs_supporting_classifier():
    inventory = load_inventory()
    classifier = FeatureClassifier(inventory)
    
    classifications = classifier.classify_all()
    
    # We defined 'AUTH-001' as supporting and 'DEV-001' as direct
    direct_ids = [f.id for f in classifications["direct_use"]]
    supporting_ids = [f.id for f in classifications["supporting_use"]]
    
    assert "DEV-001" in direct_ids
    assert "ESIG-001" in direct_ids
    assert "BATCH-001" in direct_ids
    
    assert "AUTH-001" in supporting_ids
    assert "CAPA-001" in supporting_ids
    
def test_quality_critical_features():
    inventory = load_inventory()
    classifier = FeatureClassifier(inventory)
    
    criticals = classifier.get_quality_critical_features()
    critical_ids = [f.id for f in criticals]
    
    # DASH-001 was configured with false/false for patient impact / data integrity impact
    assert "DASH-001" not in critical_ids
    
    # AUTH-001 has no patient impact but has data integrity = true
    assert "AUTH-001" in critical_ids
