"""
neo4j_connection.py
Neo4j database connection manager using the official Neo4j Python Driver.
Handles connection pooling, query execution (read-only transactions),
connectivity checks, and database statistics.
"""

from typing import List, Dict, Any, Tuple, Optional
import neo4j
from neo4j import GraphDatabase
from neo4j.exceptions import (
    AuthError,
    ServiceUnavailable,
    CypherSyntaxError,
    Neo4jError
)

from config import (
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    NEO4J_DATABASE
)


class Neo4jConnection:
    """Manages the Neo4j driver lifecycle and read-only query execution."""

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None
    ):
        self.uri = uri or NEO4J_URI
        self.username = username or NEO4J_USERNAME
        self.password = password or NEO4J_PASSWORD
        self.database = database or NEO4J_DATABASE
        self._driver: Optional[neo4j.Driver] = None

    def connect(self) -> None:
        """Initializes the Neo4j driver instance."""
        if not self._driver:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_lifetime=3600
            )

    def close(self) -> None:
        """Closes the Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def verify_connectivity(self) -> Tuple[bool, str]:
        """
        Tests if the Neo4j database is reachable and credentials are valid.
        Returns:
            (is_connected: bool, status_message: str)
        """
        if not self.password:
            return False, "Neo4j password is not configured. Please set NEO4J_PASSWORD in .env."

        try:
            self.connect()
            if self._driver:
                self._driver.verify_connectivity()
                return True, "Successfully connected to Neo4j Knowledge Graph."
            return False, "Driver initialization returned None."
        except AuthError as e:
            return False, f"Neo4j Authentication Error: Invalid username or password ({e})"
        except ServiceUnavailable as e:
            return False, f"Neo4j Service Unavailable: Could not reach server at {self.uri}. Ensure Neo4j is running. ({e})"
        except Exception as e:
            return False, f"Neo4j Connection Error: {str(e)}"

    def execute_read_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes a validated read-only Cypher query against Neo4j.
        Returns results as a list of Python dictionaries.
        """
        if not self._driver:
            self.connect()

        if parameters is None:
            parameters = {}

        try:
            with self._driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                records = [record.data() for record in result]
                return records
        except CypherSyntaxError as e:
            raise RuntimeError(f"Cypher Syntax Error: {e.message}") from e
        except Neo4jError as e:
            raise RuntimeError(f"Neo4j Execution Error: {e.message}") from e
        except Exception as e:
            raise RuntimeError(f"Database Query Error: {str(e)}") from e

    def execute_write_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes a write or merge Cypher query against Neo4j using parameterized inputs.
        Returns result records as a list of dictionaries.
        """
        if not self._driver:
            self.connect()

        if parameters is None:
            parameters = {}

        try:
            with self._driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                records = [record.data() for record in result]
                return records
        except CypherSyntaxError as e:
            raise RuntimeError(f"Cypher Syntax Error: {e.message}") from e
        except Neo4jError as e:
            raise RuntimeError(f"Neo4j Execution Error: {e.message}") from e
        except Exception as e:
            raise RuntimeError(f"Database Write Error: {str(e)}") from e

    def get_database_statistics(self) -> Dict[str, Any]:
        """
        Fetches summary stats about the active graph (counts of Movie, Person, and relationships).
        Useful for UI badges and viva demonstration.
        """
        stats = {
            "movie_count": 0,
            "person_count": 0,
            "acted_in_count": 0,
            "directed_count": 0,
            "connected": False
        }

        try:
            movie_res = self.execute_read_query("MATCH (m:Movie) RETURN count(m) AS count")
            if movie_res:
                stats["movie_count"] = movie_res[0].get("count", 0)

            person_res = self.execute_read_query("MATCH (p:Person) RETURN count(p) AS count")
            if person_res:
                stats["person_count"] = person_res[0].get("count", 0)

            acted_res = self.execute_read_query("MATCH ()-[r:ACTED_IN]->() RETURN count(r) AS count")
            if acted_res:
                stats["acted_in_count"] = acted_res[0].get("count", 0)

            directed_res = self.execute_read_query("MATCH ()-[r:DIRECTED]->() RETURN count(r) AS count")
            if directed_res:
                stats["directed_count"] = directed_res[0].get("count", 0)

            stats["connected"] = True
        except Exception:
            stats["connected"] = False

        return stats

    def get_sample_movie_titles(self, limit: int = 10) -> List[str]:
        """Returns sample movie titles from the graph for quick exploration."""
        try:
            records = self.execute_read_query(
                "MATCH (m:Movie) RETURN m.title AS title ORDER BY m.title LIMIT $limit",
                {"limit": limit}
            )
            return [r["title"] for r in records if "title" in r]
        except Exception:
            return []


# Global helper instance
_default_connection: Optional[Neo4jConnection] = None


def get_neo4j_connection() -> Neo4jConnection:
    """Returns a singleton-like Neo4jConnection instance."""
    global _default_connection
    if _default_connection is None:
        _default_connection = Neo4jConnection()
    return _default_connection
