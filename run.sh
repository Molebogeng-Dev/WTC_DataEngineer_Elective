set -e

INPUT_FILE="${1:-data/uploads/mock_statement.csv}"
DB_PATH="data/output/finance.db"
JSON_OUT="data/output/summary.json"

mkdir -p data/uploads data/output

if [ "$INPUT_FILE" = "data/uploads/mock_statement.csv" ] && [ ! -f "$INPUT_FILE" ]; then
    echo "No input file found — generating mock 3-month bank statement..."
    python3 scripts/mock_data.py --months 3 --out "$INPUT_FILE"
fi

echo "Running pipeline on: $INPUT_FILE"
echo ""
python3 scripts/extract.py --input "$INPUT_FILE" --db "$DB_PATH"
python3 scripts/transform.py --db "$DB_PATH"
python3 scripts/load.py --db "$DB_PATH" --json-out "$JSON_OUT"

echo ""
echo "Done. Results:"
echo "  SQLite DB : $DB_PATH"
echo "  JSON      : $JSON_OUT"
echo ""
#echo "To view the visual report, open frontend/index.html in a browser"
echo "and upload $INPUT_FILE directly (drag and drop)."
