import json
import os
from application.services.category_service import CategoryService

def bootstrap_categories(category_service: CategoryService, filepath: str):
    """Seed the database with default categories if it is currently empty."""
    existing_categories = category_service.list_all()
    if not existing_categories:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                categories_data = json.load(f)
            
            for item in categories_data:
                category_service.create_category(
                    name=item['name'],
                    transaction_type_str=item['type']
                )
            print(f"Bootstrapped {len(categories_data)} default categories.")
        else:
            print(f"Warning: Default categories file not found at {filepath}")
    else:
        print("Categories table already populated. Skipping bootstrap.")
