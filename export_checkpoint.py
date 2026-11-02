#!/usr/bin/env python3
"""Regenerate exports from a checkpoint without launching a browser."""
import argparse
from pathlib import Path
from turkey_scraper import Database
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('output_directory')
a=p.parse_args()
out=Path(a.output_directory)
if not (out/'checkpoint.sqlite3').is_file():p.error('No checkpoint.sqlite3 in that directory')
db=Database(out/'checkpoint.sqlite3')
try:
 report=db.export(out)
 print(f"{report['unique_lawyers']} lawyer records exported; status={report['run_status']}")
finally:db.db.close()
