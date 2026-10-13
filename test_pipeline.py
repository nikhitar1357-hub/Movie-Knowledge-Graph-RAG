"""
test_pipeline.py
Automated test suite and demonstration script for the Movie Knowledge Graph RAG project.
Tests:
1. Query Validator security & syntax rules (including apostrophes)
2. Canonical Cypher validation on the 10 required questions
3. Neo4j connectivity & special-character entity retrieval (Jerry O'Connell, etc.)
4. Ollama service health & local model availability (llama3.2:3b)
5. End-to-end live RAG pipeline execution via local Ollama
"""

import sys
from config import check_config_status, OLLAMA_BASE_URL, OLLAMA_MODEL
from query_validator import validate_cypher_query
from neo4j_connection import get_neo4j_connection
from ollama_client import get_ollama_client

# 10 Required Test Questions from Project Specification
REQUIRED_TEST_QUESTIONS = [
    "Who directed The Matrix?",
    "Who acted in The Matrix?",
    "What movies has Tom Hanks acted in?",
    "What movies did Christopher Nolan direct?",
    "When was The Matrix released?",
    "Which movies did Tom Hanks and Meg Ryan appear in together?",
    "Tell me about The Matrix.",
    "Find movies released after 2000.",
    "Recommend movies similar to The Matrix.",
    "Find movies involving Keanu Reeves."
]

# Expected canonical Cypher translations for verification
CANONICAL_CYPHER_MAPPINGS = {
    "Who directed The Matrix?":
        "MATCH (p:Person)-[:DIRECTED]->(m:Movie) WHERE toLower(m.title) = toLower('The Matrix') RETURN p.name AS director, m.title AS movie",
    "Who acted in The Matrix?":
        "MATCH (p:Person)-[:ACTED_IN]->(m:Movie) WHERE toLower(m.title) = toLower('The Matrix') RETURN p.name AS actor, m.title AS movie",
    "What movies has Tom Hanks acted in?":
        "MATCH (p:Person)-[:ACTED_IN]->(m:Movie) WHERE toLower(p.name) = toLower('Tom Hanks') RETURN m.title AS movie, m.released AS released ORDER BY m.released DESC",
    "What movies did Christopher Nolan direct?":
        "MATCH (p:Person)-[:DIRECTED]->(m:Movie) WHERE toLower(p.name) = toLower('Christopher Nolan') RETURN m.title AS movie, m.released AS released",
    "When was The Matrix released?":
        "MATCH (m:Movie) WHERE toLower(m.title) = toLower('The Matrix') RETURN m.title AS title, m.released AS released",
    "Which movies did Tom Hanks and Meg Ryan appear in together?":
        "MATCH (p1:Person)-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(p2:Person) WHERE toLower(p1.name) = toLower('Tom Hanks') AND toLower(p2.name) = toLower('Meg Ryan') RETURN m.title AS movie, m.released AS released",
    "Tell me about The Matrix.":
        "MATCH (m:Movie) WHERE toLower(m.title) = toLower('The Matrix') RETURN m.title AS title, m.released AS released, m.tagline AS tagline",
    "Find movies released after 2000.":
        "MATCH (m:Movie) WHERE m.released > 2000 RETURN m.title AS movie, m.released AS released ORDER BY m.released ASC LIMIT 25",
    "Recommend movies similar to The Matrix.":
        "MATCH (m:Movie)<-[:ACTED_IN|DIRECTED]-(p:Person)-[:ACTED_IN|DIRECTED]->(rec:Movie) WHERE toLower(m.title) = toLower('The Matrix') AND rec <> m RETURN rec.title AS movie, count(DISTINCT p) AS score ORDER BY score DESC LIMIT 5",
    "Find movies involving Keanu Reeves.":
        "MATCH (p:Person)-[r:ACTED_IN|DIRECTED]->(m:Movie) WHERE toLower(p.name) = toLower('Keanu Reeves') RETURN m.title AS movie, type(r) AS role, m.released AS released"
}


