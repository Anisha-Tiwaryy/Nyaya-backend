"""
Phase 1 — Load real Supreme Court judgements into the database. (v2: fixed date parsing)

Source: official Indian Supreme Court Judgments open dataset (eCourts data),
AWS Open Data Registry, bucket: s3://indian-supreme-court-judgments  (ap-south-1).
No AWS account needed (uses --no-sign-request via the AWS CLI).

Usage:
  python -m ingest.load_bulk --year 2023 --limit 500
"""
import argparse
import subprocess
from pathlib import Path

import pandas as pd

from core.database import get_connection

BUCKET = "s3://indian-supreme-court-judgments"
LOCAL = Path("data_download")


def run(cmd):
    print(">>", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr)
        raise SystemExit(
            "Command failed. If this says 'aws' is not recognised, install the AWS CLI "
            "and reopen the terminal."
        )
    return res.stdout


def download_year(year: int):
    LOCAL.mkdir(exist_ok=True)
    prefix = f"metadata/parquet/year={year}/"
    dest = LOCAL / f"parquet_{year}"
    dest.mkdir(parents=True, exist_ok=True)
    run(["aws", "s3", "sync", f"{BUCKET}/{prefix}", str(dest), "--no-sign-request"])
    return dest


def load_parquet_dir(folder: Path) -> pd.DataFrame:
    files = list(folder.rglob("*.parquet"))
    if not files:
        raise SystemExit(f"No parquet files under {folder}. Try a different --year.")
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    print(f"Loaded {len(df)} rows from {len(files)} parquet file(s).")
    return df


def pick(row, *names, default=None):
    for n in names:
        if n in row and pd.notna(row[n]) and str(row[n]).strip():
            return str(row[n]).strip()
    return default


def parse_date(value):
    """Dataset dates look like '30-11-2023' (DD-MM-YYYY). Return YYYY-MM-DD or None."""
    if not value:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return pd.to_datetime(value, format=fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    try:
        return pd.to_datetime(value, dayfirst=True).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def insert_rows(df: pd.DataFrame, year: int, limit: int):
    inserted = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for i, row in df.iterrows():
                if limit and inserted >= limit:
                    break

                title = pick(row, "title", "case_name")
                if not title:
                    pet = pick(row, "petitioner", default="")
                    res = pick(row, "respondent", default="")
                    title = f"{pet} v. {res}".strip(" v.") or "Untitled judgement"

                raw_id = pick(row, "cnr", "diary_number", "judgement_id", "id")
                cid = f"sc-{year}-{raw_id}" if raw_id else f"sc-{year}-{i}"

                rec = {
                    "id": cid,
                    "title": title[:500],
                    "citation": pick(row, "citation", "neutral_citation"),
                    "neutral_cite": pick(row, "neutral_citation"),
                    "court": pick(row, "court", default="Supreme Court of India"),
                    "bench": pick(row, "judge", "bench", "coram"),
                    "decided_on": parse_date(pick(row, "decision_date", "judgement_date", "date")),
                    "area": pick(row, "disposal_nature", "category", "case_type"),
                    "headnote": pick(row, "headnote", "summary"),
                    "source": "bulk",
                    "source_url": pick(row, "url", "source_url", "path"),
                }

                cur.execute(
                    """
                    INSERT INTO judgements
                      (id, title, citation, neutral_cite, court, bench, decided_on,
                       area, headnote, source, source_url)
                    VALUES
                      (%(id)s, %(title)s, %(citation)s, %(neutral_cite)s, %(court)s,
                       %(bench)s, %(decided_on)s::date, %(area)s, %(headnote)s,
                       %(source)s, %(source_url)s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    rec,
                )
                inserted += 1
        conn.commit()
    print(f"Inserted (or skipped duplicates for) {inserted} judgements.")
    return inserted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--limit", type=int, default=500, help="0 = all")
    args = ap.parse_args()

    print(f"== Phase 1: loading Supreme Court judgements for {args.year} ==")
    folder = download_year(args.year)
    df = load_parquet_dir(folder)
    print("Columns available:", list(df.columns))
    insert_rows(df, args.year, args.limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS n FROM judgements")
            total = cur.fetchone()["n"]
    print(f"Done. Total judgements now in database: {total}")


if __name__ == "__main__":
    main()
