#!/bin/zsh

# run.sh: Script to run parser, unit tests, integration tests, or all tasks

# Default input XML file
DEFAULT_INPUT="input.xml"

# Usage help function
usage() {
    echo "Usage: $0 <command> [input_file]"
    echo "Commands:"
    echo "  parser [input_file]  Run parser on specified XML file (default: $DEFAULT_INPUT)"
    echo "  unit                Run unit tests"
    echo "  integration         Run integration tests"
    echo "  all [input_file]    Run parser, unit tests, and integration tests"
    echo "  help                Display this help message"
    echo "Examples:"
    echo "  $0 parser data.xml"
    echo "  $0 unit"
    echo "  $0 all input.xml"
    exit 1
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed."
    exit 1
fi

# Check command
COMMAND="$1"
INPUT_FILE="${2:-$DEFAULT_INPUT}"

case "$COMMAND" in
    parser)
        # Check if input file exists
        if [ ! -f "$INPUT_FILE" ]; then
            echo "Error: Input file '$INPUT_FILE' not found."
            usage
        fi
        echo "Running parser on '$INPUT_FILE'..."
        python3 xml_parser_final_json.py "$INPUT_FILE"
        if [ $? -eq 0 ]; then
            echo "Parser completed. Outputs: db_objects.json, informatica_objects.json, column_lineage.json"
        else
            echo "Parser failed. Check parse_errors.log for details."
        fi
        ;;
    unit)
        echo "Running unit tests..."
        python3 -m unittest test_unit.py -v
        if [ $? -eq 0 ]; then
            echo "Unit tests completed successfully."
        else
            echo "Unit tests failed."
        fi
        ;;
    integration)
        echo "Running integration tests..."
        python3 -m unittest test_integration.py -v
        if [ $? -eq 0 ]; then
            echo "Integration tests completed successfully."
        else
            echo "Integration tests failed."
        fi
        ;;
    debug)
        echo "Debugging mode..."
        python3 xml_parser_final_json.py --debug "$INPUT_FILE"
        ;;
    all)
        # Check if input file exists
        if [ ! -f "$INPUT_FILE" ]; then
            echo "Error: Input file '$INPUT_FILE' not found."
            usage
        fi
        echo "Running all tasks (parser, unit tests, integration tests)..."
        echo "1. Running parser on '$INPUT_FILE'..."
        python3 xml_parser_final_json.py "$INPUT_FILE"
        if [ $? -eq 0 ]; then
            echo "Parser completed. Outputs: db_objects.json, informatica_objects.json, column_lineage.json"
        else
            echo "Parser failed. Check parse_errors.log for details."
        fi
        echo "2. Running unit tests..."
        python3 -m unittest test_unit.py -v
        if [ $? -eq 0 ]; then
            echo "Unit tests completed successfully."
        else
            echo "Unit tests failed."
        fi
        echo "3. Running integration tests..."
        python3 -m unittest test_integration.py -v
        if [ $? -eq 0 ]; then
            echo "Integration tests completed successfully."
        else
            echo "Integration tests failed."
        fi
        ;;
    help)
        usage
        ;;
    *)
        echo "Error: Invalid command '$COMMAND'."
        usage
        ;;
esac