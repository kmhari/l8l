from fastapi import FastAPI, HTTPException
import re
import json
import asyncio
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from scalar_fastapi import get_scalar_api_reference
from llm_client import create_llm_client
import globals as config

from models import (
    GatherRequest, GatherResponse, EvaluateRequest, EvaluateResponse,
    SkillsAssessmentRequest, SkillsAssessmentResponse
)
from cache import (
    generate_cache_key, load_from_cache, save_to_cache,
    get_cache_stats, clear_cache, delete_cache_item
)
from utils import (
    parse_technical_questions, prepare_known_questions,
    build_conversations_from_indices, extract_candidate_info_from_transcript,
    save_output_to_file, save_request_data_before_gather
)
from prompt_loader import load_prompts, load_evaluation_prompts
from evaluation import evaluate_question_group, evaluate_skills_holistically, merge_evaluations

load_dotenv(override=True)

app = FastAPI(
    title="Interview Report Generator API",
    description="API for processing interview transcripts and generating structured reports",
    version="1.0.0"
)


@app.post("/gather", response_model=GatherResponse)
async def gather(request: GatherRequest):
    try:
        print("\n" + "="*50)
        print("🚀 Starting report generation...")

        provider = "groq"
        model = config.GROQ_MODELS.GPT_OSS

        print(f"📊 Provider: {provider}")
        print(f"🤖 Model: {model}")

        print("🔑 Generating cache key...")
        cache_key = generate_cache_key(request)
        print(f"✅ Cache key: {cache_key}")

        print("🔍 Checking cache...")
        cached_result = load_from_cache(cache_key)
        if cached_result:
            print("🎯 Cache hit! Returning cached result...")
            cached_timestamp = cached_result.get("timestamp", 0)
            age_minutes = (time.time() - cached_timestamp) / 60
            print(f"📅 Cache age: {age_minutes:.1f} minutes")

            response = GatherResponse(llm_output=cached_result["llm_output"])

            try:
                timestamp = int(time.time())
                filename = f"gather_output_{timestamp}_cached.json"

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

                output_path = save_output_to_file(output_data, filename)
                print(f"✅ Cached result also saved to: {output_path}")
            except Exception as e:
                print(f"⚠️  Failed to save cached result to output: {str(e)}")

            print("✅ Report generation completed (from cache)!")
            print("="*50 + "\n")
            return response

        print("💾 Cache miss - proceeding with LLM generation...")

        print("📝 Parsing technical questions...")
        questions = parse_technical_questions(request.technical_questions)
        print(f"✅ Parsed {len(questions)} technical questions")

        print("💬 Extracting transcript messages...")
        messages = request.transcript.get("messages", [])
        print(f"✅ Found {len(messages)} conversation messages")

        print("📋 Loading system prompt and schema...")
        system_prompt, schema = await load_prompts()
        print("✅ System prompt and schema loaded")

        print("🔄 Preparing questions for LLM...")
        known_questions = prepare_known_questions(questions)
        print(f"✅ Prepared {len(known_questions)} questions for analysis")

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

        print("🔑 Checking API key...")
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            print(f"✅ Using API key from environment: GROQ_API_KEY")
        else:
            raise HTTPException(
                status_code=500,
                detail="GROQ_API_KEY not found in environment variables"
            )

        print("🔧 Creating LLM client...")
        llm_client = create_llm_client(
            provider=provider,
            model=model,
            api_key=api_key
        )
        print("✅ LLM client created successfully")

        print("📝 Preparing LLM messages...")
        llm_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Input data: {json.dumps(llm_input)}"}
        ]
        input_tokens = len(json.dumps(llm_input))
        print(f"✅ Messages prepared (~{input_tokens:,} characters)")

        print("🤖 Generating LLM response...")
        print(f"   Provider: {provider}")
        print(f"   Model: {model}")
        llm_response = await llm_client.generate(llm_messages, schema)
        print("✅ LLM response generated")

        print("🔍 Parsing LLM response...")
        try:
            llm_output = json.loads(llm_response)
            groups_count = len(llm_output.get("groups", []))
            print(f"✅ Response parsed successfully ({groups_count} conversation groups)")
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse LLM response: {str(e)}")
            print(f"Raw response preview: {llm_response[:500]}...")
            llm_output = {"error": "Failed to parse LLM response", "raw_response": llm_response}

        if "groups" in llm_output and "error" not in llm_output:
            print("🔄 Building conversations from indices...")
            llm_output["groups"] = build_conversations_from_indices(
                llm_output["groups"],
                messages
            )
            print(f"✅ Conversations built for {len(llm_output['groups'])} groups")

        print("📊 Generating final response...")
        response = GatherResponse(llm_output=llm_output)

        print("💾 Saving results to cache and disk...")

        request_metadata = {
            "transcript_messages_count": len(messages),
            "technical_questions_count": len(questions),
            "key_skill_areas_count": len(request.key_skill_areas),
        }

        if "error" not in llm_output:
            save_to_cache(cache_key, llm_output, request_metadata)

        try:
            timestamp = int(time.time())
            filename = f"gather_output_{timestamp}.json"

            output_data = {
                "timestamp": timestamp,
                "cache_key": cache_key,
                "request_data": request_metadata,
                "llm_output": llm_output
            }

            output_path = save_output_to_file(output_data, filename)
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


