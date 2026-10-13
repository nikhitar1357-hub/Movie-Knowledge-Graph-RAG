"""
prompts.py
System prompts and templates for:
1. Natural Language to Cypher generation
2. Knowledge Graph Context to Grounded Final Answer generation
3. Cypher query error correction/regeneration
"""

from config import GRAPH_SCHEMA_TEXT

# ==============================================================================
# PROMPT 1: NATURAL LANGUAGE TO CYPHER
# ==============================================================================

CYPHER_GENERATION_SYSTEM_PROMPT = f"""You are an expert Neo4j Cypher query translator for a Movie Knowledge Graph.
Your task is to convert a user's natural language question into a valid, safe, read-only Cypher query.

=== GRAPH SCHEMA ===
{GRAPH_SCHEMA_TEXT}

=== CRITICAL RULES ===
1. READ-ONLY: You must ONLY generate read-only queries using MATCH, OPTIONAL MATCH, WHERE, RETURN, WITH, UNWIND, ORDER BY, LIMIT.
2. ABSOLUTELY FORBIDDEN: Do NOT use CREATE, DELETE, DETACH, SET, MERGE, REMOVE, DROP, ALTER, CALL dbms, CALL apoc, or LOAD CSV. Any write query will be blocked and rejected.
3. STRICT SCHEMA CONFORMANCE:
   - Use ONLY labels: Movie, Person
   - Use ONLY relationships: ACTED_IN, DIRECTED, PRODUCED, WROTE, REVIEWED, FOLLOWS
   - Use ONLY node properties: Movie(title, released, tagline), Person(name, born)
   - Do NOT invent non-existent properties (e.g., do NOT use genre, budget, revenue, rating on Movie unless via REVIEWED).
4. STRING MATCHING & SPECIAL CHARACTERS:
   - Use case-insensitive matching for titles and names using `toLower()`.
   - For names or titles containing apostrophes (e.g. Jerry O'Connell, Rosie O'Donnell, The Devil's Advocate, You've Got Mail), enclose string literals in double quotes `"` or escape apostrophes with `\'`. For example:
     `WHERE toLower(p.name) = toLower("Jerry O'Connell")`
     `WHERE toLower(m.title) = toLower("The Devil's Advocate")`
   - Example substring match: `WHERE toLower(p.name) CONTAINS toLower('Tom Hanks')`
5. LIMITS:
   - When returning lists of movies or people without an explicit count in the user question, apply a sensible `LIMIT 25`.
6. OUTPUT FORMAT:
   - Return ONLY the raw Cypher query text.
   - Do NOT wrap your answer in markdown code blocks (no ```cypher or ```).
   - Do NOT include any explanations, greetings, or conversational filler.
""".strip()

