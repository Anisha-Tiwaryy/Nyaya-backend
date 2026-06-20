"""
Phase 2 — The API.

Reads real judgements from your database and serves them over HTTP, so your
frontend (or a browser) can search and fetch them.

Run it:
  uvicorn api.main:app --reload

Then open in a browser:
  http://127.0.0.1:8000/              -> health check
  http://127.0.0.1:8000/search?q=privacy
  http://127.0.0.1:8000/case/<id>
  http://127.0.0.1:8000/docs          -> interactive API explorer
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from core.database import get_connection

app = FastAPI(title="Nyaya API", version="1.0")

# Allow the frontend (any origin, for the demo) to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS n FROM judgements")
            n = cur.fetchone()["n"]
    return {"status": "ok", "judgements_in_db": n}


@app.get("/search")
def search(
    q: str = Query("", description="search text or citation"),
    area: str = Query("", description="optional area-of-law filter"),
    limit: int = Query(25, ge=1, le=100),
    only_text: bool = Query(False, description="only return judgements that have full text"),
):
    """Keyword/citation search using PostgreSQL full-text search,
    with a fallback to simple ILIKE matching."""
    clauses = []
    params = {}

    if q.strip():
        # full-text over title + headnote + full_text, plus citation match
        clauses.append(
            "(to_tsvector('english', coalesce(title,'') || ' ' || "
            "coalesce(headnote,'') || ' ' || coalesce(full_text,'')) "
            "@@ plainto_tsquery('english', %(q)s) "
            "OR title ILIKE %(like)s OR citation ILIKE %(like)s)"
        )
        params["q"] = q
        params["like"] = f"%{q}%"

    if area.strip():
        clauses.append("area ILIKE %(area)s")
        params["area"] = f"%{area}%"

    if only_text:
        clauses.append("full_text IS NOT NULL")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params["limit"] = limit

    sql = f"""
        SELECT id, title, citation, court, bench, decided_on, area, headnote, source,
               (full_text IS NOT NULL) AS has_text
        FROM judgements
        {where}
        ORDER BY (full_text IS NOT NULL) DESC, decided_on DESC NULLS LAST
        LIMIT %(limit)s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return {"count": len(rows), "results": rows}


@app.get("/case/{case_id}")
def get_case(case_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM judgements WHERE id = %s", (case_id,))
            row = cur.fetchone()
    if not row:
        return {"error": "not found", "id": case_id}
    return row


@app.get("/areas")
def areas():
    """List distinct areas of law (for filter dropdowns)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT area, count(*) AS n FROM judgements "
                "WHERE area IS NOT NULL GROUP BY area ORDER BY n DESC LIMIT 50"
            )
            rows = cur.fetchall()
    return {"areas": rows}
