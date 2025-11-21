"""
RAG Administration Router
Manage documents, embeddings, and vector store
"""
from fastapi import APIRouter, HTTPException, status, Depends, Body
from sqlalchemy.orm import Session
from src.database.config import get_db
from src.database import crud, models
from src.ai.rag_service import rag_service
from src.ai.embeddings_service import embeddings_service
from src.ai.vector_store import get_vector_store
from src.api.routers.auth_db import get_current_user
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/rag", tags=["RAG Administration"])


class DocumentIngestRequest(BaseModel):
    """Request model for document ingestion"""
    documents: List[Dict[str, Any]]
    text_field: str = "content"
    metadata_fields: Optional[List[str]] = None


class CurriculumIngestRequest(BaseModel):
    """Request model for curriculum content ingestion"""
    subject: str
    class_level: str
    topics: List[Dict[str, Any]]


class SearchRequest(BaseModel):
    """Request model for document search"""
    query: str
    top_k: int = 5
    subject: Optional[str] = None
    class_level: Optional[str] = None
    min_similarity: float = 0.5


def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure user is admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.post("/documents/ingest")
async def ingest_documents(
    request: DocumentIngestRequest,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Ingest documents into RAG system

    Requires admin access.
    """
    try:
        num_ingested = await rag_service.ingest_documents(
            documents=request.documents,
            text_field=request.text_field,
            metadata_fields=request.metadata_fields
        )

        return {
            "success": True,
            "num_ingested": num_ingested,
            "message": f"Successfully ingested {num_ingested} documents"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest documents: {str(e)}"
        )


@router.post("/curriculum/ingest")
async def ingest_curriculum(
    request: CurriculumIngestRequest,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Ingest curriculum content (topics, subtopics) into RAG system

    Requires admin access.
    """
    try:
        num_ingested = await rag_service.ingest_curriculum_content(
            subject=request.subject,
            class_level=request.class_level,
            topics=request.topics
        )

        return {
            "success": True,
            "num_ingested": num_ingested,
            "subject": request.subject,
            "class_level": request.class_level,
            "message": f"Successfully ingested {num_ingested} curriculum documents"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest curriculum: {str(e)}"
        )


@router.post("/documents/search")
async def search_documents(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search documents using semantic search

    Returns most relevant documents based on query.
    """
    try:
        results = await rag_service.retrieve_context(
            query=request.query,
            top_k=request.top_k,
            subject=request.subject,
            class_level=request.class_level,
            min_similarity=request.min_similarity
        )

        return {
            "query": request.query,
            "num_results": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/stats")
async def get_rag_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get RAG system statistics

    Returns stats about vector store, embeddings, and documents.
    """
    try:
        stats = rag_service.get_stats()

        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.post("/vector-store/rebuild")
async def rebuild_vector_store(
    current_user: dict = Depends(require_admin)
):
    """
    Rebuild vector store index

    Removes deleted documents and rebuilds FAISS index.
    Requires admin access.
    """
    try:
        vector_store = get_vector_store()
        vector_store.rebuild_index()

        stats = vector_store.get_stats()

        return {
            "success": True,
            "message": "Vector store rebuilt successfully",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild index: {str(e)}"
        )


@router.post("/vector-store/clear")
async def clear_vector_store(
    confirm: bool = Body(..., embed=True),
    current_user: dict = Depends(require_admin)
):
    """
    Clear entire vector store

    ⚠️ WARNING: This deletes all documents and embeddings!
    Requires admin access and confirmation.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must confirm deletion by setting confirm=true"
        )

    try:
        vector_store = get_vector_store()
        vector_store.clear()

        return {
            "success": True,
            "message": "Vector store cleared successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear vector store: {str(e)}"
        )


@router.get("/health")
async def rag_health_check():
    """
    Check RAG system health

    Returns status of embeddings service, vector store, and dependencies.
    """
    health = {
        "rag_service": "operational",
        "embeddings_service": {
            "openai_available": embeddings_service.openai_available,
            "local_model_available": embeddings_service.local_model is not None
        },
        "vector_store": rag_service.vector_store.get_stats()
    }

    return health


@router.post("/sample-data/load")
async def load_sample_data(
    current_user: dict = Depends(require_admin)
):
    """
    Load sample curriculum data for testing

    Ingests sample mathematics content for SS2 students.
    Requires admin access.
    """
    sample_topics = [
        {
            "name": "Quadratic Equations",
            "description": "Quadratic equations are polynomial equations of degree 2. They have the general form ax² + bx + c = 0, where a ≠ 0. Solutions can be found using factoring, completing the square, or the quadratic formula.",
            "subtopics": [
                {
                    "name": "Solving by Factoring",
                    "description": "Factoring involves expressing the quadratic as a product of two binomials, then setting each factor to zero to find solutions."
                },
                {
                    "name": "Quadratic Formula",
                    "description": "The quadratic formula x = (-b ± √(b²-4ac)) / 2a provides solutions for any quadratic equation."
                }
            ],
            "learning_objectives": [
                "Solve quadratic equations by factoring",
                "Apply the quadratic formula",
                "Determine the nature of roots using the discriminant"
            ]
        },
        {
            "name": "Trigonometry",
            "description": "Trigonometry studies relationships between angles and sides of triangles. The main ratios are sine, cosine, and tangent.",
            "subtopics": [
                {
                    "name": "Trigonometric Ratios",
                    "description": "In a right triangle: sin(θ) = opposite/hypotenuse, cos(θ) = adjacent/hypotenuse, tan(θ) = opposite/adjacent"
                },
                {
                    "name": "Trigonometric Identities",
                    "description": "Fundamental identities include sin²θ + cos²θ = 1, tan θ = sin θ / cos θ"
                }
            ],
            "learning_objectives": [
                "Calculate trigonometric ratios in right triangles",
                "Apply trigonometric identities to simplify expressions",
                "Solve problems involving angles of elevation and depression"
            ]
        }
    ]

    try:
        num_ingested = await rag_service.ingest_curriculum_content(
            subject="Mathematics",
            class_level="SS2",
            topics=sample_topics
        )

        return {
            "success": True,
            "num_ingested": num_ingested,
            "message": f"Successfully loaded {num_ingested} sample documents"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load sample data: {str(e)}"
        )
