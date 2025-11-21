"""
RAG (Retrieval-Augmented Generation) Service
Combines vector search with AI generation for grounded responses
"""
from typing import List, Dict, Any, Optional
import os
from datetime import datetime

from src.ai.embeddings_service import embeddings_service
from src.ai.vector_store import get_vector_store, VectorStore
from src.ai.openai_service import openai_service


class RAGService:
    """
    RAG pipeline for question answering with retrieved context
    """

    def __init__(
        self,
        embedding_dimension: int = 1536,
        use_local_embeddings: bool = False,
        index_type: str = "flat"
    ):
        """
        Initialize RAG service

        Args:
            embedding_dimension: Embedding vector dimension
            use_local_embeddings: Use local embedding model instead of OpenAI
            index_type: FAISS index type
        """
        self.use_local_embeddings = use_local_embeddings
        self.embedding_dimension = embedding_dimension

        # Initialize vector store
        self.vector_store = get_vector_store(
            dimension=embedding_dimension,
            index_type=index_type
        )

        print(f"✅ RAG Service initialized (local_embeddings={use_local_embeddings})")

    async def ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "content",
        metadata_fields: List[str] = None
    ) -> int:
        """
        Ingest documents into vector store

        Args:
            documents: List of documents with text and metadata
            text_field: Field containing text to embed
            metadata_fields: Additional metadata fields to store

        Returns:
            Number of documents ingested
        """
        if not documents:
            return 0

        metadata_fields = metadata_fields or []

        # Extract texts
        texts = []
        metadata_list = []

        for doc in documents:
            text = doc.get(text_field, "")
            if not text:
                continue

            # Build metadata
            metadata = {
                "text": text,
                "ingested_at": datetime.utcnow().isoformat()
            }

            # Add custom metadata fields
            for field in metadata_fields:
                if field in doc:
                    metadata[field] = doc[field]

            # Add all fields as metadata by default
            for key, value in doc.items():
                if key not in metadata:
                    metadata[key] = value

            texts.append(text)
            metadata_list.append(metadata)

        if not texts:
            return 0

        # Generate embeddings
        print(f"📊 Generating embeddings for {len(texts)} documents...")
        embeddings = await embeddings_service.batch_generate_embeddings(
            texts=texts,
            use_local=self.use_local_embeddings
        )

        # Filter out failed embeddings
        valid_embeddings = []
        valid_metadata = []

        for emb, meta in zip(embeddings, metadata_list):
            if emb is not None:
                valid_embeddings.append(emb)
                valid_metadata.append(meta)

        if not valid_embeddings:
            print("❌ Failed to generate any embeddings")
            return 0

        # Add to vector store
        self.vector_store.add_documents(
            embeddings=valid_embeddings,
            documents=valid_metadata
        )

        print(f"✅ Ingested {len(valid_embeddings)} documents")

        return len(valid_embeddings)

    async def ingest_curriculum_content(
        self,
        subject: str,
        class_level: str,
        topics: List[Dict[str, Any]]
    ) -> int:
        """
        Ingest curriculum content (topics, subtopics, learning objectives)

        Args:
            subject: Subject name
            class_level: Class level (SS1, SS2, SS3)
            topics: List of topic dicts with content

        Returns:
            Number of documents ingested
        """
        documents = []

        for topic in topics:
            topic_name = topic.get("name", "")
            description = topic.get("description", "")

            # Main topic document
            content = f"Topic: {topic_name}\n\n{description}"

            doc = {
                "content": content,
                "type": "topic",
                "subject": subject,
                "class_level": class_level,
                "topic": topic_name,
                "source": "curriculum"
            }
            documents.append(doc)

            # Subtopics
            subtopics = topic.get("subtopics", [])
            for subtopic in subtopics:
                subtopic_content = f"Subtopic: {subtopic.get('name', '')}\n\n{subtopic.get('description', '')}"

                subdoc = {
                    "content": subtopic_content,
                    "type": "subtopic",
                    "subject": subject,
                    "class_level": class_level,
                    "topic": topic_name,
                    "subtopic": subtopic.get("name", ""),
                    "source": "curriculum"
                }
                documents.append(subdoc)

            # Learning objectives
            objectives = topic.get("learning_objectives", [])
            if objectives:
                objectives_content = f"Learning Objectives for {topic_name}:\n\n" + "\n".join(f"- {obj}" for obj in objectives)

                obj_doc = {
                    "content": objectives_content,
                    "type": "learning_objectives",
                    "subject": subject,
                    "class_level": class_level,
                    "topic": topic_name,
                    "source": "curriculum"
                }
                documents.append(obj_doc)

        return await self.ingest_documents(documents)

    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        subject: Optional[str] = None,
        class_level: Optional[str] = None,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a query

        Args:
            query: User question
            top_k: Number of documents to retrieve
            subject: Filter by subject
            class_level: Filter by class level
            min_similarity: Minimum similarity threshold

        Returns:
            List of relevant documents with scores
        """
        # Generate query embedding
        query_embedding = await embeddings_service.generate_embedding(
            text=query,
            use_local=self.use_local_embeddings
        )

        if query_embedding is None:
            print("❌ Failed to generate query embedding")
            return []

        # Define filter function
        def filter_fn(doc: Dict[str, Any]) -> bool:
            # Skip deleted docs
            if doc.get("deleted", False):
                return False

            # Check similarity threshold
            if doc.get("similarity_score", 0) < min_similarity:
                return False

            # Filter by subject
            if subject and doc.get("subject") != subject:
                return False

            # Filter by class level
            if class_level and doc.get("class_level") != class_level:
                return False

            return True

        # Search vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Get more to account for filtering
            filter_fn=filter_fn
        )

        # Limit to top_k after filtering
        return results[:top_k]

    async def answer_question_with_rag(
        self,
        question: str,
        subject: str,
        class_level: str,
        use_rag: bool = True,
        top_k: int = 3,
        min_similarity: float = 0.6
    ) -> Dict[str, Any]:
        """
        Answer question using RAG pipeline

        Args:
            question: User question
            subject: Subject
            class_level: Class level
            use_rag: Whether to use RAG (if False, use AI only)
            top_k: Number of context docs to retrieve
            min_similarity: Minimum similarity for retrieval

        Returns:
            Answer dict with context and metadata
        """
        # Retrieve context if RAG enabled
        context_docs = []
        context_text = ""

        if use_rag:
            context_docs = await self.retrieve_context(
                query=question,
                top_k=top_k,
                subject=subject,
                class_level=class_level,
                min_similarity=min_similarity
            )

            if context_docs:
                # Build context text
                context_parts = []
                for i, doc in enumerate(context_docs, 1):
                    text = doc.get("text", "")
                    source = doc.get("source", "curriculum")
                    topic = doc.get("topic", "")

                    context_parts.append(f"[Source {i}] {topic} ({source}):\n{text}\n")

                context_text = "\n".join(context_parts)

        # Generate answer with AI (passing context)
        ai_response = await openai_service.answer_question(
            question=question,
            subject=subject,
            class_level=class_level,
            context=context_text if context_text else None
        )

        # Build response
        response = {
            "answer": ai_response.get("answer", ""),
            "confidence": ai_response.get("confidence", 0.0),
            "tokens_used": ai_response.get("tokens_used", 0),
            "rag_enabled": use_rag,
            "context_used": len(context_docs) > 0,
            "num_context_docs": len(context_docs),
            "sources": []
        }

        # Add source information
        for doc in context_docs:
            source_info = {
                "topic": doc.get("topic", ""),
                "subtopic": doc.get("subtopic", ""),
                "type": doc.get("type", ""),
                "similarity_score": doc.get("similarity_score", 0.0),
                "text_preview": doc.get("text", "")[:200] + "..." if len(doc.get("text", "")) > 200 else doc.get("text", "")
            }
            response["sources"].append(source_info)

        return response

    def get_stats(self) -> Dict[str, Any]:
        """
        Get RAG service statistics

        Returns:
            Stats dict
        """
        vector_stats = self.vector_store.get_stats()

        return {
            "rag_enabled": True,
            "use_local_embeddings": self.use_local_embeddings,
            "embedding_dimension": self.embedding_dimension,
            "vector_store": vector_stats
        }


# Global instance
rag_service = RAGService(
    embedding_dimension=1536,  # OpenAI text-embedding-3-small
    use_local_embeddings=False,  # Use OpenAI by default
    index_type="flat"
)
