
NYAYA-BACKEND:
Backend for Nyaya, a precedent search engine for Indian Supreme Court judgements. This repository contains the database setup, the data loaders, and the API that powers the search. The website that consumes this API lives in a separate repository (see below).

WHAT THIS DOES:
It builds and serves a searchable database of real Supreme Court of India judgements. Judgements are loaded from official open data, stored in a Postgres database, and exposed through a small API that the frontend calls to search cases, open full judgement text, and find similar precedents.

HOW IT IS PUT TOEGTHER:
Database: Supabase (hosted Postgres)
API: FastAPI, deployed on Render
Language: Python

DATA SOURCES:
Official Supreme Court eCourts judgements dataset, published as open data on the AWS Open Data Registry. This is the Court's own judgement data, distributed as files, and forms the main archive (judgements from 2000 to 2025 loaded so far, with full text).
https://registry.opendata.aws/indian-supreme-court-judgments/
bharat-courts, an open source library used to pull fresh judgements from the Supreme Court site's "Latest Judgements" feed, which is not behind a captcha.
https://github.com/iamshouvikmitra/bharat-courts
The reason for this approach: the Supreme Court search page is protected by a captcha, so it cannot be queried directly in an automated way. Instead of trying to defeat the captcha, the project uses the Court's official open dataset for the back catalogue and the no-captcha latest-judgements feed for recent cases. This keeps the data real and the method clean.

PROJECT STRUCTURE:
api/ - the FastAPI application (search, case lookup, areas)
core/ - database connection and configuration
ingest/ - data loaders: bulk dataset loader, full-text loader, and the bharat-courts scraper
scripts/ - helper script to load a range of years in one run
db/ - database schema
Setup
Create a Supabase project and run db/schema.sql in its SQL editor to create the table.
Copy .env.example to .env and add your database connection string.

INSTALL DEPENDENCIES:
   pip install -r requirements.txt

LOAD SOME JUDGEMENTS:
   python -m scripts.load_years --start 2010 --end 2025 --limit 2000

RUN THE API LOCALLY:
   uvicorn api.main:app --reload

DEPLOYEMENT:
The API is deployed on Render as a web service, with the database connection string set as an environment variable and the Python version pinned to 3.12. The frontend is deployed separately on Vercel and points at the deployed API.

FRONTEND REPO:
The website (the search interface) is kept in a separate repository:

https://github.com/Anisha-Tiwaryy/Nyaya-Site

DATA CREDIT:
Supreme Court judgement data is from the Indian Supreme Court Judgments open dataset on the AWS Open Data Registry, sourced from the eCourts system and used under its open licence.






