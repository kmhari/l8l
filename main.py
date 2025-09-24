from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import re
import json
import asyncio
import os
import time
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from scalar_fastapi import get_scalar_api_reference
from llm_client import create_llm_client
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import globals as config



# Load environment variables
load_dotenv(override=True)

app = FastAPI(
    title="Interview Report Generator API",
    description="API for processing interview transcripts and generating structured reports",
    version="1.0.0"
)



class GatherRequest(BaseModel):
    transcript: Dict[str, Any]
    technical_questions: str
    key_skill_areas: List[Dict[str, Any]]

    class Config:
        pass

class QuestionData(BaseModel):
    question: str
    green_flags: List[str]
    red_flags: List[str]

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
                    "pre_inferred_facts_global": {                        
                    }
                }
            }
        }

class EvaluateRequest(BaseModel):
    transcript: Dict[str, Any]
    resume: Optional[Dict[str, Any]] = None
    key_skill_areas: Optional[List[Dict[str, Any]]] = None

    class Config:
        pass

class EvaluateResponse(BaseModel):
    evaluation_report: Dict[str, Any]
    question_groups: Dict[str, Any]

    class Config:
        pass

def parse_technical_questions(technical_questions: str) -> List[QuestionData]:
    questions = []

    # Split by Q1:, Q2:, etc.
    question_sections = re.split(r'Q\d+:', technical_questions)

    for i, section in enumerate(question_sections[1:], 1):  # Skip first empty element
        lines = section.strip().split('\n')
        if not lines:
            continue

        # Extract question text (first line)
        question_text = lines[0].strip()

        # Extract green flags and red flags
        green_flags = []
        red_flags = []

        current_section = None
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            if line.startswith('G') and 'Green flags:' in line:
                current_section = 'green'
                continue
            elif line.startswith('Red flags:'):
                current_section = 'red'
                continue
            elif line.startswith('- '):
                # Extract flag text
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

async def load_prompts():
    """Load system prompt and schema"""
    try:
        system_prompt = Path("prompts/gather.md").read_text()
        schema = json.loads(Path("prompts/gather.schema.json").read_text())
        return system_prompt, schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading prompts: {str(e)}")

async def prepare_known_questions(questions: List[QuestionData]) -> List[Dict]:
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

        # Build conversation from indices
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

def generate_cache_key(request: GatherRequest) -> str:
    """Generate MD5 hash from the gather request input"""
    # Create a normalized representation of the input data
    cache_input = {
        "transcript": request.transcript,
        "technical_questions": request.technical_questions,
        "key_skill_areas": request.key_skill_areas,            # Include model settings as they affect the output
    }

    # Convert to JSON string with sorted keys for consistent hashing
    input_string = json.dumps(cache_input, sort_keys=True, separators=(',', ':'))

    # Generate MD5 hash
    return hashlib.md5(input_string.encode('utf-8')).hexdigest()

def get_cache_path(cache_key: str) -> Path:
    """Get the file path for a cache key"""
    cache_dir = Path("cache/gather")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{cache_key}.json"

