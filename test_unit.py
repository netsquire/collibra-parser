import unittest
import xml.etree.ElementTree as ET
from xml_parser_final_json import IDGenerator, CollibraXMLParser

collibra_parser = CollibraXMLParser(xml_file="input.xml")

class TestUnitParser(unittest.TestCase):
    def setUp(self):
        self.id_gen = IDGenerator()

    def test_db_tree(self):
    # Mock SOURCE element
        source_elem = ET.Element("SOURCE", attrib={
            "DBDNAME": "TestDB", "OWNERNAME": "dbo", "NAME": "TestTable"
        })
        field_elem = ET.SubElement(source_elem, "SOURCEFIELD", attrib={
            "NAME": "TestCol", "DATATYPE": "int"
        })
        # Add another field to test multiple fields
        field_elem2 = ET.SubElement(source_elem, "SOURCEFIELD", attrib={
            "NAME": "TestCol2", "DATATYPE": "varchar"
        })
        
        result = collibra_parser.db_tree(source_elem, self.id_gen)
        expected = {
            "TestDB": {
                "dbo": {
                    "TestTable": {
                        "TestCol": {"id": 1},
                        "TestCol2": {"id": 2}
                    }
                }
            }
        }
        self.assertEqual(result, expected)
        # Explicitly verify field_elem was processed
        self.assertIn(field_elem.get("NAME"), result["TestDB"]["dbo"]["TestTable"])
        self.assertEqual(result["TestDB"]["dbo"]["TestTable"][field_elem.get("NAME")]["id"], 1)
        self.assertIn(field_elem2.get("NAME"), result["TestDB"]["dbo"]["TestTable"])
        self.assertEqual(result["TestDB"]["dbo"]["TestTable"][field_elem2.get("NAME")]["id"], 2)

    def test_process_source_or_target_missing_field_name(self):
        # Test SOURCE with missing NAME in SOURCEFIELD
        source_elem = ET.Element("SOURCE", attrib={
            "DBDNAME": "TestDB", "OWNERNAME": "dbo", "NAME": "TestTable"
        })
        field_elem = ET.SubElement(source_elem, "SOURCEFIELD", attrib={
            "DATATYPE": "int"  # Missing NAME
        })
        
        result = collibra_parser.db_tree(source_elem, self.id_gen)
        expected = {
            "TestDB": {
                "dbo": {
                    "TestTable": {None: {'id': 1}}
                }
            }
        }
        self.assertEqual(result, expected)
        # Verify field_elem was skipped due to missing NAME
        self.assertEqual(len(result["TestDB"]["dbo"]["TestTable"]), 1)


    def test_transformation_graph(self):
        # Mock TRANSFORMATION element
        trans_elem = ET.Element("TRANSFORMATION", attrib={"NAME": "SQ_Test"})
        field_elem = ET.SubElement(trans_elem, "TRANSFORMFIELD", attrib={
            "NAME": "TestCol", "DATATYPE": "int"
        })
        # Add another field to test multiple fields
        field_elem2 = ET.SubElement(trans_elem, "TRANSFORMFIELD", attrib={
            "NAME": "TestCol2", "DATATYPE": "varchar"
        })
        
        result = collibra_parser.transformation_graph(trans_elem, self.id_gen)
        expected = {
            "SQ_Test": {
                "TestCol": {"id": 1},  # ID increments from previous tests
                "TestCol2": {"id": 2}
            }
        }
        self.assertEqual(result, expected)
        # Explicitly verify field_elem was processed
        self.assertIn(field_elem.get("NAME"), result["SQ_Test"])
        self.assertEqual(result["SQ_Test"][field_elem.get("NAME")]["id"], 1)
        self.assertIn(field_elem2.get("NAME"), result["SQ_Test"])
        self.assertEqual(result["SQ_Test"][field_elem2.get("NAME")]["id"], 2)

    def test_process_transformation_missing_field_name(self):
        # Test TRANSFORMATION with missing NAME in TRANSFORMFIELD
        trans_elem = ET.Element("TRANSFORMATION", attrib={"NAME": "SQ_Test"})
        field_elem = ET.SubElement(trans_elem, "TRANSFORMFIELD", attrib={
            "DATATYPE": "int"  # Missing NAME
        })
        
        trans_result = collibra_parser.transformation_graph(trans_elem, self.id_gen)
        field_result = collibra_parser.transformation_graph(field_elem, self.id_gen)

        trans_expected = {
            "SQ_Test": 
                { None: {'id': 1}}
        }
        self.assertEqual(trans_result, trans_expected)
        filed_expected = {None: {}}

        self.assertEqual(field_result, filed_expected)
        # Verify field_elem was skipped due to missing NAME
        self.assertEqual(len(trans_result["SQ_Test"]), 1)


    def test_mapping_graph(self):
        # Mock MAPPING element
        mapping_elem = ET.Element("MAPPING", attrib={"NAME": "m_test"})
        trans_elem = ET.SubElement(mapping_elem, "TRANSFORMATION", attrib={"NAME": "SQ_Test"})
        field_elem = ET.SubElement(trans_elem, "TRANSFORMFIELD", attrib={"NAME": "TestCol"})
        instance_elem = ET.SubElement(mapping_elem, "INSTANCE", attrib={
            "NAME": "TestTable", "TRANSFORMATION_TYPE": "Source Definition", "TYPE": "SOURCE"
        })
        instance_elem2 = ET.SubElement(mapping_elem, "INSTANCE", attrib={
            "NAME": "SQ_Test", "TRANSFORMATION_TYPE": "Source Qualifier", "TYPE": "TRANSFORMATION"
        })
        
        result, instance_types = collibra_parser.mapping_graph(mapping_elem, self.id_gen)
        expected_result = {
            "m_test": {
                "SQ_Test": {
                    "TestCol": {"id": 1}  # ID increments
                }
            }
        }
        expected_types = {
            "TestTable": "SOURCE",
            "SQ_Test": "TRANSFORMATION"
        }
        self.assertEqual(result, expected_result)
        self.assertEqual(instance_types, expected_types)
        # Explicitly verify instance_elem and field_elem were processed
        self.assertIn(instance_elem.get("NAME"), instance_types)
        self.assertEqual(instance_types[instance_elem.get("NAME")], instance_elem.get("TYPE"))
        self.assertIn(instance_elem2.get("NAME"), instance_types)
        self.assertEqual(instance_types[instance_elem2.get("NAME")], instance_elem2.get("TYPE"))
        self.assertIn(field_elem.get("NAME"), result["m_test"]["SQ_Test"])

    def test_extract_lineage(self):
        # Mock MAPPING element and instance types
        mapping_elem = ET.Element("MAPPING", attrib={"NAME": "m_test"})
        connector_elem = ET.SubElement(mapping_elem, "CONNECTOR", attrib={
            "FROMINSTANCE": "TestTable", "FROMFIELD": "TestCol",
            "TOINSTANCE": "SQ_Test", "TOFIELD": "TestCol",
            "FROMINSTANCETYPE": "Source Definition", "TOINSTANCETYPE": "Source Qualifier"
        })
        connector_elem2 = ET.SubElement(mapping_elem, "CONNECTOR", attrib={
            "FROMINSTANCE": "SQ_Test", "FROMFIELD": "TestCol",
            "TOINSTANCE": "TargetTable", "TOFIELD": "TargetCol",
            "FROMINSTANCETYPE": "Source Qualifier", "TOINSTANCETYPE": "Target Definition"
        })
        instance_types = {
            "m_test": {
                "TestTable": "SOURCE",
                "SQ_Test": "TRANSFORMATION",
                "TargetTable": "TARGET"
            }
        }
        
        # Pre-populate IDGenerator
        self.id_gen.get_id("SOURCE", "TestTable", "TestCol")  # ID 1
        self.id_gen.get_id("TRANSFORMFIELD", "SQ_Test", "TestCol")  # ID 2
        self.id_gen.get_id("TARGET", "TargetTable", "TargetCol")  # ID 3
        
        result = collibra_parser.extract_lineage(mapping_elem, self.id_gen, instance_types)
        expected = [[1, 2], [2, 3]]
        self.assertEqual(result, expected)
        # Explicitly verify connector_elem was processed
        self.assertTrue(any(
            conn[0] == self.id_gen.get_id_if_exists("SOURCE", connector_elem.get("FROMINSTANCE"), connector_elem.get("FROMFIELD")) and
            conn[1] == self.id_gen.get_id_if_exists("TRANSFORMFIELD", connector_elem.get("TOINSTANCE"), connector_elem.get("TOFIELD"))
            for conn in result
        ))
        self.assertTrue(any(
            conn[0] == self.id_gen.get_id_if_exists("TRANSFORMFIELD", connector_elem2.get("FROMINSTANCE"), connector_elem2.get("FROMFIELD")) and
            conn[1] == self.id_gen.get_id_if_exists("TARGET", connector_elem2.get("TOINSTANCE"), connector_elem2.get("TOFIELD"))
            for conn in result
        ))

    def test_extract_lineage_missing_instance(self):
        # Test with missing instance type
        mapping_elem = ET.Element("MAPPING", attrib={"NAME": "m_test"})
        connector_elem = ET.SubElement(mapping_elem, "CONNECTOR", attrib={
            "FROMINSTANCE": "UnknownTable", "FROMFIELD": "TestCol",
            "TOINSTANCE": "SQ_Test", "TOFIELD": "TestCol",
            "FROMINSTANCETYPE": "Source Definition", "TOINSTANCETYPE": "Source Qualifier"
        })
        instance_types = {"m_test": {"SQ_Test": "TRANSFORMATION"}}
        
        self.id_gen.get_id("TRANSFORMFIELD", "SQ_Test", "TestCol")  # ID 1
        result = collibra_parser.extract_lineage(mapping_elem, self.id_gen, instance_types)
        self.assertEqual(result, [])  # Should be empty due to missing FROMINSTANCE

    def test_merge_dicts(self):
        d1 = {"a": {"b": 1}}
        d2 = {"a": {"c": 2}, "d": 3}
        result = collibra_parser.merge_dicts(d1, d2)
        expected = {"a": {"b": 1, "c": 2}, "d": 3}
        self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main()