async def call_gather_endpoint(request_data: dict) -> dict:
    """Internal function to call the gather endpoint"""
    gather_request = GatherRequest(**request_data)
    gather_response = await gather(gather_request)
    return gather_response.llm_output


@app.post("/assess-skills-competency", response_model=SkillsAssessmentResponse)
async def assess_skills_competency(request: SkillsAssessmentRequest):
    """Assess candidate's skills competency holistically across the entire interview transcript"""
    try:
        print("\n" + "="*50)
        print("🚀 Starting holistic skills competency assessment...")

        eval_provider = "openrouter"
        eval_model = config.CEREBRAS_MODELS.QWEN3_32B

        print(f"📊 Provider: {eval_provider}")
        print(f"🤖 Model: {eval_model}")

        candidate_info = {}
        if request.resume:
            candidate_info = {
                "candidate_name": request.resume.get("candidate_name", "Unknown"),
                "job_title": request.resume.get("job_title", "Unknown"),
                "company_name": request.resume.get("company_name", "Unknown"),
                "salary_range": request.resume.get("salary_range", "Not specified"),
                "company_profile": request.resume.get("company_profile", "Not available"),
                "job_requirements": request.resume.get("job_requirements", "Not available")
            }
            print(f"👤 Using resume data: {candidate_info['candidate_name']} applying for {candidate_info['job_title']} at {candidate_info['company_name']}")
        else:
            candidate_info = extract_candidate_info_from_transcript(request.transcript)
            print(f"👤 Extracted from transcript: {candidate_info['candidate_name']} applying for {candidate_info['job_title']} at {candidate_info['company_name']}")

        resume_data = {
            "candidate_name": candidate_info["candidate_name"],
            "job_title": candidate_info["job_title"],
            "company_name": candidate_info["company_name"],
            "salary_range": candidate_info["salary_range"],
            "company_profile": candidate_info["company_profile"],
            "job_requirements": candidate_info["job_requirements"]
        }

        print(f"🎯 Assessing {len(request.key_skill_areas)} skill areas: {[skill['name'] for skill in request.key_skill_areas]}")

        print("🔑 Checking API key...")
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            print("✅ Using API key from environment: OPENROUTER_API_KEY")
        else:
            raise HTTPException(
                status_code=500,
                detail="OPENROUTER_API_KEY not found in environment variables"
            )

        print("🔧 Creating LLM client...")
        llm_client = create_llm_client(
            provider=eval_provider,
            model=eval_model,
            api_key=api_key
        )
        print("✅ LLM client created successfully")

        print("🔄 Performing holistic skills assessment...")
        skills_assessment = await evaluate_skills_holistically(
            transcript=request.transcript,
            key_skill_areas=request.key_skill_areas,
            resume=resume_data,
            job_requirements=candidate_info["job_requirements"],
            llm_client=llm_client
        )
        print("✅ Holistic skills assessment completed")

        response = SkillsAssessmentResponse(
            competency_mapping=skills_assessment.get("competency_mapping", []),
            overall_skills_summary=skills_assessment.get("overall_skills_summary", {})
        )

        print("💾 Saving skills assessment to disk...")
        try:
            timestamp = int(time.time())
            filename = f"skills_assessment_{timestamp}.json"

            output_data = {
                "timestamp": timestamp,
                "request_data": {
                    "candidate_name": candidate_info.get("candidate_name", "Unknown"),
                    "job_title": candidate_info.get("job_title", "Unknown"),
                    "company": candidate_info.get("company_name", "Unknown"),
                    "transcript_messages_count": len(request.transcript.get("messages", [])),
                    "key_skill_areas_count": len(request.key_skill_areas),
                },
                "skills_assessment": skills_assessment
            }

            output_path = save_output_to_file(output_data, filename)
            print(f"✅ Skills assessment saved to: {output_path}")

        except Exception as e:
            print(f"⚠️  Failed to save skills assessment: {str(e)}")

        print("✅ Skills competency assessment completed successfully!")
        print("="*50 + "\n")

        return response

    except Exception as e:
        print(f"❌ Error during skills competency assessment: {str(e)}")
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=f"Error assessing skills competency: {str(e)}")


