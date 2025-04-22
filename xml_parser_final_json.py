import xml.etree.ElementTree as ET
import json
from typing import List, Dict, Optional
from collections import defaultdict
import logging
import argparse

# Setup logging
logging.basicConfig(filename="parse_errors.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants, enums
class XML_NAMES:
    """Enum-like class for entity names."""
    SOURCE = "SOURCE"
    TARGET = "TARGET"
    TRANSFORMATION = "TRANSFORMATION"
    MAPPING = "MAPPING"
    WORKFLOW = "WORKFLOW"
    SOURCEFIELD = "SOURCEFIELD"
    TARGETFIELD = "TARGETFIELD"
    TRANSFORMFIELD = "TRANSFORMFIELD"
    CONNECTOR = "CONNECTOR"
    INSTANCE = "INSTANCE"
    ASSOC_SOURCE_INSTANCE = "ASSOCIATED_SOURCE_INSTANCE"
    TASKINSTANCE = "TASKINSTANCE"
    DB_NAME = "DBDNAME"
    OWNER_NAME = "OWNERNAME"
    NAME = "NAME"
    TYPE = "TYPE"
    SESSION = "SESSION"
    MAPPING_NAME = "MAPPINGNAME"
    FROMINSTANCE = "FROMINSTANCE"
    FROMFIELD = "FROMFIELD"
    TOINSTANCE = "TOINSTANCE"
    TOFIELD = "TOFIELD"
    REPOSITORY = "REPOSITORY"
    FOLDER = "FOLDER"
    TARGETLOADORDER = "TARGETLOADORDER"
    ERPINFO = "ERPINFO"


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


class CollibraXMLParser:
    def __init__(self, xml_file: str, debug_mode=False):
        self.xml_file = xml_file
        self.debug_mode = debug_mode
        self.id_gen = IDGenerator()
        self.db_objects = {}
        self.informatica_objects = {}
        self.lineage = []
        self.instance_types = defaultdict(dict)

    def dprint(self, message: str):
        """Debug print function."""
        if self.debug_mode:
            print(message)

    def db_tree(self, elem: ET.Element, id_gen: IDGenerator) -> Dict[str, any]:
        """Process SOURCE or TARGET, returning db object structure."""
        elem_tag = elem.tag
        db_name = elem.get(XML_NAMES.DB_NAME)
        schema_name = elem.get(XML_NAMES.OWNER_NAME)
        table_name = elem.get(XML_NAMES.NAME)
        fields = {}
        field_tag = XML_NAMES.SOURCEFIELD if elem_tag == XML_NAMES.SOURCE else XML_NAMES.TARGETFIELD
        for field in elem.findall(field_tag):
            field_name = field.get(XML_NAMES.NAME)
            field_id = id_gen.get_id(elem_tag, table_name, field_name)
            fields[field_name] = {"id": field_id}    
        return {db_name: {schema_name: {table_name: fields}}}

    def transformation_graph(self, elem: ET.Element, id_gen: IDGenerator) -> Dict[str, any]:
        """Process TRANSFORMATION, returning transformation structure."""
        trans_name = elem.get(XML_NAMES.NAME)
        fields = {}
        for field in elem.findall(XML_NAMES.TRANSFORMFIELD):
            field_name = field.get(XML_NAMES.NAME)
            field_id = id_gen.get_id(XML_NAMES.TRANSFORMFIELD, trans_name, field_name)
            fields[field_name] = {"id": field_id}
        return {trans_name: fields}

    def mapping_graph(self, elem: ET.Element, id_gen: IDGenerator) -> tuple[Dict[str, any], Dict[str, str]]:
        """Process MAPPING, returning mapping structure and collecting instance data."""
        if elem is None:
            return {}, {}
        
        mapping_name = elem.get(XML_NAMES.NAME)
        transformations = {}
        instance_types = {}  # Maps instance name to its type (SOURCE, TARGET, TRANSFORMATION)
        
        for trans in elem.findall(XML_NAMES.TRANSFORMATION):
            trans_data = self.transformation_graph(trans, id_gen)
            transformations.update(trans_data)
        
        for instance in elem.findall(XML_NAMES.INSTANCE):
            instance_name = instance.get(XML_NAMES.NAME)
            instance_type = instance.get(XML_NAMES.TYPE)
            instance_types[instance_name] = instance_type
        
        return {mapping_name: transformations}, instance_types

    def workflow_graph(self, elem: ET.Element, id_gen: IDGenerator, mappings: List[ET.Element]) -> Dict[str, any]:
        """Process WORKFLOW, returning workflow structure."""
        workflow_name = elem.get(XML_NAMES.NAME)
        sessions = {}    
        for session in elem.findall(XML_NAMES.SESSION):
            session_name = session.get(XML_NAMES.NAME)
            mapping_name = session.get(XML_NAMES.MAPPING_NAME)
            # Find matching MAPPING element
            mapping_elem = next((m for m in mappings if m.get(XML_NAMES.NAME) == mapping_name), None)
            if mapping_elem is None:
                logging.warning(f"No MAPPING found for MAPPINGNAME '{mapping_name}' in session '{session_name}'")
                continue
            mapping_data, _ = self.mapping_graph(mapping_elem, id_gen)
            sessions[session_name] = mapping_data    
        return {workflow_name: sessions}

    def extract_lineage(self, elem: ET.Element, id_gen: IDGenerator, instance_types: Dict[str, Dict[str, str]]) -> List[List[int]]:
        """Extract column lineage from CONNECTOR elements."""
        if elem is None:
            return []    
        lineage = []
        mapping_name = elem.get(XML_NAMES.NAME)
        for connector in elem.findall(XML_NAMES.CONNECTOR):
            from_instance = connector.get(XML_NAMES.FROMINSTANCE)
            from_field = connector.get(XML_NAMES.FROMFIELD)
            to_instance = connector.get(XML_NAMES.TOINSTANCE)
            to_field = connector.get(XML_NAMES.TOFIELD)
            
            # Determine object types
            from_type = instance_types.get(mapping_name, {}).get(from_instance)
            to_type = instance_types.get(mapping_name, {}).get(to_instance)
            
            # Map instance types to object types
            object_type_map = {
                XML_NAMES.SOURCE: XML_NAMES.SOURCE,
                XML_NAMES.TARGET: XML_NAMES.TARGET,
                XML_NAMES.TRANSFORMATION: XML_NAMES.TRANSFORMFIELD
            }
            from_object_type = object_type_map.get(from_type, XML_NAMES.TRANSFORMFIELD)
            to_object_type = object_type_map.get(to_type, XML_NAMES.TRANSFORMFIELD)
            
            # Get IDs
            from_id = id_gen.get_id_if_exists(from_object_type, from_instance, from_field)
            to_id = id_gen.get_id_if_exists(to_object_type, to_instance, to_field)
            
            if from_id and to_id:
                lineage.append([from_id, to_id])
            else:
                logging.info(f"Unmapped lineage: {from_instance}.{from_field} ({from_type}) -> {to_instance}.{to_field} ({to_type})")    
        return lineage

    def merge_dicts(self, acc: Dict, append: Dict) -> Dict:
        """Merge two nested dictionaries, preserving structure. (Issues possible with overwriting sets and scalars)"""
        for key, value in append.items():
            both_values_are_dicts: bool = isinstance(acc.get(key), dict) and isinstance(value, dict)
            if key in acc and both_values_are_dicts:
                acc[key] = self.merge_dicts(acc[key], value)
            else:
                acc[key] = value
        return acc

    def parse_xml(self, debug_mode=False) -> tuple[Dict, Dict, List[List[int]]]:
        """Parse XML and generate three outputs.
        (Invalid) XML structure for clarity:
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
            tree = ET.parse(self.xml_file)
            root = tree.getroot()        
            repo = root.find(f".//{XML_NAMES.REPOSITORY}")
            repo_name = repo.get(XML_NAMES.NAME) if repo is not None else "N/A"
            
            # SOURCE and TARGET as database objects
            all_source_target = root.findall(f".//{XML_NAMES.SOURCE}") + root.findall(f".//{XML_NAMES.TARGET}")
            for elem in all_source_target:
                db_objects = self.merge_dicts(db_objects, self.db_tree(elem, id_gen))
            
            # MAPPING for initial transformations and lineage
            mappings = root.findall(f".//{XML_NAMES.MAPPING}")
            for mapping in mappings:
                mapping_name = mapping.get(XML_NAMES.NAME)
                mapping_data, mapping_instance_types = self.mapping_graph(mapping, id_gen)
                informatica_objects = self.merge_dicts(informatica_objects, {repo_name: mapping_data})
                
                self.dprint(f"---\nMapping: {mapping_name}")
                self.dprint(f"---\nInstance Types: {mapping_instance_types}")
                for instance_name, instance_type in mapping_instance_types.items():
                    instance_types[mapping_name][instance_name] = instance_type
                    self.dprint(f"---\nInstance: {instance_name}, Type: {instance_type}")

                self.dprint(f"---\nMapping Data: {mapping_data}")
                self.dprint(f"---\nMapping: {mapping}")
                lineage_update = self.extract_lineage(mapping, id_gen, mapping_instance_types)
                self.dprint(f"---\nLineage Update: {lineage_update}")
                lineage.extend(lineage_update)
            
            # Update informatica_objects with WORKFLOW
            # Workflow consists of multiple sessions, each session references to mapping
            for workflow in root.findall(f".//{XML_NAMES.WORKFLOW}"):
                wf_data = self.workflow_graph(workflow, id_gen, mappings)
                informatica_objects = self.merge_dicts(informatica_objects, {repo_name: wf_data})
            
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

    def save_to_json(self, data: any, filename: str):
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Process input XML doc.")
    parser.add_argument("--input", type=str, default="imput.xml", help="Input XML file path")
    parser.add_argument("--debug", default=None, help="Enable debug output")
    args = parser.parse_args()

    print(f"Input file: {args.input}")
    debug_mode = False
    if args.debug:
        debug_mode = True
        print(f"Debug mode: {debug_mode}")
    
    folder = "output"
    collibra_parser = CollibraXMLParser("input.xml", debug_mode=debug_mode)

    db_objects, informatica_objects, lineage = collibra_parser.parse_xml()
    collibra_parser.save_to_json(db_objects, f"{folder}/db_objects.json")
    collibra_parser.save_to_json(informatica_objects, f"{folder}/informatica_objects.json")
    collibra_parser.save_to_json(lineage, f"{folder}/column_lineage.json")
    print(f"X-Ray JSON files created in '{folder}' with collected errors, mostly unmapped lineage(s) in 'parse_errors.log'.")