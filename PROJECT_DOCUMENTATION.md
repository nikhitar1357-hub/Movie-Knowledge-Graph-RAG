# PROJECT DOCUMENTATION: MOVIE KNOWLEDGE GRAPH RAG

**Department of Artificial Intelligence & Machine Learning**  
**Project Title:** Movie Knowledge Graph RAG Application using Neo4j  
**Technology Stack:** Python, Neo4j, Cypher, Ollama (llama3.2:3b), Streamlit  

---

## 1. Abstract

Large Language Models (LLMs) demonstrate remarkable linguistic comprehension and generative capabilities but are prone to factual inaccuracies, hallucination, and lack of domain-specific relational reasoning. Retrieval-Augmented Generation (RAG) mitigates these limitations by fetching relevant external context prior to synthesis. However, conventional RAG systems rely almost entirely on unstructured vector search over text chunks, which suffers when resolving complex, multi-hop queries (e.g., finding co-actors or multi-degree relationships). 

This project implements a **Knowledge Graph RAG (Graph RAG)** architecture utilizing the **Neo4j Movies Knowledge Graph**. Natural language queries from users are translated into read-only **Cypher** queries via an LLM prompted with the exact database schema. A security validation module inspects the generated Cypher to prevent unauthorized database modifications (`CREATE`, `DELETE`, `SET`, `DROP`). The query is executed against Neo4j, and the structured subgraph context is fed back to the LLM to generate a strictly grounded, factual answer. Additionally, a graph-based topological recommendation engine recommends movies based on 2nd-degree shared connections (shared actors, directors, and writers). A Streamlit web application provides an intuitive interface with inspectable Cypher queries and execution traces.

---

## 2. Introduction

Knowledge Graphs (KGs) represent facts as entities (nodes) connected by meaningful relationships (edges). Unlike tabular databases or flat vector databases, Knowledge Graphs excel at traversing interconnected networks of information. When combined with Large Language Models, Knowledge Graphs provide a verifiable, structured source of truth.

The primary objective of this project is to construct an end-to-end Graph RAG system using the official Neo4j Movies dataset. By converting natural language questions into formal Cypher queries, executing read-only graph queries, and conditioning LLM generation on the retrieved facts, this project demonstrates how graph databases eliminate factual hallucinations in AI applications.

---

## 3. Problem Statement

General-purpose LLMs face notable hurdles when answering domain-specific or relational questions:
1. **Hallucination**: Generating plausible-sounding yet false movie details, cast lists, or dates.
2. **Relational Inefficiency in Vector Search**: Vector similarity search compares semantic text embeddings. It cannot reliably answer questions requiring multi-hop traversal, such as *"Which movies did Tom Hanks and Meg Ryan co-star in?"* because semantic distance cannot substitute for graph connectivity.
3. **Database Security Risk**: Allowing an LLM to generate arbitrary queries introduces the risk of unintentional data tampering or injection attacks if write commands are executed.

---

## 4. Objectives

1. Model movie relationships using Neo4j's labeled property graph model.
2. Implement an automated Natural Language to Cypher translation pipeline with strict schema constraints.
3. Design and implement a multi-layer Cypher query validator ensuring read-only execution.
4. Retrieve structured facts from Neo4j and format them as grounded context for the LLM.
5. Guarantee zero hallucinations by enforcing strict context reliance, returning explicit notices when data is unavailable.
6. Provide graph topological recommendations using shared cast and crew connections.
7. Build a responsive Streamlit web application with transparent visibility into intermediate steps (Cypher query, graph context, execution timing).

---

## 5. Existing System

Existing approaches typically fall into two categories:

### A. Pure LLM Generation (Without Retrieval)
- **Mechanism**: Prompting an LLM directly.
- **Drawbacks**: Memory cutoff issues, hallucinated relationships, inability to cite sources.

### B. Standard Vector RAG
- **Mechanism**: Chunking text documents (e.g., movie synopses), storing embeddings in vector stores (Chroma, FAISS, Pinecone), and retrieving nearest neighbors via cosine similarity.
- **Drawbacks**:
  - Cannot perform relational queries (*"Find all actors who worked with Director X"*).
  - Struggles with discrete aggregations, counts, and filters (*"Movies released after 2000"*).
  - Retrieved text chunks often contain irrelevant prose, wasting LLM context tokens.

