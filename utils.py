from sentence_transformers import SentenceTransformer
import numpy as np
import os

embedding_model = SentenceTransformer('all-mpnet-base-v2')

def calculate_similarity(response1, response2):
    """Calculates the cosine similarity between two response embeddings."""
    embedding1 = embedding_model.encode(response1, convert_to_tensor=True)
    embedding2 = embedding_model.encode(response2, convert_to_tensor=True)
    similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
    return similarity.item()

def get_other_nodes(node_id):
    """
    Determines the addresses of other nodes in the cluster based on the current node's ID.
    """
    if node_id == "node1":
        return ["node2:7002", "node3:7003"]
    elif node_id == "node2":
        return ["node1:7001", "node3:7003"]
    elif node_id == "node3":
        return ["node1:7001", "node2:7002"]
    else:
        raise ValueError(f"Unknown node ID: {node_id}")