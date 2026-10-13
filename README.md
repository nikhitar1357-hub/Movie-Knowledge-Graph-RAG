# Movie Knowledge Graph RAG

An AI/ML college project demonstrating **Graph-based Retrieval-Augmented Generation (Graph RAG)** using **Neo4j**, **Cypher**, **Ollama (`llama3.2:3b`)**, and **Streamlit**.

The application translates natural language questions into read-only Cypher queries, retrieves structured graph relationships from the Neo4j Movies dataset, validates the queries against security vulnerabilities, and synthesizes factual, grounded answers using a local Ollama LLM.

---

## Project Overview

Traditional Retrieval-Augmented Generation (RAG) relies primarily on unstructured vector databases and semantic similarity search (cosine distance on text chunks). While effective for text documents, vector search struggles with multi-hop reasoning, explicit relationships (e.g., *"Which movies did Actor A and Actor B star in together?"*), and structural queries (e.g., *"List all directors who directed movies released after 2000"*).

This project demonstrates **Knowledge Graph RAG (Graph RAG)**:
1. Natural language questions are converted into Cypher queries by a local LLM (Ollama).
2. Queries undergo automated security and syntax validation to guarantee read-only execution.
3. Relevant factual paths and subgraphs are retrieved directly from Neo4j.
4. An LLM synthesizes the final answer grounded strictly in the retrieved graph context, preventing hallucinations.
5. Simple graph topological recommendations are computed using 2nd-degree shared graph connections.

---

## Problem Statement

Large Language Models (LLMs) suffer from:
- **Hallucinations**: Inventing actors, release dates, or connections.
- **Outdated Knowledge**: Inability to reflect structured domain knowledge without fine-tuning.
- **Relational Blindness**: Inability to execute precise relational queries over complex interconnected entities.

Standard text vector databases cannot effectively query multi-hop relationships between entities without fragmenting context.

**Solution:** Combining a **Neo4j Knowledge Graph** with an **LLM-driven Cypher query generator** ensures that relational information is precisely retrieved and answers are 100% grounded in factual database records.

---

## Objectives

- Convert natural language questions into Cypher queries using a local LLM.
- Enforce strict query validation to prevent database modifications (`CREATE`, `DELETE`, `SET`, `DROP`, etc.).
- Retrieve structured entities (Movies, Actors, Directors) from Neo4j.
- Ground LLM answers strictly on retrieved graph data.
- Fallback gracefully when information is not present in the graph.
- Implement graph-based recommendations based on shared actors and directors.
- Build an interactive, college-friendly Streamlit web interface suitable for viva and demonstration.

---

## Features

- **Movie Information Retrieval**: Retrieve summaries, release years, and taglines.
- **Cast and Crew Inquiries**: Find actors, directors, writers, and producers for any movie.
- **Actor Filmography**: List all movies an actor has appeared in.
- **Co-actor Collaboration**: Discover movies where two specific actors collaborated.
- **Filtered Searches**: Query movies by release year thresholds (e.g., released after 2000).
- **Graph-Based Recommendations**: 2nd-degree topological traversal finding movies sharing common cast and crew.
- **Query Security Validator**: Lexical filter preventing modifying or administrative Cypher operations.
- **Interactive Streamlit Interface**: Includes question inputs, sample prompts, generated Cypher inspection, and raw context display.

---

## Technologies

- **Programming Language**: Python 3.10+ (tested on Python 3.14)
- **Graph Database**: Neo4j (Neo4j Desktop or Neo4j AuraDB)
- **Database Driver**: Official `neo4j` Python Driver (v5+)
- **Query Language**: Cypher
- **Large Language Model (LLM)**: Ollama (`llama3.2:3b` running locally)
- **Web UI**: Streamlit
- **Configuration Management**: `python-dotenv`

---

## Architecture

```
User
  │
  ▼
Streamlit UI
  │
  ▼
Natural Language Question
  │
  ▼
LLM generates Cypher (guided by schema & prompt)
  │
  ▼
Cypher Validation (Read-only check, rejects CREATE/DELETE/SET)
  │
  ▼
Neo4j Knowledge Graph (Official Movies Dataset)
  │
  ▼
Relevant Graph Data (Nodes & Relationships)
  │
  ▼
Context Construction (Formatted record text)
  │
  ▼
LLM (Grounded Synthesis)
  │
  ▼
Grounded Natural-Language Answer
  │
  ▼
Streamlit UI Display (Answer + Cypher + Context Expander)
```

