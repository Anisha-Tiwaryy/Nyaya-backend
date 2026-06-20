"""
Phase A (v2) — Load judgement TEXT from the metadata we already downloaded.

The bulk metadata already contains the full case content in an HTML field
(headnote, coram/judges, issue, decision details). No PDF download needed.
This extracts and cleans that text and stores it in full_text + bench.

Usage:
  python -m ingest.load_fulltext --year 2023 --limit 200
"""
import argparse
import re
from html import unescape
from pathlib import Path

import pandas as pd

from core.database import get_connection

LOCAL = Path("data_download")


def strip_html(raw: str) -> str:
    if not raw:
        return ""
    s = unescape(str(raw))
    # turn block tags into line breaks so the text stays readable
    s = re.sub(r"(?i)<\s*(br|/p|/div|/tr|/li)\s*/?>", "\n", s)
    # drop all remaining tags
    s = re.sub(r"<[^>]+>", " ", s)
    # remove leftover UI button labels from the source page
    for junk in ["Split view", "HTML view", "Flip view", "PDF",
                 "Download", "Print", "Share", "Bookmark", "Copy"]:
        s = re.sub(r"(?i)\b" + re.escape(junk) + r"\b", " ", s)
    # collapse whitespace
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    return s.strip()


def find_text_column(df):
    """Pick the column that holds the rich case content."""
    candidates = ["raw_html", "html", "content", "judgment_text", "full_text", "text"]
    for c in candidates:
        if c in df.columns:
            return c
    # otherwise pick the column with the longest average string length
    best, best_len = None, 0
    for c in df.columns:
        try:
            avg = df[c].dropna().astype(str).str.len().mean()
        except Exception:
            avg = 0
        if avg and avg > best_len:
            best, best_len = c, avg
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    folder = LOCAL / f"parquet_{args.year}"
    files = list(folder.rglob("*.parquet"))
    if not files:
        raise SystemExit(f"No metadata for {args.year}. Run load_bulk for that year first.")
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

    text_col = find_text_column(df)
    print(f"Using text column: {text_col}")

    updated = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for i, row in df.iterrows():
                if updated >= args.limit:
                    break

                raw = row.get(text_col)
                if pd.isna(raw) or not str(raw).strip():
                    continue
                text = strip_html(raw)
                if len(text) < 80:
                    continue

                # same id scheme as load_bulk
                raw_id = None
                for idc in ["cnr", "diary_number", "judgement_id", "id"]:
                    if idc in row and pd.notna(row[idc]) and str(row[idc]).strip():
                        raw_id = str(row[idc]).strip()
                        break
                cid = f"sc-{args.year}-{raw_id}" if raw_id else f"sc-{args.year}-{i}"

                # try to pull the coram (judges) out of the text for the bench field
                bench = None
                m = re.search(r"Coram\s*:?\s*(.+?)(?:HEADNOTE|Issue|Decision Date|$)", text, re.I)
                if m:
                    bench = m.group(1).strip()[:300]

                cur.execute(
                    "UPDATE judgements SET full_text = %s, "
                    "bench = COALESCE(NULLIF(bench,''), %s), updated_at = now() "
                    "WHERE id = %s",
                    (text[:200000], bench, cid),
                )
                if cur.rowcount:
                    updated += 1
                    if updated % 25 == 0:
                        print(f"  ...{updated} updated")
        conn.commit()

    print(f"Done. Loaded full text for {updated} judgements.")


if __name__ == "__main__":
    main()
