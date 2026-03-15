"""
Test database connections
Verifies MongoDB, Neo4j, and ChromaDB connectivity
"""
import sys
from pymongo import MongoClient
from config.settings import settings
from config.logger import log
from graph.neo4j_client import Neo4jClient


def test_mongodb():
    """Test MongoDB connection"""
    try:
        client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        
        db = client[settings.mongodb_db]
        collection = db[settings.mongodb_collection]
        
        # Try to perform an operation
        collection.find_one()
        
        log.info("✓ MongoDB connection successful")
        client.close()
        return True
    except Exception as e:
        log.error(f"✗ MongoDB connection failed: {e}")
        return False


def test_neo4j():
    """Test Neo4j connection"""
    try:
        client = Neo4jClient()
        
        if client.verify_connection():
            log.info("✓ Neo4j connection successful")
            client.close()
            return True
        else:
            log.error("✗ Neo4j connection failed")
            return False
    except Exception as e:
        log.error(f"✗ Neo4j connection failed: {e}")
        return False


def test_chromadb():
    """Test ChromaDB initialization"""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        
        client = chromadb.Client(ChromaSettings(
            persist_directory=settings.chroma_persist_dir,
            anonymized_telemetry=False
        ))
        
        # Try to get or create collection
        collection = client.get_or_create_collection(
            name=settings.chroma_collection
        )
        
        log.info("✓ ChromaDB initialization successful")
        return True
    except Exception as e:
        log.error(f"✗ ChromaDB initialization failed: {e}")
        return False


def test_gemini():
    """Test Gemini API connection"""
    try:
        import google.generativeai as genai
        
        if not settings.gemini_api_key:
            log.warning("⚠ Gemini API key not set (optional for testing)")
            return True
        
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
        
        # Test with simple prompt
        response = model.generate_content("Say 'test'")
        
        log.info("✓ Gemini API connection successful")
        return True
    except Exception as e:
        log.error(f"✗ Gemini API connection failed: {e}")
        return False


def test_spacy():
    """Test spaCy model"""
    try:
        import spacy
        
        nlp = spacy.load("en_core_web_sm")
        doc = nlp("Test sentence")
        
        log.info("✓ spaCy model loaded successfully")
        return True
    except Exception as e:
        log.error(f"✗ spaCy model failed: {e}")
        log.error("   Run: python -m spacy download en_core_web_sm")
        return False


def test_sentence_transformers():
    """Test sentence-transformers model"""
    try:
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer(settings.embedding_model)
        embedding = model.encode("Test sentence")
        
        log.info(f"✓ Sentence-transformers model loaded (dim={len(embedding)})")
        return True
    except Exception as e:
        log.error(f"✗ Sentence-transformers failed: {e}")
        return False


def main():
    """Run all connection tests"""
    log.info("=" * 80)
    log.info("GraphRAG System - Connection Tests")
    log.info("=" * 80)
    
    tests = [
        ("MongoDB", test_mongodb),
        ("Neo4j", test_neo4j),
        ("ChromaDB", test_chromadb),
        ("Gemini API", test_gemini),
        ("spaCy", test_spacy),
        ("Sentence Transformers", test_sentence_transformers)
    ]
    
    results = {}
    
    for name, test_func in tests:
        log.info(f"\nTesting {name}...")
        results[name] = test_func()
    
    # Summary
    log.info("\n" + "=" * 80)
    log.info("Test Summary")
    log.info("=" * 80)
    
    passed = sum(results.values())
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        log.info(f"{name}: {status}")
    
    log.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        log.info("✓ All tests passed! System is ready.")
        return 0
    else:
        log.error(f"✗ {total - passed} test(s) failed. Please fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())