def load_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Load cached gather result if it exists"""
    cache_path = get_cache_path(cache_key)

    try:
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            # Verify cache integrity
            if "llm_output" in cached_data and "cache_key" in cached_data:
                return cached_data
            else:
                print(f"⚠️  Invalid cache file format: {cache_path}")
                cache_path.unlink()  # Remove corrupted cache file

    except Exception as e:
        print(f"⚠️  Error reading cache file {cache_path}: {str(e)}")
        if cache_path.exists():
            try:
                cache_path.unlink()  # Remove corrupted cache file
            except:
                pass

    return None

def save_to_cache(cache_key: str, llm_output: Dict[str, Any], request_metadata: Dict[str, Any]) -> None:
    """Save gather result to cache"""
    cache_path = get_cache_path(cache_key)

    try:
        cache_data = {
            "cache_key": cache_key,
            "timestamp": int(time.time()),
            "request_metadata": request_metadata,
            "llm_output": llm_output
        }

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Result cached to: {cache_path}")

    except Exception as e:
        print(f"⚠️  Failed to save to cache: {str(e)}")

@app.post("/gather", response_model=GatherResponse)
async def gather(request: GatherRequest):
    try:
        print("\n" + "="*50)
        print("🚀 Starting report generation...")

        # Get configuration from environment
       
        provider = "openrouter"  # Always use OpenRouter
        model = config.CEREBRAS_MODELS.GPT_OSS
        
        print(f"📊 Provider: {provider}")
        print(f"🤖 Model: {model}")

        # Generate cache key for this request
        print("🔑 Generating cache key...")
        cache_key = generate_cache_key(request)
        print(f"✅ Cache key: {cache_key}")

        # Check if result is already cached
        print("🔍 Checking cache...")
        cached_result = load_from_cache(cache_key)
        if cached_result:
            print("🎯 Cache hit! Returning cached result...")
            cached_timestamp = cached_result.get("timestamp", 0)
            age_minutes = (time.time() - cached_timestamp) / 60
            print(f"📅 Cache age: {age_minutes:.1f} minutes")

            # Return cached result
            response = GatherResponse(llm_output=cached_result["llm_output"])

            # Also save to output directory with current timestamp for consistency
            try:
                output_dir = Path("output")
                output_dir.mkdir(exist_ok=True)
                timestamp = int(time.time())
                filename = f"gather_output_{timestamp}_cached.json"
                output_path = output_dir / filename

                output_data = {
                    "timestamp": timestamp,
                    "cached_from": cached_result["timestamp"],
                    "cache_key": cache_key,
                    "request_data": {
                        "transcript_messages_count": len(request.transcript.get("messages", [])),
                        "technical_questions_count": len(parse_technical_questions(request.technical_questions)),
                        "key_skill_areas_count": len(request.key_skill_areas),
                    },
                    "llm_output": cached_result["llm_output"]
                }

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)

                print(f"✅ Cached result also saved to: {output_path}")
            except Exception as e:
                print(f"⚠️  Failed to save cached result to output: {str(e)}")

            print("✅ Report generation completed (from cache)!")
            print("="*50 + "\n")
            return response

        print("💾 Cache miss - proceeding with LLM generation...")

        # Parse technical questions into structured format
        print("📝 Parsing technical questions...")
        questions = parse_technical_questions(request.technical_questions)
        print(f"✅ Parsed {len(questions)} technical questions")

        # Extract messages from transcript
        print("💬 Extracting transcript messages...")
        messages = request.transcript.get("messages", [])
        print(f"✅ Found {len(messages)} conversation messages")

        # Load system prompt and schema
        print("📋 Loading system prompt and schema...")
        system_prompt, schema = await load_prompts()
        print("✅ System prompt and schema loaded")

        # Prepare known questions for LLM
        print("🔄 Preparing questions for LLM...")
        known_questions = await prepare_known_questions(questions)
        print(f"✅ Prepared {len(known_questions)} questions for analysis")

        # Prepare input data for LLM
        print("📦 Preparing input data...")
        llm_input = {
            "turns": [
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
            "known_questions": known_questions
        }
        print(f"✅ Input data prepared ({len(llm_input['turns'])} turns)")

        # Get API key from environment
        print("🔑 Checking API key...")
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            print(f"✅ Using API key from environment: OPENROUTER_API_KEY")
        else:
            raise HTTPException(
                status_code=500,
                detail="OPENROUTER_API_KEY not found in environment variables"
            )

        # Create LLM client
        print("🔧 Creating LLM client...")
        llm_client = create_llm_client(
            provider=provider,
            model=model,
            api_key=api_key
        )
        print("✅ LLM client created successfully")

        # Prepare messages for LLM
        print("📝 Preparing LLM messages...")
        llm_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Input data: {json.dumps(llm_input)}"}
        ]
        input_tokens = len(json.dumps(llm_input))
        print(f"✅ Messages prepared (~{input_tokens:,} characters)")

        # Generate LLM response
        print("🤖 Generating LLM response...")
        print(f"   Provider: {provider}")
        print(f"   Model: {model}")
        llm_response = await llm_client.generate(llm_messages, schema)
        print("✅ LLM response generated")

        # Parse response
        print("🔍 Parsing LLM response...")
        try:
            llm_output = json.loads(llm_response)
            groups_count = len(llm_output.get("groups", []))
            print(f"✅ Response parsed successfully ({groups_count} conversation groups)")
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse LLM response: {str(e)}")
            print(f"Raw response preview: {llm_response[:500]}...")
            llm_output = {"error": "Failed to parse LLM response", "raw_response": llm_response}

        # Post-process: Build conversations from indices (only if parsing succeeded)
        if "groups" in llm_output and "error" not in llm_output:
            print("🔄 Building conversations from indices...")
            llm_output["groups"] = build_conversations_from_indices(
                llm_output["groups"],
                messages
            )
            print(f"✅ Conversations built for {len(llm_output['groups'])} groups")

        print("📊 Generating final response...")
        response = GatherResponse(
            llm_output=llm_output
        )

        # Save to cache and disk
        print("💾 Saving results to cache and disk...")

        # Prepare request metadata
        request_metadata = {
            "transcript_messages_count": len(messages),
            "technical_questions_count": len(questions),
            "key_skill_areas_count": len(request.key_skill_areas),
            "llm_settings": request.llm_settings.dict()
        }

        # Save to cache (only if LLM generation was successful)
        if "error" not in llm_output:
            save_to_cache(cache_key, llm_output, request_metadata)

        # Save to output directory
        try:
            # Create output directory if it doesn't exist
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

            # Generate filename with timestamp
            timestamp = int(time.time())
            filename = f"gather_output_{timestamp}.json"
            output_path = output_dir / filename

            # Save the complete response
            output_data = {
                "timestamp": timestamp,
                "cache_key": cache_key,
                "request_data": request_metadata,
                "llm_output": llm_output
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Gather output saved to: {output_path}")

        except Exception as e:
            print(f"⚠️  Failed to save gather output: {str(e)}")

        print("✅ Report generation completed successfully!")
        print("="*50 + "\n")

        return response

    except Exception as e:
        print(f"❌ Error during report generation: {str(e)}")
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

async def call_gather_endpoint(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Internal function to call the gather endpoint"""
    gather_request = GatherRequest(**request_data)
    gather_response = await gather(gather_request)
    return gather_response.llm_output


