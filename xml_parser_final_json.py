import xml.etree.ElementTree as ET
import json
from typing import List, Dict, Optional
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(filename="parse_errors.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class IDGenerator:
    """Generate unique IDs for columns."""
    def __init__(self):
        self.counter = 0
        self.id_map = {}  # Maps (object_type, name, field) to ID

    def get_id(self, object_type: str, object_name: str, field: str) -> int:
        """Generate or retrieve an ID for a column."""
        key = (object_type, object_name, field)
        if key not in self.id_map:
            self.counter += 1
            self.id_map[key] = self.counter
        return self.id_map[key]

    def get_id_if_exists(self, object_type: str, object_name: str, field: str) -> Optional[int]:
        """Retrieve an ID if it exists, else None."""
        key = (object_type, object_name, field)
        return self.id_map.get(key)

def db_tree(elem: ET.Element, id_gen: IDGenerator) -> Dict[str, any]:
    """Process SOURCE or TARGET, returning db object structure."""
    elem_tag = elem.tag
    db_name = elem.get("DBDNAME")
    schema_name = elem.get("OWNERNAME")
    table_name = elem.get("NAME")    
    fields = {}
    field_tag = "SOURCEFIELD" if elem_tag == "SOURCE" else "TARGETFIELD"
    for field in elem.findall(field_tag):
        field_name = field.get("NAME")
        field_id = id_gen.get_id(elem_tag, table_name, field_name)
        fields[field_name] = {"id": field_id}    
    return {db_name: {schema_name: {table_name: fields}}}

def transformation_graph(elem: ET.Element, id_gen: IDGenerator) -> Dict[str, any]:
    """Process TRANSFORMATION, returning transformation structure."""
    trans_name = elem.get("NAME")
    fields = {}
    for field in elem.findall("TRANSFORMFIELD"):
        field_name = field.get("NAME")
        field_id = id_gen.get_id("TRANSFORMFIELD", trans_name, field_name)
        fields[field_name] = {"id": field_id}
    return {trans_name: fields}

def mapping_graph(elem: ET.Element, id_gen: IDGenerator) -> tuple[Dict[str, any], Dict[str, str]]:
    """Process MAPPING, returning mapping structure and collecting instance data."""
    if elem is None:
        return {}, {}
    
    mapping_name = elem.get("NAME")
    transformations = {}
    instance_types = {}  # Maps instance name to its type (SOURCE, TARGET, TRANSFORMATION)
    
    for trans in elem.findall("TRANSFORMATION"):
        trans_data = transformation_graph(trans, id_gen)
        transformations.update(trans_data)
    
    for instance in elem.findall("INSTANCE"):
        instance_name = instance.get("NAME")
        instance_type = instance.get("TYPE")
        instance_types[instance_name] = instance_type
    
    return {mapping_name: transformations}, instance_types

def workflow_graph(elem: ET.Element, id_gen: IDGenerator, mappings: List[ET.Element]) -> Dict[str, any]:
    """Process WORKFLOW, returning workflow structure."""
    workflow_name = elem.get("NAME")
    sessions = {}    
    for session in elem.findall("SESSION"):
        session_name = session.get("NAME")
        mapping_name = session.get("MAPPINGNAME")
        # Find matching MAPPING element
        mapping_elem = next((m for m in mappings if m.get("NAME") == mapping_name), None)
        if mapping_elem is None:
            logging.warning(f"No MAPPING found for MAPPINGNAME '{mapping_name}' in session '{session_name}'")
            continue
        mapping_data, _ = mapping_graph(mapping_elem, id_gen)
        sessions[session_name] = mapping_data    
    return {workflow_name: sessions}

def extract_lineage(elem: ET.Element, id_gen: IDGenerator, instance_types: Dict[str, Dict[str, str]]) -> List[List[int]]:
    """Extract column lineage from CONNECTOR elements."""
    if elem is None:
        return []    
    lineage = []
    mapping_name = elem.get("NAME")    
    for connector in elem.findall("CONNECTOR"):
        from_instance = connector.get("FROMINSTANCE")
        from_field = connector.get("FROMFIELD")
        to_instance = connector.get("TOINSTANCE")
        to_field = connector.get("TOFIELD")
        
        # Determine object types
        from_type = instance_types.get(mapping_name, {}).get(from_instance)
        to_type = instance_types.get(mapping_name, {}).get(to_instance)
        
        # Map instance types to object types
        object_type_map = {
            "SOURCE": "SOURCE",
            "TARGET": "TARGET",
            "TRANSFORMATION": "TRANSFORMFIELD"
        }
        from_object_type = object_type_map.get(from_type, "TRANSFORMFIELD")
        to_object_type = object_type_map.get(to_type, "TRANSFORMFIELD")
        
        # Get IDs
        from_id = id_gen.get_id_if_exists(from_object_type, from_instance, from_field)
        to_id = id_gen.get_id_if_exists(to_object_type, to_instance, to_field)
        
        if from_id and to_id:
            lineage.append([from_id, to_id])
        else:
            logging.info(f"Unmapped lineage: {from_instance}.{from_field} ({from_type}) -> {to_instance}.{to_field} ({to_type})")    
    return lineage

def merge_dicts(d1: Dict, d2: Dict) -> Dict:
    """Merge two nested dictionaries, preserving structure. (Issues possible with overwriting sets and scalars)"""
    for key, value in d2.items():
        both_values_are_dicts: bool = isinstance(d1.get(key), dict) and isinstance(value, dict)
        if key in d1 and both_values_are_dicts:
            d1[key] = merge_dicts(d1[key], value)
        else:
            d1[key] = value
    return d1

def parse_xml(file_path: str) -> tuple[Dict, Dict, List[List[int]]]:
    """Parse XML and generate three outputs:
    <POWERMART>
            <REPOSITORY>
                <FOLDER>
                    <SOURCE>
                        <SOURCEFIELD>
                    <TARGET>
                        <TARGETFIELD>
                    <MAPPING>
                        <TRANSFORMATION>
                            <TRANSFORMFIELD>
                        <INSTANCE>
                            <ASSOCIATED_SOURCE_INSTANCE>
                        <CONNECTOR>
                        <TARGETLOADORDER>
                        <ERPINFO>
                    <WORKFLOW>
                        <SESSION>
                        <TASKINSTANCE>
    """
    id_gen = IDGenerator()
    db_objects = {}
    informatica_objects = {}
    lineage = []
    instance_types = defaultdict(dict)
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()        
        repo = root.find(".//REPOSITORY")
        repo_name = repo.get("NAME") if repo is not None else "N/A"
        
        # SOURCE and TARGET as database objects
        all_source_target = root.findall(".//SOURCE") + root.findall(".//TARGET")
        for elem in all_source_target:
            db_objects = merge_dicts(db_objects, db_tree(elem, id_gen))
        
        # MAPPING for initial transformations and lineage
        mappings = root.findall(".//MAPPING")
        for mapping in mappings:
            mapping_name = mapping.get("NAME")
            mapping_data, mapping_instance_types = mapping_graph(mapping, id_gen)
            informatica_objects = merge_dicts(informatica_objects, {repo_name: mapping_data})
            
            print(f"---\nMapping: {mapping_name}")
            print(f"---\nInstance Types: {mapping_instance_types}")
            for instance_name, instance_type in mapping_instance_types.items():
                instance_types[mapping_name][instance_name] = instance_type
                print(f"---\nInstance: {instance_name}, Type: {instance_type}")

            print(f"---\nMapping Data: {mapping_data}")
            print(f"---\nMapping: {mapping}")
            lineage_update = extract_lineage(mapping, id_gen, mapping_instance_types)
            print(f"---\nLineage Update: {lineage_update}")
            lineage.extend(lineage_update)
        
        # Update informatica_objects with WORKFLOW
        # Workflow consists of multiple sessions, each session references to mapping
        for workflow in root.findall(".//WORKFLOW"):
            wf_data = workflow_graph(workflow, id_gen, mappings)
            informatica_objects = merge_dicts(informatica_objects, {repo_name: wf_data})
        
        # Log if outputs are empty
        if not db_objects:
            logging.warning("No database objects extracted")
        if not informatica_objects:
            logging.warning("No Informatica objects extracted")
        if not lineage:
            logging.warning("No column lineage extracted")
        
    except ET.ParseError as e:
        logging.error(f"XML parsing error: {e}")
    except FileNotFoundError:
        logging.error("XML file not found")
    except Exception as e:
        logging.error(f"Error: {e}")
    
    return db_objects, informatica_objects, lineage

def save_to_json(data: any, filename: str):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    db_objects, informatica_objects, lineage = parse_xml("input.xml")
    folder = "output"
    save_to_json(db_objects, f"{folder}/db_objects.json")
    save_to_json(informatica_objects, f"{folder}/informatica_objects.json")
    save_to_json(lineage, f"{folder}/column_lineage.json")