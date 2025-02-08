import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import itertools

# Using an embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Mkaing placeholders for received LLM outputs (Or we can directly append them to the list of outputs)
# output_node1, output_node2, output_node3 = get_responses()
output_node1 = "The sky is blue."
output_node2 = "The ocean reflects the sky, making it appear blue."
output_node3 = "Someone please hire me" 

# Appending retrieved LLM outputs to an existing list (can also be used as a history for all outputs)
outputs = []

outputs.append(output_node1)
outputs.append(output_node2)
outputs.append(output_node3)

# Converting outputs to embeddings (This embeds only the last three entries of the output array due to us using only three nodes)
embeddings = np.array(model.encode(outputs[-3:]), dtype=np.float32)

# Building FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)  # L2 (Euclidean) index
index.add(embeddings)

# Calculating cosine similarity between all outputs
norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
normalized_embeddings = embeddings / norms
cosine_sim_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)

# Getting the upper triangular indices (excluding diagonal)
pairs = list(itertools.combinations(range(3), 2)) # range 3 because we're dealing with 3 outputs at a time
similarities = [(i, j, cosine_sim_matrix[i, j]) for i, j in pairs]

# Finding the most similar pair
most_similar_pair = max(similarities, key=lambda x: x[2])

# Displaying the two most similar responses
print("\n")
i, j, sim_score = most_similar_pair
print(f"Most similar responses:")
print(f"Response 1: {outputs[-(3-i)]}")
print(f"Response 2: {outputs[-(3-j)]}")
print(f"Similarity Score: {sim_score:.4f}")