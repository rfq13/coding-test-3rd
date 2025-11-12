import sys
import os
import types
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure 'backend' package root is on sys.path so 'app.*' imports resolve
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.db.base import Base

# Always provide a minimal stub for app.db.session to avoid connecting to external DBs during tests
db_pkg = sys.modules.setdefault("app.db", types.ModuleType("app.db"))
session_mod = types.ModuleType("app.db.session")
class _DummySession:
    def execute(self, *args, **kwargs):
        return []
    def commit(self):
        pass
    def rollback(self):
        pass
session_mod.SessionLocal = lambda: _DummySession()
sys.modules["app.db.session"] = session_mod

# Provide lightweight stubs if numpy/numpy_financial are unavailable in the environment
try:
    import numpy  # noqa: F401
    import numpy_financial  # noqa: F401
except Exception:
    np_stub = types.SimpleNamespace(
        isnan=lambda x: False,
        isinf=lambda x: False,
        isscalar=lambda x: False,
        ndarray=type(None),
        bool_=bool,
        array=lambda x, dtype=None: types.SimpleNamespace(tolist=lambda: list(x)),
        float32=float,
    )
    npf_stub = types.SimpleNamespace(irr=lambda amounts: 0.1)  # 10% IRR stub
    sys.modules.setdefault("numpy", np_stub)
    sys.modules.setdefault("numpy_financial", npf_stub)

# Stub external heavy deps to avoid installation cost during unit tests
try:
    import langchain_openai  # noqa: F401
except Exception:
    class _ChatOpenAI:
        def __init__(self, *args, **kwargs):
            pass
        def invoke(self, messages):
            class R:
                content = "Stubbed LLM response"
            return R()
    class _OpenAIEmbeddings:
        def __init__(self, *args, **kwargs):
            pass
        def embed_query(self, text: str):
            # Return a fixed-size embedding vector
            return [0.0] * 1536
    lc_openai_mod = types.ModuleType("langchain_openai")
    lc_openai_mod.ChatOpenAI = _ChatOpenAI
    lc_openai_mod.OpenAIEmbeddings = _OpenAIEmbeddings
    sys.modules.setdefault("langchain_openai", lc_openai_mod)

try:
    import langchain_community.llms  # noqa: F401
except Exception:
    class _Ollama:
        def __init__(self, *args, **kwargs):
            pass
        def invoke(self, messages):
            class R:
                content = "Stubbed Ollama response"
            return R()
    lc_comm_llms = types.ModuleType("langchain_community.llms")
    lc_comm_llms.Ollama = _Ollama
    # Also register parent package
    lc_comm_pkg = types.ModuleType("langchain_community")
    lc_comm_pkg.llms = lc_comm_llms
    sys.modules.setdefault("langchain_community", lc_comm_pkg)
    sys.modules.setdefault("langchain_community.llms", lc_comm_llms)

# Stub embeddings from langchain_community if not available
try:
    import langchain_community.embeddings  # noqa: F401
except Exception:
    class _HuggingFaceEmbeddings:
        def __init__(self, *args, **kwargs):
            pass
        def encode(self, text: str):
            # Return a fixed-size embedding vector
            return [0.0] * 384
    lc_comm_embeddings = types.ModuleType("langchain_community.embeddings")
    lc_comm_embeddings.HuggingFaceEmbeddings = _HuggingFaceEmbeddings
    # Ensure parent package exists and assign embeddings submodule
    lc_comm_pkg = sys.modules.setdefault("langchain_community", types.ModuleType("langchain_community"))
    lc_comm_pkg.embeddings = lc_comm_embeddings
    sys.modules.setdefault("langchain_community.embeddings", lc_comm_embeddings)

try:
    import langchain.prompts  # noqa: F401
except Exception:
    class _ChatPromptTemplate:
        def __init__(self, messages):
            self._messages = messages
        @classmethod
        def from_messages(cls, messages):
            return cls(messages)
        def format_messages(self, **kwargs):
            # Return a simple list of strings simulating formatted messages
            return [m[1].format(**kwargs) if isinstance(m, tuple) else str(m) for m in self._messages]
    lc_prompts_mod = types.ModuleType("langchain.prompts")
    lc_prompts_mod.ChatPromptTemplate = _ChatPromptTemplate
    # Also register parent package
    lc_pkg = types.ModuleType("langchain")
    lc_pkg.prompts = lc_prompts_mod
    sys.modules.setdefault("langchain", lc_pkg)
    sys.modules.setdefault("langchain.prompts", lc_prompts_mod)

