from agents.nlp_agent import parse_request
import json

print("Sending request to Groq...")
result = parse_request("Create an S3 bucket, 50GB, private, in ap-south-1 for the dev team")

if result["success"]:
    print("✅ SUCCESS! The AI understood the request:")
    print(json.dumps(result["data"], indent=2))
else:
    print("❌ FAILED:", result["error"])