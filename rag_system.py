import os
import shutil
import time
import gc
import streamlit as st
import logging
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever

# ==========================================
# CONFIG
# ==========================================

PERSIST_DIRECTORY = "vector_store"
PDF_FOLDER = "rag_data"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LOG_FILE = "logs.txt"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ==========================================
# EMBEDDINGS (Lazy Loaded)
# ==========================================

@st.cache_resource
def get_embeddings():
    logging.info("Loading embedding model")
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

# ==========================================
# LOAD & SPLIT DOCUMENTS (Cached)
# ==========================================

@st.cache_resource
def load_and_split_documents():

    documents = []

    if not os.path.exists(PDF_FOLDER):
        return []

    for file in os.listdir(PDF_FOLDER):
        if file.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(PDF_FOLDER, file))
            docs = loader.load()

            for doc in docs:
                doc.metadata["source"] = file

            documents.extend(docs)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    return splitter.split_documents(documents)

# ==========================================
# CACHED BM25 RETRIEVER
# ==========================================

@st.cache_resource
def get_bm25():
    split_docs = load_and_split_documents()
    return BM25Retriever.from_documents(split_docs)

# ==========================================
# INDEX MULTIPLE PDFs
# ==========================================

def index_multiple_pdfs():

    logging.info("Indexing PDFs...")

    split_docs = load_and_split_documents()
    embeddings = get_embeddings()

    Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIRECTORY
    )

    logging.info("Indexing completed")

# ==========================================
# REBUILD INDEX
# ==========================================

def rebuild_index(pdf_folder="rag_data"):

    global PDF_FOLDER
    PDF_FOLDER = pdf_folder

    try:
        load_vector_store.clear()
        load_and_split_documents.clear()
        get_bm25.clear()
    except:
        pass

    gc.collect()
    time.sleep(2)

    if os.path.exists(PERSIST_DIRECTORY):
        shutil.rmtree(PERSIST_DIRECTORY, ignore_errors=True)

    index_multiple_pdfs()

    logging.info("Rebuild completed")

# ==========================================
# LOAD VECTOR STORE
# ==========================================

@st.cache_resource
def load_vector_store():

    if not os.path.exists(PERSIST_DIRECTORY):
        raise Exception("Vector store not found. Please rebuild index.")

    embeddings = get_embeddings()

    return Chroma(
        persist_directory=PERSIST_DIRECTORY,
        embedding_function=embeddings
    )

# ==========================================
# HYBRID RETRIEVAL (MMR + BM25)
# ==========================================

def hybrid_retrieve(query, k=5):

    logging.info(f"User Query: {query}")

    vectordb = load_vector_store()

    # 1️⃣ Semantic (MMR)
    retriever = vectordb.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": 10}
    )

    semantic_docs = retriever.invoke(query)

    # 2️⃣ Cached BM25
    bm25 = get_bm25()
    bm25.k = k
    keyword_docs = bm25.invoke(query)

    # 3️⃣ Combine
    combined_docs = semantic_docs + keyword_docs

    # 4️⃣ Remove duplicates
    unique_docs = {}
    for doc in combined_docs:
        unique_docs[doc.page_content] = doc

    final_docs = list(unique_docs.values())[:k]

    if not final_docs:
        logging.warning("No context found")
        return None

    # 5️⃣ Format context
    context_chunks = []
    for doc in final_docs:
        context_chunks.append(
            f"(Source: {doc.metadata.get('source','N/A')}, "
            f"Page: {doc.metadata.get('page', 0) + 1})\n"
            f"{doc.page_content}\n"
        )

    logging.info("Hybrid context retrieved successfully")

    return "\n\n".join(context_chunks)

# ==========================================
# GENERATE RAG ANSWER
# ==========================================

def generate_rag_answer(question, client, model_name):

    try:
        context = hybrid_retrieve(question)

        if not context:
            return "I do not have that information in the institute records."

        TITAN_PERSONA = """
You are the Official Counter Receptionist of TITAN Institute, Sukkur.

Your role:
- Represent the institute professionally.
- Maintain a formal, polite, and respectful tone.
- Address users as "Sir", "Madam", or "Student".
- Provide only institute-related information.
- Politely decline non-institute queries.

Do not use casual language.
Do not provide personal opinions.
Do not generate information beyond official records.
"""

        rag_rules = """
STRICT RESPONSE RULES:

1. Use ONLY the provided context below.
2. Do NOT use prior knowledge.
3. Do NOT guess.
4. Do NOT add extra information.
5. If answer is found:
   - Provide a complete answer.
   - MUST include page citation in this exact format: (Page X).
   - Example: The institute offers 8 courses. (Page 3)
6. If the answer is NOT available in the context:
   - Respond EXACTLY with:
     "I do not have that information in the institute records."
7. Never combine a valid answer with the fallback message.
8. Keep the response concise and professional.
"""

        response = client.chat.completions.create(
            model=model_name,
            temperature=0,
            max_tokens=500,
            messages=[
                {"role": "system", "content": TITAN_PERSONA},
                {"role": "system", "content": rag_rules},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}"}
            ]
        )

        answer = response.choices[0].message.content

        logging.info("======================================")
        logging.info(f"USER: {question}")
        logging.info(f"BOT: {answer}")
        logging.info("======================================")

        return answer
    
    except Exception:
        import traceback
        error_details = traceback.format_exc()
        logging.error(error_details)
        return "We are currently experiencing technical difficulties."
