"""
Evaluation module for GraphRAG system.
Compares GraphRAG vs Standard RAG with deterministic metrics.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import json
import re
import time

from reasoning.multihop import MultiHopReasoner
from generation.answer_generator import AnswerGenerator
from retrieval.vector_retrieval import VectorRetriever
from config.models import RetrievalContext, DocumentChunk
from config.logger import log


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b[a-z0-9]+\b", _normalize(text))


def exact_match(pred: str, truth: str) -> float:
    return 1.0 if _normalize(pred) == _normalize(truth) else 0.0


def token_f1(pred: str, truth: str) -> float:
    pred_tokens = _tokenize(pred)
    truth_tokens = _tokenize(truth)
    if not pred_tokens or not truth_tokens:
        return 0.0
    pred_set, truth_set = set(pred_tokens), set(truth_tokens)
    overlap = len(pred_set.intersection(truth_set))
    if overlap == 0:
        return 0.0
    precision = overlap / max(len(pred_set), 1)
    recall = overlap / max(len(truth_set), 1)
    return 2 * precision * recall / (precision + recall)


@dataclass
class EvalRow:
    question: str
    ground_truth: str
    graphrag_answer: str
    rag_answer: str
    graphrag_f1: float
    rag_f1: float
    graphrag_sources: int
    rag_sources: int
    graphrag_latency_ms: int
    rag_latency_ms: int


class GraphRAGEvaluator:
    """Evaluate GraphRAG against a vector-only RAG baseline."""

    def __init__(self):
        self.reasoner = MultiHopReasoner()
        self.generator = AnswerGenerator()
        self.vector_retriever = VectorRetriever()
        log.info("GraphRAGEvaluator initialized")

    @staticmethod
    def _to_document_chunks(vector_chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
        docs = []
        for c in vector_chunks:
            docs.append(
                DocumentChunk(
                    chunk_id=c.get("chunk_id", ""),
                    text=c.get("text", ""),
                    article_id=c.get("article_id", ""),
                    chunk_index=c.get("chunk_index", 0),
                    metadata=c.get("metadata", {}) or {},
                )
            )
        return docs

    def _answer_graphrag(self, question: str) -> Dict[str, Any]:
        t0 = time.time()
        context = self.reasoner.retrieve_context(question)
        formatted = self.reasoner.format_context_for_llm(context)
        result = self.generator.generate_query_result(question, context, formatted)
        elapsed_ms = int((time.time() - t0) * 1000)
        return {"answer": result.answer, "sources": len(result.source_articles), "latency_ms": elapsed_ms}

    def _answer_standard_rag(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        t0 = time.time()
        vector_chunks = self.vector_retriever.retrieve_similar_chunks(question, top_k=top_k)
        context = RetrievalContext(
            graph_paths=[],
            vector_results=self._to_document_chunks(vector_chunks),
            entities_detected=[],
        )
        formatted = self.reasoner.format_context_for_llm(context)
        result = self.generator.generate_query_result(question, context, formatted)
        elapsed_ms = int((time.time() - t0) * 1000)
        return {"answer": result.answer, "sources": len(result.source_articles), "latency_ms": elapsed_ms}

    def evaluate_dataset(self, questions: List[Dict[str, str]]) -> Dict[str, Any]:
        rows: List[EvalRow] = []
        for item in questions:
            question = item["question"]
            truth = item["ground_truth"]
            log.info(f"Evaluating question: {question}")
            try:
                gr = self._answer_graphrag(question)
                rg = self._answer_standard_rag(question)
                rows.append(
                    EvalRow(
                        question=question,
                        ground_truth=truth,
                        graphrag_answer=gr["answer"],
                        rag_answer=rg["answer"],
                        graphrag_f1=token_f1(gr["answer"], truth),
                        rag_f1=token_f1(rg["answer"], truth),
                        graphrag_sources=gr["sources"],
                        rag_sources=rg["sources"],
                        graphrag_latency_ms=gr["latency_ms"],
                        rag_latency_ms=rg["latency_ms"],
                    )
                )
            except Exception as e:
                log.error(f"Evaluation failed for question '{question}': {e}")

        total = len(rows)
        if total == 0:
            return {"total_questions": 0, "rows": [], "summary": {}}

        def avg(vals: List[float]) -> float:
            return sum(vals) / len(vals)

        graphrag_f1_vals = [r.graphrag_f1 for r in rows]
        rag_f1_vals = [r.rag_f1 for r in rows]

        graph_wins = sum(1 for r in rows if r.graphrag_f1 > r.rag_f1)

        summary = {
            "graphrag_avg_f1": avg(graphrag_f1_vals),
            "rag_avg_f1": avg(rag_f1_vals),
            "graphrag_avg_latency_ms": avg([r.graphrag_latency_ms for r in rows]),
            "rag_avg_latency_ms": avg([r.rag_latency_ms for r in rows]),
            "graphrag_avg_sources": avg([r.graphrag_sources for r in rows]),
            "rag_avg_sources": avg([r.rag_sources for r in rows]),
            "graphrag_win_rate": graph_wins / total,
        }

        return {
            "total_questions": total,
            "summary": summary,
            "rows": [asdict(r) for r in rows],
        }

    def save_results(self, report: Dict[str, Any], filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        log.info(f"Saved evaluation report to {filepath}")

    def close(self):
        self.reasoner.close()
        self.vector_retriever.close()


if __name__ == "__main__":
    evaluator = GraphRAGEvaluator()
    test_questions = [
        {
            "question": "Which companies collaborate with organizations funded by Microsoft?",
            "ground_truth": "Microsoft funded OpenAI, and OpenAI collaborated with Nvidia.",
        },
        {
            "question": "Which companies formed a strategic partnership on AI development?",
            "ground_truth": "Oracle and Cohere formed a strategic partnership on AI development.",
        },
    ]
    report = evaluator.evaluate_dataset(test_questions)
    print(json.dumps(report["summary"], indent=2))
    evaluator.save_results(report, "evaluation_results.json")
    evaluator.close()