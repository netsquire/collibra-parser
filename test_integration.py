import unittest
import os
import json
from xml_parser_final_json import CollibraXMLParser
from dtd_generator import extract_schema, generate_dtd, save_dtd

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.xml_file = "input.xml"
        self.parser = CollibraXMLParser(self.xml_file)
        self.output_files = ["db_objects.json", "informatica_objects.json", "column_lineage.json", "powrmart_custom.dtd"]

    def tearDown(self):
        # Clean up temporary files
        for file in self.output_files:
            if os.path.exists(file):
                os.remove(file)

    def test_full_parsing_workflow(self):
        db_objects, informatica_objects, lineage = self.parser.parse_xml()
        self.parser.save_to_json(db_objects, "db_objects.json")
        self.parser.save_to_json(informatica_objects, "informatica_objects.json")
        self.parser.save_to_json(lineage, "column_lineage.json")
        
        # Verify outputs
        with open("db_objects.json", "r") as f:
            db_data = json.load(f)
            self.assertIn("Raw", db_data)
        
        with open("informatica_objects.json", "r") as f:
            inf_data = json.load(f)
            self.assertIn("INF_REP_DEV", inf_data)
            self.assertIn("m_refine_customersalesreport", inf_data["INF_REP_DEV"])
        
        with open("column_lineage.json", "r") as f:
            lineage_data = json.load(f)
            self.assertEqual([[231, 286], [232, 287],], lineage_data[2:4])  # TestCol -> TestCol

    def test_dtd_generation_workflow(self):        
        # DTD generation
        schema = extract_schema(self.xml_file)
        dtd_content = generate_dtd(schema)
        save_dtd(dtd_content, "powrmart_custom.dtd")
        
        # Verify DTD
        with open("powrmart_custom.dtd", "r") as f:
            dtd_text = f.read()
            self.assertIn('<!DOCTYPE POWERMART SYSTEM "powrmart_custom.dtd">', dtd_text)
            self.assertIn("<!ELEMENT SOURCE (SOURCEFIELD*)>", dtd_text)

    def test_not_empty_xml(self):
        db_objects, informatica_objects, lineage = self.parser.parse_xml()
        self.assertNotEqual({}, db_objects)
        self.assertNotEqual({}, informatica_objects)
        self.assertNotEqual([], lineage[1])
        
        schema = extract_schema(self.xml_file)
        self.assertNotEqual(schema, {})

if __name__ == "__main__":
    unittest.main()