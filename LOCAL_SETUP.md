# Local Setup Guide (No Docker Build)

Run GraphRAG **without building the heavy Docker image**. This uses Python directly on your machine and optionally runs only MongoDB + Neo4j in Docker.

---

## Overview

| Component     | How to Run              | Port  |
|--------------|-------------------------|-------|
| MongoDB      | Docker (or install)     | 27017 |
| Neo4j        | Docker (or install)     | 7474, 7687 |
| FastAPI      | Python (uvicorn)        | 8000  |
| Streamlit UI | Python (streamlit)      | 8501  |

---

## Prerequisites

- **Python 3.11+**
- **Docker Desktop** (optional, only for MongoDB + Neo4j)
- **Gemini API key** – [Get one here](https://makersuite.google.com/app/apikey)

---

## Step 1: Start Databases (Choose One)

### Option A: Docker (recommended – no heavy build)

Start **only** MongoDB and Neo4j (no Python image build):

```powershell
cd d:\Internship\FreeLance\GraphRAG
docker compose up -d mongodb neo4j
```

**Verify:**
```powershell
docker ps
```
You should see `graphrag_mongodb` and `graphrag_neo4j` with status `Up`.

### Option B: No Docker – install MongoDB & Neo4j locally

- Install [MongoDB Community](https://www.mongodb.com/try/download/community)
- Install [Neo4j Desktop](https://neo4j.com/download/) or Neo4j Community

Set passwords and update `.env` (see Step 2) with your connection URIs.

---

## Step 2: Create Virtual Environment

```powershell
cd d:\Internship\FreeLance\GraphRAG
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Verify:**
```powershell
python --version
```
Expected: `Python 3.11.x` or higher.

---

## Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

**Verify:**
```powershell
pip list | findstr "fastapi streamlit pymongo neo4j"
```
Expected: All packages listed.

---

## Step 4: Configure Environment

Create `.env` in the project root:

```env
# Databases (when using Docker for mongodb + neo4j)
MONGODB_URI=mongodb://localhost:27017
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=graphrag_password

# Gemini API (required for triple extraction & answer generation)
GEMINI_API_KEY=your_api_key_here
```

**Verify:** `.env` exists and contains at least `MONGODB_URI`, `NEO4J_URI`, `NEO4J_PASSWORD`, `GEMINI_API_KEY`.

---

## Step 5: Run Connection Tests

```powershell
python test_connections.py
```

### Expected Output (Success)

```
================================================================================
GraphRAG System - Connection Tests
================================================================================

Testing MongoDB...
✓ MongoDB connection successful

Testing Neo4j...
✓ Neo4j connection successful

Testing ChromaDB...
✓ ChromaDB initialization successful

Testing Gemini API...
✓ Gemini API connection successful
(or ⚠ Gemini API key not set - if you haven't added it yet)

Testing spaCy...
✓ spaCy model loaded successfully

Testing Sentence Transformers...
✓ Sentence-transformers model loaded (dim=384)

================================================================================
Test Summary
================================================================================
MongoDB: ✓ PASS
Neo4j: ✓ PASS
ChromaDB: ✓ PASS
Gemini API: ✓ PASS
spaCy: ✓ PASS
Sentence Transformers: ✓ PASS

Total: 6/6 tests passed
✓ All tests passed! System is ready.
```

### If Tests Fail

| Test Failed | Check |
|-------------|-------|
| MongoDB | `docker ps` – is `graphrag_mongodb` running? |
| Neo4j | `docker ps` – is `graphrag_neo4j` running? Open http://localhost:7474 |
| ChromaDB | Creates `./chroma_db` – ensure write permissions |
| Gemini API | Add `GEMINI_API_KEY` to `.env` |
| spaCy | Run `python -m spacy download en_core_web_sm` |
| Sentence Transformers | First run downloads model (~90MB) – wait or check internet |

---

## Step 6: Run the Application

### Terminal 1 – FastAPI backend

```powershell
cd d:\Internship\FreeLance\GraphRAG
.venv\Scripts\Activate.ps1
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

**Verify:** Open http://localhost:8000/docs – Swagger UI should load.

### Terminal 2 – Streamlit UI

```powershell
cd d:\Internship\FreeLance\GraphRAG
.venv\Scripts\Activate.ps1
streamlit run app/streamlit_app.py --server.port=8501
```

**Verify:** Open http://localhost:8501 – Streamlit app should load.

---

## Step 7: Run Pipeline (Optional – to populate data)

```powershell
# Generate sample data (if no dataset exists)
python scripts/generate_sample_data.py

# Run full pipeline
python scripts/run_pipeline.py --dataset ./data/sample_tech_news.csv --limit 50
```

---

## Verification Checklist

Use this checklist to confirm each step:

| # | Step | Command / Action | Expected Result |
|---|------|------------------|-----------------|
| 1 | Databases running | `docker ps` | `graphrag_mongodb`, `graphrag_neo4j` = Up |
| 2 | Python version | `python --version` | 3.11 or higher |
| 3 | Venv active | Prompt shows `(.venv)` | Yes |
| 4 | Dependencies | `pip list \| findstr fastapi` | fastapi listed |
| 5 | spaCy model | `python -c "import spacy; spacy.load('en_core_web_sm')"` | No error |
| 6 | Connection tests | `python test_connections.py` | All 6 tests PASS |
| 7 | FastAPI | Open http://localhost:8000/docs | Swagger UI loads |
| 8 | Streamlit | Open http://localhost:8501 | Streamlit app loads |

---

## Quick Reference Commands

```powershell
# Start databases only (no app build)
docker compose up -d mongodb neo4j

# Stop databases
docker compose down

# Run tests
python test_connections.py

# Start FastAPI
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

# Start Streamlit
streamlit run app/streamlit_app.py --server.port=8501

# Generate sample data
python scripts/generate_sample_data.py

# Run pipeline
python scripts/run_pipeline.py --dataset ./data/sample_tech_news.csv --limit 50
```

---

## Troubleshooting

### `ModuleNotFoundError` when running scripts

Activate the venv: `.venv\Scripts\Activate.ps1`

### MongoDB / Neo4j connection refused

- Ensure Docker is running.
- Run `docker compose up -d mongodb neo4j`.
- Wait 30 seconds for databases to start, then run `python test_connections.py` again.

### Neo4j browser

Open http://localhost:7474 – login: `neo4j` / `graphrag_password`

### Port already in use

Change ports in the commands, e.g. `--port 8001` for uvicorn, `--server.port=8502` for Streamlit.

### Sentence-transformers first run is slow

First run downloads the model (~90MB). Subsequent runs use the cached model.

---

## Stopping Everything

```powershell
# Stop FastAPI / Streamlit: Ctrl+C in each terminal

# Stop databases
docker compose down
```
