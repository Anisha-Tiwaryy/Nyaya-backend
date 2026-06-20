# Nyaya Backend — Supreme Court Judgement Database

Real Supreme Court judgements, sourced from the **official eCourts/Supreme Court bulk dataset**
(AWS Open Data), loaded into your own database and served by your own API.

This is built in phases. **Right now you are doing Phase 0 (setup).** Do not skip ahead —
each phase needs the previous one working.

---

## Phase 0 — Setup (do this first)

### Step 1. Create a free cloud database (Supabase)
1. Go to https://supabase.com and sign up (free).
2. Click **New Project**. Give it a name (e.g. `nyaya`). Set a database password — **write it down.**
3. Wait ~2 minutes for it to provision.
4. Go to **Project Settings → Database → Connection string → URI**.
   Choose the **Session pooler** option. Copy that string. It looks like:
   `postgresql://postgres.abcd:[YOUR-PASSWORD]@aws-0-...pooler.supabase.com:5432/postgres`
5. Replace `[YOUR-PASSWORD]` in that string with the password from step 2.

### Step 2. Set up the project on your machine
Open a terminal in this folder, then:

```bash
# 1. create a virtual environment (keeps packages tidy)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. install the Python packages
pip install -r requirements.txt

# 3. create your .env file from the template
cp .env.example .env            # Windows: copy .env.example .env
```

Now open `.env` in a text editor and paste your connection string from Step 1
as the value of `DATABASE_URL`.

### Step 3. Create the table
In the Supabase dashboard, go to the **SQL Editor**, click **New query**, paste the
entire contents of `db/schema.sql`, and click **Run**. You should see "Success".

### Step 4. Test the connection
Back in your terminal (with the venv still active):

```bash
python -m core.database
```

If you see `OK: PostgreSQL ...` — **Phase 0 is done.** Tell Claude and we move to Phase 1
(loading real judgements from the Supreme Court bulk dataset).

If you see an error, copy it back to Claude.

---

## What comes next (not yet — after Phase 0 works)
- **Phase 1** — `ingest/load_bulk.py`: download a slice of the official SC dataset → your DB.
- **Phase 2** — `api/main.py`: search / fetch / similar endpoints over your DB.
- **Phase 3** — point your existing `index.html` frontend at the API.
- **Phase 4+** — Indian Kanoon enrichment, fresh-judgement scraper, AI "find similar".

## Data source & credit
Judgements come from the **Indian Supreme Court Judgments** open dataset
(https://registry.opendata.aws/indian-supreme-court-judgments/), sourced from the
official eCourts system, licensed CC-BY-4.0. Attribution: Vanga (2025), Dattam Labs,
via the AWS Open Data Registry.