---

## Knowledge Graph Schema

The application uses the official Neo4j Movies dataset schema:

### Node Labels & Properties
- `(:Movie)`
  - `title` (STRING, e.g., "The Matrix")
  - `released` (INTEGER, e.g., 1999)
  - `tagline` (STRING, e.g., "Welcome to the Real World")
- `(:Person)`
  - `name` (STRING, e.g., "Keanu Reeves")
  - `born` (INTEGER, e.g., 1964)

### Relationship Types
- `(:Person)-[:ACTED_IN {roles: LIST<STRING>}]->(:Movie)`
- `(:Person)-[:DIRECTED]->(:Movie)`
- `(:Person)-[:PRODUCED]->(:Movie)`
- `(:Person)-[:WROTE]->(:Movie)`
- `(:Person)-[:REVIEWED {summary: STRING, rating: INTEGER}]->(:Movie)`
- `(:Person)-[:FOLLOWS]->(:Person)`

---

## RAG Pipeline

The RAG pipeline executes through 10 distinct steps:

1. **Step 1 (Input)**: User submits a natural-language query via the Streamlit UI.
2. **Step 2 (Prompt Construction)**: User question + Knowledge Graph schema + few-shot Cypher examples are sent to the LLM.
3. **Step 3 (Cypher Generation)**: LLM produces a target Cypher query.
4. **Step 4 (Validation)**: `query_validator.py` inspects the query. If any mutating keyword (`CREATE`, `DELETE`, `SET`, `MERGE`, `DROP`) is found, query is blocked.
5. **Step 5 (Database Execution)**: Validated query is executed as a read transaction via the Neo4j Python driver.
6. **Step 6 (Record Retrieval)**: Structured dictionaries are returned from Neo4j.
7. **Step 7 (Context Serialization)**: Raw records are formatted into a structured text context.
8. **Step 8 (Grounded Prompting)**: User question + formatted context are passed to the LLM with strict grounding instructions.
9. **Step 9 (Answer Synthesis)**: LLM outputs an answer using solely the retrieved context. If records were empty, it outputs: *"I couldn't find enough information in the movie knowledge graph to answer that question."*
10. **Step 10 (Presentation)**: Streamlit renders the final answer, expandable Cypher query, and raw retrieved records.

---

## Project Structure

```
movie-kg-rag/
│
├── app.py                  # Streamlit web application & user interface
├── config.py               # Environment configuration & graph schema definition
├── neo4j_connection.py     # Neo4j driver connection & query execution manager
├── cypher_generator.py     # LLM Cypher query translator with auto-regeneration
├── query_validator.py      # Security filter enforcing read-only Cypher
├── rag_pipeline.py         # End-to-end 10-step Graph RAG pipeline
├── recommender.py          # 2nd-degree topological graph recommendation engine
├── prompts.py              # System prompts & few-shot Cypher templates
├── ollama_client.py        # Local Ollama HTTP API client & health checker
├── load_data.py            # Automated loader for the Neo4j Movies dataset
├── test_pipeline.py        # Automated test suite for validators & queries
│
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules for keys and venvs
├── README.md               # Complete project documentation
├── PROJECT_DOCUMENTATION.md# Academic report & Viva reference document
├── VIVA_QUESTIONS.md       # 35+ Viva preparation questions & answers
│
└── screenshots/            # UI demonstration screenshots
    └── README.md
```

---

## Prerequisites

- **Python**: Version 3.10 or higher.
- **Neo4j**: Either **Neo4j Desktop** (Local) OR **Neo4j AuraDB** (Free Cloud Database).
- **Ollama**: Installed locally on Windows with the model `llama3.2:3b` (`ollama pull llama3.2:3b`).

---

## Neo4j Setup

You can use either a local Neo4j Desktop instance or a free cloud instance on Neo4j AuraDB.

