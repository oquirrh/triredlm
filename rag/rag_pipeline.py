from context_fetcher import ContextFetcher
from faiss_indexer import FaissIndexer
from llm_interface import LlmInterface

class Pipeline:
    def __init__(self, embedding_model_name, doc_path, model):
        self.llm = LlmInterface(model)
        self.faiss = FaissIndexer(embedding_model_name, doc_path)
        self.faiss.create_faiss_index()
        self.context_engine = ContextFetcher(self.faiss)

    def refresh_rag(self, doc_path):
        self.faiss.add_documents_to_index(doc_path)
    def query(self, query):
        context = self.context_engine.retrieve(query=query)
        return self.llm.query(query, context)
