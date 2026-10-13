"""
rag_pipeline.py
The core Knowledge Graph RAG Pipeline orchestrating:
1. Natural language query reception
2. Cypher generation via local Ollama LLM
3. Cypher security & syntax validation
4. Read-only graph execution against Neo4j
5. Context formatting & grounding
6. Final answer generation via local Ollama LLM
"""

import time
import json
from typing import Dict, Any, List, Optional

from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from neo4j_connection import Neo4jConnection, get_neo4j_connection
from cypher_generator import CypherGenerator
from recommender import MovieRecommender
from prompts import ANSWER_GENERATION_SYSTEM_PROMPT, build_answer_prompt
from ollama_client import OllamaClient, get_ollama_client


class MovieGraphRAGPipeline:
    """End-to-end Graph RAG pipeline using Neo4j and a local Ollama LLM."""

    def __init__(
        self,
        connection: Optional[Neo4jConnection] = None,
        ollama_client: Optional[OllamaClient] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.connection = connection or get_neo4j_connection()
        self.model = model or OLLAMA_MODEL
        self.base_url = base_url or OLLAMA_BASE_URL
        self.ollama_client = ollama_client or OllamaClient(base_url=self.base_url, model=self.model)
        self.cypher_generator = CypherGenerator(ollama_client=self.ollama_client)
        self.recommender = MovieRecommender(connection=self.connection)

    def format_records_to_context(self, records: List[Dict[str, Any]]) -> str:
        """
        Transforms raw Neo4j record dictionaries into a clean, human-readable
        text context suitable for LLM grounding.
        """
        if not records:
            return "No matching records found in the movie knowledge graph."

        lines = []
        for i, record in enumerate(records, start=1):
            formatted_fields = []
            for key, val in record.items():
                if isinstance(val, list):
                    val_str = ", ".join(str(item) for item in val)
                elif isinstance(val, dict):
                    val_str = json.dumps(val)
                else:
                    val_str = str(val)
                formatted_fields.append(f"{key}: {val_str}")
            lines.append(f"Record {i} -> " + " | ".join(formatted_fields))

        return "\n".join(lines)

    def generate_grounded_answer(self, question: str, context: str) -> str:
        """
        Sends the user question and retrieved graph context to the local Ollama LLM
        to produce a grounded, natural-language answer.
        """
        # Strict fallback safeguard if no records were found
        if not context or context == "No matching records found in the movie knowledge graph.":
            return "I couldn't find enough information in the movie knowledge graph to answer that question."

        try:
            prompt_content = build_answer_prompt(question, context)
            messages = [
                {"role": "system", "content": ANSWER_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_content}
            ]
            response = self.ollama_client.chat(messages, temperature=0.1, max_tokens=600)
            return response or "No answer returned."
        except RuntimeError as e:
            return f"Ollama Error: {str(e)}"
        except Exception as e:
            return f"Error while generating final answer with Ollama: {str(e)}"

    def run(self, question: str) -> Dict[str, Any]:
        """
        Executes the full 10-step RAG pipeline:
        1. Validate input
        2. Generate Cypher via Ollama
        3. Validate Cypher
        4. Execute Cypher on Neo4j
        5. Format retrieved context
        6. Generate grounded answer via Ollama
        """
        start_time = time.time()
        pipeline_log = []

        result = {
            "question": question,
            "cypher_query": "",
            "raw_results": [],
            "context_text": "",
            "final_answer": "",
            "is_valid_cypher": False,
            "error": None,
            "execution_time_sec": 0.0,
            "pipeline_steps": []
        }

        # Step 1: Input Check
        clean_q = question.strip() if question else ""
        if not clean_q:
            result["error"] = "Please enter a valid question."
            result["final_answer"] = "No question was provided."
            return result

        pipeline_log.append("Step 1: Received user question.")

        # Step 2 & 3: Generate Cypher via Ollama
        pipeline_log.append("Step 2 & 3: Generating Cypher query using local Ollama model...")
        cypher, is_valid, val_error = self.cypher_generator.generate_cypher(clean_q)
        result["cypher_query"] = cypher
        result["is_valid_cypher"] = is_valid

        # Step 4: Validate Cypher
        if not is_valid:
            result["error"] = f"Cypher validation error: {val_error}"
            result["final_answer"] = (
                f"Could not execute the query because it failed security/syntax checks: {val_error}"
            )
            pipeline_log.append(f"Step 4: Cypher validation FAILED: {val_error}")
            result["pipeline_steps"] = pipeline_log
            result["execution_time_sec"] = round(time.time() - start_time, 2)
            return result

        pipeline_log.append("Step 4: Cypher validated successfully (Read-only verified).")

        # Step 5 & 6: Execute Query on Neo4j
        pipeline_log.append("Step 5 & 6: Executing read query on Neo4j...")
        try:
            raw_records = self.connection.execute_read_query(cypher)
            result["raw_results"] = raw_records
            pipeline_log.append(f"Retrieved {len(raw_records)} record(s) from Neo4j.")
        except Exception as e:
            err_msg = str(e)
            result["error"] = err_msg
            result["final_answer"] = f"Neo4j database execution error: {err_msg}"
            pipeline_log.append(f"Step 5/6: Execution failed: {err_msg}")
            result["pipeline_steps"] = pipeline_log
            result["execution_time_sec"] = round(time.time() - start_time, 2)
            return result

        # Step 7: Context Construction
        pipeline_log.append("Step 7: Formatting retrieved graph data into context string...")
        context = self.format_records_to_context(raw_records)
        result["context_text"] = context

        # Step 8 & 9: Generate Grounded Answer via Ollama
        pipeline_log.append("Step 8 & 9: Synthesizing final grounded answer with local Ollama model...")
        if not raw_records:
            result["final_answer"] = "I couldn't find enough information in the movie knowledge graph to answer that question."
        else:
            answer = self.generate_grounded_answer(clean_q, context)
            result["final_answer"] = answer

        # Step 10: Complete
        pipeline_log.append("Step 10: Completed RAG pipeline successfully.")
        result["pipeline_steps"] = pipeline_log
        result["execution_time_sec"] = round(time.time() - start_time, 2)
        return result
