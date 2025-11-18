from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import os

# Initialize the embedding model (using a lightweight model)
# You can change this to a different model if needed
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # 384 dimensions, fast and lightweight

_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """Lazy load the embedding model"""
    global _model
    if _model is None:
        print(f"[EMBEDDINGS] Loading model: {EMBEDDING_MODEL_NAME}")
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print(f"[EMBEDDINGS] Model loaded successfully")
    return _model


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for a given text.
    
    Args:
        text: Input text to generate embedding for
        
    Returns:
        List of floats representing the embedding vector
    """
    if not text or not text.strip():
        # Return zero vector if text is empty
        model = get_embedding_model()
        return [0.0] * model.get_sentence_embedding_dimension()
    
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batch.
    
    Args:
        texts: List of input texts
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.tolist()


def get_embedding_dimension() -> int:
    """Get the dimension of the embeddings"""
    model = get_embedding_model()
    return model.get_sentence_embedding_dimension()