def run_validator_unit_tests() -> bool:
    """Tests the security validator against safe, dangerous, and malformed queries."""
    print("\n--- 1. Testing Cypher Query Validator ---")

    test_cases = [
        (
            "MATCH (m:Movie {title: 'The Matrix'}) RETURN m.title",
            True,
            "Valid simple MATCH"
        ),
        (
            "CREATE (m:Movie {title: 'Inception'})",
            False,
            "Reject CREATE mutation"
        ),
        (
            "MATCH (m:Movie) DETACH DELETE m",
            False,
            "Reject DETACH DELETE mutation"
        ),
        (
            "MATCH (m:Movie) SET m.rating = 5",
            False,
            "Reject SET mutation"
        ),
        (
            "MERGE (m:Movie {title: 'Avatar'})",
            False,
            "Reject MERGE mutation"
        ),
        (
            "MATCH (m:Movie) DROP CONSTRAINT constraint_name",
            False,
            "Reject DROP administrative command"
        ),
        (
            "MATCH (m:Movie {title: 'Set It Off'}) RETURN m.title",
            True,
            "Allow safe query with keyword inside string literal"
        ),
        (
            "MATCH (m:Movie {title: 'The Matrix' RETURN m",
            False,
            "Reject unbalanced parentheses"
        ),
        (
            'MATCH (p:Person {name: "Jerry O\'Connell"}) RETURN p.name',
            True,
            "Allow safe double-quoted name with apostrophe (Jerry O'Connell)"
        ),
        (
            'MATCH (m:Movie {title: "The Devil\'s Advocate"}) RETURN m.title',
            True,
            "Allow safe double-quoted title with apostrophe (The Devil's Advocate)"
        ),
        (
            "MATCH (p:Person {name: 'Jerry O\\'Connell'}) RETURN p.name",
            True,
            "Allow safe escaped single-quote name (Jerry O\\'Connell)"
        ),
        (
            "",
            False,
            "Reject empty query"
        )
    ]

    all_passed = True
    for query, expected_valid, desc in test_cases:
        is_valid, err, cleaned = validate_cypher_query(query)
        if is_valid == expected_valid:
            print(f"  [PASS] {desc}")
        else:
            print(f"  [FAIL] {desc} (Got: is_valid={is_valid}, Expected: {expected_valid}, Msg: {err})")
            all_passed = False

    return all_passed


def run_canonical_cypher_validation() -> bool:
    """Verifies that all 10 canonical test questions yield valid Cypher queries."""
    print("\n--- 2. Validating 10 Canonical Cypher Queries ---")
    all_passed = True
    for idx, (question, cypher) in enumerate(CANONICAL_CYPHER_MAPPINGS.items(), start=1):
        is_valid, err, _ = validate_cypher_query(cypher)
        if is_valid:
            print(f"  [PASS] Q{idx}: {question}")
        else:
            print(f"  [FAIL] Q{idx}: {question} -> {err}")
            all_passed = False
    return all_passed


def run_special_character_and_repeatability_tests(conn) -> bool:
    """Tests special-character querying and verifies no duplicate nodes exist in Neo4j."""
    print("\n--- 3. Testing Special Characters & Repeatable Loading in Neo4j ---")
    is_connected, _ = conn.verify_connectivity()
    if not is_connected:
        print("  [SKIP] Neo4j is not connected; skipping live database entity checks.")
        return True

    all_passed = True

    # 1. Test Jerry O'Connell retrieval and filmography
    jerry_query = """
    MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
    WHERE p.name = $name
    RETURN p.name AS name, p.born AS born, collect(m.title) AS movies
    """
    records = conn.execute_read_query(jerry_query, {"name": "Jerry O'Connell"})
    if records and records[0].get("name") == "Jerry O'Connell":
        movies = records[0].get("movies", [])
        if "Jerry Maguire" in movies and "Stand By Me" in movies:
            print(f"  [PASS] Jerry O'Connell retrieved with correct filmography: {movies}")
        else:
            print(f"  [FAIL] Jerry O'Connell filmography incomplete: {movies}")
            all_passed = False
    else:
        print("  [FAIL] Could not retrieve Person 'Jerry O\\'Connell' from Neo4j.")
        all_passed = False

    # 2. Test Rosie O'Donnell retrieval
    rosie_records = conn.execute_read_query(
        "MATCH (p:Person {name: $name}) RETURN p.name AS name, p.born AS born",
        {"name": "Rosie O'Donnell"}
    )
    if rosie_records:
        print(f"  [PASS] Rosie O'Donnell retrieved: {rosie_records[0]}")
    else:
        print("  [FAIL] Could not retrieve Person 'Rosie O\\'Donnell' from Neo4j.")
        all_passed = False

    # 3. Test The Devil's Advocate retrieval
    devils_records = conn.execute_read_query(
        "MATCH (m:Movie {title: $title}) RETURN m.title AS title, m.released AS released",
        {"title": "The Devil's Advocate"}
    )
    if devils_records and devils_records[0].get("released") == 1997:
        print(f"  [PASS] The Devil's Advocate retrieved: {devils_records[0]}")
    else:
        print("  [FAIL] Could not retrieve Movie 'The Devil\\'s Advocate' from Neo4j.")
        all_passed = False

    # 4. Test Repeatable Loading (Zero duplicate nodes)
    dup_query = """
    MATCH (p:Person {name: $name})
    RETURN count(p) AS count
    """
    dup_records = conn.execute_read_query(dup_query, {"name": "Jerry O'Connell"})
    if dup_records and dup_records[0]["count"] == 1:
        print("  [PASS] Repeatable loading verified: Jerry O'Connell node count is exactly 1 (no duplicates).")
    else:
        count = dup_records[0]["count"] if dup_records else 0
        print(f"  [FAIL] Duplicate nodes detected! Jerry O'Connell count is {count} (expected 1).")
        all_passed = False

    return all_passed


