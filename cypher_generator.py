"""
cypher_generator.py
Converts Natural Language user questions into valid Cypher queries using a local Ollama LLM.
Includes automated validation and one-pass regeneration upon validation error.
"""

from typing import Tuple, Optional
from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from prompts import (
    CYPHER_GENERATION_SYSTEM_PROMPT,
    build_cypher_prompt,
    build_regeneration_prompt
)
from query_validator import validate_cypher_query
from ollama_client import OllamaClient, get_ollama_client


class CypherGenerator:
    """Generates and validates Cypher queries from natural language input using local Ollama."""

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.model = model or OLLAMA_MODEL
        self.base_url = base_url or OLLAMA_BASE_URL
        self.client = ollama_client or OllamaClient(base_url=self.base_url, model=self.model)

    def generate_cypher(self, user_question: str) -> Tuple[str, bool, str]:
        """
        Translates a natural language question into a Cypher query using Ollama.
        Validates the output. If validation fails, attempts one-shot regeneration.

        Returns:
            (cypher_query: str, is_valid: bool, error_message: str)
        """
        if not user_question or not user_question.strip():
            return "", False, "Question cannot be empty."

        # Step 1: Initial Local LLM Generation via Ollama
        prompt_text = build_cypher_prompt(user_question.strip())
        messages = [
            {"role": "system", "content": CYPHER_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text}
        ]

        try:
            raw_cypher = self.client.chat(messages, temperature=0.0, max_tokens=400)
        except RuntimeError as e:
            return "", False, str(e)
        except Exception as e:
            return "", False, f"Unexpected error while generating Cypher with Ollama: {str(e)}"

        # Step 2: Validate Generated Cypher
        is_valid, validation_error, cleaned_cypher = validate_cypher_query(raw_cypher)

        # Step 3: If invalid, attempt one-time regeneration
        if not is_valid:
            regen_prompt = build_regeneration_prompt(
                user_question=user_question,
                invalid_cypher=raw_cypher,
                error_reason=validation_error
            )
            regen_messages = [
                {"role": "system", "content": CYPHER_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": regen_prompt}
            ]
            try:
                raw_regen_cypher = self.client.chat(regen_messages, temperature=0.0, max_tokens=400)
                is_valid, validation_error, cleaned_cypher = validate_cypher_query(raw_regen_cypher)
            except Exception as e:
                return (
                    cleaned_cypher,
                    False,
                    f"Cypher validation failed ({validation_error}), and regeneration failed: {str(e)}"
                )

        return cleaned_cypher, is_valid, validation_error
