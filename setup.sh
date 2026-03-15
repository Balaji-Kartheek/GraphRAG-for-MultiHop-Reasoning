#!/bin/bash

# GraphRAG System Setup Script
# Run this after: docker-compose up -d

set -e

echo "=========================================="
echo "GraphRAG System Setup & Verification"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo "  Creating from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please edit .env and add your GEMINI_API_KEY${NC}"
    echo "  Then run this script again."
    exit 1
fi

# Check if Gemini API key is set
if grep -q "your_gemini_api_key_here" .env; then
    echo -e "${RED}✗ Gemini API key not configured${NC}"
    echo -e "${YELLOW}⚠ Please edit .env and add your actual GEMINI_API_KEY${NC}"
    exit 1
fi

echo "Step 1: Testing database connections..."
echo "----------------------------------------"
docker-compose exec -T graphrag_app python test_connections.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All connections successful${NC}"
else
    echo -e "${RED}✗ Connection tests failed${NC}"
    exit 1
fi

echo ""
echo "Step 2: Generating sample dataset..."
echo "----------------------------------------"
docker-compose exec -T graphrag_app python scripts/generate_sample_data.py

echo ""
echo "Step 3: Running pipeline (limited to 20 articles for quick setup)..."
echo "----------------------------------------"
docker-compose exec -T graphrag_app python scripts/run_pipeline.py \
    --dataset ./data/sample_tech_news.csv \
    --limit 20

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "🌐 Access Points:"
echo "  • Streamlit UI:  http://localhost:8501"
echo "  • FastAPI Docs:  http://localhost:8000/docs"
echo "  • Neo4j Browser: http://localhost:7474"
echo ""
echo "📝 Try These Queries:"
echo "  • Which companies collaborate with organizations funded by Microsoft?"
echo "  • What partnerships does OpenAI have?"
echo "  • Show me investments in AI companies"
echo ""
echo "📚 Next Steps:"
echo "  • Open Streamlit UI and try queries"
echo "  • Run evaluation: docker-compose exec graphrag_app python -m evaluation.benchmark"
echo "  • Add more data: docker-compose exec graphrag_app python scripts/run_pipeline.py --dataset your_data.csv"
echo ""