# Informatica PowerCenter XML Parser and DTD Generator

Python-based solution to parse Informatica PowerCenter XML files, extract database objects, Informatica objects, and column lineage, and generate a Document Type Definition (DTD) schema - according provided assignment(assignment.pdf): a parser script, a DTD generator, and comprehensive unit and integration tests to ensure reliability.

## Purpose

The project processes XML files conforming to Informatica PowerCenter’s `powrmart.dtd`, producing:
- `db_objects.json`: Database, schema, table, and column hierarchy.
- `informatica_objects.json`: Informatica repository, folder, mapping, and workflow details.
- `column_lineage.json`: Column-level data lineage from source to target.
- `powrmart_custom.dtd`: A DTD schema derived from the input XML.


## Prerequisites

- **Python 3.8+**
- **Dependencies**:
  - `xml.etree.ElementTree` (standard library)
  - `json` (standard library)
  - `logging` (standard library)
  - `collections` (standard library)
  - `unittest` (standard library for testing)


## Project Structure

```
project/
├── xml_parser_final_json.py # Script to parse XML and generate JSON outputs
├── dtd_generator.py        # Script to generate DTD from XML
├── test_unit.py            # Unit tests for parser and DTD generator
├── test_integration.py     # Integration tests for end-to-end workflow
├── run.sh                  # Shell script to run parser, tests, or all
├── README.md               # Project documentation
├── input.xml               # Default input XML file (user-provided)
├── parse_errors.log        # Log for parser errors
├── dtd_generation.log      # Log for DTD generator errors
├── output/
    ├── informatica_objects.json# Output: Informatica objects
    ├── column_lineage.json     # Output: Column lineage
    ├── db_objects.json         # Output: Database objects
```

## Setup

1. **Clone or Download the Project**:
   ```bash
   git clone <repository-url>
   cd project
   ```

2. **Prepare Input XML**:
   - Place your Informatica PowerCenter XML file as `input.xml` in the project directory, or specify a different file when running the parser.

3. **Ensure Executable Permissions for Shell Script**:
   ```bash
   chmod +x run.sh
   ```

## Usage

Use the `run.sh` script to execute tasks. Available commands:

- **Run Parser**:
  ```bash
  ./run.sh parser [input_file]
  ```
  - Parses the specified XML file (default: `input.xml`).
  - Outputs: `db_objects.json`, `informatica_objects.json`, `column_lineage.json`.
  - Example:
    ```bash
    ./run.sh parser data.xml
    ```

- **Run Unit Tests**:
  ```bash
  ./run.sh unit
  ```
  - Runs unit tests (`test_unit.py`) for individual functions.

- **Run Integration Tests**:
  ```bash
  ./run.sh integration
  ```
  - Runs integration tests (`test_integration.py`) for end-to-end workflow.

- **Run All Tasks**:
  ```bash
  ./run.sh all [input_file]
  ```
  - Runs parser, unit tests, and integration tests.
  - Example:
    ```bash
    ./run.sh all input.xml
    ```

- **Display Help**:
  ```bash
  ./run.sh help
  ```
  - Shows usage instructions.

If invalid options are provided, the script displays usage help. To run parser in DEBUG mode, use option --debug

## Example

To parse `data.xml` and run all tests:
```bash
./run.sh all data.xml
```

To run only the parser with default `input.xml`:
```bash
./run.sh parser
```

## Troubleshooting Empty Outputs

If the parser produces empty outputs (`[]`, `{}`, `{}`), follow these steps:

1. **Check Logs**:
   - Inspect `parse_errors.log` for parsing issues (e.g., `XML file not found`, `No FOLDER element found`).
   - Inspect `dtd_generation.log` for schema extraction errors.

2. **Verify Input XML**:
   - Ensure the XML file exists and contains `POWERMART`, `REPOSITORY`, `FOLDER`, `SOURCE`, `MAPPING`, etc.
   - Print the first 500 characters:
     ```python
     with open("input.xml", "r") as f:
         print(f.read()[:500])
     ```

3. **Validate XML Structure**:
   - Use the generated DTD to validate the XML:
     ```bash
     xmllint --dtdvalid powrmart_custom.dtd input.xml
     ```
   - Fix any validation errors (e.g., missing `NAME` attributes).

4. **Run Tests**:
   - Execute unit and integration tests to identify parsing issues:
     ```bash
     ./run.sh unit
     ./run.sh integration
     ```
   - Check test failures for clues.

5. **Debug Parsing**:
   - Add debug prints in `parser.py` (see comments in code) and rerun:
     ```bash
     ./run.sh parser input.xml
     ```
   - Share `parse_errors.log` or debug output.

## Contributing

- Report issues or suggest improvements via GitHub Issues.
- Ensure tests pass before submitting changes:
  ```bash
  ./run.sh all input.xml
  ```

## License

MIT License. See `LICENSE` file for details.
