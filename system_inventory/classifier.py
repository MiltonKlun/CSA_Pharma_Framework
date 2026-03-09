from typing import List, Dict
from .inventory import SystemInventory, SystemFeature

class FeatureClassifier:
    """
    Classifies software features based on FDA CSA Step 1 criteria:
    Direct Use vs. Supporting Use.
    """
    def __init__(self, inventory: SystemInventory):
        self.inventory = inventory
        
    def classify_all(self) -> Dict[str, List[SystemFeature]]:
        direct = []
        supporting = []
        
        for feature in self.inventory.features:
            if feature.is_direct_use:
                direct.append(feature)
            else:
                supporting.append(feature)
                
        return {
            "direct_use": direct,
            "supporting_use": supporting
        }
        
    def get_quality_critical_features(self) -> List[SystemFeature]:
        """
        Features that impact patient safety or data integrity.
        These feed directly into the Risk Assessment (Step 2).
        """
        return [
            f for f in self.inventory.features 
            if f.patient_safety_impact or f.data_integrity_impact
        ]
        
    def generate_classification_report(self) -> str:
        classifications = self.classify_all()
        critical = self.get_quality_critical_features()
        
        report = [
            f"CSA Step 1: Intended Use Classification Report",
            f"System: {self.inventory.system.name}",
            f"{'='*50}",
            f"Total Features Evaluated: {len(self.inventory.features)}",
            f"Direct Use Features: {len(classifications['direct_use'])}",
            f"Supporting Use Features: {len(classifications['supporting_use'])}",
            f"Quality Critical Features: {len(critical)}",
            f"\n--- Direct Use Features ---"
        ]
        
        for f in classifications['direct_use']:
            safety = "⚠️ Safety" if f.patient_safety_impact else ""
            integrity = "🔒 Data" if f.data_integrity_impact else ""
            report.append(f"[{f.id}] {f.name} {safety} {integrity}")
            
        report.append(f"\n--- Supporting Use Features ---")
        for f in classifications['supporting_use']:
            safety = "⚠️ Safety" if f.patient_safety_impact else ""
            integrity = "🔒 Data" if f.data_integrity_impact else ""
            report.append(f"[{f.id}] {f.name} {safety} {integrity}")
            
        return "\n".join(report)

if __name__ == "__main__":
    from .inventory import load_inventory
    classifier = FeatureClassifier(load_inventory())
    print(classifier.generate_classification_report())