---

## 6. Proposed System

The proposed system adopts **Knowledge Graph RAG (Graph RAG)**:
- Replaces vector approximations with deterministic, exact graph queries in **Cypher**.
- Enforces relational integrity: node labels (`Movie`, `Person`) and relationship types (`ACTED_IN`, `DIRECTED`, etc.) are explicitly governed.
- Adds a **Query Security Validator** that analyzes Cypher tokens before execution, rejecting any mutation.
- Feeds retrieved key-value records into an LLM with strict instructions to answer only using retrieved data.
- Implements a dedicated graph-based recommendation algorithm leveraging 2nd-degree paths in the graph.

---

## 7. Technologies Used

| Technology | Role in System | Justification |
| :--- | :--- | :--- |
| **Python 3.10+** | Core programming language | Industry standard for AI/ML pipelines and driver integrations. |
| **Neo4j** | Graph Database Management System | Native graph storage engine optimized for traversing property graphs. |
| **Cypher** | Declarative Graph Query Language | Expressive pattern-matching syntax for traversing graph nodes and edges. |
| **Neo4j Python Driver** | Database Connectivity | Official, thread-safe driver managing connection pooling and sessions. |
| **Ollama (`llama3.2:3b`)** | Local Language Model | Local private inference on Windows, translating natural language to Cypher and synthesizing grounded answers without external API fees. |
| **Streamlit** | Frontend Web Framework | Fast, Python-native UI development with interactive expanders and cards. |
| **python-dotenv** | Environment Management | Secure handling of database credentials and API keys without hardcoding. |

---

## 8. Knowledge Graph Fundamentals

A **Knowledge Graph** represents information as a network of nodes, edges, and properties:
- **Nodes (Vertices)**: Represent discrete entities (e.g., a specific Movie or Person).
- **Edges (Relationships)**: Directed connections between entities describing how they relate (e.g., `ACTED_IN`, `DIRECTED`).
- **Properties (Attributes)**: Key-value pairs attached to nodes or edges (e.g., `title`, `released`, `roles`).

In contrast to relational databases (RDBMS), which require computationally expensive `JOIN` operations across foreign keys, graph databases store direct physical pointers between related nodes, allowing index-free adjacency traversal.

---

## 9. Neo4j Schema

The application uses the official Neo4j Movies dataset schema:

### Nodes
- **`(:Movie)`**:
  - `title` (STRING): Unique title of the movie (e.g., *"The Matrix"*).
  - `released` (INTEGER): Year of theatrical release (e.g., `1999`).
  - `tagline` (STRING): Promotional slogan (e.g., *"Welcome to the Real World"*).
- **`(:Person)`**:
  - `name` (STRING): Full name of the person (e.g., *"Keanu Reeves"*).
  - `born` (INTEGER): Year of birth (e.g., `1964`).

### Relationships
- `(:Person)-[:ACTED_IN {roles: LIST<STRING>}]->(:Movie)`
- `(:Person)-[:DIRECTED]->(:Movie)`
- `(:Person)-[:PRODUCED]->(:Movie)`
- `(:Person)-[:WROTE]->(:Movie)`
- `(:Person)-[:REVIEWED {summary: STRING, rating: INTEGER}]->(:Movie)`
- `(:Person)-[:FOLLOWS]->(:Person)`

---

## 10. RAG Architecture

The 10-step execution pipeline operates sequentially:

```
[User Question]
      │
      ▼
(Step 1) Streamlit receives question
      │
      ▼
(Step 2) Prompt Construction with Schema & Few-shot Cypher
      │
      ▼
(Step 3) LLM generates raw Cypher query
      │
      ▼
(Step 4) Query Validator verifies Read-Only safety
      │
      ▼
(Step 5) Neo4j Driver executes query in Read Transaction
      │
      ▼
(Step 6) Structured Records retrieved from Graph
      │
      ▼
(Step 7) Records serialized into clean Context Text
      │
      ▼
(Step 8) LLM receives (Question + Grounded Context)
      │
      ▼
(Step 9) LLM generates factual answer (or fallback if empty)
      │
      ▼
(Step 10) Streamlit renders Answer, Cypher, and Context Expanders
```

