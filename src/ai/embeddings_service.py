"""
Embeddings Service
Generates embeddings using OpenAI API and local models
"""
from typing import List, Optional, Dict, Any
import os
import numpy as np
from openai import AsyncOpenAI
import tiktoken

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️  sentence-transformers not available - using OpenAI embeddings only")


class EmbeddingsService:
    """
    Service for generating embeddings using OpenAI and local models
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        # OpenAI client
        if self.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
            self.openai_available = True
        else:
            self.openai_client = None
            self.openai_available = False
            print("⚠️  OPENAI_API_KEY not set - OpenAI embeddings disabled")

        # Local model (sentence-transformers)
        self.local_model = None
        self.local_model_name = "all-MiniLM-L6-v2"  # Fast, efficient, 384 dimensions

        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                print(f"📦 Loading local embedding model: {self.local_model_name}")
                self.local_model = SentenceTransformer(self.local_model_name)
                print(f"✅ Local embedding model loaded!")
            except Exception as e:
                print(f"⚠️  Failed to load local model: {e}")
                self.local_model = None

        # Tokenizer for chunking
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    async def generate_openai_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-small"
    ) -> Optional[List[float]]:
        """
        Generate embedding using OpenAI API

        Args:
            text: Text to embed
            model: OpenAI embedding model (text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002)

        Returns:
            Embedding vector or None if failed
        """
        if not self.openai_available:
            return None

        try:
            # Clean text
            text = text.replace("\n", " ").strip()

            if not text:
                return None

            # Generate embedding
            response = await self.openai_client.embeddings.create(
                input=text,
                model=model
            )

            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            print(f"❌ OpenAI embedding error: {e}")
            return None

    def generate_local_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding using local sentence-transformers model

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        if self.local_model is None:
            return None

        try:
            # Clean text
            text = text.replace("\n", " ").strip()

            if not text:
                return None

            # Generate embedding
            embedding = self.local_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()

        except Exception as e:
            print(f"❌ Local embedding error: {e}")
            return None

    async def generate_embedding(
        self,
        text: str,
        use_local: bool = False,
        model: str = "text-embedding-3-small"
    ) -> Optional[List[float]]:
        """
        Generate embedding using best available method

        Args:
            text: Text to embed
            use_local: Force local model (default: False - prefer OpenAI)
            model: OpenAI model to use if not using local

        Returns:
            Embedding vector or None if failed
        """
        if use_local or not self.openai_available:
            return self.generate_local_embedding(text)
        else:
            return await self.generate_openai_embedding(text, model=model)

    async def batch_generate_embeddings(
        self,
        texts: List[str],
        use_local: bool = False,
        model: str = "text-embedding-3-small",
        batch_size: int = 100
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batches

        Args:
            texts: List of texts to embed
            use_local: Use local model
            model: OpenAI model
            batch_size: Batch size for OpenAI API

        Returns:
            List of embedding vectors
        """
        embeddings = []

        if use_local or not self.openai_available:
            # Local model can handle all at once
            for text in texts:
                emb = self.generate_local_embedding(text)
                embeddings.append(emb)
        else:
            # OpenAI API - batch requests
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                try:
                    # Clean texts
                    cleaned_batch = [text.replace("\n", " ").strip() for text in batch]

                    # Generate embeddings
                    response = await self.openai_client.embeddings.create(
                        input=cleaned_batch,
                        model=model
                    )

                    # Extract embeddings
                    batch_embeddings = [item.embedding for item in response.data]
                    embeddings.extend(batch_embeddings)

                except Exception as e:
                    print(f"❌ Batch embedding error: {e}")
                    # Add None for failed items
                    embeddings.extend([None] * len(batch))

        return embeddings

    def chunk_text(
        self,
        text: str,
        max_tokens: int = 512,
        overlap: int = 50
    ) -> List[str]:
        """
        Split text into chunks for embedding

        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk
            overlap: Overlap between chunks (in tokens)

        Returns:
            List of text chunks
        """
        if self.tokenizer is None:
            # Fallback: simple character-based chunking
            max_chars = max_tokens * 4  # Rough estimate
            overlap_chars = overlap * 4

            chunks = []
            start = 0
            while start < len(text):
                end = start + max_chars
                chunk = text[start:end]
                chunks.append(chunk)
                start = end - overlap_chars

            return chunks

        # Token-based chunking
        tokens = self.tokenizer.encode(text)

        chunks = []
        start = 0
        while start < len(tokens):
            end = start + max_tokens
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            start = end - overlap

        return chunks

    def get_embedding_dimension(self, use_local: bool = False, model: str = "text-embedding-3-small") -> int:
        """
        Get embedding dimension for the specified model

        Args:
            use_local: Local model
            model: OpenAI model

        Returns:
            Embedding dimension
        """
        if use_local:
            if self.local_model:
                return self.local_model.get_sentence_embedding_dimension()
            return 384  # Default for all-MiniLM-L6-v2
        else:
            # OpenAI embedding dimensions
            if model == "text-embedding-3-small":
                return 1536
            elif model == "text-embedding-3-large":
                return 3072
            elif model == "text-embedding-ada-002":
                return 1536
            return 1536  # Default

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)

        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)


# Global instance
embeddings_service = EmbeddingsService()
