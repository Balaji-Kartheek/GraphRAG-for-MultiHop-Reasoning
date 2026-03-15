# GraphRAG System for Multi-Hop Reasoning

A production-ready **GraphRAG (Graph Retrieval-Augmented Generation)** system that combines **Knowledge Graphs + Vector Retrieval** to enable multi-hop reasoning over Tech & AI industry news.

## 🎯 Problem Statement

Standard RAG systems struggle with multi-hop reasoning questions that require connecting information across multiple documents. For example:

**Article 1:** Microsoft invested in OpenAI  
**Article 2:** OpenAI partnered with Nvidia

**Question:** Which companies collaborate with organizations funded by Microsoft?

**Answer Chain:** Microsoft → invested_in → OpenAI → partnered_with → Nvidia

This system solves this by building a **knowledge graph** alongside vector embeddings to enable complex reasoning chains.

## 🏗️ Architecture

```
News Dataset
    ↓
MongoDB (raw storage)
    ↓
NER (spaCy) → Triple Extraction (Gemini)
    ↓
Neo4j (Knowledge Graph) + ChromaDB (Vector Store)
    ↓
Query → Entity Detection → Subgraph Retrieval + Vector Search
    ↓
Multi-Hop Reasoning → Answer Generation (Gemini)
```

## 🚀 Tech Stack

- **Language:** Python 3.11+
- **Databases:** MongoDB, Neo4j, ChromaDB
- **NLP:** spaCy, sentence-transformers
- **LLM:** Google Gemini Flash API
- **Backend:** FastAPI
- **UI:** Streamlit + PyVis
- **Deployment:** Docker + Docker Compose

## 📦 Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Gemini API key ([get here](https://makersuite.google.com/app/apikey))

### Setup

1. **Clone the repository**
```bash
git clone <repo-url>
cd graphrag-project
```

2. **Create environment file**
```bash
cp .env.example .env
```

3. **Edit `.env` and add your Gemini API key**
```bash
GEMINI_API_KEY=your_api_key_here
```

4. **Start services with Docker**
```bash
docker-compose up -d
```

This will start:
- MongoDB (port 27017)
- Neo4j (ports 7474, 7687)
- FastAPI (port 8000)
- Streamlit (port 8501)

5. **Test connections**
```bash
docker-compose exec graphrag_app python test_connections.py
```

## 📊 Data Preparation

### Option 1: Use Sample Data

```bash
# Create sample dataset (included in project)
python -c "from ingestion.fetch_articles import ArticleIngestion; ArticleIngestion()"
```

### Option 2: Use Your Own Dataset

Prepare a CSV file with columns:
- `title`: Article title
- `content`: Article content
- `source`: Source name (e.g., TechCrunch)
- `date`: Publication date
- `url`: Article URL

Place your CSV in the `data/` directory.

## 🔄 Running the Pipeline

### Full Pipeline (Automated)

```bash
python scripts/run_pipeline.py --dataset ./data/tech_news.csv --limit 100
```

This runs all steps:
1. Ingest articles
2. Preprocess & clean
3. Extract entities (NER)
4. Extract triples (Gemini)
5. Build knowledge graph (Neo4j)
6. Generate embeddings (ChromaDB)

### Step-by-Step (Manual)

```bash
# 1. Ingest articles
python -m ingestion.fetch_articles

# 2. Preprocess
python -m ingestion.preprocess

# 3. Extract entities
python -m extraction.ner

# 4. Extract triples
python -m extraction.triple_extractor

# 5. Build graph
python -m graph.graph_builder

# 6. Embed documents
python -m vector.chroma_client
```

### Pipeline Steps: What Happens at Each Step (2 Examples)

Two example articles are traced through all 6 steps so you can see the input and output at each stage.

**Case A – Investment article**  
*Title:* Microsoft Invests $10B in OpenAI  
*Content:* Microsoft announced a $10 billion investment in OpenAI, strengthening their partnership in AI development.

**Case B – Partnership article**  
*Title:* OpenAI Partners with Nvidia for GPU Infrastructure  
*Content:* OpenAI has formed a strategic partnership with Nvidia to leverage their advanced GPU technology for AI model training.

---

**Step 1 – Ingest (MongoDB)**

