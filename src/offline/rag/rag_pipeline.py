"""
RAG Pipeline for Offline Q&A
Epic 3.1: Curriculum-grounded answers using local vector store

Pipeline:
1. User asks question
2. Retrieve relevant curriculum content from vector store
3. Augment LLM prompt with retrieved context
4. Generate grounded answer
"""
from typing import List, Dict, Any, Optional
from src.offline.rag.vector_store import create_vector_store, VectorStoreType
from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)


class OfflineRAGPipeline:
    """
    Offline RAG pipeline for ExamsTutor AI

    Features:
    - Fast semantic search (<500ms)
    - Subject/topic filtering
    - Context-aware answer generation
    - Citation of sources
    """

    def __init__(
        self,
        vector_store_type: VectorStoreType = "faiss",
        collection_name: str = "examstutor_curriculum",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        top_k: int = 5,
    ):
        self.vector_store_type = vector_store_type
        self.collection_name = collection_name
        self.top_k = top_k

        # Initialize vector store
        logger.info(f"Initializing RAG pipeline with {vector_store_type}")
        self.vector_store = create_vector_store(
            store_type=vector_store_type,
            collection_name=collection_name,
            embedding_model=embedding_model,
        )

        logger.info("✓ RAG pipeline initialized")

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context from vector store

        Args:
            query: User question
            top_k: Number of results (uses default if None)
            filters: Metadata filters

        Returns:
            List of retrieved documents with scores
        """
        top_k = top_k or self.top_k

        logger.info(f"Retrieving context for query: '{query[:50]}...'")

        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            filters=filters,
        )

        logger.info(f"✓ Retrieved {len(results)} context documents")

        return results

    def build_prompt(
        self,
        question: str,
        context_docs: List[Dict[str, Any]],
        subject: Optional[str] = None,
    ) -> str:
        """
        Build RAG prompt with retrieved context

        Args:
            question: User question
            context_docs: Retrieved context documents
            subject: Subject filter (optional)

        Returns:
            Formatted prompt for LLM
        """
        # Build context section
        context_text = ""
        for i, doc in enumerate(context_docs):
            metadata = doc.get("metadata", {})
            source_info = f"[Source: {metadata.get('subject', 'N/A')} - {metadata.get('topic', 'N/A')}]"

            context_text += f"\nContext {i+1} {source_info}:\n{doc['text']}\n"

        # Build prompt
        subject_instruction = f" about {subject}" if subject else ""

        prompt = f"""You are an expert AI tutor for Nigerian secondary school students preparing for WAEC and JAMB examinations.

**Question{subject_instruction}:**
{question}

**Relevant Curriculum Content:**
{context_text}

**Instructions:**
1. Use the provided curriculum content to answer the question accurately
2. Provide step-by-step explanations where appropriate
3. Use simple, clear language suitable for secondary school students
4. If the answer is not fully covered in the context, acknowledge it but still provide your best answer
5. Cite which context source(s) you used

