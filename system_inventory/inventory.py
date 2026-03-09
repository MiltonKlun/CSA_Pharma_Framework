import yaml
from typing import List, Optional
from pydantic import BaseModel, Field
import os

class SystemFeature(BaseModel):
    id: str
    name: str
    description: str
    intended_use: str = Field(..., description="'direct' or 'supporting'")
    patient_safety_impact: bool
    data_integrity_impact: bool
    gamp_category: int

    @property
    def is_direct_use(self) -> bool:
        return self.intended_use.lower() == "direct"

class SystemProfile(BaseModel):
    name: str
    version: str
    description: str
    vendor: str
    gamp_category: int

class SystemInventory(BaseModel):
    system: SystemProfile
    features: List[SystemFeature]

def load_inventory(config_path: Optional[str] = None) -> SystemInventory:
    """
    Load the system inventory (CSA Step 1) from the YAML configuration.
    """
    if not config_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config", "qms_system.yaml")
        
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Inventory configuration not found at {config_path}")
        
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
        
    return SystemInventory.model_validate(data)

if __name__ == "__main__":
    inventory = load_inventory()
    print(f"Loaded System: {inventory.system.name} v{inventory.system.version}")
    print(f"Found {len(inventory.features)} features for intended use evaluation.")
    for feature in inventory.features:
        print(f" - [{feature.id}] {feature.name} (Use: {feature.intended_use})")
