import json
import os
import hashlib
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

try:
    import streamlit as st
except ImportError:  # pragma: no cover - optional dependency
    class _DummyProgress:
        def progress(self, *args, **kwargs):
            return self

        def empty(self):
            return None

    class _DummyStreamlit:
        def progress(self, *args, **kwargs):
            return _DummyProgress()

        def toast(self, *args, **kwargs):
            return None

    st = _DummyStreamlit()

try:
    from langchain_community.vectorstores import FAISS
    from langchain_core.prompts import PromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover - optional dependency
    class PromptTemplate:
        def __init__(self, template: str):
            self.template = template

        @classmethod
        def from_template(cls, template: str):
            return cls(template)

        def format(self, **kwargs):
            return self.template.format(**kwargs)

    class Document:
        def __init__(self, page_content: str = "", metadata: Optional[dict] = None):
            self.page_content = page_content
            self.metadata = metadata or {}

    class RecursiveCharacterTextSplitter:
        def __init__(self, chunk_size=3000, chunk_overlap=300, separators=None):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap

        def split_text(self, text: str):
            text = text or ""
            if not text:
                return []
            chunks = []
            step = max(1, self.chunk_size - self.chunk_overlap)
            start = 0
            total = len(text)
            while start < total:
                end = min(total, start + self.chunk_size)
                chunks.append(text[start:end])
                if end >= total:
                    break
                start += step
            return chunks

    class FAISS:  # pragma: no cover - fallback only
        @classmethod
        def from_texts(cls, *args, **kwargs):
            raise RuntimeError("FAISS non disponibile")

        @classmethod
        def load_local(cls, *args, **kwargs):
            raise RuntimeError("FAISS non disponibile")

    class ChatGoogleGenerativeAI:  # pragma: no cover - fallback only
        def __init__(self, *args, **kwargs):
            raise RuntimeError("langchain_google_genai non disponibile")

    class GoogleGenerativeAIEmbeddings:  # pragma: no cover - fallback only
        def __init__(self, *args, **kwargs):
            raise RuntimeError("langchain_google_genai non disponibile")

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except ImportError:
        HuggingFaceEmbeddings = None

try:
    from langchain_community.chat_models import ChatOllama
except ImportError:
    ChatOllama = None

# Carica automaticamente eventuali variabili da file .env
load_dotenv(override=True)

DEFAULT_EMBEDDING_MODELS = [
    os.environ.get("GOOGLE_EMBEDDING_MODEL", "").strip(),
    "local:sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "text-embedding-004",
    "gemini-embedding-001",
]

DEFAULT_LLM_MODELS = [
    os.environ.get("GOOGLE_LLM_MODEL", "").strip(),
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
]

