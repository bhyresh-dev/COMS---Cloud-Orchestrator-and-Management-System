"""
NLP Agent — converts natural language → structured cloud intent JSON.
Primary: Groq (Llama 3.3 70B, free)  |  Fallback: Google Gemini 2.5 Flash (free)
"""
import os
import json
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are COMS NLP parsing agent. Convert cloud infrastructure requests to JSON.

RESPOND WITH ONLY A VALID JSON OBJECT — no markdown, no extra text, no ```json fences.

SUPPORTED INTENTS (use exactly these strings):
  S3   : create_s3_bucket | list_s3_buckets | delete_s3_bucket
  EC2  : launch_ec2_instance | describe_ec2_instances | terminate_ec2_instance
  IAM  : create_iam_role | list_iam_roles | delete_iam_role
  Lambda: create_lambda_function | list_lambda_functions | delete_lambda_function | invoke_lambda_function
  SNS  : create_sns_topic | list_sns_topics | delete_sns_topic
  Logs : create_log_group | list_log_groups

RESPONSE FORMAT:
{
  "intent": "<intent from list above>",
  "service": "<s3 | ec2 | iam | lambda | sns | logs | unknown>",
  "action": "<create | delete | list | describe | launch | terminate | invoke | unknown>",
  "parameters": {
    // S3: bucket_name, region, access_level (public/private), size_gb, purpose, team
    // EC2: instance_type, ami_id, region, count, purpose, team
    // IAM: role_name, trust_policy_service, description
    // Lambda: function_name, runtime (python3.12/nodejs20.x/etc), handler, description, role_arn
    // SNS: topic_name, topic_arn
    // Logs: log_group_name, region
  },
  "user_context": {
    "team": "<team name or null>",
    "purpose": "<purpose or null>",
    "environment": "<dev | staging | prod | null>"
  },
  "confidence": <0.0 to 1.0>,
  "missing_fields": ["<critical fields not provided>"],
  "clarification_needed": <true if critical info is missing>,
  "clarification_question": "<question if clarification_needed, else null>"
}

RULES:
1. Default region: ap-south-1. Default access: private.
2. Generate sensible resource names if not given (e.g. "team-s3-dev-001").
3. EC2 free tier: always default to t2.micro unless user specifies otherwise.
4. Lambda free tier: default runtime python3.12.
5. If request is too vague (e.g. "I need some resources"), set clarification_needed: true.
6. For list/describe operations, parameters can be empty {}.
7. ONLY output valid JSON."""


def parse_request(user_message: str, conversation_history: list = None) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history[-10:])  # keep last 10 turns for context
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.1, max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
        return {"success": True, "data": parsed, "raw": raw}
    except Exception as e:
        print(f"[WARN] Groq failed ({e}), trying Gemini fallback...")
        return _parse_gemini_backup(user_message)


def _parse_gemini_backup(user_message: str) -> dict:
    try:
        from google import genai
        gemini = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\nUser request: {user_message}",
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
        return {"success": True, "data": parsed, "raw": raw}
    except Exception as e:
        return {"success": False, "error": f"Both Groq and Gemini failed: {e}"}


class ConversationManager:
    """Multi-turn conversation — carries context across clarification rounds."""
    def __init__(self):
        self.history = []
        self.current_parse = None

    def send_message(self, user_message: str) -> dict:
        result = parse_request(user_message, self.history)
        self.history.append({"role": "user", "content": user_message})
        if result["success"]:
            self.history.append({"role": "assistant", "content": result["raw"]})
            self.current_parse = result["data"]
        return result

    def reset(self):
        self.history = []
        self.current_parse = None
