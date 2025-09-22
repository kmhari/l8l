from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import re
import json
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from scalar_fastapi import get_scalar_api_reference
from llm_client import create_llm_client
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Interview Report Generator API",
    description="API for processing interview transcripts and generating structured reports",
    version="1.0.0"
)

class LLMSettings(BaseModel):
    provider: str = "openrouter"
    model: str = "openai/gpt-oss-120b:nitro"
    api_key: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "provider": "openrouter",
                "model": "openai/gpt-oss-120b:nitro",
                "api_key": "optional_if_set_in_env"
            }
        }

class GatherRequest(BaseModel):
    transcript: Dict[str, Any]
    technical_questions: str
    key_skill_areas: List[Dict[str, Any]]
    llm_settings: Optional[LLMSettings] = LLMSettings()

    class Config:
        @staticmethod
        def _load_sample_data():
            try:
                return json.loads(Path("sample/gather.json").read_text())
            except:
                return {
                    "transcript": {"messages": []},
                    "technical_questions": "Sample questions...",
                    "key_skill_areas": [],
                    "llm_settings": {"provider": "openrouter", "model": "openai/gpt-oss-120b:nitro"}
                }

        schema_extra = {
            "example": _load_sample_data()
        }

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
                        "candidate_name": "Mohammed",
                        "experience_years": 3,
                        "current_location": "Coimbatore",
                        "willing_to_relocate": true,
                        "current_ctc": 7.3,
                        "expected_ctc": 9.5,
                        "notice_period": "10-15 days"
                    }
                }
            }
        }

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

@app.post("/gather", response_model=GatherResponse)
async def gather(request: GatherRequest):
    try:
        print("\n" + "="*50)
        print("🚀 Starting report generation...")
        print(f"📊 Provider: {request.llm_settings.provider}")
        print(f"🤖 Model: {request.llm_settings.model}")

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

        # Get API key from environment if not provided
        print("🔑 Checking API key...")
        api_key = request.llm_settings.api_key
        if not api_key:
            env_key_map = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "groq": "GROQ_API_KEY",
                "openrouter": "OPENROUTER_API_KEY"
            }
            env_key = env_key_map.get(request.llm_settings.provider.lower())
            if env_key:
                api_key = os.getenv(env_key)
                print(f"✅ Using API key from environment: {env_key}")
            else:
                print("⚠️  No API key found")
        else:
            print("✅ Using provided API key")

        # Create LLM client
        print("🔧 Creating LLM client...")
        llm_client = create_llm_client(
            provider=request.llm_settings.provider,
            model=request.llm_settings.model,
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
        print(f"   Provider: {request.llm_settings.provider}")
        print(f"   Model: {request.llm_settings.model}")
        llm_response = await llm_client.generate(llm_messages, schema)
        print("✅ LLM response generated")

        # Parse response
        print("🔍 Parsing LLM response...")
        try:
            llm_output = json.loads(llm_response)
            groups_count = len(llm_output.get("groups", []))
            print(f"✅ Response parsed successfully ({groups_count} conversation groups)")

            # Post-process: Build conversations from indices
            print("🔄 Building conversations from indices...")
            if "groups" in llm_output:
                llm_output["groups"] = build_conversations_from_indices(
                    llm_output["groups"],
                    messages
                )
                print(f"✅ Conversations built for {len(llm_output['groups'])} groups")

        except json.JSONDecodeError:
            print("❌ Failed to parse LLM response as JSON")
            llm_output = {"error": "Failed to parse LLM response", "raw_response": llm_response}

        print("📊 Generating final response...")
        response = GatherResponse(
            llm_output=llm_output
        )
        print("✅ Report generation completed successfully!")
        print("="*50 + "\n")

        return response

    except Exception as e:
        print(f"❌ Error during report generation: {str(e)}")
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/sample", response_model=GatherRequest)
async def get_sample_data():
    """Get sample data for testing the API"""
    try:
        sample_data = json.loads(Path("sample/gather.json").read_text())
        return GatherRequest(**sample_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading sample data: {str(e)}")

@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Interview Report Generator API Documentation"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)