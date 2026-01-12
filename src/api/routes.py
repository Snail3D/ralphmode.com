from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from services.question_generator import DynamicQuestionService, CodebaseAnalyzer
from integrations.llm_factory import get_llm_client

router = APIRouter()

class QuestionRequest(BaseModel):
    repository_path: str
    focus_area: Optional[str] = None

class QuestionResponse(BaseModel):
    questions: List[str]

@router.post("/generate-questions", response_model=QuestionResponse)
def generate_questions(
    request: QuestionRequest,
    llm_client = Depends(get_llm_client)
):
    """
    Generates contextual questions based on the provided codebase path.
    """
    if not os.path.exists(request.repository_path):
        raise HTTPException(status_code=404, detail="Repository path not found")

    analyzer = CodebaseAnalyzer()
    service = DynamicQuestionService(analyzer, llm_client)
    
    try:
        questions = service.generate_questions(request.repository_path, request.focus_area)
        return QuestionResponse(questions=questions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))