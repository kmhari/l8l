import json
import re
import asyncio
from typing import Dict, Any, List, Optional
from utils import extract_candidate_info_from_transcript
from prompt_loader import load_skills_assessment_prompts


async def evaluate_question_group(group: Dict[str, Any], resume: Dict[str, Any],
                                job_requirements: str, llm_client, evaluation_prompt: str,
                                evaluation_schema: Dict) -> Dict[str, Any]:
    """Evaluate a single question group focusing on question analysis only"""
    print(f"🔍 Evaluating question group: {group.get('question_id', 'Unknown')} (question analysis only)")

    populated_prompt = evaluation_prompt.replace(
        "{{RESUME_CONTENT}}", json.dumps(resume, indent=2)
    ).replace(
        "{{JOB_REQUIREMENTS}}", job_requirements
    ).replace(
        "{{KEY_SKILL_AREAS}}", "[]"
    )

    evaluation_input = {
        "question_group": group,
        "transcript_messages": group.get("conversation", [])
    }

    evaluation_messages = [
        {"role": "system", "content": populated_prompt},
        {"role": "user", "content": f"Evaluate this specific question group: {json.dumps(evaluation_input)}"}
    ]

    try:
        evaluation_result = await llm_client.generate(evaluation_messages, evaluation_schema)

        print(f"📋 Response for {group.get('question_id', 'Unknown')}: {len(evaluation_result)} chars")

        try:
            evaluation_data = json.loads(evaluation_result)
            print(f"✅ Evaluation parsed successfully for group {group.get('question_id', 'Unknown')}")
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse evaluation for group {group.get('question_id', 'Unknown')}: {str(e)}")
            print(f"📄 Raw response (first 1000 chars): {evaluation_result[:1000]}")
            evaluation_data = {
                "overall_assessment": {
                    "recommendation": "No Hire",
                    "confidence": "Low",
                    "overall_answer_score": 0,
                    "overall_key_skill_score": 0,
                    "summary": "Failed to parse evaluation response"
                },
                "question_analysis": [],
                "communication_assessment": {
                    "verbal_articulation": "Fair",
                    "logical_flow": "Fair",
                    "professional_vocabulary": "Fair",
                    "cultural_fit_indicators": []
                },
                "critical_analysis": {
                    "problem_solving_approach": "Unable to assess due to parsing failure"
                },
                "improvement_recommendations": ["Re-evaluate this response manually"],
                "parsing_error": True,
                "raw_response_preview": evaluation_result[:500] if len(evaluation_result) > 500 else evaluation_result
            }

        evaluation_data["group_metadata"] = {
            "question_id": group.get("question_id"),
            "question_title": group.get("question_title"),
            "type": group.get("type"),
            "time_range": group.get("time_range")
        }

        print(f"✅ Completed evaluation for group: {group.get('question_id', 'Unknown')}")
        return evaluation_data

    except Exception as e:
        print(f"❌ Error evaluating group {group.get('question_id', 'Unknown')}: {str(e)}")
        return {
            "error": f"Failed to evaluate group: {str(e)}",
            "group_metadata": {
                "question_id": group.get("question_id"),
                "question_title": group.get("question_title"),
                "type": group.get("type"),
                "time_range": group.get("time_range")
            }
        }


