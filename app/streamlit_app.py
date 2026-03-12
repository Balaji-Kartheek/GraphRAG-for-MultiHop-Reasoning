"""
Streamlit UI for GraphRAG system
Interactive interface with graph visualization
"""
import streamlit as st
from pyvis.network import Network
import streamlit.components.v1 as components
from typing import List, Dict

from reasoning.multihop import MultiHopReasoner
from generation.answer_generator import AnswerGenerator
from config.logger import log

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
    
    # Add nodes and edges from paths
    nodes_added = set()
    edges_added = set()
    
    for path in graph_paths:
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
    
    # Generate HTML
    html = net.generate_html()
    return html


def main():
    """Main Streamlit app"""
    
    # Title
    st.title("🧠 GraphRAG: Multi-Hop Reasoning System")
    st.markdown("*Knowledge Graph + Vector Retrieval for Tech & AI News*")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        graph_depth = st.slider(
            "Graph Traversal Depth",
            min_value=1,
            max_value=5,
            value=3,
            help="How many hops to traverse in the knowledge graph"
        )
        
        top_k_vector = st.slider(
            "Top K Documents",
            min_value=1,
            max_value=10,
            value=5,
            help="Number of similar documents to retrieve"
        )
        
        st.divider()
        
        st.header("📊 System Stats")
        if st.button("Refresh Stats"):
            st.info("Stats will be displayed here")
        
        st.divider()
        
        st.header("📝 Query History")
        if st.session_state.query_history:
            for i, query in enumerate(reversed(st.session_state.query_history[-5:]), 1):
                st.text(f"{i}. {query[:50]}...")
    
    # Main content - 3 columns
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
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
                search_button = True
    
    # Process query if button clicked
    if search_button and query:
        try:
            with st.spinner("🔄 Processing query..."):
                # Add to history
                st.session_state.query_history.append(query)
                
                # Retrieve context
                context = st.session_state.reasoner.retrieve_context(
                    query,
                    graph_depth=graph_depth,
                    top_k_vector=top_k_vector
                )
                
                # Format context
                formatted_context = st.session_state.reasoner.format_context_for_llm(context)
                
                # Generate answer
                result = st.session_state.generator.generate_query_result(
                    query,
                    context,
                    formatted_context
                )
                
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