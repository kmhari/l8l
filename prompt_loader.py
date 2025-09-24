import json
from pathlib import Path
from typing import Dict, Any, Tuple
from fastapi import HTTPException


async def load_prompts() -> Tuple[str, Dict[str, Any]]:
    """Load gather system prompt and schema"""
    try:
        system_prompt = Path("prompts/gather.md").read_text()
        schema = json.loads(Path("prompts/gather.schema.json").read_text())
        return system_prompt, schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading gather prompts: {str(e)}")


async def load_evaluation_prompts() -> Tuple[str, Dict[str, Any]]:
    """Load evaluation prompt and schema"""
    try:
        evaluation_prompt = Path("prompts/evaluate.md").read_text()
        evaluation_schema = json.loads(Path("prompts/evaluation.schema.json").read_text())
        return evaluation_prompt, evaluation_schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading evaluation prompts: {str(e)}")


async def load_skills_assessment_prompts() -> Tuple[str, Dict[str, Any]]:
    """Load skills assessment prompt and schema"""
    try:
        skills_prompt = Path("prompts/assess_skills.md").read_text()
        skills_schema = json.loads(Path("prompts/skills_assessment.schema.json").read_text())
        return skills_prompt, skills_schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading skills assessment prompts: {str(e)}")


async def load_evaluation_config() -> Dict[str, Any]:
    """Load evaluation configuration - returns empty config, expects data to be provided in requests"""
    # Return empty configuration - all data should be provided via API requests
    return {}