---

## 11. Natural Language to Cypher Translation

To translate arbitrary user questions into Cypher, the system provides the LLM with:
1. **Schema Context**: Explicit listing of valid node labels, relationship types, and allowed properties.
2. **Few-Shot Examples**: Exemplar pairings demonstrating common query patterns (cast search, director search, co-actors, year filters).
3. **Case-Insensitive Normalization**: Instructions to use `toLower()` on string properties to ensure reliable matching regardless of user casing.
4. **Deterministic Settings**: Temperature set to `0.0` to minimize randomness.

---

## 12. Query Validation and Security

Allowing an LLM to generate database code introduces critical security vulnerabilities (prompt injection, accidental deletion, denial-of-service). The `query_validator.py` module enforces three lines of defense:

1. **Forbidden Keyword Filter**:
   Scans the query for mutating or administrative tokens:
   `CREATE`, `DELETE`, `DETACH`, `SET`, `MERGE`, `REMOVE`, `DROP`, `ALTER`, `LOAD CSV`, `PERIODIC COMMIT`, `GRANT`, `APOC`, `DBMS`.
2. **String Literal Masking**:
   Before checking keywords, string literals (e.g. `'Set It Off'`) are masked to prevent false positives when a movie title contains a forbidden word.
3. **Structural Verification**:
   - Ensures the query contains valid read clauses (`MATCH`, `RETURN`, `WITH`, `UNWIND`).
   - Ensures balanced parentheses `()`, brackets `[]`, and braces `{}`.

If validation fails, the generator performs a one-pass automated regeneration, supplying the LLM with the rejection reason.

---

## 13. Retrieval Mechanism

Retrieved data is fetched through the official Neo4j driver using scoped sessions:
```python
with self._driver.session(database=self.database) as session:
    result = session.run(query, parameters)
    records = [record.data() for record in result]
```
The records are extracted as native Python dictionaries containing node and relationship properties.

---

## 14. LLM Answer Generation & Grounding

The retrieved records are serialized into a clean textual representation:
```text
Record 1 -> director: Lana Wachowski | movie: The Matrix
Record 2 -> director: Lilly Wachowski | movie: The Matrix
```

The LLM is prompted under strict constraints:
- Must only use facts present in the retrieved records.
- Must not draw upon general pre-trained knowledge to supplement unverified facts.
- **Empty Result Fallback**: If records are empty, the model outputs:
  *"I couldn't find enough information in the movie knowledge graph to answer that question."*

---

## 15. Recommendation System

The recommendation feature is implemented as a **2nd-degree topological graph query** rather than a collaborative filtering or embedding model:

### Recommendation Algorithm
Given target movie $M_{target}$:
1. Traverse all `Person` nodes $P$ connected to $M_{target}$ via `ACTED_IN`, `DIRECTED`, or `WROTE`.
2. Traverse outward from $P$ to other movies $M_{rec}$ where $M_{rec} \neq M_{target}$.
3. Calculate connection strength score $S = \text{Count}(\text{Distinct } P)$.
4. Rank recommendations by descending score $S$ and descending release year.

### Cypher Representation
```cypher
MATCH (target:Movie {title: $title})<-[r1:ACTED_IN|DIRECTED|WROTE]-(p:Person)-[r2:ACTED_IN|DIRECTED|WROTE]->(rec:Movie)
WHERE rec <> target
WITH rec, count(DISTINCT p) AS score, collect(DISTINCT p.name) AS shared_crew
RETURN rec.title AS title, rec.released AS released, score, shared_crew
ORDER BY score DESC, rec.released DESC
LIMIT $limit
```

This approach provides clear explainability (*"Recommended because Keanu Reeves acted in both movies and Lana Wachowski directed both"*).

---

## 16. Implementation Details

