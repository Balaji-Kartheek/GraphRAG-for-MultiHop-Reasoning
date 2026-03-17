"""
End-to-end pipeline orchestration
Runs the complete GraphRAG pipeline from data ingestion to graph building
"""
import sys
import argparse
from pathlib import Path

# Ensure project root is on path when run as python scripts/run_pipeline.py
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from ingestion.fetch_articles import ArticleIngestion
from ingestion.preprocess import ArticlePreprocessor
from extraction.ner import EntityExtractor
from extraction.triple_extractor import TripleExtractor
from graph.graph_builder import GraphBuilder
from vector.chroma_client import ChromaClient
from config.logger import log


def run_full_pipeline(
    dataset_path: str = None,
    source: str = "csv",
    limit: int = None,
    skip_steps: list = None
):
    """
    Run the complete GraphRAG pipeline.

    Args:
        dataset_path: Path to CSV dataset (required when source=csv).
        source: "csv" = load from CSV, "fetch" = load from RSS/News API.
        limit: Limit number of articles to process.
        skip_steps: List of steps to skip.
    """
    skip_steps = skip_steps or []

    log.info("=" * 80)
    log.info("STARTING GRAPHRAG PIPELINE")
    log.info("=" * 80)

    # Step 1: Ingest Articles
    if "ingest" not in skip_steps:
        ingestion = ArticleIngestion()
        if source == "fetch":
            log.info("\n[STEP 1/6] Ingesting articles from fetchers (RSS/News API)...")
            count = ingestion.load_from_fetchers(limit)
        else:
            log.info("\n[STEP 1/6] Ingesting articles from dataset...")
            count = ingestion.load_from_csv(dataset_path, limit)
        log.info(f"✓ Ingested {count} articles")
        ingestion.close()
    else:
        log.info("\n[STEP 1/6] Skipping ingestion")
    
    # Step 2: Preprocess
    if "preprocess" not in skip_steps:
        log.info("\n[STEP 2/6] Preprocessing articles...")
        preprocessor = ArticlePreprocessor()
        
        # Remove duplicates
        dup_count = preprocessor.remove_duplicates()
        log.info(f"✓ Removed {dup_count} duplicates")
        
        # Preprocess
        proc_count = preprocessor.preprocess_batch(limit)
        log.info(f"✓ Preprocessed {proc_count} articles")
        
        preprocessor.close()
    else:
        log.info("\n[STEP 2/6] Skipping preprocessing")
    
    # Step 3: Extract Entities
    if "entities" not in skip_steps:
        log.info("\n[STEP 3/6] Extracting named entities...")
        extractor = EntityExtractor()
        ent_count = extractor.extract_batch(limit)
        log.info(f"✓ Extracted entities from {ent_count} articles")
        
        stats = extractor.get_entity_stats()
        log.info(f"  Total unique entities: {stats['total_unique_entities']}")
        
        extractor.close()
    else:
        log.info("\n[STEP 3/6] Skipping entity extraction")
    
    # Step 4: Extract Triples
    if "triples" not in skip_steps:
        log.info("\n[STEP 4/6] Extracting knowledge triples...")
        triple_extractor = TripleExtractor()
        triple_count = triple_extractor.extract_batch(limit)
        log.info(f"✓ Extracted triples from {triple_count} articles")
        
        stats = triple_extractor.get_triple_stats()
        log.info(f"  Total triples: {stats['total_triples']}")
        
        triple_extractor.close()
    else:
        log.info("\n[STEP 4/6] Skipping triple extraction")
    
    # Step 5: Build Knowledge Graph
    if "graph" not in skip_steps:
        log.info("\n[STEP 5/6] Building knowledge graph...")
        graph_builder = GraphBuilder()
        graph_stats = graph_builder.build_full_graph(limit)
        log.info(f"✓ Built knowledge graph")
        log.info(f"  Nodes: {graph_stats['total_nodes']}")
        log.info(f"  Relationships: {graph_stats['total_relationships']}")
        
        graph_builder.close()
    else:
        log.info("\n[STEP 5/6] Skipping graph building")
    
    # Step 6: Embed Documents
    if "embed" not in skip_steps:
        log.info("\n[STEP 6/6] Embedding documents...")
        chroma_client = ChromaClient()
        embed_stats = chroma_client.embed_batch(limit)
        log.info(f"✓ Embedded documents")
        log.info(f"  Articles: {embed_stats['articles_embedded']}")
        log.info(f"  Chunks: {embed_stats['total_chunks']}")
        
        chroma_client.close()
    else:
        log.info("\n[STEP 6/6] Skipping embedding")
    
    log.info("\n" + "=" * 80)
    log.info("PIPELINE COMPLETE!")
    log.info("=" * 80)
    log.info("System is ready for queries.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GraphRAG Pipeline Orchestrator")
    parser.add_argument(
        "--source",
        type=str,
        choices=["csv", "fetch"],
        default="csv",
        help="Ingestion source: csv (from file) or fetch (RSS/News API)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to CSV dataset (required when --source csv)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of articles to process",
    )
    parser.add_argument(
        "--skip",
        type=str,
        nargs="+",
        default=[],
        choices=["ingest", "preprocess", "entities", "triples", "graph", "embed"],
        help="Steps to skip",
    )
    args = parser.parse_args()

    if args.source == "csv":
        if not args.dataset:
            log.error("--dataset is required when --source csv")
            sys.exit(1)
        if not Path(args.dataset).exists():
            log.error(f"Dataset not found: {args.dataset}")
            sys.exit(1)

    try:
        run_full_pipeline(
            dataset_path=args.dataset,
            source=args.source,
            limit=args.limit,
            skip_steps=args.skip,
        )
    except Exception as e:
        log.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()