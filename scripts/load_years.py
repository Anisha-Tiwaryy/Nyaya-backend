"""
One-shot loader: loads metadata + full text for a range of years.
Run once, walk away.

Usage:
  python -m scripts.load_years --start 2010 --end 2025 --limit 2000
"""
import argparse
import runpy
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2010)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--limit", type=int, default=2000)
    args = ap.parse_args()

    from ingest import load_bulk, load_fulltext

    for year in range(args.start, args.end + 1):
        print(f"\n========== YEAR {year} ==========")
        try:
            # 1) metadata
            sys.argv = ["load_bulk", "--year", str(year), "--limit", str(args.limit)]
            load_bulk.main()
            # 2) full text (from the metadata we just downloaded)
            sys.argv = ["load_fulltext", "--year", str(year), "--limit", str(args.limit)]
            load_fulltext.main()
        except SystemExit as e:
            print(f"  (year {year} skipped: {e})")
        except Exception as e:
            print(f"  (year {year} error, continuing: {e})")

    print("\nALL DONE.")
    from core.database import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(id) AS n FROM judgements")
            total = cur.fetchone()["n"]
            cur.execute("SELECT count(id) AS n FROM judgements WHERE full_text IS NOT NULL")
            withtext = cur.fetchone()["n"]
    print(f"Total judgements: {total} | with full text: {withtext}")


if __name__ == "__main__":
    main()
