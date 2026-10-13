"""
app.py
Streamlit Web Application for Movie Knowledge Graph RAG.
Provides a clean, interactive user interface for querying the Neo4j Movies dataset,
generating Cypher queries via local Ollama LLM, validating Cypher, retrieving graph data,
and producing grounded natural-language answers.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from config import (
    NEO4J_URI,
    NEO4J_USERNAME,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    GRAPH_SCHEMA_TEXT,
    check_config_status
)
from neo4j_connection import get_neo4j_connection
from rag_pipeline import MovieGraphRAGPipeline
from recommender import MovieRecommender
from ollama_client import get_ollama_client

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Movie Knowledge Graph RAG",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished presentation and viva demonstration
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .answer-card {
        background-color: #F8FAFC;
        border-left: 5px solid #3B82F6;
        padding: 1.2rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-size: 1.05rem;
        line-height: 1.6;
    }
    .metric-box {
        background-color: #F1F5F9;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
    }
    .badge-success {
        color: #059669;
        font-weight: 600;
    }
    .badge-error {
        color: #DC2626;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def get_cached_pipeline(model_name: str) -> MovieGraphRAGPipeline:
    """Helper to initialize the RAG pipeline with selected Ollama model."""
    conn = get_neo4j_connection()
    return MovieGraphRAGPipeline(connection=conn, model=model_name)


def main():
    # Application Title & Subtitle
    st.markdown('<div class="main-header">🎬 Movie Knowledge Graph RAG</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Ask questions about movies, actors, and directors using Neo4j + Local Ollama (llama3.2:3b).</div>',
        unsafe_allow_html=True
    )

    # --------------------------------------------------------------------------
    # SIDEBAR: SYSTEM STATUS & CONFIGURATION
    # --------------------------------------------------------------------------
    with st.sidebar:
        st.header("⚙️ System Status")

        conn = get_neo4j_connection()
        is_neo_ok, neo_msg = conn.verify_connectivity()

        # Neo4j Status Display
        if is_neo_ok:
            st.markdown("🟢 **Neo4j:** Connected")
            st.caption(f"URI: `{NEO4J_URI}`")
            # Fetch DB Stats
            stats = conn.get_database_statistics()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Movies", stats.get("movie_count", 0))
            with col2:
                st.metric("People", stats.get("person_count", 0))
        else:
            st.markdown("🔴 **Neo4j:** Disconnected")
            st.caption(neo_msg)

        st.divider()

        # Ollama Status Display
        ollama = get_ollama_client()
        is_ollama_ok, ollama_msg, available_models = ollama.check_health()

        if is_ollama_ok and any(OLLAMA_MODEL in m for m in available_models):
            st.markdown(f"🟢 **Ollama:** Online")
            st.caption(f"Endpoint: `{OLLAMA_BASE_URL}`")
        elif is_ollama_ok:
            st.markdown("🟡 **Ollama:** Online (Model Missing)")
            st.caption(ollama_msg)
        else:
            st.markdown("🔴 **Ollama:** Offline")
            st.caption(ollama_msg)

        st.divider()

        # LLM Model Selection
        model_options = available_models if available_models else [OLLAMA_MODEL]
        default_index = 0
        if OLLAMA_MODEL in model_options:
            default_index = model_options.index(OLLAMA_MODEL)

        selected_model = st.selectbox(
            "Selected Ollama Model",
            options=model_options,
            index=default_index,
            help="Local model running via Ollama on your computer."
        )

        st.divider()

        # Quick Example Questions for Viva & Demonstration
        st.subheader("💡 Sample Questions")
        sample_questions = [
            "Who directed The Matrix?",
            "Who acted in The Matrix?",
            "What movies has Tom Hanks acted in?",
            "What movies did Christopher Nolan direct?",
            "When was The Matrix released?",
            "Which movies did Tom Hanks and Meg Ryan appear in together?",
            "Tell me about The Matrix.",
            "Find movies released after 2000.",
            "Recommend movies similar to The Matrix."
        ]

        for q in sample_questions:
            if st.button(q, key=f"btn_{q}", use_container_width=True):
                st.session_state["query_input"] = q

        st.divider()
        with st.expander("📖 Graph Schema Reference"):
            st.code(GRAPH_SCHEMA_TEXT, language="cypher")

    # --------------------------------------------------------------------------
    # TABS INTERFACE
    # --------------------------------------------------------------------------
    tab_qa, tab_rec, tab_schema = st.tabs([
        "💬 Movie Q&A (Graph RAG)",
        "🎯 Graph Recommendations",
        "📊 Database Explorer & Architecture"
    ])

    # ==========================================================================
    # TAB 1: MOVIE Q&A (GRAPH RAG)
    # ==========================================================================
    with tab_qa:
        # Check connection warnings
        if not is_neo_ok:
            st.warning(
                "⚠️ **Neo4j is not connected.** Please ensure Neo4j Desktop or Neo4j AuraDB is running, "
                "load the Movies dataset (`python load_data.py`), and check your `.env` settings."
            )
        if not is_ollama_ok:
            st.warning(
                f"⚠️ **Ollama is not running.** Start Ollama on your machine or run `ollama serve` in PowerShell."
            )

        # Input Area
        default_query = st.session_state.get("query_input", "")
        user_question = st.text_input(
            "Enter your question about movies, actors, or directors:",
            value=default_query,
            placeholder="e.g. Who directed The Matrix?",
            key="main_question_input"
        )

        col_btn1, col_btn2 = st.columns([1, 5])
        with col_btn1:
            ask_pressed = st.button("🚀 Ask Question", type="primary", use_container_width=True)
        with col_btn2:
            if st.button("Clear", use_container_width=False):
                st.session_state["query_input"] = ""
                st.rerun()

        # Pipeline Execution
        if ask_pressed and user_question.strip():
            pipeline = get_cached_pipeline(selected_model)

            with st.spinner("Processing through Knowledge Graph RAG Pipeline via local Ollama..."):
                result = pipeline.run(user_question.strip())

            # Display Final Answer
            st.markdown("### Answer")
            st.markdown(
                f'<div class="answer-card">{result["final_answer"]}</div>',
                unsafe_allow_html=True
            )

            # Technical Details in Expanders (Requested for Viva & Demonstration)
            col_t1, col_t2 = st.columns(2)

            with col_t1:
                with st.expander("▼ Generated Cypher Query", expanded=True):
                    if result["cypher_query"]:
                        st.code(result["cypher_query"], language="cypher")
                        if result["is_valid_cypher"]:
                            st.success("✅ Security Validation: Read-only query confirmed.")
                        else:
                            st.error(f"❌ Security Validation Failed: {result.get('error')}")
                    else:
                        st.info("No Cypher query was generated.")

            with col_t2:
                with st.expander("▼ Retrieved Knowledge Graph Context", expanded=True):
                    if result["raw_results"]:
                        st.write(f"**Records Retrieved:** {len(result['raw_results'])}")
                        # Convert records to a DataFrame for clean presentation
                        try:
                            df = pd.DataFrame(result["raw_results"])
                            st.dataframe(df, use_container_width=True)
                        except Exception:
                            st.json(result["raw_results"])
                    else:
                        st.write("No matching records found in Neo4j.")
                        st.code(result.get("context_text", "Empty context"), language="text")

            # Execution Pipeline Trace
            with st.expander("⏱️ Pipeline Execution Trace & Timing"):
                st.write(f"**Total Execution Time:** `{result['execution_time_sec']} seconds`")
                st.write(f"**LLM Backend:** `Ollama ({selected_model})`")
                st.write("**Step-by-step Execution Log:**")
                for step in result.get("pipeline_steps", []):
                    st.text(f"• {step}")

        elif ask_pressed and not user_question.strip():
            st.warning("Please enter a question before clicking Ask.")

    # ==========================================================================
    # TAB 2: GRAPH RECOMMENDATIONS
    # ==========================================================================
    with tab_rec:
        st.subheader("🎯 Graph-Based Movie Recommendations")
        st.markdown("""
        This recommendation engine uses **2nd-degree topological graph relationships** in Neo4j.
        Instead of machine learning collaborative filtering or black-box vectors, it traverses shared
        entities (such as **shared actors, directors, and writers**) to calculate connection strength.
        """)

        rec_movie = st.text_input(
            "Select or enter a movie title to find recommendations for:",
            value="The Matrix",
            key="rec_movie_input"
        )
        rec_limit = st.slider("Maximum recommendations:", min_value=1, max_value=10, value=5)

        if st.button("🔍 Find Recommendations", key="btn_run_rec"):
            if not rec_movie.strip():
                st.warning("Please enter a movie title.")
            else:
                recommender = MovieRecommender(conn)
                with st.spinner(f"Traversing graph connections for '{rec_movie}'..."):
                    rec_result = recommender.get_recommendations(rec_movie.strip(), limit=rec_limit)

                if rec_result.get("found") and rec_result.get("recommendations"):
                    st.success(f"Found recommendations for **{rec_result['target_movie']}**:")

                    for idx, item in enumerate(rec_result["recommendations"], start=1):
                        with st.container():
                            st.markdown(
                                f"#### {idx}. {item['title']} ({item.get('released', 'N/A')})"
                            )
                            if item.get("tagline"):
                                st.markdown(f"*{item['tagline']}*")
                            st.markdown(f"**Connection Score:** `{item['score']}` shared entities")
                            st.info(f"💡 {item['explanation']}")
                            st.divider()

                    with st.expander("▼ Graph Recommendation Cypher Query"):
                        st.code(rec_result.get("cypher_query", ""), language="cypher")
                else:
                    st.info(f"No graph recommendations found for '{rec_movie}'. Ensure the title exists in the Neo4j dataset.")

    # ==========================================================================
    # TAB 3: DATABASE EXPLORER & ARCHITECTURE
    # ==========================================================================
    with tab_schema:
        st.subheader("🏛️ Architecture: Graph RAG Flow with Local Ollama")

        st.markdown("""
        ```
        User Question
             │
             ▼
        Streamlit UI
             │
             ▼
        Ollama Local LLM (llama3.2:3b) Generates Cypher (with Schema & Constraints)
             │
             ▼
        Cypher Security Validation (Read-Only Enforcement)
             │
             ▼
        Neo4j Knowledge Graph Query Execution
             │
             ▼
        Retrieved Graph Context Construction
             │
             ▼
        Ollama Local LLM (llama3.2:3b) Synthesizes Grounded Answer
             │
             ▼
        Grounded Natural-Language Answer Displayed in UI
        ```
        """)

        st.subheader("📚 Sample Movies in Database")
        if is_neo_ok:
            sample_titles = conn.get_sample_movie_titles(limit=15)
            if sample_titles:
                st.write(", ".join([f"`{t}`" for t in sample_titles]))
            else:
                st.write("No movies found. Load dataset using `python load_data.py`.")
        else:
            st.info("Connect to Neo4j to view sample movies.")


if __name__ == "__main__":
    main()