async def evaluate_question_group(group: Dict[str, Any], resume: Dict[str, Any],
                                job_requirements: str, key_skill_areas: List[Dict[str, Any]],
                                llm_client, evaluation_prompt: str, evaluation_schema: Dict) -> Dict[str, Any]:
    """Evaluate a single question group using the thinking model"""
    print(f"🔍 Evaluating question group: {group.get('question_id', 'Unknown')}")

    # Remove sample response structure - let the LLM use only schema and instructions
    print(f"🔧 Using schema-only evaluation for {len(key_skill_areas)} skill areas")
    print(f"📋 Expected skill areas: {[skill['name'] for skill in key_skill_areas]}")

    # Populate the system prompt with candidate information only
    populated_prompt = evaluation_prompt.replace(
        "{{RESUME_CONTENT}}", json.dumps(resume, indent=2)
    ).replace(
        "{{JOB_REQUIREMENTS}}", job_requirements
    ).replace(
        "{{KEY_SKILL_AREAS}}", json.dumps(key_skill_areas, indent=2)
    )

    # Prepare the input data for this specific group (without resume, job_requirements, key_skill_areas)
    evaluation_input = {
        "question_group": group,
        "transcript_messages": group.get("conversation", [])
    }

    # Create the evaluation prompt with specific data
    evaluation_messages = [
        {"role": "system", "content": populated_prompt},
        {"role": "user", "content": f"Evaluate this specific question group: {json.dumps(evaluation_input)}"}
    ]

    try:
        # Generate evaluation using thinking model
        evaluation_result = await llm_client.generate(evaluation_messages, evaluation_schema)

        # Debug: Log response length and preview
        print(f"📋 Response for {group.get('question_id', 'Unknown')}: {len(evaluation_result)} chars")
        # if len(evaluation_result) < 100:
        # print(f"📄 Short response: {evaluation_result}")
        # else:
            # print(f"📄 Response preview: {evaluation_result[:200]}...")

        # Parse evaluation result
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
                    "overall_score": 0,
                    "summary": "Failed to parse evaluation response"
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
                    "red_flags": ["Evaluation parsing failed"],
                    "exceptional_responses": [],
                    "inconsistencies": [],
                    "problem_solving_approach": "Unable to assess due to parsing failure"
                },
                "improvement_recommendations": ["Re-evaluate this response manually"],
                "parsing_error": True,
                "raw_response_preview": evaluation_result[:500] if len(evaluation_result) > 500 else evaluation_result
            }

        # Add group metadata
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

