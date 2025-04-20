import xml.etree.ElementTree as ET
import json
import logging
import os
from typing import Dict, Set, List
from collections import defaultdict

# Setup logging
logging.basicConfig(filename="dtd_generation.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def extract_schema(file_path: str) -> Dict:
    """Extract schema from XML for DTD generation."""
    schema = defaultdict(lambda: {
        "attributes": defaultdict(lambda: {"values": set(), "occurrences": 0}),
        "children": set(),
        "parents": set(),
        "occurrences": 0,
        "has_text": False
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
            
            # Collect attributes and values
            for attr, value in element.attrib.items():
                schema[tag]["attributes"][attr]["values"].add(value)
                schema[tag]["attributes"][attr]["occurrences"] += 1
            
            # Check for text content
            if element.text and element.text.strip():
                schema[tag]["has_text"] = True
            
            # Collect children
            for child in element:
                schema[tag]["children"].add(child.tag)
                traverse_element(child, tag)
        
        traverse_element(root)
        
        # Convert to JSON-serializable format
        result = {
            tag: {
                "attributes": {
                    attr: {
                        "values": list(info["values"])[:10],  # Limit for logging
                        "total_values": len(info["values"]),
                        "occurrences": info["occurrences"],
                        "mandatory": info["occurrences"] == schema[tag]["occurrences"]
                    }
                    for attr, info in data["attributes"].items()
                },
                "children": list(data["children"]),
                "parents": list(data["parents"]),
                "occurrences": data["occurrences"],
                "has_text": data["has_text"]
            }
            for tag, data in schema.items()
        }
        
        logging.info(f"Extracted schema with {len(result)} unique elements")
        return result
    
    except ET.ParseError as e:
        logging.error(f"XML parsing error: {e}")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {}

def generate_dtd(schema: Dict) -> str:
    """Generate DTD from schema."""
    dtd_lines = ['<!DOCTYPE POWERMART SYSTEM "powrmart_custom.dtd">']
    
    for tag, data in schema.items():
        # Determine element content
        children = data["children"]
        if not children:
            content = "EMPTY" if not data["has_text"] else "PCDATA"
        else:
            # Infer cardinality based on XML structure
            child_counts = defaultdict(int)
            for child_tag in children:
                child_counts[child_tag] = schema[child_tag]["occurrences"]
            
            child_decls = []
            for child in children:
                if child_counts[child] > 1 or child in ["SOURCEFIELD", "TARGETFIELD", "TRANSFORMFIELD", "CONNECTOR", "INSTANCE", "SESSION", "TASKINSTANCE"]:
                    child_decls.append(f"{child}*")
                elif child in ["REPOSITORY", "FOLDER"]:
                    child_decls.append(f"{child}+")
                elif child in ["ERPINFO", "ASSOCIATED_SOURCE_INSTANCE"]:
                    child_decls.append(f"{child}?")
                else:
                    child_decls.append(child)
            content = f"({'|'.join(child_decls)})"
        
        dtd_lines.append(f"<!ELEMENT {tag} {content}>")
        
        # Generate attribute list
        if data["attributes"]:
            attr_lines = [f"<!ATTLIST {tag}"]
            for attr, attr_data in data["attributes"].items():
                # Determine attribute type
                values = attr_data["values"]
                if len(values) <= 5 and all(len(v) < 20 for v in values):
                    attr_type = f"({'|'.join(sorted(values))})"
                else:
                    attr_type = "CDATA"
                
                # Determine requirement
                requirement = "#REQUIRED" if attr_data["mandatory"] else "#IMPLIED"
                
                attr_lines.append(f"    {attr} {attr_type} {requirement}")
            
            attr_lines.append(">")
            dtd_lines.extend(attr_lines)
        
        # Log element details
        logging.debug(f"Generated DTD for {tag}: {content}, {len(data['attributes'])} attributes")
    
    return "\n".join(dtd_lines)

def save_dtd(dtd_content: str, filename: str):
    """Save DTD to a file."""
    try:
        with open(filename, "w") as f:
            f.write(dtd_content)
        logging.info(f"Saved DTD to {filename}")
    except Exception as e:
        logging.error(f"Failed to save {filename}: {e}")

# Example usage
if __name__ == "__main__":
    file_path = "data.xml"
    schema = extract_schema(file_path)
    if schema:
        dtd_content = generate_dtd(schema)
        save_dtd(dtd_content, "powrmart_custom.dtd")