async def evaluate_skills_holistically(transcript: Dict[str, Any], key_skill_areas: List[Dict[str, Any]],
                                     resume: Dict[str, Any], job_requirements: str, llm_client) -> Dict[str, Any]:
    """Evaluate skills competency holistically across the entire transcript"""
    print("🔍 Starting holistic skills competency assessment...")

    skills_prompt, skills_schema = await load_skills_assessment_prompts()

    populated_prompt = skills_prompt.replace(
        "{{RESUME_CONTENT}}", json.dumps(resume, indent=2)
    ).replace(
        "{{JOB_REQUIREMENTS}}", job_requirements
    ).replace(
        "{{KEY_SKILL_AREAS}}", json.dumps(key_skill_areas, indent=2)
    )

    messages = transcript.get("messages", [])

    skills_input = {
        "transcript_messages": [
            {
                "idx": i,
                "role": msg.get("role"),
                "time": msg.get("time"),
                "message": msg.get("message"),
                "endTime": msg.get("endTime"),
                "duration": msg.get("duration"),
                "secondsFromStart": msg.get("secondsFromStart")
            }
            for i, msg in enumerate(messages)
        ],
        "key_skill_areas": key_skill_areas
    }

    skills_messages = [
        {"role": "system", "content": populated_prompt},
        {"role": "user", "content": f"Assess skills competency based on this complete interview data: {json.dumps(skills_input)}"}
    ]

    try:
        print(f"🤖 Generating skills assessment for {len(key_skill_areas)} skill areas...")

        skills_result = await llm_client.generate(skills_messages, skills_schema)

        try:
            skills_data = json.loads(skills_result)
            print(f"✅ Skills assessment completed successfully")
            return skills_data
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse skills assessment: {str(e)}")
            print(f"📄 Raw response (first 1000 chars): {skills_result[:1000]}")
            return {
                "competency_mapping": [],
                "overall_skills_summary": {
                    "total_skill_areas_assessed": 0,
                    "skill_areas_meeting_requirements": 0,
                    "strongest_skill_areas": [],
                    "development_areas": [],
                    "overall_competency_level": "Entry",
                    "hiring_recommendation_skills": "No Hire",
                    "key_findings": ["Failed to parse skills assessment response"]
                },
                "parsing_error": True,
                "raw_response_preview": skills_result[:500] if len(skills_result) > 500 else skills_result
            }

    except Exception as e:
        print(f"❌ Error during skills assessment: {str(e)}")
        return {
            "competency_mapping": [],
            "overall_skills_summary": {
                "total_skill_areas_assessed": 0,
                "skill_areas_meeting_requirements": 0,
                "strongest_skill_areas": [],
                "development_areas": [],
                "overall_competency_level": "Entry",
                "hiring_recommendation_skills": "No Hire",
                "key_findings": [f"Skills assessment failed: {str(e)}"]
            },
            "error": str(e)
        }


