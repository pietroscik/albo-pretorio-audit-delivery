import streamlit as st
from pathlib import Path
import json
import os

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

st.set_page_config(page_title="Albo Pretorio RAG", page_icon="💬", layout="wide")

@st.cache_resource
def get_vectorstore(ente: str):
    base_dir = Path(f"data/{ente}/albo_download")
    corpus_file = base_dir / "documenti_corpus.jsonl"
    vs_path = base_dir / "faiss_index"

    # Usa un modello di embedding leggero e locale per la privacy e la velocità
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Se l'indice esiste già, caricalo (per non ricalcolarlo ogni volta)
    if vs_path.exists():
        return FAISS.load_local(str(vs_path), embeddings, allow_dangerous_deserialization=True)

    if not corpus_file.exists():
        return None

    # Altrimenti, costruiamo il Vector Store leggendo il corpus
    texts = []
    metadatas = []
    with open(corpus_file, "r", encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            if doc.get("text"):
                texts.append(doc["text"])
                metadatas.append({
                    "pdf_name": doc.get("pdf_name", ""),
                    "oggetto": doc.get("oggetto", "Nessun oggetto"),
                    "data_atto": doc.get("data_atto", ""),
                    "rup": doc.get("responsabile", "Sconosciuto")
                })

    if not texts:
        return None

    vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
    vectorstore.save_local(str(vs_path))
    return vectorstore

def main():
    st.title("💬 Chat con l'Albo Pretorio (RAG)")
    st.markdown("Fai domande sui documenti estratti. L'IA cercherà le risposte direttamente negli atti dell'Ente.")

    data_dir = Path("data")
    if not data_dir.exists():
        st.error("Cartella dati non trovata.")
        st.stop()

    enti = [d.name for d in data_dir.iterdir() if d.is_dir() and (d / "albo_download" / "documenti_corpus.jsonl").exists()]
    if not enti:
        st.error("Nessun ente trovato con un corpus testuale. Esegui la pipeline senza --no-corpus.")
        st.stop()

    selected_ente = st.sidebar.selectbox("Seleziona Ente", enti)

    # Gestione sicura dell'API Key
    if not os.environ.get("GOOGLE_API_KEY"):
        api_key = st.sidebar.text_input("Inserisci GOOGLE_API_KEY", type="password")
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        else:
            st.warning("Per favore, inserisci la tua Google API Key nella barra laterale per usare Gemini.")
            st.stop()

    with st.spinner(f"Caricamento Indice Semantico per {selected_ente.capitalize()}..."):
        vectorstore = get_vectorstore(selected_ente)

    if not vectorstore:
        st.error("Impossibile caricare i documenti.")
        st.stop()

    retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) # Trova i 5 frammenti più rilevanti
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    template = """Sei un revisore legale esperto. Usa i seguenti frammenti estratti dagli atti amministrativi per rispondere alla domanda dell'utente.
Se la risposta non è contenuta nei frammenti, di' chiaramente che le informazioni non sono presenti nei documenti. Non inventare dati.

Contesto:
{context}

Domanda: {question}

Risposta Dettagliata:"""
    prompt = ChatPromptTemplate.from_template(template)

    def format_docs(docs):
        return "\n\n".join(f"[{doc.metadata.get('pdf_name')} - RUP: {doc.metadata.get('rup')}]\n{doc.page_content}" for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # ... Logica di rendering della chat (UI)
    question = st.chat_input("Chiedi qualcosa sugli atti (es. 'Quali lavori sono stati affidati all'impresa Segma?')")
    if question:
        st.chat_message("user").markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Ricerca nei documenti..."):
                docs = retriever.invoke(question)
                response = rag_chain.invoke(question)
                st.markdown(response)
                with st.expander("📄 Documenti Sorgente Analizzati"):
                    for i, d in enumerate(docs):
                        st.markdown(f"**{i+1}. {d.metadata.get('pdf_name')}** (RUP: {d.metadata.get('rup')})")
                        st.caption(d.metadata.get('oggetto'))

if __name__ == "__main__":
    main()