@app.post("/generate-report", response_model=EvaluateResponse)
async def generate_report(request: EvaluateRequest):
    """Generate comprehensive evaluation report by calling gather endpoint and evaluating question groups"""
    try:
        print("\n" + "="*50)
        print("🚀 Starting comprehensive report generation...")

        eval_provider = "openrouter"
        eval_model = config.CEREBRAS_MODELS.QWEN3_32B

        print(f"📊 Evaluation Provider: {eval_provider}")
        print(f"🤖 Evaluation Model: {eval_model}")

        # No evaluation config loading - all data provided via request

        candidate_info = {}
        if request.resume:
            candidate_info = {
                "candidate_name": request.resume.get("candidate_name"),
                "job_title": request.resume.get("job_title"),
                "company_name": request.resume.get("company_name"),
                "salary_range": request.resume.get("salary_range"),
                "company_profile": request.resume.get("company_profile"),
                "job_requirements": request.resume.get("job_requirements")
            }
            print(f"👤 Used resume field for candidate info: {candidate_info['candidate_name']} applying for {candidate_info['job_title']} at {candidate_info['company_name']}")
        else:
            candidate_info = extract_candidate_info_from_transcript(request.transcript)
            print(f"👤 Extracted candidate info from transcript: {candidate_info['candidate_name']} applying for {candidate_info['job_title']} at {candidate_info['company_name']}")

        resume_data = {
            "candidate_name": candidate_info["candidate_name"],
            "job_title": candidate_info["job_title"],
            "company_name": candidate_info["company_name"],
            "salary_range": candidate_info["salary_range"],
            "company_profile": candidate_info["company_profile"],
            "job_requirements": candidate_info["job_requirements"]
        }
        print(f"📋 Resume data prepared for evaluation", request.technical_questions)
        # Only use data provided in the request - no fallbacks
        if not request.key_skill_areas:
            raise HTTPException(status_code=400, detail="key_skill_areas must be provided in request")
        if not request.technical_questions:
            raise HTTPException(status_code=400, detail="technical_questions must be provided in request")

        key_skill_areas = request.key_skill_areas
        print(f"🎯 Using {len(key_skill_areas)} skill areas: {[skill['name'] for skill in key_skill_areas]}")

        print("🔄 Step 1: Gathering question groups using /gather endpoint...")

        gather_data = {
            "transcript": request.transcript,
            "technical_questions": request.technical_questions,
            "key_skill_areas": key_skill_areas,
        }

        # Save data before sending to gather endpoint
        print("💾 Saving request data before gather endpoint...")
        try:
            pre_gather_path = save_request_data_before_gather(gather_data, candidate_info)
            print(f"✅ Pre-gather data saved to: {pre_gather_path}")
        except Exception as e:
            print(f"⚠️  Failed to save pre-gather data: {str(e)}")

        question_groups_result = await call_gather_endpoint(gather_data)
        groups = question_groups_result.get("groups", [])
        global_facts = question_groups_result.get("pre_inferred_facts_global", {})

        print(f"✅ Step 1 completed: Found {len(groups)} question groups")

        print("📋 Step 2: Loading evaluation prompt and schema...")
        try:
            evaluation_prompt, evaluation_schema = await load_evaluation_prompts()
            print("✅ Step 2 completed: Evaluation materials loaded")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error loading evaluation materials: {str(e)}")

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

        print(f"🔄 Step 4: Filtering question groups (excluding custom questions)...")

        q_numbered_groups = []
        excluded_groups = []

        for group in groups:
            question_id = group.get("question_id", "")
            if re.match(r'^Q\d+$', question_id):
                q_numbered_groups.append(group)
                print(f"✅ Including question group: {question_id}")
            else:
                excluded_groups.append(group)
                print(f"🚫 Excluding custom question group: {question_id}")

        print(f"📊 Will process {len(q_numbered_groups)} Q-numbered questions, excluding {len(excluded_groups)} custom questions")

        evaluation_tasks = []
        for group in q_numbered_groups:
            task = evaluate_question_group(
                group=group,
                resume=resume_data,
                job_requirements=candidate_info["job_requirements"],
                llm_client=eval_llm_client,
                evaluation_prompt=evaluation_prompt,
                evaluation_schema=evaluation_schema
            )
            evaluation_tasks.append(task)

        individual_evaluations = await asyncio.gather(*evaluation_tasks, return_exceptions=True)

        valid_evaluations = []
        for i, result in enumerate(individual_evaluations):
            if isinstance(result, Exception):
                print(f"❌ Q-numbered group {i+1} evaluation failed: {str(result)}")
                valid_evaluations.append({
                    "error": str(result),
                    "group_metadata": q_numbered_groups[i] if i < len(q_numbered_groups) else {}
                })
            else:
                valid_evaluations.append(result)

        print(f"✅ Step 4 completed: {len(valid_evaluations)} Q-numbered evaluations processed (excluded {len(excluded_groups)} custom questions)")

        print("🔄 Step 5: Performing holistic skills competency assessment...")
        skills_assessment = await evaluate_skills_holistically(
            transcript=request.transcript,
            key_skill_areas=key_skill_areas,
            resume=resume_data,
            job_requirements=candidate_info["job_requirements"],
            llm_client=eval_llm_client
        )
        print("✅ Step 5 completed: Skills competency assessment generated")

        print("🔄 Step 6: Merging question evaluations and skills assessment...")
        final_evaluation = await merge_evaluations(valid_evaluations, global_facts, skills_assessment)
        print("✅ Step 6 completed: Final evaluation report generated")

        response = EvaluateResponse(
            evaluation_report=final_evaluation,
            question_groups=question_groups_result,
            skills_assessment=skills_assessment
        )

        print("💾 Saving evaluation report to disk...")
        try:
            timestamp = int(time.time())
            if request.call_id:
                filename = f"{request.call_id}.json"
                print(f"💾 Using custom filename: {filename}")
            else:
                filename = f"evaluation_report_{timestamp}.json"
                print(f"💾 Using timestamp filename: {filename}")

            output_data = {
                "timestamp": timestamp,
                "call_id": request.call_id,
                "request_data": {
                    "candidate_name": candidate_info.get("candidate_name", "Unknown"),
                    "job_title": candidate_info.get("job_title", "Unknown"),
                    "company": candidate_info.get("company_name", "Unknown"),
                    "transcript_messages_count": len(request.transcript.get("messages", [])),
                    "key_skill_areas_count": len(key_skill_areas),
                },
                "evaluation_report": final_evaluation,
                "question_groups": question_groups_result,
                "skills_assessment": skills_assessment,
                "individual_evaluations_count": len(valid_evaluations),
                "successful_evaluations": len([e for e in valid_evaluations if "error" not in e])
            }

            output_path = save_output_to_file(output_data, filename)
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
async def cache_stats():
    """Get cache statistics"""
    try:
        return get_cache_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")


@app.delete("/cache/clear")
async def clear_all_cache():
    """Clear all cached gather results"""
    try:
        return clear_cache()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@app.delete("/cache/{cache_key}")
async def delete_specific_cache_item(cache_key: str):
    """Delete a specific cached item"""
    try:
        return delete_cache_item(cache_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Cache item not found: {cache_key}")
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