async def merge_evaluations(evaluations: List[Dict[str, Any]],
                          global_facts: Dict[str, Any]) -> Dict[str, Any]:
    """Merge individual group evaluations into a comprehensive report"""
    print("🔄 Merging individual evaluations into comprehensive report...")
    print(f"📊 Received {len(evaluations)} evaluations to merge")

    # Debug: Log evaluation types and structure
    for i, eval_item in enumerate(evaluations):
        print(f"🔍 Evaluation {i+1}: type={type(eval_item)}, keys={list(eval_item.keys()) if isinstance(eval_item, dict) else 'N/A'}")

    # Initialize merged report structure
    merged_report = {
        "overall_assessment": {
            "recommendation": "No Hire",
            "confidence": "Medium",
            "overall_score": 0,
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
            "red_flags": [],
            "exceptional_responses": [],
            "inconsistencies": [],
            "problem_solving_approach": ""
        },
        "improvement_recommendations": []
    }

    # Collect all question analyses
    for evaluation in evaluations:
        if isinstance(evaluation, dict) and "error" not in evaluation and "question_analysis" in evaluation:
            if isinstance(evaluation["question_analysis"], list):
                merged_report["question_analysis"].extend(evaluation["question_analysis"])

    # Aggregate competency mappings by skill area
    skill_areas = {}
    for evaluation in evaluations:
        if isinstance(evaluation, dict) and "error" not in evaluation and "competency_mapping" in evaluation:
            if isinstance(evaluation["competency_mapping"], list):
                for competency in evaluation["competency_mapping"]:
                    if isinstance(competency, dict) and "skill_area" in competency:
                        skill_area = competency["skill_area"]
                        if skill_area not in skill_areas:
                            skill_areas[skill_area] = competency.copy()
                            # Ensure lists exist
                            if "sub_skills" not in skill_areas[skill_area]:
                                skill_areas[skill_area]["sub_skills"] = []
                            if "assessment_notes" not in skill_areas[skill_area]:
                                skill_areas[skill_area]["assessment_notes"] = []
                        else:
                            # Merge sub-skills and aggregate assessments
                            existing = skill_areas[skill_area]
                            if "sub_skills" in competency and isinstance(competency["sub_skills"], list):
                                # Deduplicate sub-skills by name and merge their evidence
                                existing_sub_skills = {}

                                # First, index existing sub-skills by name
                                for sub_skill in existing["sub_skills"]:
                                    if isinstance(sub_skill, dict) and "name" in sub_skill:
                                        name = sub_skill["name"]
                                        existing_sub_skills[name] = sub_skill

                                # Then merge new sub-skills, consolidating duplicates
                                for new_sub_skill in competency["sub_skills"]:
                                    if isinstance(new_sub_skill, dict) and "name" in new_sub_skill:
                                        name = new_sub_skill["name"]
                                        if name in existing_sub_skills:
                                            # Merge evidence and gaps for duplicate sub-skill
                                            existing_skill = existing_sub_skills[name]

                                            # Take highest proficiency
                                            prof_levels = {"Entry": 1, "Basic": 2, "Intermediate": 3, "Advanced": 4, "Expert": 5}
                                            existing_prof = prof_levels.get(existing_skill.get("proficiency", "Entry"), 1)
                                            new_prof = prof_levels.get(new_sub_skill.get("proficiency", "Entry"), 1)
                                            if new_prof > existing_prof:
                                                existing_skill["proficiency"] = new_sub_skill.get("proficiency", "Entry")

                                            # Combine evidence arrays
                                            if "evidence" in new_sub_skill and new_sub_skill["evidence"]:
                                                existing_evidence = existing_skill.get("evidence", [])
                                                new_evidence = new_sub_skill["evidence"]

                                                # Ensure existing_evidence is a list
                                                if not isinstance(existing_evidence, list):
                                                    existing_evidence = [existing_evidence] if existing_evidence else []

                                                # Handle new_evidence as either string or list
                                                if isinstance(new_evidence, list):
                                                    for evidence_point in new_evidence:
                                                        if evidence_point and evidence_point not in existing_evidence:
                                                            existing_evidence.append(evidence_point)
                                                elif isinstance(new_evidence, str) and new_evidence:
                                                    if new_evidence not in existing_evidence:
                                                        existing_evidence.append(new_evidence)

                                                existing_skill["evidence"] = existing_evidence

                                            # Combine gaps
                                            if "gaps_identified" in new_sub_skill and isinstance(new_sub_skill["gaps_identified"], list):
                                                existing_gaps = existing_skill.get("gaps_identified", [])
                                                for gap in new_sub_skill["gaps_identified"]:
                                                    if gap not in existing_gaps:
                                                        existing_gaps.append(gap)
                                                existing_skill["gaps_identified"] = existing_gaps

                                            # Update confidence to highest
                                            conf_levels = {"Low": 1, "Medium": 2, "High": 3}
                                            existing_conf = conf_levels.get(existing_skill.get("confidence", "Low"), 1)
                                            new_conf = conf_levels.get(new_sub_skill.get("confidence", "Low"), 1)
                                            if new_conf > existing_conf:
                                                existing_skill["confidence"] = new_sub_skill.get("confidence", "Low")

                                            # Set demonstrated to true if either is true
                                            existing_skill["demonstrated"] = existing_skill.get("demonstrated", False) or new_sub_skill.get("demonstrated", False)
                                        else:
                                            # Add new sub-skill
                                            existing_sub_skills[name] = new_sub_skill

                                # Replace the sub_skills list with deduplicated results
                                existing["sub_skills"] = list(existing_sub_skills.values())

                            # Skip individual group assessment_notes - we'll generate holistic notes later
                            # This prevents conflicting statements like "No star schema discussion" from one group
                            # while another group might have covered star schema concepts
                            pass

    # Generate holistic assessment notes for each skill area based on consolidated evidence
    print("🔄 Generating holistic assessment notes for each skill area...")
    for skill_area_data in skill_areas.values():
        skill_name = skill_area_data.get("skill_area", "Unknown")
        sub_skills = skill_area_data.get("sub_skills", [])
        overall_assessment = skill_area_data.get("overall_assessment", "Not Assessed")
        meets_requirements = skill_area_data.get("meets_requirements", False)

        holistic_notes = []

        # Analyze overall performance
        if meets_requirements:
            holistic_notes.append(f"Candidate demonstrates competency in {skill_name} with {overall_assessment.lower()} level performance.")
        else:
            holistic_notes.append(f"Candidate shows {overall_assessment.lower()} level performance in {skill_name} but does not fully meet requirements.")

        # Analyze sub-skills coverage - only report positively if overall assessment is not "Not Demonstrated"
        demonstrated_skills = [skill for skill in sub_skills if skill.get("demonstrated", False)]
        not_demonstrated_skills = [skill for skill in sub_skills if not skill.get("demonstrated", False)]

        # Only report demonstrated experience if the overall assessment indicates actual demonstration
        if demonstrated_skills and overall_assessment != "Not Demonstrated":
            skill_names = [skill["name"] for skill in demonstrated_skills]
            proficiencies = [skill.get("proficiency", "Unknown") for skill in demonstrated_skills]
            holistic_notes.append(f"Demonstrated experience in: {', '.join(skill_names)} with proficiency levels ranging from {min(proficiencies)} to {max(proficiencies)}.")
        elif demonstrated_skills and overall_assessment == "Not Demonstrated":
            # If overall is "Not Demonstrated" but sub-skills show some evidence, clarify the contradiction
            skill_names = [skill["name"] for skill in demonstrated_skills]
            holistic_notes.append(f"Some evidence found for: {', '.join(skill_names)}, but insufficient for overall competency demonstration.")

        if not_demonstrated_skills:
            skill_names = [skill["name"] for skill in not_demonstrated_skills]
            holistic_notes.append(f"Areas requiring further assessment or development: {', '.join(skill_names)}.")

        # Identify confidence levels
        high_confidence_skills = [skill["name"] for skill in sub_skills if skill.get("confidence") == "High"]
        low_confidence_skills = [skill["name"] for skill in sub_skills if skill.get("confidence") == "Low"]

        if high_confidence_skills:
            holistic_notes.append(f"Strong evidence of competency in: {', '.join(high_confidence_skills)}.")

        if low_confidence_skills:
            holistic_notes.append(f"Limited evidence provided for: {', '.join(low_confidence_skills)}.")

        skill_area_data["assessment_notes"] = holistic_notes

    merged_report["competency_mapping"] = list(skill_areas.values())

    # Aggregate other assessments
    all_red_flags = []
    all_exceptional_responses = []
    all_inconsistencies = []
    all_recommendations = []

    for evaluation in evaluations:
        if isinstance(evaluation, dict) and "error" not in evaluation:
            if "critical_analysis" in evaluation and isinstance(evaluation["critical_analysis"], dict):
                critical_analysis = evaluation["critical_analysis"]
                if "red_flags" in critical_analysis and isinstance(critical_analysis["red_flags"], list):
                    all_red_flags.extend(critical_analysis["red_flags"])
                if "exceptional_responses" in critical_analysis and isinstance(critical_analysis["exceptional_responses"], list):
                    all_exceptional_responses.extend(critical_analysis["exceptional_responses"])
                if "inconsistencies" in critical_analysis and isinstance(critical_analysis["inconsistencies"], list):
                    all_inconsistencies.extend(critical_analysis["inconsistencies"])

            if "improvement_recommendations" in evaluation and isinstance(evaluation["improvement_recommendations"], list):
                all_recommendations.extend(evaluation["improvement_recommendations"])

    merged_report["critical_analysis"]["red_flags"] = list(set(all_red_flags))
    merged_report["critical_analysis"]["exceptional_responses"] = list(set(all_exceptional_responses))
    merged_report["critical_analysis"]["inconsistencies"] = list(set(all_inconsistencies))
    merged_report["improvement_recommendations"] = list(set(all_recommendations))

    # Calculate overall scores and recommendations
    valid_evaluations = []
    for e in evaluations:
        if (isinstance(e, dict) and
            "error" not in e and
            "overall_assessment" in e and
            isinstance(e["overall_assessment"], dict) and
            "overall_score" in e["overall_assessment"] and
            isinstance(e["overall_assessment"]["overall_score"], (int, float))):
            valid_evaluations.append(e)

    if valid_evaluations:
        avg_score = sum(e["overall_assessment"]["overall_score"] for e in valid_evaluations) / len(valid_evaluations)
        merged_report["overall_assessment"]["overall_score"] = round(avg_score, 1)

        # Determine overall recommendation based on average score - more lenient thresholds
        if avg_score >= 75:
            merged_report["overall_assessment"]["recommendation"] = "Strong Hire"
        elif avg_score >= 55:
            merged_report["overall_assessment"]["recommendation"] = "Hire"
        elif avg_score >= 35:
            merged_report["overall_assessment"]["recommendation"] = "No Hire"
        else:
            merged_report["overall_assessment"]["recommendation"] = "Strong No Hire"

        # Add summary
        successful_evaluations = len(valid_evaluations)
        total_evaluations = len(evaluations)
        merged_report["overall_assessment"]["summary"] = f"Evaluation based on {successful_evaluations}/{total_evaluations} successfully processed question groups."

    print("✅ Evaluation merging completed")
    return merged_report