- **Input:** CSV rows (title, content, source, date, url).
- **Action:** Filter tech/AI rows, generate `article_id` (hash of title+source), insert into MongoDB. Duplicates (same title+source) are skipped.
- **Output (per article):**

| Field        | Case A                    | Case B                          |
|-------------|----------------------------|----------------------------------|
| article_id  | (hash, e.g. a1b2c3...)     | (different hash)                 |
| title       | Microsoft Invests $10B...   | OpenAI Partners with Nvidia...   |
| content     | Microsoft announced...     | OpenAI has formed...             |
| source      | TechCrunch                 | VentureBeat                      |
| processed   | false                      | false                            |

---

**Step 2 – Preprocess**

- **Input:** MongoDB articles with `processed: false`.
- **Action:** Clean text (strip HTML, URLs, normalize spaces), segment content into sentences with spaCy, update same document.
- **Output (added/updated on same doc):**

| Field           | Case A              | Case B              |
|-----------------|---------------------|---------------------|
| title           | (cleaned same)      | (cleaned same)       |
| content         | (cleaned same)      | (cleaned same)       |
| sentences       | ["Microsoft announced...", "strengthening their..."] | ["OpenAI has formed...", ...] |
| sentence_count  | 2                   | 2                   |

*(Note: `processed` is not set to true here; later steps use other flags.)*

---

**Step 3 – Extract entities (NER)**

- **Input:** Articles that don’t have an `entities` field yet (from MongoDB).
- **Action:** Run spaCy NER on title + content; keep types ORG, PERSON, PRODUCT, GPE, MONEY, etc.; normalize (e.g. "Open AI" → "OpenAI"); store by type.
- **Output (stored in same doc as `entities`):**

| Type  | Case A              | Case B              |
|-------|---------------------|---------------------|
| ORG   | ["Microsoft", "OpenAI"] | ["OpenAI", "Nvidia"] |
| MONEY | ["$10 billion"]     | (none)              |

---

**Step 4 – Extract triples (Gemini)**

- **Input:** Articles with `triples_extracted != true`; text = title + content.
- **Action:** Send text to Gemini; get (subject, relation, object, confidence); filter by confidence (e.g. ≥ 0.8); store in MongoDB `triples` collection and set `triples_extracted: true` on the article.
- **Output (in `triples` collection, one doc per article):**

| Article (Case A)      | subject   | relation    | object  | confidence |
|------------------------|-----------|-------------|--------|------------|
| (article_id for A)     | Microsoft | INVESTED_IN | OpenAI | 0.95       |

| Article (Case B)      | subject | relation       | object  | confidence |
|------------------------|---------|----------------|---------|------------|
| (article_id for B)     | OpenAI  | PARTNERED_WITH | Nvidia  | 0.92       |

---

**Step 5 – Build knowledge graph (Neo4j)**

- **Input:** All documents in the `triples` collection.
- **Action:** For each triple: create/merge nodes for subject and object (label `Entity`), create relationship with type (e.g. INVESTED_IN, PARTNERED_WITH). Node names normalized.
- **Output (in Neo4j):**

| Case A in graph      | Case B in graph       |
|----------------------|------------------------|
| (Microsoft)-[:INVESTED_IN]->(OpenAI) | (OpenAI)-[:PARTNERED_WITH]->(Nvidia) |

Combined graph: **Microsoft → INVESTED_IN → OpenAI → PARTNERED_WITH → Nvidia** (so multi-hop queries like “Who collaborates with companies funded by Microsoft?” can traverse Microsoft → OpenAI → Nvidia).

---

**Step 6 – Embed documents (ChromaDB)**

- **Input:** Articles with `embedded != true`.
- **Action:** Concatenate title + content, chunk (e.g. size 300, overlap 50), embed each chunk with sentence-transformers, store in ChromaDB with metadata (article_id, source, title), set `embedded: true` on the article.
- **Output:**

| Case A                         | Case B                          |
|--------------------------------|----------------------------------|
| 1+ chunks (e.g. "Microsoft announced a $10 billion...") | 1+ chunks (e.g. "OpenAI has formed a strategic...") |
| Each chunk: vector (384-dim) + metadata | Same                               |

ChromaDB is used for semantic search; Neo4j is used for graph traversal. Together they feed the multi-hop reasoner and answer generator.

---