def run_ollama_and_pipeline_tests(conn) -> bool:
    """Tests Ollama connectivity, model availability, and executes live Graph RAG."""
    print("\n--- 4. Checking Ollama Local LLM & Live Services ---")
    cfg_status = check_config_status()
    print(f"  Neo4j Configured: {'Yes' if cfg_status['neo4j_configured'] else 'No'}")
    print(f"  Ollama Configured: {'Yes' if cfg_status['ollama_configured'] else 'No'} ({OLLAMA_BASE_URL}, model: {OLLAMA_MODEL})")

    is_neo_ok, neo_msg = conn.verify_connectivity()
    print(f"  Neo4j Connection: {neo_msg}")

    ollama = get_ollama_client()
    is_ollama_ok, ollama_msg, available_models = ollama.check_health()
    print(f"  Ollama Health: {ollama_msg}")

    if not is_ollama_ok:
        print("  [SKIP] Ollama is not running. Live LLM tests skipped.")
        print("  (Start Ollama with 'ollama serve' or open the Ollama application to run live LLM tests)")
        return True

    if not is_neo_ok:
        print("  [SKIP] Neo4j is not connected. Live end-to-end RAG skipped.")
        return True

    print("\n--- 5. Executing Live End-to-End Graph RAG with Ollama ---")
    from rag_pipeline import MovieGraphRAGPipeline
    pipeline = MovieGraphRAGPipeline(connection=conn, ollama_client=ollama)

    test_q = "Who directed The Matrix?"
    print(f"  Running query: '{test_q}'")
    res = pipeline.run(test_q)

    print(f"  Generated Cypher: {res['cypher_query']}")
    print(f"  Cypher Valid:     {res['is_valid_cypher']}")
    print(f"  Records Retrieved: {len(res['raw_results'])}")
    print(f"  Final Answer:     {res['final_answer']}")
    print(f"  Elapsed Time:     {res['execution_time_sec']}s")

    if res["is_valid_cypher"] and len(res["raw_results"]) > 0 and res["final_answer"]:
        print("  [PASS] Live Graph RAG pipeline executed successfully with Ollama!")
        return True
    else:
        print("  [FAIL] Live Graph RAG pipeline encountered an issue.")
        if res.get("error"):
            print(f"  Error details: {res['error']}")
        return False


def main():
    print("=" * 65)
    print("Movie Knowledge Graph RAG - Automated Test Suite (Ollama Edition)")
    print("=" * 65)

    conn = get_neo4j_connection()
    v_ok = run_validator_unit_tests()
    c_ok = run_canonical_cypher_validation()
    s_ok = run_special_character_and_repeatability_tests(conn)
    o_ok = run_ollama_and_pipeline_tests(conn)

    print("\n" + "=" * 65)
    if v_ok and c_ok and s_ok and o_ok:
        print("[SUCCESS] All tests and live service checks passed successfully!")
        print("=" * 65)
        return 0
    else:
        print("[FAILURE] Some tests failed. Please review the output above.")
        print("=" * 65)
        return 1


if __name__ == "__main__":
    sys.exit(main())
