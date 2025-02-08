import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import torch
import pdfplumber


class FaissIndexer:
    def __init__(self, model_name, doc_path, raft_service):
        self.index = None
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()
        self.doc_path = doc_path
        self.batch_size = 8
        self.default_dim = 768
        self.raft_service = raft_service

    import torch
    import numpy as np

    def __create_embeddings(self, texts=None):
        embeddings = []
        device = torch.device(
            "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")

        if not texts:
            texts = self.texts

        self.model.to(device)

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            inputs = self.tokenizer(batch, return_tensors='pt', padding=True, truncation=True, max_length=512)

            # Move input tensors to the same device as the model
            inputs = {key: val.to(device) for key, val in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                # Move to CPU before converting to NumPy
                embeddings_batch = outputs.last_hidden_state.mean(dim=1).cpu().numpy()

            embeddings.extend(embeddings_batch)

        return np.array(embeddings)

    def __doc_loader(self):
        self.texts = []
        self.filenames = []

        for filename in os.listdir(self.doc_path):
            file_path = os.path.join(self.doc_path, filename)

            # Check if it's a PDF file
            if os.path.isfile(file_path) and filename.lower().endswith('.pdf'):
                with pdfplumber.open(file_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text()  # Extract text from each page

                    # Append the extracted text and filename
                    self.texts.append(text)
                    self.filenames.append(filename)

            # If you want to process other file types (like txt), you can add:
            elif os.path.isfile(file_path) and filename.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    self.texts.append(text)
                    self.filenames.append(filename)

    def __normalize_embeddings(self, embeddings):
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / norms

    def create_faiss_index(self):
        self.__doc_loader()
        # embeddings = self.__create_embeddings()
        embeddings = self.__create_embeddings(["Hello world!"])

        embeddings = self.__normalize_embeddings(embeddings)
        self.index = faiss.IndexFlatIP(self.default_dim)
        self.index.add(embeddings)

    def faiss_search(self, query, k=5):
        embeddings = self.__create_embeddings([query])
        distances, indices = self.index.search(embeddings, k)
        # Retrieve matching documents
        results = [(self.filenames[i], self.texts[i], distances[0][j]) for j, i in enumerate(indices[0])]
        return results

    def add_documents_to_index(self, new_folder_path):
        # Load new documents from the new folder
        new_texts = []
        new_filenames = []
        for filename in os.listdir(new_folder_path):
            file_path = os.path.join(new_folder_path, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    new_texts.append(text)
                    new_filenames.append(filename)

        # Create embeddings for the new documents
        new_embeddings = self.__create_embeddings(new_texts)
        new_embeddings = self.__normalize_embeddings(new_embeddings)

        # Add new embeddings to the existing index
        self.index.add(new_embeddings)

        # Optionally, store the new texts and filenames for future reference (for search)
        self.texts.extend(new_texts)
        self.filenames.extend(new_filenames)

    def most_similar_strings(self, string_dict):
        if not self.raft_service.is_leader():
            return {}
        if len(string_dict) < 2:
           return string_dict, None
        keys = list(string_dict.keys())
        texts = list(string_dict.values())
        embeddings = self.__create_embeddings(texts)
        embeddings = self.__normalize_embeddings(embeddings)
        similarity_matrix = np.dot(embeddings, embeddings.T)
        best_pair = None
        best_score = -1
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):  # Avoid duplicate comparisons
                if similarity_matrix[i][j] > best_score:
                    best_score = similarity_matrix[i][j]
                    best_pair = {
                        keys[i]: texts[i],
                        keys[j]: texts[j]
                    }
        return best_pair, best_score

