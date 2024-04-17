from typing import List

from langchain_community.vectorstores.pgvector import PGVector
from langchain_community.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from env_vars_helpers import DATABASE_URL


class EmbeddingManager:
    
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings() 

        # Dynamically get 'model_name' or 'model' from embeddings, with a fallback default value
        self.model_name = getattr(self.embeddings, 'model_name', 
                                       getattr(self.embeddings, 'model', 'default_collection_name'))
        
        self.collection_name = "document_embeddings"
        self.pg_vector = PGVector(
            connection_string=DATABASE_URL,
            embedding_function=self.embeddings,
            collection_name=self.collection_name,
            )
        self.retriever = self.pg_vector.as_retriever()
        print("finished creating embedding manager")

    def get_embedding_type(self):
        return self.embeddings.__class__.__name__
    
    def get_model_name(self):
        return self.model_name

    def split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        # Create an instance of RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
        
        # Split the input text into smaller chunks
        split_texts = text_splitter.split_text(text)
        
        return split_texts

    def embed_documents( 
            self,       
            texts: List[str],
            metadatas: List[dict]
    ) -> None:
        self.pg_vector.add_texts(texts=texts, metadatas=metadatas)

    def similarity_search_with_filters(
            self,
            query: str,
            filter: dict,
            knns: int = 4      
    ):
        return self.pg_vector.similarity_search(query=query, filter=filter, k=knns)
