from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class QuestionData(BaseModel):
    question: str
    green_flags: List[str]
    red_flags: List[str]


class GatherRequest(BaseModel):
    transcript: Dict[str, Any]
    technical_questions: str
    key_skill_areas: List[Dict[str, Any]]

    class Config:
        pass


class GatherResponse(BaseModel):
    llm_output: Dict[str, Any]

    class Config:
        schema_extra = {
            "example": {
                "llm_output": {
                    "groups": [
                        {
                            "question_id": "Q1",
                            "question_title": "Node.js Async Operations",
                            "type": "technical",
                            "source": "known_questions",
                            "time_range": {"start": 100, "end": 200},
                            "turn_indices": [5, 6, 7],
                            "conversation": [
                                {
                                    "idx": 5,
                                    "role": "agent",
                                    "message": "How does Node.js handle async operations?"
                                },
                                {
                                    "idx": 6,
                                    "role": "user",
                                    "message": "Node.js uses event loop..."
                                }
                            ],
                            "facts": {
                                "answers": ["Uses event loop for async operations"],
                                "entities": {"experience_level": "intermediate"}
                            },
                            "greenFlags": ["Mentions event loop"],
                            "redFlags": []
                        }
                    ],
                    "misc_or_unclear": [],
                    "pre_inferred_facts_global": {}
                }
            }
        }


class EvaluateRequest(BaseModel):
    transcript: Dict[str, Any]
    resume: Optional[Dict[str, Any]] = None
    key_skill_areas: Optional[List[Dict[str, Any]]] = None
    call_id: Optional[str] = None  # Interview room name for custom filename

    class Config:
        pass


class EvaluateResponse(BaseModel):
    evaluation_report: Dict[str, Any]
    question_groups: Dict[str, Any]
    skills_assessment: Optional[Dict[str, Any]] = None

    class Config:
        pass


class SkillsAssessmentRequest(BaseModel):
    transcript: Dict[str, Any]
    key_skill_areas: List[Dict[str, Any]]
    resume: Optional[Dict[str, Any]] = None

    class Config:
        pass


class SkillsAssessmentResponse(BaseModel):
    competency_mapping: List[Dict[str, Any]]
    overall_skills_summary: Dict[str, Any]

    class Config:
        pass