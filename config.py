"""
config.py
Configuration loader and Knowledge Graph schema definitions for Movie KG RAG.
Reads connection parameters from .env and exposes schema metadata.
"""

import os
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Neo4j Database Configuration
NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")

# Ollama Local LLM Configuration
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# ==============================================================================
# KNOWLEDGE GRAPH SCHEMA DEFINITION (Neo4j Movies Dataset)
# ==============================================================================

# Allowed node labels in the Neo4j Movies dataset
ALLOWED_NODE_LABELS: List[str] = ["Movie", "Person"]

# Allowed relationship types
ALLOWED_RELATIONSHIPS: List[str] = [
    "ACTED_IN",
    "DIRECTED",
    "PRODUCED",
    "WROTE",
    "REVIEWED",
    "FOLLOWS"
]

# Explicit property mappings for validation and prompt grounding
NODE_PROPERTIES: Dict[str, List[str]] = {
    "Movie": ["title", "released", "tagline"],
    "Person": ["name", "born"]
}

RELATIONSHIP_PROPERTIES: Dict[str, List[str]] = {
    "ACTED_IN": ["roles"],
    "REVIEWED": ["summary", "rating"],
    "DIRECTED": [],
    "PRODUCED": [],
    "WROTE": [],
    "FOLLOWS": []
}

# Formatted schema description string used in LLM prompts
GRAPH_SCHEMA_TEXT = """
Nodes:
- (:Movie {title: STRING, released: INTEGER, tagline: STRING})
- (:Person {name: STRING, born: INTEGER})

Relationships:
- (:Person)-[:ACTED_IN {roles: LIST<STRING>}]->(:Movie)
- (:Person)-[:DIRECTED]->(:Movie)
- (:Person)-[:PRODUCED]->(:Movie)
- (:Person)-[:WROTE]->(:Movie)
- (:Person)-[:REVIEWED {summary: STRING, rating: INTEGER}]->(:Movie)
- (:Person)-[:FOLLOWS]->(:Person)
""".strip()


def check_config_status() -> Dict[str, Any]:
    """
    Checks whether required environment variables are set.
    Returns status flags and user-friendly error messages.
    """
    status = {
        "neo4j_configured": bool(NEO4J_URI and NEO4J_USERNAME and NEO4J_PASSWORD),
        "ollama_configured": bool(OLLAMA_BASE_URL and OLLAMA_MODEL),
        "missing_items": []
    }
    
    if not NEO4J_PASSWORD:
        status["missing_items"].append("NEO4J_PASSWORD is not set in .env")
        
    return status