# Stub vector_store to avoid importing heavy dependencies
try:
    import app.services.vector_store  # noqa: F401
except Exception:
    # Provide a minimal stub for app.db.session to satisfy imports
    db_pkg = sys.modules.setdefault("app.db", types.ModuleType("app.db"))
    session_mod = types.ModuleType("app.db.session")
    class _DummySession:
        def execute(self, *args, **kwargs):
            return []
        def commit(self):
            pass
        def rollback(self):
            pass
    session_mod.SessionLocal = lambda: _DummySession()
    sys.modules.setdefault("app.db.session", session_mod)

    vs_mod = types.ModuleType("app.services.vector_store")
    class _VectorStore:
        def __init__(self, *args, **kwargs):
            self._docs = []
            self.logger = types.SimpleNamespace(error=lambda *args, **kwargs: None)
        async def add_document(self, content: str, metadata: dict):
            self._docs.append({"content": content, "metadata": metadata})
        async def similarity_search(self, query: str, k: int = 5, filter_metadata=None):
            return []
        async def lexical_search(self, query: str, k: int = 5, filter_metadata=None):
            return []
        async def pattern_search(self, query: str, k: int = 5, filter_metadata=None):
            return []
        async def hybrid_search(self, query: str, k: int, filter_metadata=None, weights=None):
            # Simple RRF fusion over similarity/lexical/pattern results
            dense = await self.similarity_search(query, k, filter_metadata)
            lexical = await self.lexical_search(query, k, filter_metadata)
            pattern = await self.pattern_search(query, k, filter_metadata)
            def rank_map(results):
                return {res["id"]: idx for idx, res in enumerate(results)}
            r_dense = rank_map(dense)
            r_lex = rank_map(lexical)
            r_pat = rank_map(pattern)
            w_dense = (weights or {}).get("dense", 1.0)
            w_lex = (weights or {}).get("lexical", 1.0)
            w_pat = (weights or {}).get("pattern", 1.0)
            k_rrf = 60.0
            scores = {}
            items = {}
            all_ids = set(list(r_dense.keys()) + list(r_lex.keys()) + list(r_pat.keys()))
            for _id in all_ids:
                s = 0.0
                if _id in r_dense:
                    s += w_dense * (1.0 / (k_rrf + r_dense[_id] + 1))
                if _id in r_lex:
                    s += w_lex * (1.0 / (k_rrf + r_lex[_id] + 1))
                if _id in r_pat:
                    s += w_pat * (1.0 / (k_rrf + r_pat[_id] + 1))
                scores[_id] = s
            def get_item(_id):
                for coll in (dense, lexical, pattern):
                    for r in coll:
                        if r["id"] == _id:
                            return r
                return {}
            for _id in all_ids:
                items[_id] = get_item(_id)
            ranked = sorted(all_ids, key=lambda x: scores.get(x, 0.0), reverse=True)
            out = []
            for _id in ranked[:k]:
                item = dict(items[_id])
                item["score"] = float(scores[_id])
                out.append(item)
            return out
        def clear(self, fund_id=None):
            # Emulate SQL DELETE statements if a db stub is present
            if hasattr(self, "db") and self.db is not None:
                try:
                    if fund_id is None:
                        # Without fund_id
                        self.db.execute("DELETE FROM document_embeddings", None)
                    else:
                        # With fund_id
                        self.db.execute("DELETE FROM document_embeddings WHERE fund_id = :fund_id", {"fund_id": fund_id})
                    self.db.commit()
                except Exception:
                    self.db.rollback()
            else:
                self._docs.clear()
    vs_mod.VectorStore = _VectorStore
    # Ensure package structure exists
    app_pkg = sys.modules.setdefault("app", types.ModuleType("app"))
    services_pkg = sys.modules.setdefault("app.services", types.ModuleType("app.services"))
    sys.modules.setdefault("app.services.vector_store", vs_mod)


@pytest.fixture(scope="session")
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    # Ensure all models are imported so SQLAlchemy relationships can resolve
    from app.models.fund import Fund  # noqa: F401
    from app.models.transaction import CapitalCall, Distribution, Adjustment  # noqa: F401
    from app.models.document import Document  # noqa: F401
    try:
        from app.models.conversation import Conversation, ChatMessage  # noqa: F401
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(sqlite_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()