async def merge_evaluations(evaluations: List[Dict[str, Any]],
                          global_facts: Dict[str, Any],
                          skills_assessment: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Merge individual group evaluations into a comprehensive report"""
    print("🔄 Merging individual evaluations into comprehensive report...")
    print(f"📊 Received {len(evaluations)} evaluations to merge")

    for i, eval_item in enumerate(evaluations):
        print(f"🔍 Evaluation {i+1}: type={type(eval_item)}, keys={list(eval_item.keys()) if isinstance(eval_item, dict) else 'N/A'}")

    merged_report = {
        "overall_assessment": {
            "recommendation": "No Hire",
            "confidence": "Medium",
            "overall_answer_score": 0,
            "overall_key_skill_score": 0,
            "summary": ""
        },
        "competency_mapping": [],
        "question_analysis": [],
        "communication_assessment": {
            "verbal_articulation": "Fair",
            "logical_flow": "Fair",
            "professional_vocabulary": "Fair",
            "cultural_fit_indicators": []
        },
        "critical_analysis": {
            "problem_solving_approach": ""
        },
        "improvement_recommendations": []
    }

    if skills_assessment and "competency_mapping" in skills_assessment:
        merged_report["competency_mapping"] = skills_assessment["competency_mapping"]
        print(f"✅ Used holistic skills assessment for competency mapping ({len(skills_assessment['competency_mapping'])} skill areas)")
    else:
        print("⚠️  No skills assessment provided, competency mapping will be empty")

    for evaluation in evaluations:
        if isinstance(evaluation, dict) and "error" not in evaluation and "question_analysis" in evaluation:
            if isinstance(evaluation["question_analysis"], list):
                merged_report["question_analysis"].extend(evaluation["question_analysis"])

    all_recommendations = []
    problem_solving_approaches = []

    for evaluation in evaluations:
        if isinstance(evaluation, dict) and "error" not in evaluation:
            if "critical_analysis" in evaluation and isinstance(evaluation["critical_analysis"], dict):
                critical_analysis = evaluation["critical_analysis"]
                if "problem_solving_approach" in critical_analysis and isinstance(critical_analysis["problem_solving_approach"], str):
                    if critical_analysis["problem_solving_approach"].strip():
                        problem_solving_approaches.append(critical_analysis["problem_solving_approach"])

            if "improvement_recommendations" in evaluation and isinstance(evaluation["improvement_recommendations"], list):
                all_recommendations.extend(evaluation["improvement_recommendations"])

    if problem_solving_approaches:
        merged_report["critical_analysis"]["problem_solving_approach"] = max(problem_solving_approaches, key=len)
    else:
        merged_report["critical_analysis"]["problem_solving_approach"] = "No clear problem-solving approach demonstrated"

    merged_report["improvement_recommendations"] = list(set(all_recommendations))

    print(f"🔍 Starting overall score calculation from {len(evaluations)} evaluations")
    all_question_analyses = []
    for i, e in enumerate(evaluations):
        print(f"🔍 Processing evaluation {i+1}: has question_analysis = {isinstance(e.get('question_analysis'), list)}")
        if (isinstance(e, dict) and
            "error" not in e and
            "question_analysis" in e and
            isinstance(e["question_analysis"], list)):

            print(f"🔍 Evaluation {i+1} has {len(e['question_analysis'])} question analyses")
            for j, qa in enumerate(e["question_analysis"]):
                qa_valid = (isinstance(qa, dict) and
                    "question_id" in qa and
                    "answer_quality" in qa and
                    isinstance(qa["answer_quality"], dict) and
                    "relevance_score" in qa["answer_quality"] and
                    isinstance(qa["answer_quality"]["relevance_score"], (int, float)))
                print(f"🔍 Question analysis {j+1} valid: {qa_valid}, question_id: {qa.get('question_id', 'N/A')}")
                if qa_valid:
                    all_question_analyses.append(qa)

    print(f"🔍 Found {len(all_question_analyses)} total valid question analyses")

    valid_question_analyses = []
    for qa in all_question_analyses:
        question_id = qa.get("question_id", "")
        if re.match(r'^Q\d+$', question_id):
            valid_question_analyses.append(qa)
            print(f"🔍 Including question {question_id} in overall score calculation (relevance_score: {qa['answer_quality']['relevance_score']})")
        else:
            print(f"🔍 Excluding non-standard question {question_id} from overall score calculation")

    print(f"🔍 Found {len(valid_question_analyses)} Q-numbered questions for scoring")

    if valid_question_analyses:
        avg_score = sum(qa["answer_quality"]["relevance_score"] for qa in valid_question_analyses) / len(valid_question_analyses)
        merged_report["overall_assessment"]["overall_answer_score"] = round(avg_score, 1)
        print(f"📊 Overall score calculated from {len(valid_question_analyses)} Q-numbered questions: {avg_score:.1f}")

        if avg_score >= 75:
            merged_report["overall_assessment"]["recommendation"] = "Strong Hire"
        elif avg_score >= 55:
            merged_report["overall_assessment"]["recommendation"] = "Hire"
        elif avg_score >= 35:
            merged_report["overall_assessment"]["recommendation"] = "No Hire"
        else:
            merged_report["overall_assessment"]["recommendation"] = "Strong No Hire"

        successful_evaluations = len(valid_question_analyses)
        total_questions = len(all_question_analyses)

        merged_report["overall_assessment"]["summary"] = f"Evaluation based on {successful_evaluations} Q-numbered questions. Custom questions are filtered out before processing."
    else:
        print("⚠️ No valid Q-numbered questions found for overall score calculation")
        merged_report["overall_assessment"]["overall_answer_score"] = 0

    # Calculate overall_key_skill_score from competency mapping
    overall_key_skill_score = calculate_overall_key_skill_score(merged_report.get("competency_mapping", []))
    if overall_key_skill_score is not None:
        merged_report["overall_assessment"]["overall_key_skill_score"] = overall_key_skill_score
        print(f"✅ Overall key skill score calculated: {overall_key_skill_score}")
    else:
        merged_report["overall_assessment"]["overall_key_skill_score"] = 0
        print("⚠️ No skill data available for overall key skill score")

    # Calculate overall skill scoring from skills assessment
    if skills_assessment and "competency_mapping" in skills_assessment:
        print("🔄 Calculating overall skill scoring from skills assessment...")
        print(f"📊 Skills assessment structure: {list(skills_assessment.keys())}")
        print(f"📋 Competency mapping has {len(skills_assessment['competency_mapping'])} skill areas")

        # Debug: show first skill area structure
        if skills_assessment["competency_mapping"]:
            first_skill = skills_assessment["competency_mapping"][0]
            print(f"🔍 First skill area structure: {list(first_skill.keys())}")

    else:
        print("⚠️ No skills assessment data available")

    print("✅ Evaluation merging completed")
    return merged_report


def convert_qualitative_to_score(assessment: str) -> int:
    """Convert qualitative skill assessment to numerical score (0-100)"""
    if not assessment:
        return 0

    assessment_lower = assessment.lower()

    # Map qualitative levels to numerical scores
    if "expert" in assessment_lower:
        return 90
    elif "advanced" in assessment_lower:
        return 80
    elif "intermediate" in assessment_lower:
        return 70
    elif "basic" in assessment_lower:
        return 60
    elif "entry" in assessment_lower:
        return 50
    elif "not demonstrated" in assessment_lower or "none" in assessment_lower:
        return 20
    else:
        return 50  # Default fallback


def calculate_overall_skill_scoring(competency_mapping: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Calculate overall skill scoring from competency mapping"""
    if not competency_mapping:
        return None

    try:
        overall_skill_score = calculate_overall_key_skill_score(competency_mapping)
        if overall_skill_score is None:
            return None

        return {
            "overall_skill_score": overall_skill_score,
            "total_skills_assessed": len(competency_mapping),
            "calculation_method": "Average of all skill and sub-skill scores"
        }
    except Exception as e:
        print(f"❌ Error calculating overall skill scoring: {str(e)}")
        return None


def calculate_overall_key_skill_score(competency_mapping: List[Dict[str, Any]]) -> Optional[float]:
    """Calculate overall key skill score as average of all skills and sub-skills"""
    if not competency_mapping:
        return None

    all_scores = []

    for skill in competency_mapping:
        # Get main skill score
        if "skill_score" in skill and isinstance(skill["skill_score"], (int, float)):
            all_scores.append(skill["skill_score"])
        else:
            # Convert qualitative assessment to score
            overall_assessment = skill.get("overall_assessment", "")
            if overall_assessment:
                score = convert_qualitative_to_score(overall_assessment)
                all_scores.append(score)

        # Get sub-skills scores if available
        if "sub_skills" in skill and isinstance(skill["sub_skills"], list):
            for sub_skill in skill["sub_skills"]:
                if isinstance(sub_skill, dict):
                    if "skill_score" in sub_skill and isinstance(sub_skill["skill_score"], (int, float)):
                        all_scores.append(sub_skill["skill_score"])
                    else:
                        # Try proficiency level for sub-skills
                        proficiency = sub_skill.get("proficiency", "")
                        if proficiency:
                            score = convert_qualitative_to_score(proficiency)
                            all_scores.append(score)

    if not all_scores:
        return None

    overall_score = sum(all_scores) / len(all_scores)
    print(f"🔢 Calculated overall key skill score from {len(all_scores)} individual scores: {overall_score:.1f}")
    return round(overall_score, 1)