## 💻 Usage

### Streamlit UI

1. Open http://localhost:8501
2. Enter your question
3. View:
   - Interactive knowledge graph visualization
   - Answer with reasoning path
   - Source articles

### FastAPI

1. API Docs: http://localhost:8000/docs
2. Query endpoint:

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which companies collaborate with organizations funded by Microsoft?",
    "graph_depth": 3,
    "top_k_vector": 5
  }'
```

### MongoDB Tables

browse for: mongodb://localhost:27017

open the respective connections.

### Neo4J Graphs:

browse to :

RUN Query:
```
   MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50
```


### Python SDK

```python
from reasoning.multihop import MultiHopReasoner
from generation.answer_generator import AnswerGenerator

# Initialize
reasoner = MultiHopReasoner()
generator = AnswerGenerator()

# Query
query = "Which companies collaborate with organizations funded by Microsoft?"
context = reasoner.retrieve_context(query)
formatted_context = reasoner.format_context_for_llm(context)

# Generate answer
result = generator.generate_query_result(query, context, formatted_context)

print(result.answer)
print(result.reasoning_path)
```

## 📈 Evaluation

Compare GraphRAG vs Standard RAG vs Plain LLM:

```bash
python -m evaluation.benchmark
```

This evaluates:
- **Exact Match (EM)**
- **F1 Score**
- **LLM-as-Judge** faithfulness
- **Multi-hop reasoning accuracy**

## 🗂️ Project Structure

```
graphrag-project/
├── config/              # Settings, models, logging
├── ingestion/           # Data loading & preprocessing
├── extraction/          # NER & triple extraction
├── graph/               # Neo4j client & graph builder
├── vector/              # Embeddings & ChromaDB
├── retrieval/           # Query processing & retrieval
├── reasoning/           # Multi-hop reasoning
├── generation/          # Answer generation
├── evaluation/          # Benchmarking
├── app/                 # FastAPI + Streamlit
├── scripts/             # Orchestration scripts
├── tests/               # Unit tests
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 🔧 Configuration

Key settings in `.env`:

```bash
# Graph traversal depth (1-5)
GRAPH_TRAVERSAL_DEPTH=3

# Number of vector results
TOP_K_VECTOR=5

# Chunk size for embeddings
CHUNK_SIZE=300
CHUNK_OVERLAP=50

# Triple confidence threshold
CONFIDENCE_THRESHOLD=0.8
```

## 📊 Example Queries

### 2-Hop Reasoning
**Q:** What is the relationship between OpenAI and Nvidia?  
**A:** Microsoft invested in OpenAI, and OpenAI partnered with Nvidia.

### 3-Hop Reasoning
**Q:** Which companies collaborate with organizations funded by Microsoft?  
**A:** Microsoft → OpenAI → Nvidia partnership

### Multi-Entity
**Q:** What partnerships involve companies working with Google?  
**A:** [Traverses graph to find multi-hop partnerships]

## 🐛 Troubleshooting

### Neo4j Connection Failed
```bash
# Check Neo4j is running
docker-compose ps neo4j

# View logs
docker-compose logs neo4j
```

### Gemini API Errors
- Verify API key in `.env`
- Check rate limits
- Ensure billing is enabled

### spaCy Model Missing
```bash
python -m spacy download en_core_web_sm
```

## 📝 API Documentation

FastAPI auto-generated docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Test specific module
pytest tests/test_graph.py
```

## 🔒 Security Notes

- Never commit `.env` file
- Use environment variables for secrets
- Neo4j password should be strong
- API rate limiting recommended for production

## 📚 Key Features

✅ Multi-hop reasoning with knowledge graphs  
✅ Hybrid retrieval (graph + vector)  
✅ Entity normalization & deduplication  
✅ Confidence-based triple filtering  
✅ Interactive graph visualization  
✅ REST API + Python SDK  
✅ Docker deployment  
✅ Comprehensive evaluation framework  

## 🎓 Citations

Based on research in:
- GraphRAG (Microsoft Research)
- Knowledge Graph RAG
- Multi-hop Question Answering

## 📄 License

MIT License

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Submit a pull request

## 📧 Contact

For questions or support, open an issue on GitHub.

---

**Built with ❤️ for multi-hop reasoning over Tech & AI news**