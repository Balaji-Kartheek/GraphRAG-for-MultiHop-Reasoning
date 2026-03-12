"""
Evaluation module for GraphRAG system
Compares GraphRAG vs Standard RAG vs Plain LLM
"""
from typing import List, Dict, Any, Tuple
import json
from dataclasses import dataclass
import google.generativeai as genai
from reasoning.multihop import MultiHopReasoner
from generation.answer_generator import AnswerGenerator
from vector.chroma_client import ChromaClient
from config.settings import settings
from config.logger import log


@dataclass
class EvaluationResult:
    """Evaluation result for a single question"""
    question: str
    ground_truth: str
    graphrag_answer: str
    standard_rag_answer: str
    plain_llm_answer: str
    graphrag_score: float
    standard_rag_score: float
    plain_llm_score: float


class GraphRAGEvaluator:
    """Evaluate GraphRAG performance"""
    
    def __init__(self):
        """Initialize evaluation components"""
        self.reasoner = MultiHopReasoner()
        self.generator = AnswerGenerator()
        self.chroma_client = ChromaClient()
        
        genai.configure(api_key=settings.gemini_api_key)
        self.judge_model = genai.GenerativeModel(settings.gemini_model)
        
        log.info("GraphRAGEvaluator initialized")
    
    def graphrag_answer(self, question: str) -> str:
        """
        Get answer using full GraphRAG pipeline
        
        Graph + Vector retrieval
        """
        # Retrieve context
        context = self.reasoner.retrieve_context(question)
        formatted_context = self.reasoner.format_context_for_llm(context)
        
        # Generate answer
        result = self.generator.generate_query_result(
            question,
            context,
            formatted_context
        )
        
        return result.answer
    
    def standard_rag_answer(self, question: str) -> str:
        """
        Get answer using standard RAG (vector only)
        
        No graph retrieval
        """
        # Vector retrieval only
        chunks = self.chroma_client.query(question, n_results=5)
        
        # Format context
        context = "Retrieved Documents:\n\n"
        for i, doc in enumerate(chunks["documents"], 1):
            context += f"Document {i}: {doc}\n\n"
        
        # Generate answer
        prompt = f"""Answer the following question using only the provided documents.

Question: {question}

{context}

Answer:"""
        
        response = self.judge_model.generate_content(prompt)
        return response.text.strip()
    
    def plain_llm_answer(self, question: str) -> str:
        """
        Get answer using plain LLM (no retrieval)
        
        Knowledge from training data only
        """
        prompt = f"""Answer the following question based on your knowledge.

Question: {question}

Answer:"""
        
        response = self.judge_model.generate_content(prompt)
        return response.text.strip()
    
    def llm_as_judge_score(
        self, 
        question: str, 
        answer: str, 
        ground_truth: str
    ) -> float:
        """
        Use LLM to judge answer quality
        
        Returns score 0-1
        """
        prompt = f"""You are an expert evaluator. Score the answer based on:
1. Factual accuracy compared to ground truth
2. Completeness
3. Relevance to the question

Question: {question}

Ground Truth: {ground_truth}

Answer to Evaluate: {answer}

Provide a score from 0.0 to 1.0 where:
- 1.0 = Perfect answer, matches ground truth
- 0.7-0.9 = Good answer, mostly correct
- 0.4-0.6 = Partial answer, some errors
- 0.0-0.3 = Poor answer, mostly incorrect

Return ONLY the numeric score as a decimal number (e.g., 0.85)"""
        
        try:
            response = self.judge_model.generate_content(prompt)
            score_text = response.text.strip()
            
            # Extract numeric score
            score = float(score_text)
            return max(0.0, min(1.0, score))
        except:
            log.warning(f"Failed to parse score, using 0.0")
            return 0.0
    
    def evaluate_question(
        self, 
        question: str, 
        ground_truth: str
    ) -> EvaluationResult:
        """
        Evaluate a single question with all three methods
        """
        log.info(f"Evaluating question: {question}")
        
        # Get answers from all three methods
        graphrag_ans = self.graphrag_answer(question)
        standard_rag_ans = self.standard_rag_answer(question)
        plain_llm_ans = self.plain_llm_answer(question)
        
        # Score each answer
        graphrag_score = self.llm_as_judge_score(question, graphrag_ans, ground_truth)
        standard_rag_score = self.llm_as_judge_score(question, standard_rag_ans, ground_truth)
        plain_llm_score = self.llm_as_judge_score(question, plain_llm_ans, ground_truth)
        
        result = EvaluationResult(
            question=question,
            ground_truth=ground_truth,
            graphrag_answer=graphrag_ans,
            standard_rag_answer=standard_rag_ans,
            plain_llm_answer=plain_llm_ans,
            graphrag_score=graphrag_score,
            standard_rag_score=standard_rag_score,
            plain_llm_score=plain_llm_score
        )
        
        log.info(f"Scores - GraphRAG: {graphrag_score:.2f}, Standard RAG: {standard_rag_score:.2f}, Plain LLM: {plain_llm_score:.2f}")
        
        return result
    
    def evaluate_dataset(
        self, 
        questions: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Evaluate a dataset of questions
        
        Args:
            questions: List of dicts with 'question' and 'ground_truth'
        
        Returns:
            Evaluation summary with scores
        """
        results = []
        
        for item in questions:
            try:
                result = self.evaluate_question(
                    item["question"],
                    item["ground_truth"]
                )
                results.append(result)
            except Exception as e:
                log.error(f"Error evaluating question: {e}")
        
        # Calculate aggregate metrics
        avg_graphrag = sum(r.graphrag_score for r in results) / len(results)
        avg_standard_rag = sum(r.standard_rag_score for r in results) / len(results)
        avg_plain_llm = sum(r.plain_llm_score for r in results) / len(results)
        
        summary = {
            "total_questions": len(results),
            "avg_scores": {
                "graphrag": avg_graphrag,
                "standard_rag": avg_standard_rag,
                "plain_llm": avg_plain_llm
            },
            "improvement": {
                "vs_standard_rag": ((avg_graphrag - avg_standard_rag) / avg_standard_rag * 100),
                "vs_plain_llm": ((avg_graphrag - avg_plain_llm) / avg_plain_llm * 100)
            },
            "results": results
        }
        
        return summary
    
    def save_results(self, summary: Dict[str, Any], filepath: str):
        """Save evaluation results to file"""
        # Convert dataclass to dict
        results_dict = []
        for result in summary["results"]:
            results_dict.append({
                "question": result.question,
                "ground_truth": result.ground_truth,
                "answers": {
                    "graphrag": result.graphrag_answer,
                    "standard_rag": result.standard_rag_answer,
                    "plain_llm": result.plain_llm_answer
                },
                "scores": {
                    "graphrag": result.graphrag_score,
                    "standard_rag": result.standard_rag_score,
                    "plain_llm": result.plain_llm_score
                }
            })
        
        output = {
            "summary": {
                "total_questions": summary["total_questions"],
                "avg_scores": summary["avg_scores"],
                "improvement": summary["improvement"]
            },
            "results": results_dict
        }
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        log.info(f"Results saved to {filepath}")
    
    def close(self):
        """Close connections"""
        self.reasoner.close()
        self.chroma_client.close()


if __name__ == "__main__":
    # Example evaluation
    evaluator = GraphRAGEvaluator()
    
    # Sample multi-hop questions
    test_questions = [
        {
            "question": "Which companies collaborate with organizations funded by Microsoft?",
            "ground_truth": "OpenAI partners with Nvidia, and Microsoft funded OpenAI."
        },
        {
            "question": "What partnerships involve companies that invested in AI startups?",
            "ground_truth": "Microsoft invested in OpenAI, which partnered with Nvidia."
        }
    ]
    
    # Run evaluation
    summary = evaluator.evaluate_dataset(test_questions)
    
    print("\n" + "="*80)
    print("EVALUATION SUMMARY")
    print("="*80)
    print(f"Total Questions: {summary['total_questions']}")
    print(f"\nAverage Scores:")
    print(f"  GraphRAG:      {summary['avg_scores']['graphrag']:.3f}")
    print(f"  Standard RAG:  {summary['avg_scores']['standard_rag']:.3f}")
    print(f"  Plain LLM:     {summary['avg_scores']['plain_llm']:.3f}")
    print(f"\nImprovement:")
    print(f"  vs Standard RAG: +{summary['improvement']['vs_standard_rag']:.1f}%")
    print(f"  vs Plain LLM:    +{summary['improvement']['vs_plain_llm']:.1f}%")
    
    # Save results
    evaluator.save_results(summary, "evaluation_results.json")
    
    evaluator.close()