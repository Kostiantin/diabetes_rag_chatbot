import streamlit as st
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
import openai

# Constants
CHROMA_PATH = "chroma"
PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

# Load API key
load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]

# Load DB & models once (cache for performance)
@st.cache_resource
def load_db():
    embedding_function = OpenAIEmbeddings()
    return Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

db = load_db()
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# Streamlit UI
st.title("🩺 Diabetes RAG Chatbot")
st.write("Ask questions based on the diabetes PDF knowledge base.")

# Custom CSS for input styling
st.markdown("""
    <style>
    /* Style for text input */
    .stTextInput > div > div > input {
        border: 2px solid #ccc;
        border-radius: 8px;
        padding: 6px;
    }
    /* Blue border on focus */
    .stTextInput > div > div > input:focus {
        border: 2px solid #4da6ff;
        outline: none;
        box-shadow: 0 0 8px rgba(77, 166, 255, 0.5);
    }
    .st-c2,.st-c1, .st-c0, .st-bz {
        border-color: #4da6ff!important;        
    }
    </style>
""", unsafe_allow_html=True)

query_text = st.text_input("💬 Enter your question:")

if query_text:

    status = st.empty()
    status.write("Analizing...Please Wait")

    # Search DB
    results = db.similarity_search_with_relevance_scores(query_text, k=3)

    if len(results) == 0 or results[0][1] < 0.7:

        st.warning("⚠️ Unable to find matching results.")
        status.empty()

    else:
        # Build context
        context_text = "\n\n---\n\n".join([doc.page_content for doc, _ in results])
        prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        prompt = prompt_template.format(context=context_text, question=query_text)

        # Query LLM
        response_text = llm.predict(prompt)

        # Format sources
        sources = [
            f"{doc.metadata.get('source', 'unknown')} (page {doc.metadata.get('page', 'N/A') +1})"
            for doc, _ in results
        ]

        # Display answer
        st.subheader("🤖 Response:")
        st.write(response_text)

        # Show sources
        st.subheader("📚 Sources:")

        for doc, _ in results:
            src_path = doc.metadata.get("source", "unknown")
            page_num = doc.metadata.get("page", "N/A")
            file_name = os.path.basename(src_path) if src_path != "unknown" else "unknown.pdf"

            cols = st.columns([3,1])  # text on left, button on right
            with cols[0]:
                st.write(f"- {file_name} (page {page_num+1})")

            if src_path != "unknown" and os.path.exists(src_path):
                with cols[1]:
                    with open(src_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download",
                            data=f,
                            file_name=file_name,
                            mime="application/pdf",
                            key=f"download-{file_name}-{page_num}"
                        )


        status.empty()
