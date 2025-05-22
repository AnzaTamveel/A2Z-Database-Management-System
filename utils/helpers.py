import re
from typing import Dict, Any

def validate_db_name(name: str):
    """Validate a database name"""
    if not name:
        raise ValueError("Database name cannot be empty")
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError("Database name can only contain alphanumeric characters, underscores, and hyphens")

def deep_update(target: Dict, update: Dict):
    """Recursively update a dictionary"""
    for key, value in update.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_update(target[key], value)
        else:
            target[key] = value

def match_document(doc: Dict, query: Dict) -> bool:
    """Check if a document matches a query"""
    for key, query_value in query.items():
        if key not in doc:
            return False
        
        doc_value = doc[key]
        
        # Handle nested queries
        if isinstance(query_value, dict):
            if not isinstance(doc_value, dict):
                return False
            if not match_document(doc_value, query_value):
                return False
        # Handle exact match
        elif doc_value != query_value:
            return False
    
    return True