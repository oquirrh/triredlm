import grpc

from context_fetcher import ContextFetcher
from faiss_indexer import FaissIndexer
from llm_interface import LlmInterface
from raft.raft_server import RaftNode
from raft.raft_server import start_server, send_response
import sys


class Pipeline:
    def __init__(self, embedding_model_name, doc_path, model, raft):
        self.llm = LlmInterface(model)
        self.faiss = FaissIndexer(embedding_model_name, doc_path, raft)
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
    peers = sys.argv[3:5]  # done
    embedding_model_name = sys.argv[5]  # sentence-transformers/all-MiniLM-L6-v2
    doc_path = sys.argv[6]  # /Users/aaditya/Documents/Notes
    model = sys.argv[7]  # google/gemini-2.0-pro-exp-02-05:free
    raft = RaftNode(node_id, peers)
    start_server(node_id, port, peers, raft)
    pipeline = Pipeline(embedding_model_name, doc_path, model, raft)
    # configure this to liten for queries.
    while True:
        query = input("Enter your query (or type 'exit' to quit): ")

        if query.lower() == 'exit':
            print("Exiting the program.")
            break  # Exit the loop if user types 'exit'

        # Process the query using the pipeline
        response = pipeline.query(query)
        # print("Response:", response)
        if not raft.is_leader():
            for peer in raft.peers:
                send_response(peer, response)
        else:
            while len(raft.messages) != 3:
                continue
            # now compute similarity:
            message_dict = {i: mes for i, mes in enumerate(raft.messages)}
            mp, ms = pipeline.faiss.most_similar_strings(message_dict)
        #   new func to send response to the leader.
        # todo need stable elections, if leader keeps changing, we might never get a response
        # pipeline.faiss.most_similar_strings()
        continue
