from context_fetcher import ContextFetcher
from faiss_indexer import FaissIndexer
from llm_interface import LlmInterface
from raft.raft_server import RaftNode
import sys

class Pipeline:
    def __init__(self, embedding_model_name, doc_path, model, raft):
        self.llm = LlmInterface(model)
        self.faiss = FaissIndexer(embedding_model_name, doc_path)
        self.faiss.create_faiss_index()
        self.context_engine = ContextFetcher(self.faiss)
        self.raft = raft

    def refresh_rag(self, doc_path):
        self.faiss.add_documents_to_index(doc_path)

    def query(self, query):
        context = self.context_engine.retrieve(query=query)
        return self.llm.query(query, context)


if __name__ == '__main__':
    # create the raft service
    node_id = int(sys.argv[1])  # Node ID from command-line arguments
    port = int(sys.argv[2])  # Port to run the server
    peers = sys.argv[3:]
    embedding_model_name = sys.argv[4:]
    doc_path = sys.argv[5:]
    model = sys.argv[6:]
    raft = RaftNode(node_id, peers)
    raft.start_server(node_id, port, peers)
    pipeline = Pipeline(embedding_model_name, doc_path, model, raft)
    # configure this to liten for queries.
    while True:
        query = input("Enter your query (or type 'exit' to quit): ")

        if query.lower() == 'exit':
            print("Exiting the program.")
            break  # Exit the loop if user types 'exit'

        # Process the query using the pipeline
        response = pipeline.query(query)
        print("Response:", response)