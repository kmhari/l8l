import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from llm_client import create_llm_client
import os


class QuestionGenerationRequest(BaseModel):
    job_description: str
    skills: List[Dict[str, Any]]


class GeneratedQuestion(BaseModel):
    question: str = Field(..., min_length=10, max_length=500)
    linkedSkillArea: str
    linkedSubSkillArea: str
    difficultyLevel: str = Field(..., pattern="^(low|medium|high)$")
    questionType: str = Field(..., pattern="^(experience|tradeoff|concept-application|concept-definition|concept)$")
    greenFlags: List[str] = Field(..., min_items=3, max_items=5)
    redFlags: List[str] = Field(..., min_items=3, max_items=5)
    followUps: List[str] = Field(..., min_items=3, max_items=3)
    timeToAnswer: int = Field(..., ge=60, le=300)
    questionId: str = Field(..., pattern="^Q\\d+\\.\\d+\\.\\d+$")
    expectedAnswerPoints: List[str] = Field(..., min_items=2, max_items=5)


class QuestionGenerationResponse(BaseModel):
    questions: List[GeneratedQuestion]
    metadata: Dict[str, Any] = {}


# Create the router
router = APIRouter()

# Question generation schema
QUESTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft/2020-12/schema",
    "title": "Phone Interview Questions Compatible Schema",
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "description": "Array of interview questions",
            "items": {
                "type": "object",
                "required": [
                    "question",
                    "linkedSkillArea",
                    "linkedSubSkillArea",
                    "difficultyLevel",
                    "questionType",
                    "greenFlags",
                    "redFlags"
                ],
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The interview question text"
                    },
                    "linkedSkillArea": {
                        "type": "string",
                        "description": "Main skill category this question belongs to"
                    },
                    "linkedSubSkillArea": {
                        "type": "string",
                        "description": "Specific sub-skill being assessed"
                    },
                    "difficultyLevel": {
                        "type": "string",
                        "description": "Question difficulty level (low, medium, high)"
                    },
                    "questionType": {
                        "type": "string",
                        "description": "Type of question (experience, tradeoff, concept-application, concept-definition, concept)"
                    },
                    "greenFlags": {
                        "type": "array",
                        "description": "Positive indicators in the response",
                        "items": {"type": "string"}
                    },
                    "redFlags": {
                        "type": "array",
                        "description": "Warning signs or incorrect understanding",
                        "items": {"type": "string"}
                    },
                    "followUps": {
                        "type": "array",
                        "description": "Follow-up questions",
                        "items": {"type": "string"}
                    },
                    "timeToAnswer": {
                        "type": "integer",
                        "description": "Recommended time for this question in seconds"
                    },
                    "questionId": {
                        "type": "string",
                        "description": "Unique identifier for tracking"
                    },
                    "expectedAnswerPoints": {
                        "type": "array",
                        "description": "Key points expected in a good answer",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    },
    "required": ["questions"]
}

SYSTEM_PROMPT = """## System Role
You are an expert technical recruiter and interviewer with 20+ years of experience conducting phone screens for technology positions. You specialize in creating efficient, revealing phone interview questions that effectively assess candidates within the constraints of a 30-minute phone conversation.

## Context and Constraints
You are generating phone interview questions with these specific constraints:
- **Medium**: Phone call (no visual aids, no screen sharing, no live coding)
- **Duration**: 30 minutes total (including introductions and candidate questions)
- **Purpose**: Initial technical screening and culture fit assessment
- **Format**: Verbal Q&A that can be clearly communicated and answered over phone
- **Evaluation**: Questions must enable clear pass/fail decisions

## Input Structure
You will receive:
1. **Job Description**: Complete role details including responsibilities, requirements, and desired skills
2. **Skills Array**: Structured skill categories with sub-skills and difficulty levels
   - Each sub-skill has a difficulty rating: easy, medium, or hard
   - Generate exactly 5 questions per sub-skill at the specified difficulty level

## Generation Requirements

### For Each Sub-Skill, Generate 5 Questions Following This Distribution:
1. **Question 1**: Fundamental Concept Verification (20% of difficulty level)
2. **Question 2**: Practical Application Scenario (40% of difficulty level)
3. **Question 3**: Problem-Solving Approach (60% of difficulty level)
4. **Question 4**: Experience-Based Situational (80% of difficulty level)
5. **Question 5**: Deep Dive/Edge Case (100% of difficulty level)

### Difficulty Level Calibration:
- **Easy**: Junior level (0-2 years), basic understanding, common scenarios  -> Map to "low"
- **Medium**: Mid-level (2-5 years), solid grasp, real-world applications    -> Map to "medium"
- **Hard**: Senior level (5+ years), expert knowledge, complex scenarios     -> Map to "high"

### Question Design Principles:
1. **Verbal-Friendly**: Can be clearly asked and answered without visual aids
2. **Time-Bound**: Answerable in 1-3 minutes
3. **Unambiguous**: Clear, specific, single-focused
4. **Progressive**: Build from simple to complex within each sub-skill
5. **Revealing**: Distinguish between genuine experience and theoretical knowledge
6. **Objective**: Enable consistent evaluation across different interviewers

## Output Requirements

For each question, you MUST provide:
1. **question**: Clear, specific question text (10-500 characters)
2. **linkedSkillArea**: Main skill category name
3. **linkedSubSkillArea**: Specific sub-skill being assessed
4. **difficultyLevel**: "low", "medium", or "high"
5. **questionType**: One of: "experience", "tradeoff", "concept-application", "concept-definition", "concept"
6. **greenFlags**: 3-5 positive indicators in responses
7. **redFlags**: 3-5 warning signs or incorrect understanding
8. **followUps**: Exactly 3 follow-up questions
9. **timeToAnswer**: Time in seconds (60-300)
10. **questionId**: Format "Q[skill_num].[subskill_num].[question_num]"
11. **expectedAnswerPoints**: 2-5 key points for a good answer

### Question Type Guidelines:
- **experience**: "Tell me about a time when..." or "In your experience..."
- **tradeoff**: Comparing options, discussing pros/cons, decision-making
- **concept-application**: Applying knowledge to solve problems
- **concept-definition**: Explaining concepts, definitions, how things work
- **concept**: General conceptual understanding

### For Phone Interview Appropriateness:
1. **Avoid**: "Show me how you would..." or "Write code for..."
2. **Prefer**: "Describe your approach to..." or "Walk me through how you would..."
3. **Avoid**: Complex algorithms requiring visualization
4. **Prefer**: Conceptual understanding and trade-off discussions

Return valid JSON matching the provided schema."""