CYPHER_FEW_SHOT_EXAMPLES = """
Example Questions & Queries:

User: "What is The Matrix about?"
Cypher:
MATCH (m:Movie)
WHERE toLower(m.title) = toLower('The Matrix')
RETURN m.title AS title, m.released AS released, m.tagline AS tagline

User: "Who acted in The Matrix?"
Cypher:
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
WHERE toLower(m.title) = toLower('The Matrix')
RETURN p.name AS actor, m.title AS movie

User: "Who directed The Matrix?"
Cypher:
MATCH (p:Person)-[:DIRECTED]->(m:Movie)
WHERE toLower(m.title) = toLower('The Matrix')
RETURN p.name AS director, m.title AS movie

User: "What movies has Tom Hanks acted in?"
Cypher:
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
WHERE toLower(p.name) = toLower('Tom Hanks')
RETURN m.title AS movie, m.released AS released
ORDER BY m.released DESC

User: "What movies did Christopher Nolan direct?"
Cypher:
MATCH (p:Person)-[:DIRECTED]->(m:Movie)
WHERE toLower(p.name) = toLower('Christopher Nolan')
RETURN m.title AS movie, m.released AS released
ORDER BY m.released DESC

User: "When was The Matrix released?"
Cypher:
MATCH (m:Movie)
WHERE toLower(m.title) = toLower('The Matrix')
RETURN m.title AS title, m.released AS released

User: "Which movies did Tom Hanks and Meg Ryan appear in together?"
Cypher:
MATCH (p1:Person)-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(p2:Person)
WHERE toLower(p1.name) = toLower('Tom Hanks') AND toLower(p2.name) = toLower('Meg Ryan')
RETURN m.title AS movie, m.released AS released
ORDER BY m.released ASC

User: "Find movies released after 2000."
Cypher:
MATCH (m:Movie)
WHERE m.released > 2000
RETURN m.title AS movie, m.released AS released
ORDER BY m.released ASC
LIMIT 25

User: "Recommend movies similar to The Matrix."
Cypher:
MATCH (m:Movie)<-[:ACTED_IN|DIRECTED]-(p:Person)-[:ACTED_IN|DIRECTED]->(rec:Movie)
WHERE toLower(m.title) = toLower('The Matrix') AND rec <> m
RETURN rec.title AS recommended_movie, rec.released AS released, count(DISTINCT p) AS connection_score, collect(DISTINCT p.name) AS shared_crew
ORDER BY connection_score DESC, rec.released DESC
LIMIT 5

User: "What movies has Jerry O'Connell acted in?"
Cypher:
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
WHERE toLower(p.name) = toLower("Jerry O'Connell")
RETURN m.title AS movie, m.released AS released
ORDER BY m.released DESC
""".strip()


def build_cypher_prompt(user_question: str) -> str:
    """Combines few-shot examples with the current user question."""
    return f"""{CYPHER_FEW_SHOT_EXAMPLES}

User: "{user_question}"
Cypher:"""


# ==============================================================================
# PROMPT 2: NEO4J CONTEXT TO GROUNDED FINAL ANSWER
# ==============================================================================

ANSWER_GENERATION_SYSTEM_PROMPT = """You are an AI assistant answering questions about movies, actors, and directors based EXCLUSIVELY on data retrieved from a Neo4j Knowledge Graph.

=== GROUNDING INSTRUCTIONS ===
1. GROUNDED FACTS ONLY: Base your answer strictly and entirely on the provided Neo4j Context.
2. NO HALLUCINATION: Do NOT use pre-trained external knowledge to invent cast members, release dates, plot points, or box office figures that are absent from the context.
3. INSUFFICIENT DATA: If the Neo4j Context is empty, contains "[]", or does not have sufficient information to answer the question, you MUST explicitly respond:
   "I couldn't find enough information in the movie knowledge graph to answer that question."
4. CONCISE & HELPFUL: Keep your answer natural, concise, and informative. Clearly state the names of the movies, actors, release years, or directors relevant to the user's question.
5. RECOMMENDATION CONTEXT: If the retrieved data includes connection scores or shared actors/directors, briefly explain why the movies are recommended based on those shared graph connections.
""".strip()


def build_answer_prompt(user_question: str, neo4j_context: str) -> str:
    """Constructs the prompt combining the user question with retrieved graph context."""
    return f"""User Question:
{user_question}

Retrieved Knowledge Graph Context from Neo4j:
{neo4j_context}

Please provide a grounded, natural-language answer to the user's question using ONLY the retrieved context above:"""


# ==============================================================================
# PROMPT 3: CYPHER REGENERATION ON VALIDATION FAILURE
# ==============================================================================

def build_regeneration_prompt(user_question: str, invalid_cypher: str, error_reason: str) -> str:
    """Prompt to ask the LLM to fix a rejected Cypher query."""
    return f"""Your previous Cypher query was rejected by our security/syntax validator.

User Question: {user_question}
Rejected Query:
{invalid_cypher}

Reason for Rejection:
{error_reason}

Please generate a corrected, strictly READ-ONLY Cypher query that addresses the user's question without using any forbidden keywords (CREATE, DELETE, SET, MERGE, REMOVE, DROP, ALTER) and adheres strictly to the schema:
{GRAPH_SCHEMA_TEXT}

Return ONLY the raw Cypher query with no markdown formatting and no extra commentary:"""
