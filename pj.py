"""Load the source spreadsheet into Unify.db.

This is the ingest step; `preprocessing.py` reads the database it writes.

    pip install pandas openpyxl
    python pj.py path/to/UNIfy_Database_23_08_25.xlsx

Every sheet becomes a table of the same name, replacing any existing one. The
raw sheets are kept verbatim — parsing, validation and cleaning all happen in
preprocessing.py, so that the untouched source is always recoverable.
"""

import argparse
import os
import sqlite3
import sys

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", help="path to the source .xlsx workbook")
    parser.add_argument("--db", default="Unify.db", help="output SQLite database")
    args = parser.parse_args()

    if not os.path.exists(args.xlsx):
        print(f"error: no such file: {args.xlsx}", file=sys.stderr)
        return 1

    workbook = pd.ExcelFile(args.xlsx, engine="openpyxl")
    conn = sqlite3.connect(args.db)
    try:
        for sheet in workbook.sheet_names:
            frame = pd.read_excel(workbook, sheet_name=sheet, engine="openpyxl")
            frame.to_sql(sheet, conn, if_exists="replace", index=False)
            print(f"loaded sheet {sheet!r} -> table {sheet!r} ({len(frame)} rows)")
    finally:
        conn.close()

    print(f"\nwrote {os.path.abspath(args.db)}")
    print("next: python preprocessing.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