MODEL_PROFILES = {
    "Locale (Zero Quota API)": {
        "embedding_models": [
            "local:sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ],
        "llm_models": [
            "ollama:llama3.1",
            "ollama:llama3",
            "gemini-2.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash",
        ],
        "embed_batch_size": 500,
        "embed_pause_sec": 0.0,
    },
    "Conservativo (meno quota)": {
        "embedding_models": [
            "text-embedding-004",
            "gemini-embedding-001",
            "local:sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ],
        "llm_models": [
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
        ],
        "embed_batch_size": 30,
        "embed_pause_sec": 62.0,
    },
    "Bilanciato": {
        "embedding_models": [
            "text-embedding-004",
            "gemini-embedding-001",
            "local:sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ],
        "llm_models": [
            "gemini-2.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-1.5-flash",
        ],
        "embed_batch_size": 35,
        "embed_pause_sec": 60.0,
    },
    "Prestazioni (piu' veloce)": {
        "embedding_models": [
            "text-embedding-004",
            "gemini-embedding-001",
            "local:sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ],
        "llm_models": [
            "gemini-2.5-flash",
            "gemini-1.5-flash",
            "gemini-3.1-flash-lite",
        ],
        "embed_batch_size": 40,
        "embed_pause_sec": 60.0,
    },
}

USE_GEMINI_DEFAULT = os.environ.get("RAG_USE_GEMINI_BY_DEFAULT", "").strip().lower() in {
    "1", "true", "yes", "on"
}
USE_LOCAL_RETRIEVER_WITH_GEMINI_DEFAULT = (
    os.environ.get("RAG_USE_LOCAL_RETRIEVER_WITH_GEMINI", "").strip().lower()
    in {"1", "true", "yes", "on"}
)

PROMPT_TEMPLATE = """Sei un assistente per l'analisi di atti amministrativi comunali e trasparenza antifrode (Linee guida AGID e D.Lgs 36/2023). 
Usa i seguenti frammenti di testo estratti dai documenti per rispondere alla domanda in modo analitico e preciso.
Ogni frammento ha un'intestazione con i metadati chiave (Oggetto, CIG, Beneficiario, RUP, Capitolo, Procedura). Usa queste informazioni relazionali (come in un Knowledge Graph) per mappare gli appalti e identificare collegamenti.
Se non conosci la risposta in base al contesto fornito, dì semplicemente che le informazioni non sono presenti nei documenti.
Cita SEMPRE il nome del documento [Fonte: nome_file.pdf] da cui hai preso le informazioni alla fine della tua risposta.
Se pertinenti e disponibili nel contesto, includi sempre l'importo, i codici CIG/CUP e il Beneficiario per garantire la massima trasparenza.

Contesto:
{context}

Domanda: {question}

Risposta:"""


def _split_env_list(raw: str):
    if not raw:
        return []
    return [x.strip() for x in raw.replace("\n", ",").split(",") if x.strip()]


def _unique_non_empty(items):
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_index_manifest(index_dir: Path, embedding_model: Optional[str] = None) -> dict:
    files = []
    for fp in sorted(index_dir.glob("*")):
        if fp.is_file():
            files.append({
                "name": fp.name,
                "size": fp.stat().st_size,
                "sha256": _sha256_file(fp),
            })
    return {
        "files": files,
        "embedding_model": embedding_model,
    }


def _index_is_trusted(index_dir: Path, manifest_path: Path, embedding_model: str) -> bool:
    if not index_dir.exists() or not manifest_path.exists():
        return False
    try:
        expected = json.loads(manifest_path.read_text(encoding="utf-8"))
        if expected.get("embedding_model") != embedding_model:
            return False
        current = _build_index_manifest(index_dir, embedding_model=embedding_model)
    except Exception:
        return False
    return expected == current


def _instantiate_embeddings_candidates(candidates):
    ready = []
    errors = []
    for model_name in _unique_non_empty(candidates):
        if model_name.startswith("local:"):
            if HuggingFaceEmbeddings is None:
                errors.append((model_name, "Modulo mancante. Esegui: pip install sentence-transformers langchain-huggingface"))
                continue
            try:
                local_model = model_name.split("local:", 1)[1]
                ready.append((model_name, HuggingFaceEmbeddings(model_name=local_model)))
            except Exception as exc:
                errors.append((model_name, str(exc)))
        else:
            try:
                # max_retries=0 velocizza il failover sul modello di embedding successivo in caso di quota esaurita
                ready.append((model_name, GoogleGenerativeAIEmbeddings(model=model_name, max_retries=0)))
            except Exception as exc:
                errors.append((model_name, str(exc)))
    return ready, errors


def _load_corpus_documents(corpus_path: Path):
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=300,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            text_content = data.get("text", "")
            if not text_content or len(text_content) < 50:
                continue

            metadata = {
                "pdf_name": data.get("pdf_name", "Sconosciuto"),
                "oggetto": data.get("oggetto", "N/D"),
                "cig": data.get("cig"),
                "cup": data.get("cup"),
                "beneficiario": data.get("beneficiario"),
                "responsabile": data.get("responsabile"),
                "capitolo": data.get("capitolo"),
                "tipo_procedura": data.get("tipo_procedura"),
                "category": data.get("category"),
                "accounting_relevant": data.get("accounting_relevant", False),
            }

            # Prepariamo un prefisso con i metadati chiave per arricchire ogni chunk.
            # Questo migliora drasticamente l'accuratezza del retrieval e il contesto per l'LLM.
            prefix_parts = []
            if metadata["oggetto"] and metadata["oggetto"] != "N/D":
                # Puliamo e tronchiamo l'oggetto per non appesantire troppo
                clean_oggetto = " ".join(str(metadata['oggetto']).split())[:250]
                prefix_parts.append(f"Oggetto: {clean_oggetto}")
            if metadata["cig"]:
                prefix_parts.append(f"CIG: {metadata['cig']}")
            if metadata["cup"]:
                prefix_parts.append(f"CUP: {metadata['cup']}")
            if metadata["beneficiario"]:
                prefix_parts.append(f"Beneficiario: {metadata['beneficiario']}")
            if metadata["responsabile"]:
                prefix_parts.append(f"RUP: {metadata['responsabile']}")
            if metadata["capitolo"]:
                prefix_parts.append(f"Capitolo: {metadata['capitolo']}")
            if metadata["tipo_procedura"]:
                prefix_parts.append(f"Procedura: {metadata['tipo_procedura']}")
                
            prefix = ". ".join(prefix_parts)
            if prefix:
                prefix += ".\n\n"

            chunks = text_splitter.split_text(text_content)
            for chunk in chunks:
                # Aggiungiamo il prefisso a ogni frammento
                enriched_content = prefix + chunk
                documents.append(Document(page_content=enriched_content, metadata=metadata))
    return documents


def _tokenize(text: str):
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_]+", (text or "").lower())


class LocalSearchChain:
    """Fallback locale senza API: ranking lessicale + snippet con fonti."""
    def __init__(self, documents, top_k=6):
        self.top_k = top_k
        self.retriever = LocalTokenRetriever(documents, top_k=top_k)

    def invoke(self, question: str, only_accounting: bool = False, only_personnel_competence: bool = False, k: int = 6) -> str:
        top_docs = self.retriever.invoke(question, only_accounting=only_accounting, only_personnel_competence=only_personnel_competence, k=k)

        if not top_docs:
            return (
                "Modalita' fallback locale attiva: "
                "nessun frammento rilevante trovato."
            )

        lines = [
            "⚠️ **Attenzione: L'Intelligenza Artificiale (Gemini) non è attiva.**",
            "Il sistema sta funzionando come un semplice motore di ricerca testuale. Per ottenere risposte ragionate dall'AI, inserisci la tua `GOOGLE_API_KEY` nel file `.env` e attiva Gemini dal menu laterale.",
            "",
            "**Ecco i documenti che contengono le parole cercate:**",
        ]
        for i, doc in enumerate(top_docs, 1):
            metadata = doc.metadata
            content = doc.page_content
            snippet = " ".join(content.split())[:320]
            source = metadata.get("pdf_name", "Sconosciuto")
            cig = metadata.get("cig")
            cup = metadata.get("cup")
            
            meta_str = f"[Fonte: {source}]"
            if cig: meta_str += f" [CIG: {cig}]"
            if cup: meta_str += f" [CUP: {cup}]"
            
            lines.append(f"{i}. {meta_str}\n   {snippet}...")
        return "\n\n".join(lines)


class LocalTokenRetriever:
    """Retriever lessicale locale compatibile con interfaccia retriever.invoke()."""

    def __init__(self, documents, top_k=6):
        self.top_k = top_k
        self.rows = []
        for doc in documents:
            tokens = set(_tokenize(doc.page_content))
            self.rows.append((tokens, doc))

    def invoke(self, question: str, only_accounting: bool = False, only_personnel_competence: bool = False, k: int = 6):
        q_tokens = set(_tokenize(question))
        if not q_tokens:
            return []

        scored = []
        for tokens, doc in self.rows:
            if only_accounting and not doc.metadata.get("accounting_relevant", False):
                continue
            if only_personnel_competence and not doc.metadata.get("is_personnel_competence_relevant", False):
                continue
            overlap = len(tokens & q_tokens)
            if overlap:
                scored.append((overlap, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[: k]]


class LLMFailoverRAGChain:
    def __init__(self, retriever, prompt_template: str, llm_models):
        self.retriever = retriever
        self.prompt = PromptTemplate.from_template(prompt_template)
        self.llm_candidates = []
        self.last_model = None
        self.cooldowns = {}
        errs = []
        for model_name in _unique_non_empty(llm_models):
            try:
                if model_name.startswith("ollama:"):
                    if ChatOllama is None:
                        errs.append((model_name, "Libreria mancante per Ollama"))
                        continue
                    local_model = model_name.split("ollama:", 1)[1]
                    llm = ChatOllama(model=local_model, temperature=0.1)
                    self.llm_candidates.append((model_name, llm))
                else:
                    # max_retries=0 disabilita il retry interno per far scattare subito il nostro failover
                    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.1, max_retries=0)
                    self.llm_candidates.append((model_name, llm))
            except Exception as exc:
                errs.append((model_name, str(exc)))

        if not self.llm_candidates:
            details = "\n".join([f"- {m}: {e}" for m, e in errs]) or "- nessun dettaglio"
            raise RuntimeError(
                "Nessun modello LLM Gemini inizializzabile. Imposta GOOGLE_LLM_MODEL_PRIORITY o GOOGLE_LLM_MODEL.\n"
                f"Tentativi:\n{details}"
            )

    def _format_docs(self, docs):
        formatted = []
        for d in docs:
            source = d.metadata.get('pdf_name', 'Sconosciuto')
            cig = d.metadata.get('cig')
            cup = d.metadata.get('cup')
            
            meta_str = f"[Fonte: {source}]"
            if cig: meta_str += f" [CIG: {cig}]"
            if cup: meta_str += f" [CUP: {cup}]"
                
            formatted.append(f"{meta_str}\nTesto: {d.page_content}")
        return "\n\n".join(formatted)

    def invoke(self, question: str, only_accounting: bool = False) -> str:
        if hasattr(self.retriever, "as_retriever"):
            k_fetch = 20 if only_accounting else 6
            docs = self.retriever.as_retriever(search_kwargs={"k": k_fetch}).invoke(question)
            if only_accounting:
                docs = [d for d in docs if d.metadata.get("accounting_relevant", False)][:6]
            else:
                docs = docs[:6]
        else:
            docs = self.retriever.invoke(question, only_accounting=only_accounting)
            
        context = self._format_docs(docs)
        prompt_value = self.prompt.format(context=context, question=question)

        errors = []
        now = time.time()
        tried_any = False
        for model_name, llm in self.llm_candidates:
            cooldown_until = self.cooldowns.get(model_name, 0.0)
            if cooldown_until > now:
                continue
            tried_any = True
            try:
                answer = llm.invoke(prompt_value)
                self.last_model = model_name
                if hasattr(answer, "content"):
                    return answer.content
                return str(answer)
            except Exception as exc:
                msg = str(exc)
                # Check più permissivo per intercettare ogni tipo di messaggio di esaurimento quota
                if "429" in msg or "exhausted" in msg.lower() or "quota" in msg.lower() or "rate" in msg.lower():
                    # Evita di riprovare subito il modello saturo per 60 secondi.
                    self.cooldowns[model_name] = time.time() + 60.0
                    st.toast(f"⚠️ Quota esaurita per `{model_name}`. Cambio modello in corso...", icon="🔄")
                errors.append((model_name, msg))

        if not tried_any:
            raise RuntimeError(
                "Tutti i modelli LLM sono in cooldown temporaneo (rate-limit). "
                "Riprova tra ~60 secondi."
            )
        details = "\n".join([f"- {m}: {e}" for m, e in errors])
        raise RuntimeError(f"Tutti i modelli LLM in failover hanno fallito:\n{details}")


def _build_vectorstore_in_batches(documents, embeddings, batch_size: int, pause_sec: float, existing_vectorstore=None):
    vectorstore = existing_vectorstore
    total = len(documents)
    start = 0
    retries = 0
    max_retries = 3
    
    progress_bar = st.progress(0.0, text=f"Indicizzazione in corso... (0/{total} frammenti)")
    
    while start < total:
        batch = documents[start:start + batch_size]
        texts = [doc.page_content for doc in batch]
        metadatas = [doc.metadata for doc in batch]
        
        try:
            if vectorstore is None:
                vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
            else:
                vectorstore.add_texts(texts, metadatas=metadatas)
            
            start += batch_size
            retries = 0  # Resetta i tentativi se il batch va a buon fine
            
            current = min(start, total)
            progress_bar.progress(current / total, text=f"Indicizzazione in corso... ({current}/{total} frammenti)")
            
            if pause_sec > 0 and start < total:
                time.sleep(pause_sec)
        except Exception as exc:
            msg = str(exc).lower()
            if "429" in msg or "exhausted" in msg or "quota" in msg or "rate" in msg:
                if retries < max_retries:
                    retries += 1
                    st.toast(f"⏳ Quota embeddings esaurita ({start}/{total} frammenti). Pausa 60s (tentativo {retries}/{max_retries})...", icon="⏳")
                    time.sleep(60.0)
                else:
                    progress_bar.empty()
                    raise RuntimeError(f"Limite tentativi superato per errore quota: {exc}")
            else:
                progress_bar.empty()
                raise
    progress_bar.empty()
    return vectorstore


def get_tenant_dir(ente: Optional[str] = None) -> Path:
    if ente:
        tenant_path = Path("data") / ente / "albo_download"
        if tenant_path.exists():
            return tenant_path
        if ente.lower() == "avella":
            return Path("albo_download")
        return tenant_path
    return Path("albo_download")

def _init_local_chain_core(base_dir: Path):
    local_docs = _init_local_documents_core(base_dir)
    if not local_docs:
        return None
    return LocalSearchChain(local_docs, top_k=6)

def _init_local_documents_core(base_dir: Path):
    corpus_path = base_dir / "documenti_corpus.jsonl"
    if not corpus_path.exists():
        return None
    return _load_corpus_documents(corpus_path)

def _init_rag_system_core(embedding_models, llm_models, embed_batch_size: int, embed_pause_sec: float, build_if_missing: bool, base_dir: Path):
    faiss_index_path = base_dir / "faiss_index"
    faiss_manifest_path = base_dir / "faiss_index_manifest.json"
    corpus_path = base_dir / "documenti_corpus.jsonl"

    emb_ready, emb_init_errors = _instantiate_embeddings_candidates(embedding_models)
    if not emb_ready:
        details = "\n".join([f"- {m}: {e}" for m, e in emb_init_errors]) or "- nessun dettaglio"
        raise RuntimeError(
            "Nessun modello embeddings inizializzabile. Verifica GOOGLE_EMBEDDING_MODEL_PRIORITY.\n"
            f"Tentativi:\n{details}"
        )

    # Prova prima il load in sola lettura su un indice trusted per uno dei modelli disponibili
    for embedding_model, embeddings in emb_ready:
        if _index_is_trusted(faiss_index_path, faiss_manifest_path, embedding_model=embedding_model):
            try:
                vectorstore = FAISS.load_local(str(faiss_index_path), embeddings, allow_dangerous_deserialization=True)
                chain = LLMFailoverRAGChain(
                        retriever=vectorstore,
                    prompt_template=PROMPT_TEMPLATE,
                    llm_models=llm_models,
                )
                return chain, embedding_model
            except Exception:
                pass

    if not build_if_missing:
        return None, None

    if not corpus_path.exists():
        return None, None

    documents = _load_corpus_documents(corpus_path)
    if not documents:
        return None, None

    # Build con fallback tra modelli embedding e throttling per ridurre picchi quota
    build_errors = []
    for embedding_model, embeddings in emb_ready:
        try:
            vectorstore = _build_vectorstore_in_batches(
                documents=documents,
                embeddings=embeddings,
                batch_size=max(1, int(embed_batch_size)),
                pause_sec=max(0.0, float(embed_pause_sec)),
            )
            vectorstore.save_local(str(faiss_index_path))
            faiss_manifest_path.write_text(
                json.dumps(
                    _build_index_manifest(faiss_index_path, embedding_model=embedding_model),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            chain = LLMFailoverRAGChain(
                retriever=vectorstore,
                prompt_template=PROMPT_TEMPLATE,
                llm_models=llm_models,
            )
            return chain, embedding_model
        except Exception as exc:
            build_errors.append((embedding_model, str(exc)))

    details = "\n".join([f"- {m}: {e}" for m, e in build_errors]) or "- nessun dettaglio"
    raise RuntimeError(
        "Build indice embeddings fallita per tutti i modelli candidati.\n"
        f"Tentativi:\n{details}"
    )


_multi_tenant_rag_chains = {}

def esegui_query_rag_core(query: str, ente: str = "avella", only_accounting: bool = False, only_personnel_competence: bool = False, k: int = 6) -> str:
    """Versione core del motore RAG invocabile dall'esterno (Control Room)."""
    global _multi_tenant_rag_chains
    try:
        tenant_dir = get_tenant_dir(ente)
        chain_key = f"{tenant_dir}_{only_accounting}_{only_personnel_competence}"
        
        if chain_key not in _multi_tenant_rag_chains or _multi_tenant_rag_chains[chain_key] is None:
            google_api_key = (os.environ.get("GOOGLE_API_KEY") or "").strip()
            profile = MODEL_PROFILES["Bilanciato"]
            embedding_models = _unique_non_empty(_split_env_list(os.environ.get("GOOGLE_EMBEDDING_MODEL_PRIORITY", "")) or profile["embedding_models"] or DEFAULT_EMBEDDING_MODELS)
            llm_models = _unique_non_empty(_split_env_list(os.environ.get("GOOGLE_LLM_MODEL_PRIORITY", "")) or profile["llm_models"] or DEFAULT_LLM_MODELS)
            
            chain = None
            if google_api_key:
                try:
                    chain, _ = _init_rag_system_core(
                        embedding_models=tuple(embedding_models),
                        llm_models=tuple(llm_models),
                        embed_batch_size=int(profile["embed_batch_size"]),
                        embed_pause_sec=float(profile["embed_pause_sec"]),
                        build_if_missing=False,
                        base_dir=tenant_dir
                    )
                except Exception:
                    pass
                    
            if chain is None:
                chain = _init_local_chain_core(tenant_dir)

            if chain is None:
                return f"❌ Errore: Motore RAG non disponibile (mancano i documenti corpus in {tenant_dir}?)."
                
            _multi_tenant_rag_chains[chain_key] = chain

        return _multi_tenant_rag_chains[chain_key].invoke(query, only_accounting=only_accounting, only_personnel_competence=only_personnel_competence, k=k)
    except Exception as e:
        return f"⚠️ Errore durante l'audit RAG: {str(e)}"
