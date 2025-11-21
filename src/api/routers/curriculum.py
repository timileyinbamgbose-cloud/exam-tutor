"""
Curriculum and Learning Router
Handles subjects, topics, and learning content
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.api.models import SubjectResponse, TopicResponse, ProgressResponse
from src.api.auth import get_current_user, get_current_student
from typing import List

router = APIRouter(prefix="/api/v1/curriculum", tags=["Curriculum & Learning"])


# Mock curriculum data
SUBJECTS_DATA = [
    {
        "id": "math",
        "name": "Mathematics",
        "description": "Core mathematics for WAEC and JAMB",
        "topics": ["Algebra", "Geometry", "Trigonometry", "Calculus", "Statistics"],
        "class_levels": ["SS1", "SS2", "SS3"]
    },
    {
        "id": "physics",
        "name": "Physics",
        "description": "Physics for WAEC and JAMB",
        "topics": ["Mechanics", "Electricity", "Waves", "Optics", "Modern Physics"],
        "class_levels": ["SS1", "SS2", "SS3"]
    },
    {
        "id": "chemistry",
        "name": "Chemistry",
        "description": "Chemistry for WAEC and JAMB",
        "topics": ["Atomic Structure", "Chemical Bonding", "Acids and Bases", "Organic Chemistry", "Electrochemistry"],
        "class_levels": ["SS1", "SS2", "SS3"]
    },
    {
        "id": "biology",
        "name": "Biology",
        "description": "Biology for WAEC and JAMB",
        "topics": ["Cell Biology", "Genetics", "Ecology", "Evolution", "Human Physiology"],
        "class_levels": ["SS1", "SS2", "SS3"]
    },
    {
        "id": "english",
        "name": "English Language",
        "description": "Use of English for WAEC and JAMB",
        "topics": ["Grammar", "Comprehension", "Essay Writing", "Oral English", "Literature"],
        "class_levels": ["SS1", "SS2", "SS3"]
    },
    {
        "id": "agriculture",
        "name": "Agriculture Science",
        "description": "Agriculture for WAEC and JAMB",
        "topics": ["Crop Production", "Animal Husbandry", "Soil Science", "Farm Management", "Agricultural Economics"],
        "class_levels": ["SS1", "SS2", "SS3"]
    }
]


@router.get("/subjects", response_model=List[SubjectResponse])
async def get_subjects(current_user: dict = Depends(get_current_user)):
    """Get list of all available subjects"""
    return [SubjectResponse(**subject) for subject in SUBJECTS_DATA]


@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
async def get_subject(subject_id: str, current_user: dict = Depends(get_current_user)):
    """Get details of a specific subject"""
    subject = next((s for s in SUBJECTS_DATA if s["id"] == subject_id), None)

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject '{subject_id}' not found"
        )

    return SubjectResponse(**subject)


@router.get("/subjects/{subject_id}/topics", response_model=List[TopicResponse])
async def get_subject_topics(
    subject_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all topics for a subject"""
    subject = next((s for s in SUBJECTS_DATA if s["id"] == subject_id), None)

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject '{subject_id}' not found"
        )

    topics = []
    for topic_name in subject["topics"]:
        topic = TopicResponse(
            id=f"{subject_id}_{topic_name.lower().replace(' ', '_')}",
            name=topic_name,
            subject=subject["name"],
            subtopics=[f"{topic_name} - Introduction", f"{topic_name} - Advanced"],
            difficulty="medium",
            curriculum_coverage="WAEC & JAMB"
        )
        topics.append(topic)

    return topics


@router.get("/progress", response_model=ProgressResponse)
async def get_student_progress(
    subject: str = None,
    current_user: dict = Depends(get_current_student)
):
    """Get student's learning progress"""
    # Mock progress data
    import datetime

    return ProgressResponse(
        student_id=current_user["id"],
        subject=subject or "All Subjects",
        topics_completed=15,
        total_topics=30,
        questions_answered=250,
        accuracy_rate=0.78,
        study_time_hours=42.5,
        last_activity=datetime.datetime.utcnow()
    )


@router.get("/topics/{topic_id}/content")
async def get_topic_content(
    topic_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get learning content for a specific topic"""
    # Mock content
    return {
        "topic_id": topic_id,
        "content": {
            "introduction": "Introduction to the topic...",
            "key_concepts": ["Concept 1", "Concept 2", "Concept 3"],
            "examples": ["Example 1", "Example 2"],
            "practice_questions": 50,
            "video_lessons": 3,
            "reading_time_minutes": 45
        }
    }


@router.get("/search")
async def search_curriculum(
    query: str,
    current_user: dict = Depends(get_current_user)
):
    """Search across curriculum content"""
    # Mock search
    return {
        "query": query,
        "results": [
            {
                "type": "topic",
                "subject": "Mathematics",
                "topic": "Algebra",
                "relevance": 0.95
            },
            {
                "type": "topic",
                "subject": "Physics",
                "topic": "Mechanics",
                "relevance": 0.82
            }
        ],
        "total": 2
    }
