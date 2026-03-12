# 🚀 Quick Start Guide

Get GraphRAG up and running in 10 minutes!

## Prerequisites

- Docker & Docker Compose installed
- Python 3.11+ (for local development)
- Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Step-by-Step Setup

### 1. Environment Setup (2 minutes)

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_actual_api_key_here
```

### 2. Start Services (3 minutes)

```bash
# Start all services
docker-compose up -d

# Wait for healthy status
docker-compose ps
```

### 3. Test Connections (1 minute)

```bash
docker-compose exec graphrag_app python test_connections.py
```

### 4. Generate Sample Data (1 minute)

```bash
docker-compose exec graphrag_app python scripts/generate_sample_data.py
```

### 5. Run Pipeline (3 minutes)

```bash
docker-compose exec graphrag_app python scripts/run_pipeline.py \
  --dataset ./data/sample_tech_news.csv --limit 50
```

### 6. Start Querying!

**Streamlit UI:** http://localhost:8501

Try: *"Which companies collaborate with organizations funded by Microsoft?"*

## Common Commands

```bash
# View logs
docker-compose logs -f graphrag_app

# Restart services
docker-compose restart

# Stop all
docker-compose down

# Clean restart
docker-compose down -v && docker-compose up -d
```