def extract_candidate_info_from_transcript(transcript: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract candidate information from transcript variables field

    Args:
        transcript: The transcript data containing variables field

    Returns:
        Dictionary with candidate information
    """
    candidate_info = {
        "candidate_name": "Unknown",
        "job_title": "Unknown",
        "company_name": "Unknown",
        "salary_range": "Not specified",
        "company_profile": "Not available",
        "job_requirements": "Not available"
    }

    # Check if variables field exists in transcript
    if "variables" in transcript:
        variables = transcript["variables"]
        if isinstance(variables, dict):
            # Extract all available fields from variables
            candidate_info.update({
                "candidate_name": variables.get("candidate_name", candidate_info["candidate_name"]),
                "job_title": variables.get("job_title", candidate_info["job_title"]),
                "company_name": variables.get("company_name", candidate_info["company_name"]),
                "salary_range": variables.get("salary_range", candidate_info["salary_range"]),
                "company_profile": variables.get("company_profile", candidate_info["company_profile"]),
                "job_requirements": variables.get("job_requirements", candidate_info["job_requirements"])
            })

    return candidate_info

async def load_evaluation_config():
    """Load resume, job requirements, and key skill areas from sample data"""
    try:
        sample_data = json.loads(Path("samplenomore/evaluate.json").read_text())
        return {
            "resume": sample_data.get("resume", {}),
            "job_requirements": sample_data.get("resume", {}).get("job_requirements", ""),
            "technical_questions": sample_data.get("technical_questions", ""),
            "key_skill_areas": sample_data.get("key_skill_areas", [])
        }
    except Exception as e:
        print(f"⚠️  Failed to load evaluation config: {str(e)}")
        return {
            "resume": {
                "candidate_name": "Sample Candidate",
                "job_title": "Software Developer",
                "company_name": "Tech Company",
                "job_requirements": "No job requirements specified"
            },
            "job_requirements": "No job requirements specified",
            "technical_questions": "No technical questions specified",
            "key_skill_areas": []
        }

@app.post("/generate-report", response_model=EvaluateResponse)
async def generate_report(request: EvaluateRequest):
    """Generate comprehensive evaluation report by calling gather endpoint and evaluating question groups"""
    try:
        print("\n" + "="*50)
        print("🚀 Starting comprehensive report generation...")
        
        # Get evaluation configuration from environment
        eval_provider = "openrouter"  # Always use OpenRouter
        eval_model = config.CEREBRAS_MODELS.QWEN3_32B
        
        print(f"📊 Evaluation Provider: {eval_provider}")
        print(f"🤖 Evaluation Model: {eval_model}")

        # Load evaluation configuration (resume, job requirements, technical questions)
        print("📋 Loading evaluation configuration...")
        eval_config = await load_evaluation_config()
        print("✅ Evaluation configuration loaded")

        # Extract candidate information from request (either resume field or transcript variables)
        candidate_info = {}
        if request.resume:
            # Use resume data from request if available (from fetch_call_logs.py)
            candidate_info = {
                "candidate_name": request.resume.get("candidate_name", "Unknown"),
                "job_title": request.resume.get("job_title", "Unknown"),
                "company_name": request.resume.get("company_name", "Unknown"),
                "salary_range": request.resume.get("salary_range", "Not specified"),
                "company_profile": request.resume.get("company_profile", "Not available"),
                "job_requirements": request.resume.get("job_requirements", "Not available")
            }
            print(f"👤 Used resume field for candidate info: {candidate_info['candidate_name']} applying for {candidate_info['job_title']} at {candidate_info['company_name']}")
        else:
            # Fall back to extracting from transcript variables field
            candidate_info = extract_candidate_info_from_transcript(request.transcript)
            print(f"👤 Extracted candidate info from transcript: {candidate_info['candidate_name']} applying for {candidate_info['job_title']} at {candidate_info['company_name']}")

        # Create resume structure from extracted candidate info
        resume_data = {
            "candidate_name": candidate_info["candidate_name"],
            "job_title": candidate_info["job_title"],
            "company_name": candidate_info["company_name"],
            "salary_range": candidate_info["salary_range"],
            "company_profile": candidate_info["company_profile"],
            "job_requirements": candidate_info["job_requirements"]
        }

        # Use key_skill_areas from request if provided, otherwise use sample data
        key_skill_areas = request.key_skill_areas if request.key_skill_areas else eval_config["key_skill_areas"]
        print(f"🎯 Using {len(key_skill_areas)} skill areas: {[skill['name'] for skill in key_skill_areas]}")

        # Step 1: Call gather endpoint to get question groups
        print("🔄 Step 1: Gathering question groups using /gather endpoint...")
        
        # Check if gather configuration is available from environment
      
        gather_data = {
            "transcript": request.transcript,
            "technical_questions": eval_config["technical_questions"],
            "key_skill_areas": key_skill_areas,
        }

        question_groups_result = await call_gather_endpoint(gather_data)
        groups = question_groups_result.get("groups", [])
        global_facts = question_groups_result.get("pre_inferred_facts_global", {})

        print(f"✅ Step 1 completed: Found {len(groups)} question groups")

        # Step 2: Load evaluation prompt and schema
        print("📋 Step 2: Loading evaluation prompt and schema...")
        try:
            evaluation_prompt = Path("prompts/evaluate.md").read_text()
            evaluation_schema = json.loads(Path("prompts/evaluation.schema.json").read_text())
            print("✅ Step 2 completed: Evaluation materials loaded")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error loading evaluation materials: {str(e)}")

        # Step 3: Create LLM client for evaluation
        print("🔧 Step 3: Creating evaluation LLM client...")
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            print("✅ Using API key from environment: OPENROUTER_API_KEY")
        else:
            raise HTTPException(
                status_code=500,
                detail="OPENROUTER_API_KEY not found in environment variables"
            )

        eval_llm_client = create_llm_client(
            provider=eval_provider,
            model=eval_model,
            api_key=api_key
        )
        print("✅ Step 3 completed: Evaluation LLM client created")

        # Step 4: Process question groups in parallel
        print(f"🔄 Step 4: Processing {len(groups)} question groups in parallel...")

        # Create tasks for parallel processing
        evaluation_tasks = []
        for group in groups:
            task = evaluate_question_group(
                group=group,
                resume=resume_data,
                job_requirements=candidate_info["job_requirements"],
                key_skill_areas=key_skill_areas,
                llm_client=eval_llm_client,
                evaluation_prompt=evaluation_prompt,
                evaluation_schema=evaluation_schema
            )
            evaluation_tasks.append(task)

        # Execute all evaluations in parallel
        individual_evaluations = await asyncio.gather(*evaluation_tasks, return_exceptions=True)

        # Filter out exceptions and convert to proper format
        valid_evaluations = []
        for i, result in enumerate(individual_evaluations):
            if isinstance(result, Exception):
                print(f"❌ Group {i+1} evaluation failed: {str(result)}")
                valid_evaluations.append({
                    "error": str(result),
                    "group_metadata": groups[i] if i < len(groups) else {}
                })
            else:
                valid_evaluations.append(result)

        print(f"✅ Step 4 completed: {len(valid_evaluations)} evaluations processed")

        # Step 5: Merge evaluations into comprehensive report
        print("🔄 Step 5: Merging evaluations into comprehensive report...")
        final_evaluation = await merge_evaluations(valid_evaluations, global_facts)
        print("✅ Step 5 completed: Final evaluation report generated")

        # Prepare response
        response = EvaluateResponse(
            evaluation_report=final_evaluation,
            question_groups=question_groups_result
        )

        # Save evaluation report to disk
        print("💾 Saving evaluation report to disk...")
        try:
            # Create output directory if it doesn't exist
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

            # Generate filename with timestamp
            timestamp = int(time.time())
            filename = f"evaluation_report_{timestamp}.json"
            output_path = output_dir / filename

            # Save the complete response
            output_data = {
                "timestamp": timestamp,
                "request_data": {
                    "candidate_name": candidate_info.get("candidate_name", "Unknown"),
                    "job_title": candidate_info.get("job_title", "Unknown"),
                    "company": candidate_info.get("company_name", "Unknown"),
                    "transcript_messages_count": len(request.transcript.get("messages", [])),
                    "key_skill_areas_count": len(key_skill_areas),
                    "llm_settings": {"provider": eval_provider, "model": eval_model}
                },
                "evaluation_report": final_evaluation,
                "question_groups": question_groups_result,
                "individual_evaluations_count": len(valid_evaluations),
                "successful_evaluations": len([e for e in valid_evaluations if "error" not in e])
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Evaluation report saved to: {output_path}")

        except Exception as e:
            print(f"⚠️  Failed to save evaluation report: {str(e)}")

        print("✅ Comprehensive report generation completed successfully!")
        print("="*50 + "\n")

        return response

    except Exception as e:
        print(f"❌ Error during comprehensive report generation: {str(e)}")
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=f"Error generating comprehensive report: {str(e)}")

@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        cache_dir = Path("cache/gather")
        if not cache_dir.exists():
            return {
                "cache_enabled": True,
                "cache_directory": str(cache_dir),
                "total_cached_items": 0,
                "total_cache_size_mb": 0,
                "cached_files": []
            }

        # Get all cache files
        cache_files = list(cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)

        # Get details of cached files
        cached_items = []
        for cache_file in cache_files:
            try:
                stat = cache_file.stat()
                cached_items.append({
                    "cache_key": cache_file.stem,
                    "created": stat.st_ctime,
                    "size_bytes": stat.st_size,
                    "age_hours": (time.time() - stat.st_ctime) / 3600
                })
            except Exception:
                continue

        # Sort by creation time (newest first)
        cached_items.sort(key=lambda x: x["created"], reverse=True)

        return {
            "cache_enabled": True,
            "cache_directory": str(cache_dir),
            "total_cached_items": len(cached_items),
            "total_cache_size_mb": round(total_size / (1024 * 1024), 2),
            "cached_files": cached_items
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")

@app.delete("/cache/clear")
async def clear_cache():
    """Clear all cached gather results"""
    try:
        cache_dir = Path("cache/gather")
        if not cache_dir.exists():
            return {"message": "Cache directory does not exist", "files_deleted": 0}

        # Get all cache files
        cache_files = list(cache_dir.glob("*.json"))
        deleted_count = 0

        for cache_file in cache_files:
            try:
                cache_file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete {cache_file}: {e}")

        return {
            "message": f"Cache cleared successfully",
            "files_deleted": deleted_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

@app.delete("/cache/{cache_key}")
async def delete_cache_item(cache_key: str):
    """Delete a specific cached item"""
    try:
        cache_path = get_cache_path(cache_key)

        if not cache_path.exists():
            raise HTTPException(status_code=404, detail=f"Cache item not found: {cache_key}")

        cache_path.unlink()
        return {"message": f"Cache item deleted: {cache_key}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting cache item: {str(e)}")

@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Interview Report Generator API Documentation"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)