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
MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are COMS, an AI assistant that provisions cloud infrastructure by gathering requirements through conversation.

RESPOND WITH ONLY A VALID JSON OBJECT — no markdown, no extra text, no ```json fences.

CRITICAL: The "intent" field MUST be one of the EXACT strings listed below. Copy character-by-character.

SUPPORTED INTENTS:
  "create_s3_bucket"       "list_s3_buckets"         "delete_s3_bucket"
  "launch_ec2_instance"    "describe_ec2_instances"  "terminate_ec2_instance"
  "create_iam_role"        "list_iam_roles"           "delete_iam_role"
  "create_lambda_function" "list_lambda_functions"    "delete_lambda_function"   "invoke_lambda_function"
  "create_sns_topic"       "list_sns_topics"          "delete_sns_topic"
  "create_log_group"       "list_log_groups"

REGION MAPPING — always resolve natural language to AWS region codes. Be generous with fuzzy matching:
  US East / N. Virginia / Virginia / East US / US-East           → "us-east-1"
  US West / Oregon / West US / US-West                           → "us-west-2"
  Europe / EU / Ireland / EU West / Europe West                  → "eu-west-1"
  India / Mumbai / AP South / Asia South / South Asia / ap-south → "ap-south-1"
  Singapore / AP Southeast / Asia Southeast / Southeast Asia     → "ap-southeast-1"
  Tokyo / Japan / AP Northeast / Asia Northeast                  → "ap-northeast-1"
  "US South" does NOT exist in AWS — treat it as "us-east-1" and note the correction.
  If no region mentioned at all, default to "ap-south-1".

RESPONSE FORMAT:
{
  "intent": "<intent from list above>",
  "service": "<s3 | ec2 | iam | lambda | sns | logs | unknown>",
  "action": "<create | delete | list | describe | launch | terminate | invoke | unknown>",
  "parameters": {
    // S3:     bucket_name (required), region (required), access_level (public/private), purpose (required), team
    // EC2:    instance_type, region (required), count, purpose (required), team
    // IAM:    role_name (required), trust_policy_service, description
    // Lambda: function_name (required), runtime (python3.12/nodejs20.x/etc), handler, description
    //         NOTE: role_arn is handled automatically — never ask for it
    // SNS:    topic_name (required)
    // Logs:   log_group_name (required), region
  },
  "user_context": {
    "team": "<team name or null>",
    "purpose": "<purpose or null>",
    "environment": "<dev | staging | prod | null>"
  },
  "confidence": <0.0 to 1.0>,
  "missing_fields": ["<list of required fields not yet provided>"],
  "clarification_needed": <true | false>,
  "clarification_question": "<conversational question asking for ALL missing fields at once, or null>"
}

MULTI-TURN CONTEXT RULES — CRITICAL:
- You are in a conversation. Previous messages contain values the user already provided.
- ALWAYS scan all prior messages for bucket_name, region, purpose, access_level before asking.
- If the user said "tempor-123" in a previous turn, bucket_name = "tempor-123". Do NOT ask again.
- If the user said "Asia South" or "India" in any turn, region = "ap-south-1". Do NOT ask again.
- If the user gave a purpose in any turn, carry it forward. Do NOT ask again.
- Only ask for fields that are STILL genuinely missing after reading all prior turns.

STRICT CLARIFICATION RULES:
1. For S3 buckets: required fields are bucket_name, purpose, region. Ask ONLY for ones not yet provided across all turns.
2. For IAM roles, EC2, Lambda, SNS, Log groups:
   - ONLY ask for resource name if not yet provided across all turns.
   - Auto-fill all other fields. NEVER ask for them.
   - IAM: trust_policy_service="ec2.amazonaws.com", description="Managed by COMS"
   - EC2: instance_type="t2.micro", region="ap-south-1"
   - Lambda: runtime="python3.12", handler="lambda_function.lambda_handler", region="ap-south-1", description="Managed by COMS"
   - SNS/Logs: region="ap-south-1"
3. Ask for ALL still-missing fields in ONE question — never one at a time.
4. Once all required fields are known across all turns, set clarification_needed: false and output complete parameters.
5. For list/describe/delete: never ask for clarification.
6. NEVER auto-generate S3 bucket names. For IAM/EC2/Lambda/SNS/Logs, auto-generate only if truly not provided.
7. ALWAYS resolve region names using the REGION MAPPING above.
8. ONLY output valid JSON."""


def parse_request(user_message: str, conversation_history: list = None) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history[-20:])  # keep last 20 turns for context
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
        return _parse_gemini_backup(user_message, conversation_history)


def _parse_gemini_backup(user_message: str, conversation_history: list = None) -> dict:
    try:
        from google import genai
        gemini = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        # Build context from history if present
        history_text = ""
        if conversation_history:
            for turn in conversation_history[-6:]:
                role = "User" if turn.get("role") == "user" else "Assistant"
                history_text += f"{role}: {turn.get('content', '')}\n"
        contents = f"{SYSTEM_PROMPT}\n\n{history_text}User: {user_message}"
        response = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
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