### Option A: Neo4j Desktop (Local)
1. Download and install [Neo4j Desktop](https://neo4j.com/download/).
2. Create a new local Project and click **Add -> Local DBMS**.
3. Set a password (e.g., `password123`) and click **Start**.
4. Note your connection details:
   - URI: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: `password123`
5. Open Neo4j Browser and run `:play movies`, then execute the dataset script.
   *(Alternatively, run `python load_data.py` from this project to load the data automatically!)*

### Option B: Neo4j AuraDB (Cloud - Recommended & Free)
1. Go to [Neo4j Aura Console](https://console.neo4j.io/) and sign in.
2. Click **New Instance** -> Select **AuraDB Free**.
3. Download the generated credentials file containing your **Connection URI** and **Password**.
4. Once the instance is active, you can load the dataset by running:
   ```powershell
   python load_data.py
   ```

---

## Python Setup & Installation

### 1. Clone or Open the Project
Open PowerShell and navigate into the project directory:
```powershell
cd "C:\Users\Nikhita Rajendra\.gemini\antigravity\scratch\movie-kg-rag"
```

### 2. (Optional) Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## Environment Variables

Copy `.env.example` to create your active `.env` file:
```powershell
Copy-Item .env.example .env
```

Edit `.env` using VS Code or Notepad:
```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_actual_password
NEO4J_DATABASE=neo4j

# Ollama Local LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

---

## Loading the Movies Dataset

If your Neo4j database is empty, run the automated dataset loader:
```powershell
python load_data.py
```
This loads all official movies, actors, directors, and relationships into your database.

---

## Running the Application

### 1. Run the Test Suite
Verify that validation rules and configurations are functional:
```powershell
python test_pipeline.py
```

### 2. Start the Streamlit Web Application
```powershell
streamlit run app.py
```
Streamlit will launch locally at `http://localhost:8501`.

---

## Example Questions

Try asking the following questions in the application:

1. **Movie Information**:
   - *"Tell me about The Matrix."*
   - *"When was The Matrix released?"*
2. **Movie Cast**:
   - *"Who acted in The Matrix?"*
   - *"Who are the actors in Apollo 13?"*
3. **Director Information**:
   - *"Who directed The Matrix?"*
   - *"What movies did Rob Reiner direct?"*
4. **Actor Filmography**:
   - *"What movies has Tom Hanks acted in?"*
   - *"Which movies did Keanu Reeves act in?"*
5. **Actor Collaboration**:
   - *"Which movies did Tom Hanks and Meg Ryan appear in together?"*
6. **Filtered Search**:
   - *"Find movies released after 2000."*
   - *"Show me movies released in 1999."*
7. **Graph Recommendations**:
   - *"Recommend movies similar to The Matrix."*
   - *(Or visit the dedicated Graph Recommendations tab)*

---

## Screenshots

Screenshots of the application can be added to the `screenshots/` directory:
- `screenshots/main_interface.png`: Main interface showing live database metrics and question input.
- `screenshots/qa_cypher_result.png`: Q&A response displaying final grounded answer and generated Cypher.
- `screenshots/recommendation_tab.png`: Graph-based recommendation tab showing shared entity score.

---

## Limitations

- **Dataset Scope**: The standard Neo4j Movies dataset contains approximately 170 nodes and 250 relationships. Queries for entities outside this dataset (e.g., *Inception*, *Oppenheimer*) will return no records.
- **Topological Recommendations**: Recommendations are based solely on 2nd-degree graph entity connections (shared actors/directors) rather than collaborative user ratings or semantic embeddings.
- **Strict Read-Only Mode**: Write operations are blocked by design; the system cannot dynamically append new movies.

---

## Future Enhancements

- **Hybrid Graph + Vector RAG**: Combine graph relations with node vector embeddings (using Neo4j vector index).
- **Expanded Knowledge Graph**: Ingest TMDB or IMDb full dumps for comprehensive coverage.
- **Graph Visualization**: Integrate an interactive network graph renderer (like `pyvis` or `vis.js`) directly in Streamlit.
- **Multi-Turn Conversational Memory**: Maintain conversational history across consecutive queries.

---

## Conclusion

This project successfully bridges structured knowledge representation with generative AI. By replacing opaque vector proximity with deterministic Cypher queries over a Neo4j Knowledge Graph, it eliminates hallucinations, provides clear auditability (inspectable Cypher and context), and showcases a practical Graph RAG architecture.
