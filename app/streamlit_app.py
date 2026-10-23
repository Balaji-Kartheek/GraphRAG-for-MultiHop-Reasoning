"""
Streamlit UI for GraphRAG system
<<<<<<< HEAD
Interactive interface with graph visualization
"""
import streamlit as st
from pyvis.network import Network
import streamlit.components.v1 as components
from typing import List, Dict
=======
Interactive interface with graph visualization.
Supports multilingual (UI, query, response) and voice (STT + TTS).
"""
import os
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
import streamlit as st
from pyvis.network import Network
import streamlit.components.v1 as components
from typing import List, Dict, Optional
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e

from reasoning.multihop import MultiHopReasoner
from generation.answer_generator import AnswerGenerator
from config.logger import log
<<<<<<< HEAD
=======
from utils.translate import (
    SUPPORTED_LANGUAGES,
    get_ui_label,
    translate_to_english,
    translate_to_language,
)
from utils.voice import speech_to_text, text_to_speech
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e

# Page config
st.set_page_config(
    page_title="GraphRAG System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "reasoner" not in st.session_state:
    st.session_state.reasoner = MultiHopReasoner()
    st.session_state.generator = AnswerGenerator()
    st.session_state.query_history = []
<<<<<<< HEAD
=======
if "lang" not in st.session_state:
    st.session_state.lang = "en"
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None
if "last_answer_lang" not in st.session_state:
    st.session_state.last_answer_lang = "en"

# Optional: mic recorder (install streamlit-mic-recorder)
try:
    from streamlit_mic_recorder import mic_recorder
    HAS_MIC_RECORDER = True
except ImportError:
    HAS_MIC_RECORDER = False
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e


def create_graph_visualization(graph_paths: List[List[str]]) -> str:
    """
    Create interactive graph visualization using PyVis
    
    Returns HTML string
    """
    net = Network(
        height="500px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#000000",
        directed=True
    )
    
    # Configure physics
    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -80000,
                "centralGravity": 0.3,
                "springLength": 200,
                "springConstant": 0.04
            }
        },
        "nodes": {
            "font": {"size": 16}
        },
        "edges": {
            "font": {"size": 12},
            "arrows": {"to": {"enabled": true}}
        }
    }
    """)
    
<<<<<<< HEAD
    # Add nodes and edges from paths
    nodes_added = set()
    edges_added = set()
    
    for path in graph_paths:
=======
    # Add all nodes first, then edges (PyVis requires nodes to exist before add_edge)
    nodes_added = set()
    edges_to_add = []
    
    for path in graph_paths:
        path = [n for n in path if n and str(n).strip()]
        if len(path) < 2:
            continue
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
        for i, node in enumerate(path):
            if node not in nodes_added:
                net.add_node(
                    node,
                    label=node,
                    title=node,
                    color="#4CAF50" if i == 0 else "#2196F3",
                    size=30 if i == 0 else 20
                )
                nodes_added.add(node)
<<<<<<< HEAD
            
            # Add edges
            if i < len(path) - 1:
                edge = (path[i], path[i + 1])
                if edge not in edges_added:
                    net.add_edge(
                        path[i],
                        path[i + 1],
                        title="",
                        color="#888888"
                    )
                    edges_added.add(edge)
=======
            if i < len(path) - 1:
                edges_to_add.append((path[i], path[i + 1]))
    
    edges_added = set()
    for a, b in edges_to_add:
        if (a, b) not in edges_added and a in nodes_added and b in nodes_added:
            net.add_edge(a, b, title="", color="#888888")
            edges_added.add((a, b))
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
    
    # Generate HTML
    html = net.generate_html()
    return html


def main():
    """Main Streamlit app"""
