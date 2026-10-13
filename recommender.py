"""
recommender.py
Graph-based movie recommendation engine.
Recommends movies sharing common actors, directors, and writers in the knowledge graph.
"""

from typing import List, Dict, Any, Optional
from neo4j_connection import Neo4jConnection, get_neo4j_connection


class MovieRecommender:
    """
    Implements 2nd-degree topological graph recommendations.
    Finds movies connected through shared Person nodes (actors, directors, writers).
    """

    def __init__(self, connection: Optional[Neo4jConnection] = None):
        self.connection = connection or get_neo4j_connection()

    def get_recommendations(self, movie_title: str, limit: int = 5) -> Dict[str, Any]:
        """
        Finds movies related to the target movie through shared actors, directors, and writers.
        
        Args:
            movie_title: The title of the movie to find recommendations for.
            limit: Maximum number of recommendations to return (default 5).

        Returns:
            Dict containing:
                - target_movie: Found target title
                - found: bool
                - recommendations: List of recommended movies with scores and explanations
                - cypher_query: The Cypher query executed
        """
        # Read-only Cypher recommendation query
        query = """
        MATCH (target:Movie)
        WHERE toLower(target.title) = toLower($title)
        MATCH (target)<-[r1:ACTED_IN|DIRECTED|WROTE]-(p:Person)-[r2:ACTED_IN|DIRECTED|WROTE]->(rec:Movie)
        WHERE rec <> target
        WITH rec,
             count(DISTINCT p) AS score,
             collect(DISTINCT {
                 name: p.name,
                 rel1: type(r1),
                 rel2: type(r2)
             }) AS shared_people
        RETURN rec.title AS title,
               rec.released AS released,
               rec.tagline AS tagline,
               score,
               shared_people
        ORDER BY score DESC, rec.released DESC
        LIMIT $limit
        """

        try:
            records = self.connection.execute_read_query(
                query,
                {"title": movie_title.strip(), "limit": limit}
            )
        except Exception as e:
            return {
                "target_movie": movie_title,
                "found": False,
                "recommendations": [],
                "error": str(e),
                "cypher_query": query
            }

        # If no records found with exact match, try a CONTAINS search
        if not records:
            fallback_query = """
            MATCH (target:Movie)
            WHERE toLower(target.title) CONTAINS toLower($title)
            WITH target LIMIT 1
            MATCH (target)<-[r1:ACTED_IN|DIRECTED|WROTE]-(p:Person)-[r2:ACTED_IN|DIRECTED|WROTE]->(rec:Movie)
            WHERE rec <> target
            WITH target, rec,
                 count(DISTINCT p) AS score,
                 collect(DISTINCT {
                     name: p.name,
                     rel1: type(r1),
                     rel2: type(r2)
                 }) AS shared_people
            RETURN target.title AS target_title,
                   rec.title AS title,
                   rec.released AS released,
                   rec.tagline AS tagline,
                   score,
                   shared_people
            ORDER BY score DESC, rec.released DESC
            LIMIT $limit
            """
            try:
                records = self.connection.execute_read_query(
                    fallback_query,
                    {"title": movie_title.strip(), "limit": limit}
                )
                if records and "target_title" in records[0]:
                    movie_title = records[0]["target_title"]
                query = fallback_query
            except Exception:
                pass

        if not records:
            return {
                "target_movie": movie_title,
                "found": False,
                "recommendations": [],
                "cypher_query": query
            }

        recommendations = []
        for rec in records:
            shared = rec.get("shared_people", [])
            shared_names = [f"{p['name']} ({p['rel2']})" for p in shared if isinstance(p, dict) and "name" in p]
            explanation = f"Connected via: {', '.join(shared_names)}" if shared_names else "Shared graph entities."
            
            recommendations.append({
                "title": rec.get("title", "Unknown"),
                "released": rec.get("released"),
                "tagline": rec.get("tagline"),
                "score": rec.get("score", 0),
                "explanation": explanation
            })

        return {
            "target_movie": movie_title,
            "found": True,
            "recommendations": recommendations,
            "cypher_query": query
        }

    @staticmethod
    def format_recommendations_context(rec_result: Dict[str, Any]) -> str:
        """Formats recommendation results into human-readable text for LLM grounding."""
        if not rec_result.get("found") or not rec_result.get("recommendations"):
            return "No graph-connected movie recommendations were found in the database."

        target = rec_result.get("target_movie", "the selected movie")
        lines = [f"Graph Recommendations for '{target}' (based on shared actors/directors):"]
        for idx, item in enumerate(rec_result["recommendations"], start=1):
            title = item.get("title")
            year = item.get("released", "Unknown year")
            score = item.get("score", 0)
            expl = item.get("explanation", "")
            lines.append(f"{idx}. {title} ({year}) - Connection Strength: {score} | {expl}")

        return "\n".join(lines)