@router.post("/generate-questions", response_model=QuestionGenerationResponse)
async def generate_interview_questions(request: QuestionGenerationRequest):
    """
    Generate phone interview questions based on job description and skills requirements.

    Takes job description and skills array, uses LLM to generate structured interview questions
    optimized for 30-minute phone screens.
    """
    try:
        print("\n" + "="*50)
        print("🚀 Starting interview question generation...")

        # Use OpenRouter with Qwen model that works in the codebase
        provider = "openrouter"
        model = "qwen/qwen3-235b-a22b-2507"  # Same model used in evaluation endpoint

        print(f"📊 Provider: {provider}")
        print(f"🤖 Model: {model}")

        # Check API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="OPENROUTER_API_KEY not found in environment variables"
            )

        # Create LLM client
        llm_client = create_llm_client(
            provider=provider,
            model=model,
            api_key=api_key
        )

        # Prepare input data
        input_data = {
            "job_description": request.job_description,
            "skills": request.skills
        }

        print(f"📋 Processing {len(request.skills)} skill areas...")
        for i, skill in enumerate(request.skills):
            skill_name = skill.get("skill_name", f"Skill {i+1}")
            sub_skills = skill.get("sub_skills", {})
            print(f"   - {skill_name}: {len(sub_skills)} sub-skills")

        # Prepare LLM messages
        llm_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate interview questions for this job: {json.dumps(input_data, indent=2)}"}
        ]

        print("🤖 Generating questions with LLM...")
        llm_response = await llm_client.generate(llm_messages, QUESTION_SCHEMA)

        print("🔍 Parsing LLM response...")
        try:
            questions_data = json.loads(llm_response)
            print(f"✅ Generated {len(questions_data.get('questions', []))} questions successfully")

            # Add metadata
            metadata = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": model,
                "provider": provider,
                "total_questions": len(questions_data.get("questions", [])),
                "skill_areas_processed": len(request.skills)
            }

            response = QuestionGenerationResponse(
                questions=questions_data.get("questions", []),
                metadata=metadata
            )

            print("✅ Question generation completed successfully!")
            print("="*50 + "\n")

            return response

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse LLM response: {str(e)}")
            print(f"📄 Raw response (first 1000 chars): {llm_response[:1000]}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse question generation response: {str(e)}"
            )

    except Exception as e:
        print(f"❌ Error during question generation: {str(e)}")
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=f"Error generating questions: {str(e)}")


# Function to extract JSON safely from LLM response
def extract_json_from_response(response_text: str) -> str:
    """Extract JSON from potentially wrapped LLM response"""
    try:
        # First try parsing as-is
        json.loads(response_text)
        return response_text
    except json.JSONDecodeError:
        # Look for JSON block markers
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                return response_text[start:end].strip()

        # Look for JSON object boundaries
        start = response_text.find("{")
        if start != -1:
            # Find matching closing brace
            brace_count = 0
            for i, char in enumerate(response_text[start:], start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return response_text[start:i+1]

        return response_text