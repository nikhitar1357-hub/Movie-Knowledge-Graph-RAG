"""
ollama_client.py
Client for Ollama's local HTTP API.
Communicates directly with the local Ollama daemon on Windows without external API keys.
"""

from typing import List, Dict, Any, Tuple, Optional
import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


class OllamaClient:
    """Manages chat completions and health checks against a local Ollama server."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL

    def check_health(self) -> Tuple[bool, str, List[str]]:
        """
        Checks if Ollama is running and whether the requested model is downloaded.

        Returns:
            (is_online: bool, status_message: str, available_models: List[str])
        """
        tags_url = f"{self.base_url}/api/tags"
        try:
            response = requests.get(tags_url, timeout=3.0)
            if response.status_code != 200:
                return (
                    False,
                    f"Ollama server returned unexpected status code {response.status_code}.",
                    []
                )

            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]

            # Check if requested model or matching base name exists
            model_found = any(
                m == self.model or m.startswith(self.model) or self.model.startswith(m)
                for m in models
            )

            if not model_found:
                return (
                    True,
                    f"Ollama is running, but model '{self.model}' is not downloaded. Run 'ollama pull {self.model}' in PowerShell.",
                    models
                )

            return True, f"Ollama is online with model '{self.model}'.", models

        except requests.exceptions.ConnectionError:
            return (
                False,
                f"Could not connect to Ollama at {self.base_url}. Ensure Ollama is running locally on your computer.",
                []
            )
        except requests.exceptions.Timeout:
            return (
                False,
                f"Connection to Ollama timed out at {self.base_url}.",
                []
            )
        except Exception as e:
            return (
                False,
                f"Ollama health check error: {str(e)}",
                []
            )

    def get_available_models(self) -> List[str]:
        """Returns the list of model names currently available in Ollama."""
        is_online, _, models = self.check_health()
        if is_online and models:
            return models
        return [self.model]

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: float = 60.0
    ) -> str:
        """
        Sends a chat request to Ollama's /api/chat endpoint.

        Args:
            messages: List of message dicts: [{'role': 'system'|'user', 'content': '...'}]
            temperature: Sampling temperature (0.0 for deterministic output)
            max_tokens: Maximum number of tokens to generate (num_predict in Ollama)
            timeout: Request timeout in seconds

        Returns:
            Generated assistant message text.
        """
        chat_url = f"{self.base_url}/api/chat"

        options: Dict[str, Any] = {
            "temperature": temperature
        }
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": options
        }

        try:
            response = requests.post(chat_url, json=payload, timeout=timeout)
            if response.status_code == 404:
                raise RuntimeError(
                    f"Model '{self.model}' not found in Ollama. Run 'ollama pull {self.model}' to download it."
                )
            response.raise_for_status()

            data = response.json()
            message = data.get("message", {})
            content = message.get("content", "")
            return content.strip()

        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"Ollama is not running. Please start Ollama at {self.base_url} (e.g. run 'ollama serve' or launch Ollama)."
            ) from e
        except requests.exceptions.Timeout as e:
            raise RuntimeError(
                f"Ollama request timed out after {timeout} seconds."
            ) from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Ollama communication error: {str(e)}"
            ) from e


# Global singleton instance
_default_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Returns a singleton OllamaClient instance."""
    global _default_ollama_client
    if _default_ollama_client is None:
        _default_ollama_client = OllamaClient()
    return _default_ollama_client
