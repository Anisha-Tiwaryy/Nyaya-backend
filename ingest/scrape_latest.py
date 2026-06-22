"""
Source 3 — Fresh Supreme Court judgements via the bharat-courts library.

Uses ONLY the no-captcha routes of bharat-courts:
  - the "Latest Judgements / Orders" feed on the SC homepage, and
  - the historical archive (CC-BY-4.0 open data; no captcha, no rate limits).
It does NOT use the captcha-solver paths.

Results are written into the SAME judgements table as the bulk loader and the
Indian Kanoon enrichment, with source='scraper'. So all three sources coexist.

Install first (on a hotspot if campus WiFi blocks pip):
  pip install bharat-courts

Usage:
  python -m ingest.scrape_latest --limit 30
  python -m ingest.scrape_latest --text "right to privacy" --year 2024 --limit 20
"""
import argparse
import asyncio

from core.database import get_connection

try:
    from bharat_courts import Judgments
except ImportError:
    Judgments = None


def save(items):
    inserted = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for it in items:
                # bharat-courts returns Judgment objects; pull fields defensively
                def g(*names):
                    for n in names:
                        v = getattr(it, n, None)
                        if v:
                            return str(v)
                    return None

                title = g("title", "case_name", "name") or "Untitled judgement"
                cid_raw = g("cnr", "id", "citation") or title[:40]
                cid = "sc-live-" + cid_raw.replace(" ", "_")[:60]

                rec = {
                    "id": cid,
                    "title": title[:500],
                    "citation": g("citation", "neutral_citation"),
                    "court": g("court") or "Supreme Court of India",
                    "bench": g("judge", "bench", "coram"),
                    "decided_on": g("date", "decision_date", "judgement_date"),
                    "area": g("disposal_nature", "category"),
                    "headnote": g("headnote", "summary"),
                    "full_text": g("text", "full_text", "body"),
                    "source": "scraper",
                    "source_url": g("url", "pdf_url", "link"),
                }
                cur.execute(
                    """
                    INSERT INTO judgements
                      (id, title, citation, court, bench, decided_on, area,
                       headnote, full_text, source, source_url)
                    VALUES
                      (%(id)s, %(title)s, %(citation)s, %(court)s, %(bench)s,
                       NULLIF(%(decided_on)s,'')::date, %(area)s, %(headnote)s,
                       %(full_text)s, %(source)s, %(source_url)s)
                    ON CONFLICT (id) DO UPDATE
                       SET full_text = COALESCE(EXCLUDED.full_text, judgements.full_text),
                           updated_at = now()
                    """,
                    rec,
                )
                inserted += 1
        conn.commit()
    return inserted


async def fetch(text, year, limit):
    # Judgments().find routes between archive (no captcha) and the live latest feed.
    async with Judgments() as j:
        kwargs = {"court": "sci", "limit": limit, "source": "auto"}
        if text:
            kwargs["text"] = text
        if year:
            kwargs["year"] = year
        return await j.find(**kwargs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", type=str, default=None, help="optional keyword search")
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()

    if Judgments is None:
        raise SystemExit(
            "bharat-courts is not installed. Run:  pip install bharat-courts\n"
            "(use a phone hotspot if campus WiFi blocks pip)."
        )

    print("Fetching fresh Supreme Court judgements via bharat-courts (no-captcha routes)...")
    items = asyncio.run(fetch(args.text, args.year, args.limit))
    print(f"Fetched {len(items)} judgements. Saving...")
    n = save(items)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(id) AS n FROM judgements")
            total = cur.fetchone()["n"]
            cur.execute("SELECT source, count(id) AS n FROM judgements GROUP BY source")
            by_src = cur.fetchall()
    print(f"Saved/updated {n}. Total in DB: {total}")
    print("By source:", {r["source"]: r["n"] for r in by_src})


if __name__ == "__main__":
    main()