<<<<<<< HEAD
    
    # Title
    st.title("🧠 GraphRAG: Multi-Hop Reasoning System")
    st.markdown("*Knowledge Graph + Vector Retrieval for Tech & AI News*")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        graph_depth = st.slider(
            "Graph Traversal Depth",
=======
    lang = st.session_state.lang
    L = lambda key: get_ui_label(key, lang)
    
    # Title (localized)
    st.title("🧠 " + L("title"))
    st.markdown("*" + L("subtitle") + "*")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ " + L("settings"))
        
        # Language selector (Apply to take effect)
        lang_options = list(SUPPORTED_LANGUAGES.keys())
        idx = lang_options.index(lang) if lang in lang_options else 0
        selected_lang = st.selectbox(
            L("language"),
            options=lang_options,
            format_func=lambda x: SUPPORTED_LANGUAGES[x],
            index=idx,
            key="lang_select",
        )
        if st.button(L("apply"), key="apply_lang"):
            st.session_state.lang = selected_lang
            st.rerun()
        lang = st.session_state.lang
        
        graph_depth = st.slider(
            L("graph_traversal_depth"),
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
            min_value=1,
            max_value=5,
            value=3,
            help="How many hops to traverse in the knowledge graph"
        )
        
        top_k_vector = st.slider(
<<<<<<< HEAD
            "Top K Documents",
=======
            L("top_k_documents"),
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
            min_value=1,
            max_value=10,
            value=5,
            help="Number of similar documents to retrieve"
        )
        
        st.divider()
        
<<<<<<< HEAD
        st.header("📊 System Stats")
        if st.button("Refresh Stats"):
=======
        st.header("📊 " + L("system_stats"))
        if st.button(L("refresh_stats")):
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
            st.info("Stats will be displayed here")
        
        st.divider()
        
<<<<<<< HEAD
        st.header("📝 Query History")
        if st.session_state.query_history:
            for i, query in enumerate(reversed(st.session_state.query_history[-5:]), 1):
                st.text(f"{i}. {query[:50]}...")
=======
        st.header("📝 " + L("query_history"))
        if st.session_state.query_history:
            for i, q in enumerate(reversed(st.session_state.query_history[-5:]), 1):
                st.text(f"{i}. {q[:50]}...")
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
    
    # Main content - 3 columns
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
<<<<<<< HEAD
    # Column 1: Query Input
    with col1:
        st.header("🔍 Query Input")
        
        query = st.text_area(
            "Enter your question:",
            height=150,
            placeholder="Example: Which companies collaborate with organizations funded by Microsoft?"
        )
        
        search_button = st.button("🚀 Search", type="primary", use_container_width=True)
        
        # Example queries
        st.divider()
        st.subheader("💡 Example Queries")
        
        examples = [
            "Which companies collaborate with organizations funded by Microsoft?",
            "What is the relationship between OpenAI and Nvidia?",
            "Who are the partners of companies that invested in AI startups?",
            "What partnerships involve companies working with Google?"
        ]
        
        for example in examples:
            if st.button(f"📌 {example[:40]}...", use_container_width=True, key=example):
                query = example
=======
    # Column 1: Query Input (with voice)
    with col1:
        st.header("🔍 " + L("query_input"))
        
        query = ""
        
        # Voice input
        st.caption(L("voice_query"))
        if HAS_MIC_RECORDER:
            audio = mic_recorder(
                start_prompt="🎤 " + L("record"),
                stop_prompt="⏹ " + L("stop"),
                key="mic",
            )
            audio_bytes = None
            if audio is not None:
                audio_bytes = audio.get("bytes") if isinstance(audio, dict) else (audio if isinstance(audio, bytes) else None)
            if audio_bytes:
                if st.button("🔄 " + L("convert_voice_to_text"), key="stt_btn"):
                    with st.spinner(L("converting")):
                        text_out, err = speech_to_text(audio_bytes)
                        if text_out:
                            st.session_state.voice_query_text = text_out
                            st.success((text_out[:80] + ("..." if len(text_out) > 80 else "")))
                        else:
                            st.error(err or L("could_not_recognize"))
            if st.session_state.get("voice_query_text"):
                query = st.session_state.voice_query_text
        else:
            audio_file = st.file_uploader(
                L("record_or_upload"),
                type=["wav", "mp3", "ogg"],
                key="audio_upload"
            )
            if audio_file:
                raw = audio_file.read()
                if st.button("🔄 " + L("convert_voice_to_text"), key="stt_upload"):
                    with st.spinner(L("converting")):
                        text_out, err = speech_to_text(raw, content_type=audio_file.type)
                        if text_out:
                            st.session_state.voice_query_text = text_out
                            st.success((text_out[:80] + ("..." if len(text_out) > 80 else "")))
                        else:
                            st.error(err or L("could_not_recognize"))
                if st.session_state.get("voice_query_text"):
                    query = st.session_state.voice_query_text
        
        st.caption(L("or_type"))
        query = st.text_area(
            L("enter_question"),
            value=query,
            height=120,
            placeholder="Example: Which companies collaborate with organizations funded by Microsoft?" if lang == "en" else "",
            key="query_ta"
        )
        
        search_button = st.button("🚀 " + L("search"), type="primary", use_container_width=True)
        
        st.divider()
        st.subheader("💡 " + L("example_queries"))
        
        examples_en = [
            "Which companies collaborate with organizations funded by Microsoft?",
            "What is the relationship between OpenAI and Nvidia?",
            "Who are the partners of companies that invested in AI startups?",
            "What partnerships involve companies working with Google?",
        ]
        
        for i, ex in enumerate(examples_en):
            display_text = translate_to_language(ex, lang) if lang != "en" else ex
            btn_label = f"📌 {display_text[:45]}{'...' if len(display_text) > 45 else ''}"
            if st.button(btn_label, use_container_width=True, key=f"ex_{i}_{lang}"):
                query = ex
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
                search_button = True
    
    # Process query if button clicked
    if search_button and query:
        try:
<<<<<<< HEAD
            with st.spinner("🔄 Processing query..."):
                # Add to history
                st.session_state.query_history.append(query)
                
                # Retrieve context
                context = st.session_state.reasoner.retrieve_context(
                    query,
=======
            with st.spinner("🔄 " + L("processing")):
                # Translate query to English for retrieval (graph/vector stay in English)
                query_en = translate_to_english(query, lang) if lang != "en" else query
                st.session_state.query_history.append(query)
                
                # Retrieve context using English query
                context = st.session_state.reasoner.retrieve_context(
                    query_en,
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
                    graph_depth=graph_depth,
                    top_k_vector=top_k_vector
                )
                
<<<<<<< HEAD
                # Format context
                formatted_context = st.session_state.reasoner.format_context_for_llm(context)
                
                # Generate answer
                result = st.session_state.generator.generate_query_result(
                    query,
=======
                formatted_context = st.session_state.reasoner.format_context_for_llm(context)
                
                # Generate answer (in English)
                result = st.session_state.generator.generate_query_result(
                    query_en,
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
                    context,
                    formatted_context
                )
                
<<<<<<< HEAD
                # Column 2: Graph Visualization
                with col2:
                    st.header("🕸️ Knowledge Graph Paths")
                    
                    if result.graph_paths:
                        # Create graph visualization
                        graph_html = create_graph_visualization(result.graph_paths)
                        components.html(graph_html, height=550)
                        
                        # Show paths as text
                        with st.expander("📋 View Graph Paths as Text"):
                            for i, path in enumerate(result.graph_paths[:10], 1):
                                st.text(f"{i}. {' → '.join(path)}")
                    else:
                        st.info("No graph paths found for this query")
                
                # Column 3: Answer and Sources
                with col3:
                    st.header("💡 Answer")
                    
                    st.success(result.answer)
                    
                    st.divider()
                    
                    st.subheader("🔗 Reasoning Path")
                    for i, step in enumerate(result.reasoning_path, 1):
                        st.text(f"{i}. {step[:100]}...")
                    
                    st.divider()
                    
                    st.subheader("📚 Source Articles")
                    for i, article in enumerate(result.source_articles, 1):
                        with st.expander(f"Source {i}: {article.get('source', 'Unknown')}"):
                            st.text(f"Article ID: {article['article_id']}")
                            if article.get('title'):
                                st.text(f"Title: {article['title']}")
        
        except Exception as e:
            st.error(f"❌ Error processing query: {e}")
=======
                # Translate answer to user language for display
                display_answer = translate_to_language(result.answer, lang) if lang != "en" else result.answer
                st.session_state.last_answer = display_answer
                st.session_state.last_answer_lang = lang
                
                # Column 2: Graph Visualization (labels stay in English)
                with col2:
                    st.header("🕸️ " + L("graph_paths"))
                    
                    if result.graph_paths:
                        graph_html = create_graph_visualization(result.graph_paths)
                        components.html(graph_html, height=550)
                        with st.expander("📋 " + L("view_paths")):
                            for i, path in enumerate(result.graph_paths[:10], 1):
                                st.text(f"{i}. {' → '.join(path)}")
                    else:
                        st.info(L("no_graph_paths"))
                
                # Column 3: Answer and Sources
                with col3:
                    st.header("💡 " + L("answer"))
                    
                    if getattr(result, "insufficient_context", False):
                        st.warning("⚠️ " + L("no_data_warning"))
                        st.info(L("try_rephrasing"))
                    st.success(display_answer)
                    
                    # Play answer (TTS)
                    if st.session_state.last_answer:
                        if st.button("🔊 " + L("play_answer"), key="tts_btn"):
                            audio_bytes = text_to_speech(st.session_state.last_answer, st.session_state.last_answer_lang)
                            if audio_bytes:
                                st.audio(audio_bytes, format="audio/mpeg")
                            else:
                                st.caption("TTS unavailable for this language or text.")
                    
                    st.divider()
                    
                    st.subheader("🔗 " + L("reasoning_path"))
                    if result.reasoning_path:
                        for i, step in enumerate(result.reasoning_path, 1):
                            step_display = translate_to_language(step, lang) if lang != "en" else step
                            st.text(f"{i}. {step_display[:100]}{'...' if len(step_display) > 100 else ''}")
                    else:
                        st.caption(L("no_reasoning"))
                    
                    st.divider()
                    
                    st.subheader("📚 " + L("source_articles"))
                    if result.source_articles:
                        for i, article in enumerate(result.source_articles, 1):
                            with st.expander(f"Source {i}: {article.get('source', 'Unknown')}"):
                                st.text(f"Article ID: {article['article_id']}")
                                if article.get('title'):
                                    st.text(f"Title: {article['title']}")
                    else:
                        st.caption(L("no_sources"))
        
        except Exception as e:
            st.error("❌ " + L("error") + f": {e}")
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
            log.error(f"Streamlit query error: {e}")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray;'>
    GraphRAG System v1.0 | Built with Neo4j, ChromaDB, Gemini | 
    <a href='/docs'>API Documentation</a>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()