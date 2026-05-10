"""
Answer generation module
Uses configured LLM backend to generate answers from retrieved context
"""
import google.generativeai as genai
import requests
from typing import Dict, Any, List
from config.settings import settings
from config.logger import log
from config.models import QueryResult, RetrievalContext
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception


def _should_retry_generate(exc: Exception) -> bool:
    """Retry only for transient non-quota errors."""
    return not AnswerGenerator._is_rate_limit_error(exc)


class AnswerGenerator:
    """Generate answers using configured LLM provider"""
    
    def __init__(self):
        """Initialize configured LLM backend"""
        self.provider = (settings.llm_provider or "ollama").lower()
        self.model = None
        self.ollama_generate_url = settings.ollama_base_url.rstrip("/") + "/api/generate"

        if self.provider == "gemini":
            if not settings.gemini_api_key:
                log.warning("Gemini API key not set")
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
            log.info(f"AnswerGenerator initialized with Gemini ({settings.gemini_model})")
        else:
            # Default path: Ollama-first
            self.provider = "ollama"
            log.info(
                f"AnswerGenerator initialized with Ollama ({settings.ollama_model}) "
                f"at {settings.ollama_base_url}"
            )

    @staticmethod
    def _chunk_get(chunk: Any, key: str, default=None):
        """Read field from either dict chunk or Pydantic model chunk."""
        if isinstance(chunk, dict):
            return chunk.get(key, default)
        return getattr(chunk, key, default)

    def _chunk_source(self, chunk: Any) -> str:
        """Resolve source from top-level field or metadata fallback."""
        source = self._chunk_get(chunk, "source")
        if source:
            return source
        metadata = self._chunk_get(chunk, "metadata", {}) or {}
        return metadata.get("source", "Unknown")
    
    @staticmethod
    def has_sufficient_context(context: RetrievalContext) -> bool:
        """Return False when there is no graph or vector data to answer from."""
        has_graph = bool(context.graph_paths)
        has_vector = bool(context.vector_results)
        return has_graph or has_vector
    
    def create_prompt(self, query: str, context: str) -> str:
        """
        Create prompt for answer generation
        
        Instructs model to use context and show reasoning
        """
        prompt = f"""You are an expert AI assistant specialized in analyzing Tech & AI industry news using knowledge graphs and semantic search.

User Question:
{query}

Context Information:
{context}

Instructions:
1. Answer the question using ONLY the provided context (graph paths and documents)
2. Show your reasoning by explaining which graph paths and documents support your answer
3. If the context contains graph paths, explain the multi-hop reasoning chain
4. Cite specific sources (article IDs) that support your answer
5. If the context is insufficient or empty, you MUST say clearly: "I don't have enough information in the knowledge base to answer this question." Do not guess or make up facts.
6. Be concise but thorough

Output Format:
Answer: [Your answer here]

Reasoning Path:
[Explain the logical reasoning using graph paths and documents]

Supporting Evidence:
[List specific graph paths and document excerpts with article IDs]

Source Articles:
[List article IDs used in your answer]

Now provide your response:"""
        
        return prompt

    @staticmethod
    def _is_rate_limit_error(err: Exception) -> bool:
        """Detect Gemini quota/rate-limit errors from wrapped exceptions."""
        current = err
        # Unwrap common nested exceptions (e.g., tenacity RetryError -> RuntimeError cause)
        while current is not None:
            msg = str(current).lower()
            if (
                "429" in msg
                or "resourceexhausted" in msg
                or "quota" in msg
                or "rate limit" in msg
                or "retryerror" in msg
            ):
                return True
            current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
        return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_should_retry_generate),
    )
    def generate_answer(
        self, 
        query: str,
        formatted_context: str
    ) -> str:
        """
        Generate answer using configured provider
        
        Returns generated answer text
        """
        prompt = self.create_prompt(query, formatted_context)
        
        try:
            if self.provider == "ollama":
                answer = self._generate_answer_ollama(prompt)
            else:
                response = self.model.generate_content(prompt)
                answer = response.text.strip()
            
            log.info("Generated answer successfully")
            return answer
            
        except Exception as e:
            if self.provider == "gemini" and self._is_rate_limit_error(e):
                # Surface a clean, handled signal to caller so API doesn't fail with 500.
                log.warning(f"Gemini rate limit/quota reached while generating answer: {e}")
                raise RuntimeError("GEMINI_RATE_LIMIT") from e
            log.error(f"Error generating answer using {self.provider}: {e}")
            raise

    def _generate_answer_ollama(self, prompt: str) -> str:
        """Generate answer from local Ollama model."""
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        response = requests.post(self.ollama_generate_url, json=payload, timeout=180)
        response.raise_for_status()
        body = response.json()
        text = (body.get("response") or "").strip()
        if not text:
            raise RuntimeError("OLLAMA_EMPTY_RESPONSE")
        return text
    
    def parse_answer_response(self, answer_text: str) -> Dict[str, Any]:
        """
        Parse structured answer from Gemini response
        
        Extracts answer, reasoning, and sources
        """
        sections = {
            "answer": "",
            "reasoning_path": "",
            "supporting_evidence": "",
            "source_articles": []
        }
        
        current_section = None
        
        for line in answer_text.split("\n"):
            line_lower = line.lower().strip()
            
            # Detect section headers
            if line_lower.startswith("answer:"):
                current_section = "answer"
                sections["answer"] = line.split(":", 1)[1].strip() if ":" in line else ""
            elif "reasoning path" in line_lower:
                current_section = "reasoning_path"
            elif "supporting evidence" in line_lower:
                current_section = "supporting_evidence"
            elif "source article" in line_lower:
                current_section = "source_articles"
            elif current_section and line.strip():
                # Add content to current section
                if current_section == "source_articles":
                    # Extract article IDs
                    if line.strip().startswith("-") or line.strip().startswith("*"):
                        article_id = line.strip()[1:].strip()
                        sections["source_articles"].append(article_id)
                else:
                    sections[current_section] += line + "\n"
        
        return sections
    
    def generate_query_result(
        self, 
        query: str,
        context: RetrievalContext,
        formatted_context: str
    ) -> QueryResult:
        """
        Main method: generate complete query result
        
        Returns QueryResult object. When no context is available, returns a safe
        "insufficient context" result without calling the LLM.
        """
        log.info(f"Generating answer for query: {query}")
        
        # No graph paths and no vector results: return safe result, no LLM call
        if not self.has_sufficient_context(context):
            log.warning("No context retrieved; returning insufficient_context result")
            return QueryResult(
                answer=(
                    "I don't have enough information in the knowledge base to answer this question. "
                    "No relevant graph paths or documents were found. Try rephrasing your query, "
                    "or the topic may not be covered in the ingested articles."
                ),
                reasoning_path=[],
                source_articles=[],
                graph_paths=[],
                insufficient_context=True
            )
        
        # Generate answer with LLM
        try:
            answer_text = self.generate_answer(query, formatted_context)
        except Exception as e:
            if self._is_rate_limit_error(e):
                # Graceful fallback: return context-backed response without hard failing.
                log.warning("Returning fallback answer due to Gemini quota/rate limit.")
                source_articles = []
                article_ids = set()
                for chunk in context.vector_results:
                    article_id = self._chunk_get(chunk, "article_id")
                    if article_id and article_id not in article_ids:
                        article_ids.add(article_id)
                        source_articles.append({
                            "article_id": article_id,
                            "source": self._chunk_source(chunk),
                            "title": self._chunk_get(chunk, "metadata", {}).get("title", "")[:100]
                        })

                reasoning_path = []
                for path in context.graph_paths[:5]:
                    reasoning_path.append(" -> ".join(path.nodes))

                return QueryResult(
                    answer=(
                        "I found relevant context, but answer generation is temporarily limited "
                        "because the Gemini quota/rate limit was reached. "
                        "Please retry later, reduce query frequency, or increase API quota."
                    ),
                    reasoning_path=reasoning_path,
                    source_articles=source_articles,
                    graph_paths=[[node for node in path.nodes] for path in context.graph_paths[:5]],
                    insufficient_context=False
                )
            log.warning(f"Returning fallback answer due to {self.provider} generation error: {e}")
            source_articles = []
            article_ids = set()
            for chunk in context.vector_results:
                article_id = self._chunk_get(chunk, "article_id")
                if article_id and article_id not in article_ids:
                    article_ids.add(article_id)
                    source_articles.append({
                        "article_id": article_id,
                        "source": self._chunk_source(chunk),
                        "title": self._chunk_get(chunk, "metadata", {}).get("title", "")[:100]
                    })

            reasoning_path = []
            for path in context.graph_paths[:5]:
                reasoning_path.append(" -> ".join(path.nodes))

            return QueryResult(
                answer=(
                    f"I found relevant context, but answer generation is temporarily unavailable "
                    f"on the configured {self.provider} backend. "
                    "Please verify the model service is running and retry."
                ),
                reasoning_path=reasoning_path,
                source_articles=source_articles,
                graph_paths=[[node for node in path.nodes] for path in context.graph_paths[:5]],
                insufficient_context=False
            )
        
        # Parse response
        parsed = self.parse_answer_response(answer_text)
        
        # Extract reasoning path
        reasoning_path = []
        if context.graph_paths:
            # Include graph path descriptions
            for path in context.graph_paths[:5]:
                path_str = " -> ".join(path.nodes)
                reasoning_path.append(path_str)
        
        # Also add reasoning from LLM
        if parsed["reasoning_path"]:
            reasoning_path.append(parsed["reasoning_path"].strip())
        
        # Extract source articles
        source_articles = []
        article_ids = set()
        
        # From vector results
        for chunk in context.vector_results:
            article_id = self._chunk_get(chunk, "article_id")
            if article_id and article_id not in article_ids:
                article_ids.add(article_id)
                source_articles.append({
                    "article_id": article_id,
                    "source": self._chunk_source(chunk),
                    "title": self._chunk_get(chunk, "metadata", {}).get("title", "")[:100]
                })
        
        # Create QueryResult
        result = QueryResult(
            answer=parsed["answer"] or answer_text,
            reasoning_path=reasoning_path,
            source_articles=source_articles,
            graph_paths=[[node for node in path.nodes] for path in context.graph_paths[:5]],
            insufficient_context=False
        )
        
        log.info("Query result generated successfully")
        return result
    
    def format_query_result(self, result: QueryResult) -> str:
        """
        Format QueryResult for display
        
        Returns formatted string
        """
        formatted = "=" * 80 + "\n"
        formatted += "QUERY RESULT\n"
        formatted += "=" * 80 + "\n\n"
        
        # Answer
        formatted += "ANSWER:\n"
        formatted += result.answer + "\n\n"
        
        # Reasoning Path
        formatted += "=" * 80 + "\n"
        formatted += "REASONING PATH:\n"
        formatted += "=" * 80 + "\n"
        for i, step in enumerate(result.reasoning_path, 1):
            formatted += f"{i}. {step}\n"
        formatted += "\n"
        
        # Graph Paths
        if result.graph_paths:
            formatted += "=" * 80 + "\n"
            formatted += "KNOWLEDGE GRAPH PATHS:\n"
            formatted += "=" * 80 + "\n"
            for i, path in enumerate(result.graph_paths, 1):
                formatted += f"{i}. {' -> '.join(path)}\n"
            formatted += "\n"
        
        # Source Articles
        formatted += "=" * 80 + "\n"
        formatted += "SOURCE ARTICLES:\n"
        formatted += "=" * 80 + "\n"
        for i, article in enumerate(result.source_articles, 1):
            formatted += f"{i}. Article ID: {article['article_id']}\n"
            formatted += f"   Source: {article['source']}\n"
            if article.get('title'):
                formatted += f"   Title: {article['title']}\n"
            formatted += "\n"
        
        return formatted


if __name__ == "__main__":
    # Example usage
    from reasoning.multihop import MultiHopReasoner
    
    # Initialize
    reasoner = MultiHopReasoner()
    generator = AnswerGenerator()
    
    # Test query
    query = "Which companies collaborate with organizations funded by Microsoft?"
    
    print(f"Query: {query}\n")
    
    # Get context
    context = reasoner.retrieve_context(query)
    formatted_context = reasoner.format_context_for_llm(context)
    
    # Generate answer
    result = generator.generate_query_result(query, context, formatted_context)
    
    # Display result
    output = generator.format_query_result(result)
    print(output)
    
    reasoner.close()