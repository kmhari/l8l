import re
import json
from typing import List, Dict, Any
from models import QuestionData


def parse_technical_questions(technical_questions: str) -> List[QuestionData]:
    """Parse technical questions string into structured QuestionData objects"""
    questions = []

    question_sections = re.split(r'Q\d+:', technical_questions)

    for i, section in enumerate(question_sections[1:], 1):
        lines = section.strip().split('\n')
        if not lines:
            continue

        question_text = lines[0].strip()

        green_flags = []
        red_flags = []

        current_section = None
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            if line.startswith('G') and 'Green flags:' in line:
                current_section = 'green'
                continue
            elif line.startswith('Red flags:'):
                current_section = 'red'
                continue
            elif line.startswith('- '):
                flag_text = line[2:].strip()
                if current_section == 'green' and flag_text:
                    green_flags.append(flag_text)
                elif current_section == 'red' and flag_text:
                    red_flags.append(flag_text)

        questions.append(QuestionData(
            question=question_text,
            green_flags=green_flags,
            red_flags=red_flags
        ))

    return questions


def prepare_known_questions(questions: List[QuestionData]) -> List[Dict]:
    """Convert parsed questions to the format expected by the LLM"""
    known_questions = []
    for i, q in enumerate(questions, 1):
        known_questions.append({
            "id": f"Q{i}",
            "title": f"Question {i}",
            "text": q.question,
            "greenFlags": q.green_flags,
            "redFlags": q.red_flags
        })
    return known_questions


def build_conversations_from_indices(groups: List[Dict], all_messages: List[Dict]) -> List[Dict]:
    """Build conversation arrays from turn indices for performance optimization"""
    processed_groups = []

    for group in groups:
        processed_group = group.copy()

        conversation = []
        for idx in group.get("turn_indices", []):
            if idx < len(all_messages):
                message = all_messages[idx]
                conversation.append({
                    "idx": idx,
                    "role": message.get("role"),
                    "message": message.get("message"),
                    "time": message.get("time"),
                    "endTime": message.get("endTime"),
                    "duration": message.get("duration"),
                    "secondsFromStart": message.get("secondsFromStart")
                })

        processed_group["conversation"] = conversation
        processed_groups.append(processed_group)

    return processed_groups


def extract_candidate_info_from_transcript(transcript: Dict[str, Any]) -> Dict[str, str]:
    """Extract candidate information from transcript variables field"""
    candidate_info = {
        "candidate_name": "Unknown",
        "job_title": "Unknown",
        "company_name": "Unknown",
        "salary_range": "Not specified",
        "company_profile": "Not available",
        "job_requirements": "Not available"
    }

    if "variables" in transcript:
        variables = transcript["variables"]
        if isinstance(variables, dict):
            candidate_info.update({
                "candidate_name": variables.get("candidate_name", candidate_info["candidate_name"]),
                "job_title": variables.get("job_title", candidate_info["job_title"]),
                "company_name": variables.get("company_name", candidate_info["company_name"]),
                "salary_range": variables.get("salary_range", candidate_info["salary_range"]),
                "company_profile": variables.get("company_profile", candidate_info["company_profile"]),
                "job_requirements": variables.get("job_requirements", candidate_info["job_requirements"])
            })

    return candidate_info


def save_output_to_file(output_data: Dict[str, Any], filename: str, directory: str = "output") -> str:
    """Save output data to a JSON file"""
    from pathlib import Path

    output_dir = Path(directory)
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / filename

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    return str(output_path)