**Answer:**"""

        return prompt

    def answer_question(
        self,
        question: str,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: Optional[int] = None,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        max_new_tokens: int = 300,
    ) -> Dict[str, Any]:
        """
        Answer question using RAG pipeline

        Args:
            question: User question
            subject: Subject filter
            topic: Topic filter
            top_k: Number of context docs to retrieve
            model: LLM model (pass quantized model)
            tokenizer: Tokenizer
            max_new_tokens: Max tokens to generate

        Returns:
            Answer with sources and metadata
        """
        import time

        start_time = time.time()

        # Build filters
        filters = {}
        if subject:
            filters["subject"] = subject
        if topic:
            filters["topic"] = topic

        # Retrieve context
        context_docs = self.retrieve(
            query=question,
            top_k=top_k,
            filters=filters if filters else None,
        )

        retrieval_time = time.time() - start_time

        # Build prompt
        prompt = self.build_prompt(question, context_docs, subject)

        # Generate answer (if model provided)
        answer_text = ""
        generation_time = 0

        if model and tokenizer:
            logger.info("Generating answer with LLM")
            gen_start = time.time()

            inputs = tokenizer(prompt, return_tensors="pt")
            if hasattr(model, 'device'):
                inputs = {k: v.to(model.device) for k, v in inputs.items()}

            import torch
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    temperature=0.7,
                    pad_token_id=tokenizer.eos_token_id,
                )

            answer_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract only the answer portion (after "**Answer:**")
            if "**Answer:**" in answer_text:
                answer_text = answer_text.split("**Answer:**")[1].strip()

            generation_time = time.time() - gen_start

        total_time = time.time() - start_time

        result = {
            "question": question,
            "answer": answer_text,
            "context_documents": context_docs,
            "filters_applied": filters,
            "num_sources": len(context_docs),
            "retrieval_time_ms": round(retrieval_time * 1000, 2),
            "generation_time_ms": round(generation_time * 1000, 2),
            "total_time_ms": round(total_time * 1000, 2),
            "prompt": prompt,  # For debugging
        }

        logger.info(
            f"✓ RAG pipeline complete:\n"
            f"  Retrieval: {result['retrieval_time_ms']}ms\n"
            f"  Generation: {result['generation_time_ms']}ms\n"
            f"  Total: {result['total_time_ms']}ms"
        )

        return result

    def add_curriculum_content(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> None:
        """
        Add curriculum content to vector store

        Documents format:
        [
            {
                "text": "content",
                "metadata": {
                    "subject": "Mathematics",
                    "topic": "Algebra",
                    "subtopic": "Quadratic Equations",
                    "class": "SS2",
                    "source": "textbook_page_45"
                }
            },
            ...
        ]
        """
        logger.info(f"Adding {len(documents)} curriculum documents")
        self.vector_store.add_documents(documents, batch_size)
        logger.info("✓ Curriculum content added successfully")


# Example usage
if __name__ == "__main__":
    # Initialize RAG pipeline
    rag = OfflineRAGPipeline(
        vector_store_type="faiss",
        top_k=3,
    )

    # Add sample curriculum content
    curriculum_docs = [
        {
            "text": "Photosynthesis is the process by which green plants use sunlight to synthesize nutrients from carbon dioxide and water. The process occurs in chloroplasts and produces glucose and oxygen. The equation is: 6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂",
            "metadata": {
                "subject": "Biology",
                "topic": "Plant Physiology",
                "subtopic": "Photosynthesis",
                "class": "SS2",
            }
        },
        {
            "text": "A quadratic equation is a second-degree polynomial equation in the form ax² + bx + c = 0, where a ≠ 0. The quadratic formula is: x = (-b ± √(b² - 4ac)) / (2a). The discriminant (b² - 4ac) determines the nature of the roots.",
            "metadata": {
                "subject": "Mathematics",
                "topic": "Algebra",
                "subtopic": "Quadratic Equations",
                "class": "SS2",
            }
        },
        {
            "text": "Newton's first law of motion states that an object at rest stays at rest and an object in motion continues in motion with constant velocity unless acted upon by an external force. This is also called the law of inertia.",
            "metadata": {
                "subject": "Physics",
                "topic": "Mechanics",
                "subtopic": "Newton's Laws",
                "class": "SS1",
            }
        },
    ]

    rag.add_curriculum_content(curriculum_docs)

    # Test RAG pipeline (without model for now)
    result = rag.answer_question(
        question="What is the quadratic formula?",
        subject="Mathematics",
        top_k=2,
    )

    print(f"\nQuestion: {result['question']}")
    print(f"\nRetrieved {result['num_sources']} sources in {result['retrieval_time_ms']}ms")
    print(f"\nContext documents:")
    for i, doc in enumerate(result['context_documents']):
        print(f"{i+1}. {doc['text'][:100]}...")
        print(f"   Subject: {doc['metadata']['subject']}, Topic: {doc['metadata']['topic']}")
