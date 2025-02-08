class ContextFetcher:
    def __init__(self, faiss_index):
        self.faiss = faiss_index

    def retrieve(self, query, k=3):
        top_results = self.faiss.faiss_search(query, k)
        context = "\n\n".join([f"{i + 1}. {doc}" for i, (_, doc, _) in enumerate(top_results)])
        return context
