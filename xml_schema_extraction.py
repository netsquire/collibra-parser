import xml.etree.ElementTree as ET
import json
import logging
import os
from typing import Dict, Set, List
from collections import defaultdict

logging.basicConfig(filename="schema_extraction.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def extract_schema(file_path: str) -> Dict:
    """Extract the schema of an XML file."""
    schema = defaultdict(lambda: {
        "attributes": set(),
        "children": set(),
        "parents": set(),
        "occurrences": 0
    })
    
    try:
        # Validate file
        if not os.path.exists(file_path):
            logging.error(f"XML file '{file_path}' not found")
            return {}
        if os.path.getsize(file_path) == 0:
            logging.error(f"XML file '{file_path}' is empty")
            return {}
        
        logging.info(f"Processing XML file: {file_path} (size: {os.path.getsize(file_path)} bytes)")
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        logging.info(f"Root tag: {root.tag}")
        
        def traverse_element(element: ET.Element, parent: str = None):
            """Recursively traverse XML elements to build schema."""
            tag = element.tag
            schema[tag]["occurrences"] += 1
            if parent:
                schema[tag]["parents"].add(parent)
            
            # Collect attributes
            for attr in element.attrib:
                schema[tag]["attributes"].add(attr)
            
            # Collect children
            for child in element:
                schema[tag]["children"].add(child.tag)
                traverse_element(child, tag)
        
        traverse_element(root)
        
        # Convert sets to lists for JSON serialization
        result = {
            tag: {
                "attributes": list(info["attributes"]),
                "children": list(info["children"]),
                "parents": list(info["parents"]),
                "occurrences": info["occurrences"]
            }
            for tag, info in schema.items()
        }
        
        logging.info(f"Extracted schema with {len(result)} unique elements")
        return result
    
    except ET.ParseError as e:
        logging.error(f"XML parsing error: {e}")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {}

def save_schema(schema: Dict, filename: str):
    """Save schema to a JSON file."""
    try:
        with open(filename, "w") as f:
            json.dump(schema, f, indent=2, sort_keys=True)
        logging.info(f"Saved schema to {filename}")
    except Exception as e:
        logging.error(f"Failed to save {filename}: {e}")

if __name__ == "__main__":
    file_path = "input.xml"
    schema = extract_schema(file_path)
    save_schema(schema, "xml_doc_schema.json")