import yaml
import os
from pydantic import BaseModel
from typing import Dict

class GampCategory(BaseModel):
    name: str
    description: str
    validation_approach: str

class GampCategorizer:
    """
    Assigns GAMP 5 categories and identifies the required validation approach.
    """
    def __init__(self, config_path: str = None):
        if not config_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "config", "gamp_categories.yaml")
            
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
            self.categories: Dict[int, GampCategory] = {
                k: GampCategory(**v) for k, v in data.get('categories', {}).items()
            }
            
    def get_category_info(self, category_num: int) -> GampCategory:
        if category_num not in self.categories:
            raise ValueError(f"Invalid GAMP Category: {category_num}. Valid options are 1, 3, 4, 5.")
        return self.categories[category_num]