The implementation is structured into modular, clean Python files:
- `config.py`: Environment configuration and graph schema constants.
- `neo4j_connection.py`: Thread-safe driver connection pooling and read transactions.
- `query_validator.py`: Cypher syntax and security validation.
- `prompts.py`: Prompt templates for Cypher generation, answer generation, and regeneration.
- `cypher_generator.py`: LLM-based query translation with automated validation checks.
- `rag_pipeline.py`: 10-step orchestrator linking query generation, validation, retrieval, and grounding.
- `recommender.py`: 2nd-degree graph recommendation engine.
- `load_data.py`: Direct data seeder for fresh Neo4j databases.
- `app.py`: Streamlit frontend with system metrics, sample questions, and expandable technical details.
- `test_pipeline.py`: Comprehensive test suite verifying validator edge cases and canonical Cypher queries.

---

## 17. Example Interactions

### Interaction 1: Director Query
- **User Question**: *"Who directed The Matrix?"*
- **Generated Cypher**:
  ```cypher
  MATCH (p:Person)-[:DIRECTED]->(m:Movie)
  WHERE toLower(m.title) = toLower('The Matrix')
  RETURN p.name AS director, m.title AS movie
  ```
- **Retrieved Context**: `Record 1 -> director: Lana Wachowski | movie: The Matrix`, `Record 2 -> director: Lilly Wachowski | movie: The Matrix`
- **Final Answer**: *"The Matrix was directed by Lana Wachowski and Lilly Wachowski."*

### Interaction 2: Co-Actor Collaboration
- **User Question**: *"Which movies did Tom Hanks and Meg Ryan appear in together?"*
- **Generated Cypher**:
  ```cypher
  MATCH (p1:Person)-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(p2:Person)
  WHERE toLower(p1.name) = toLower('Tom Hanks') AND toLower(p2.name) = toLower('Meg Ryan')
  RETURN m.title AS movie, m.released AS released
  ```
- **Retrieved Context**:
  - `Record 1 -> movie: Joe Versus the Volcano | released: 1990`
  - `Record 2 -> movie: Sleepless in Seattle | released: 1993`
  - `Record 3 -> movie: You've Got Mail | released: 1998`
- **Final Answer**: *"Tom Hanks and Meg Ryan appeared together in Joe Versus the Volcano (1990), Sleepless in Seattle (1993), and You've Got Mail (1998)."*

### Interaction 3: Missing Information
- **User Question**: *"What movies did Christopher Nolan direct?"*
- **Generated Cypher**:
  ```cypher
  MATCH (p:Person)-[:DIRECTED]->(m:Movie)
  WHERE toLower(p.name) = toLower('Christopher Nolan')
  RETURN m.title AS movie, m.released AS released
  ```
- **Retrieved Context**: `No matching records found in the movie knowledge graph.`
- **Final Answer**: *"I couldn't find enough information in the movie knowledge graph to answer that question."*

---

## 18. Limitations

1. **Closed Domain**: The knowledge base is limited to the ~170 nodes present in the Neo4j Movies dataset.
2. **Recommendation Simplicity**: Recommendations reflect topological co-occurrence rather than personalized collaborative filtering or vector semantic similarity.
3. **Single-Hop Text Matching**: Full-text fuzzy search is limited to `toLower()` and `CONTAINS` rather than Levenshtein distance indexing.

---

## 19. Future Scope

1. **Hybrid Graph + Vector RAG**: Integrate Neo4j's native vector search index to combine text similarity with relationship traversals.
2. **Interactive Graph Visualization**: Incorporate interactive Force-Directed graph rendering (via D3.js or PyVis) within the Streamlit UI.
3. **Conversational Memory**: Implement multi-turn session tracking for sequential questions.
4. **Automated Knowledge Expansion**: Ingest live movie APIs (such as TMDB or OMDb) with automated entity resolution.

---

## 20. Conclusion

This project successfully demonstrates the architecture and advantages of **Knowledge Graph RAG**. By utilizing a Neo4j graph database as a structured factual foundation, translating natural language queries to Cypher, validating queries against security hazards, and restricting the LLM to retrieved context, the application provides completely grounded, verifiable, and explainable responses to complex movie queries.
