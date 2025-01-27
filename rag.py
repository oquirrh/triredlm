from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from llm_module import LLM  # Import the LLM class

class RAG:
    def __init__(self, index_path="index.faiss", knowledge_base_path="knowledge_base.txt"):
        self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
        self.index = faiss.read_index(index_path)
        self.knowledge_base = self._load_knowledge_base(knowledge_base_path)
        self.llm = LLM()  # Instantiate the LLM

    def _load_knowledge_base(self, knowledge_base_path):
        with open(knowledge_base_path, "r") as f:
            return [line.strip() for line in f]

    def retrieve(self, query, k=3):
        query_embedding = self.embedding_model.encode([query], convert_to_tensor=True, show_progress_bar=False).cpu().numpy()
        _, I = self.index.search(query_embedding, k)
        return [self.knowledge_base[i] for i in I[0]]

    def generate(self, query, context):
        # Use the LLM to generate a response
        prompt = f"Context: {context} \n\nQuery: {query} \n\nAnswer:"
        return self.llm.generate_text(prompt)

    def query(self, query):
        context = self.retrieve(query)
        response = self.generate(query, " ".join(context))
        return {"response": response, "context": context}