# COMS — Cloud Orchestration and Management System

> **AWS Hackathon Project** — Autonomous IT Operations Orchestrator

COMS eliminates the "manual execution gap" in enterprise cloud provisioning. What previously required 150–200 personnel to validate and execute is now handled autonomously in seconds — a Master Agent orchestrates NLP parsing, policy enforcement, risk classification, and AWS execution, with human approval required only for high-risk operations.

---

## The Problem

Standard cloud resource requests (S3 buckets, IAM roles, EC2 instances) in enterprise environments pass through 150–200 people for validation and approval, taking days or weeks. The actual AWS provisioning takes 3 seconds. COMS eliminates the wait.

```
Before COMS:  Request → 150-200 people → days → AWS (3 seconds)
After COMS:   Request → AI pipeline → seconds → AWS (3 seconds)
                                   ↑
                         Admin approval only for high-risk
```

---

## Architecture

### Multi-Agent Pipeline

```
User (natural language)
        ↓
   NLP Agent              — Groq LLM (Llama 3.1) parses intent + parameters
        ↓
  Policy Engine           — RBAC checks, resource limits, scope enforcement
        ↓
 Risk Classifier          — Scores request; auto-fills safe defaults
        ↓
  Orchestrator            — Master Agent: decides execute or escalate
        ↓
   ┌────┴────┐
Execute    Approval Queue
(boto3)    (admin action)
   ↓            ↓
Firestore   Firestore
```

### Agent Roles

| Agent | File | Responsibility |
|---|---|---|
| Master Agent | `agents/orchestrator.py` | Coordinates full pipeline, decides execution path |
| NLP Agent | `agents/nlp_agent.py` | LLM-based intent extraction (Groq + Gemini fallback) |
| Policy Engine | `agents/policy_engine.py` | RBAC, resource limits, scope rules |
| Risk Classifier | `agents/risk_classifier.py` | Risk scoring, auto-applies safe defaults |
| Executor | `agents/executor.py` | Direct AWS API calls via boto3 |

---

## Features

- **Conversational provisioning** — natural language input: *"Create an IAM role for EC2"* is parsed, validated, and executed without any form or ticket
- **Multi-turn clarification** — for ambiguous requests (e.g. S3 bucket missing region), the AI asks follow-up questions in the same chat thread
- **Risk-tiered execution** — low-risk requests auto-execute; high-risk (IAM, EC2, Lambda) route to admin approval queue
- **Auto-filled defaults** — high-risk resource parameters are auto-populated with safe defaults rather than blocking the user with questions
- **Chat history** — all conversations persist in localStorage, accessible from the sidebar like ChatGPT/Gemini
- **Resource inventory** — provisioned resources (S3, IAM, EC2, Lambda, SNS, CloudWatch) visible in the sidebar with live counts; pending approvals shown with amber badge
- **Admin approval workflow** — admins approve/reject with optional remarks; full request details visible in modal
- **Role-based access control** — `user` and `admin` roles; admin emails configured in `config/admins.py`
- **Append-only audit log** — every action logged to Firestore; admin view grouped by session; non-admins redirected
- **Firebase Authentication** — Google Sign-In, server-side ID token verification on every request

### Supported AWS Resources

| Resource | Intent | Risk Level |
|---|---|---|
| S3 Bucket | `create_s3_bucket` | Low → auto-execute |
| IAM Role | `create_iam_role` | High → approval required |
| EC2 Instance | `launch_ec2_instance` | High → approval required |
| Lambda Function | `create_lambda_function` | High → approval required |
| SNS Topic | `create_sns_topic` | Medium |
| CloudWatch Log Group | `create_log_group` | Low |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11+) |
| AI / NLP | Groq API — Llama 3.1 8B Instant; Google Gemini fallback |
| Cloud | AWS via boto3 (S3, IAM, EC2, Lambda, SNS, CloudWatch) |
| Auth | Firebase Authentication (Google Sign-In) |
| Database | Cloud Firestore (resources, approvals, audit log, users) |
| Frontend | React 18 + Vite + Tailwind CSS |
| Chat persistence | localStorage via ChatContext |

---

## Project Structure

```
COAS/
├── agents/
│   ├── orchestrator.py      # Master Agent — pipeline coordinator
│   ├── nlp_agent.py         # LLM intent parser (Groq + Gemini)
│   ├── policy_engine.py     # RBAC + resource limit enforcement
│   ├── risk_classifier.py   # Risk scoring + auto-defaults
│   └── executor.py          # AWS boto3 execution layer
├── config/
│   ├── admins.py            # Admin email whitelist
│   ├── policies.json        # Per-role resource limits and permissions
│   └── serviceAccountKey.json  # Firebase service account (not committed)
├── utils/
│   ├── firestore_db.py      # All Firestore read/write operations
│   ├── auth.py              # Firebase token verification
│   ├── firebase_init.py     # Firebase Admin SDK initialization
│   └── rate_limiter.py      # Request rate limiting
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.jsx       # Main chat interface
│       │   ├── ResourcesPage.jsx   # Resource inventory with detail panel
│       │   ├── Approvals.jsx       # Approval queue management
│       │   ├── AuditLog.jsx        # Admin-only session-grouped audit log
│       │   ├── AdminDashboard.jsx  # User management
│       │   ├── Security.jsx        # Security documentation
│       │   └── Profile.jsx         # User profile + sign out
│       ├── components/
│       │   └── Layout.jsx          # Sidebar with chat history + resource nav
│       └── contexts/
│           ├── AuthContext.jsx     # Firebase auth state
│           └── ChatContext.jsx     # Persistent chat session management
├── server.py                # FastAPI app + all API routes
└── tests/
    └── security_test.py     # Security layer tests
```

---

## Environment Variables

### Backend (`.env` in project root)

| Variable | Required | Description |
|---|---|---|
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `FIREBASE_SERVICE_ACCOUNT_KEY` | Yes (dev) | Path to Firebase service account JSON |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Yes (prod) | Full service account JSON as string |
| `GROQ_API_KEY` | Yes | Groq API key for Llama 3.1 8B Instant |
| `GOOGLE_API_KEY` | No | Google Gemini API key (NLP fallback) |
| `AWS_ACCESS_KEY_ID` | Yes | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS secret key |
| `AWS_DEFAULT_REGION` | Yes | Default AWS region (e.g. `ap-south-1`) |
| `LAMBDA_EXECUTION_ROLE_ARN` | Yes | IAM role ARN for Lambda execution |
| `CORS_ORIGIN` | Prod | Frontend domain for CORS |
| `APP_ENV` | No | `development` (default) or `production` |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|---|---|---|
| `VITE_FIREBASE_API_KEY` | Yes | Firebase web app API key |
| `VITE_FIREBASE_AUTH_DOMAIN` | Yes | Firebase auth domain |
| `VITE_FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `VITE_API_BASE_URL` | Prod | Backend API URL (leave empty in dev) |

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- Firebase project with Authentication (Google provider) and Firestore enabled
- AWS account (Free Tier sufficient for demo)

### Backend

```bash
# Clone the repo
git clone <repo-url>
cd COAS

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in Firebase, AWS, and Groq credentials in .env

# Start API server
uvicorn server:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Fill in Firebase web app credentials

npm run dev
# Open http://localhost:5173
```

---

## AWS Setup

### Required IAM Permissions

Your AWS user/role needs these permissions for full functionality:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:CreateBucket", "s3:DeleteBucket", "s3:ListAllMyBuckets",
    "iam:CreateRole", "iam:AttachRolePolicy", "iam:GetRole",
    "ec2:RunInstances", "ec2:DescribeInstances",
    "lambda:CreateFunction", "lambda:GetFunction",
    "sns:CreateTopic", "sns:ListTopics",
    "logs:CreateLogGroup", "logs:DescribeLogGroups"
  ],
  "Resource": "*"
}
```

### Lambda Execution Role

Create an IAM role named `coms-lambda-execution-role`:
1. AWS Console → IAM → Roles → Create Role
2. Trusted entity: **AWS Service → Lambda**
3. Attach policy: `AWSLambdaBasicExecutionRole`
4. Copy the ARN → set as `LAMBDA_EXECUTION_ROLE_ARN` in `.env`

---

## API Reference

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | Health check |
| POST | `/api/auth/me` | user | Verify token, return profile |
| POST | `/api/nlp/process` | user | Full AI orchestration pipeline |
| GET | `/api/resources` | user | List active + pending resources |
| GET | `/api/buckets` | user | List S3 buckets |
| DELETE | `/api/buckets/{name}` | user | Delete S3 bucket |
| GET | `/api/approvals` | user | List approvals (filtered by status) |
| POST | `/api/approvals/{id}/approve` | admin | Approve and execute |
| POST | `/api/approvals/{id}/reject` | admin | Reject with reason |
| GET | `/api/audit` | user | Audit log (own entries only) |
| GET | `/api/admin/users` | admin | All users with resource counts |
| GET | `/api/admin/buckets` | admin | All buckets across all users |
| GET | `/api/admin/audit` | admin | Full audit log |
| GET | `/api/admin/stats` | admin | Aggregate stats |

---

## Admin Setup

Add admin email addresses to `config/admins.py`:

```python
ADMIN_EMAILS = [
    "your-email@gmail.com",
]
```

Users whose email matches this list are automatically assigned the `admin` role on first sign-in.

---

## Security Architecture

### Token Verification
Every protected endpoint verifies `Authorization: Bearer <token>` using Firebase Admin SDK. Revoked and expired tokens return `401`. No anonymous access path exists.

### Role Separation

| Role | Can request via AI | Admin endpoints |
|---|---|---|
| `user` | All 6 resource types | 403 |
| `admin` | All 6 resource types | Allowed |

### AI Scope Enforcement
After LLM parsing, the server validates the resolved intent against `_ALLOWED_INTENTS`. Any intent outside this set returns `403` and writes an `ai_scope_violation` to the audit log.

### Audit Logging
All mutating operations write to `audit_logs` in Firestore: action, status, user UID, email, role, and UTC timestamp. The collection is append-only — no delete endpoint exists for log entries.

### Credentials
No AWS credentials, Firebase keys, or API tokens are hardcoded. Missing required credentials cause immediate `sys.exit` with a descriptive message.

---

## Deployment

### Backend (Render / Railway / Fly.io)

1. Set all environment variables in the platform dashboard
2. Set `APP_ENV=production` and `CORS_ORIGIN=https://your-frontend.com`
3. Use `FIREBASE_SERVICE_ACCOUNT_JSON` (full JSON as string) instead of file path
4. Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT --workers 2`

### Frontend (Vercel / Netlify)

```bash
cd frontend
npm run build
# Deploy frontend/dist/ as static site
```

Set `VITE_API_BASE_URL` to your deployed backend URL.

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Firebase Setup

1. Create project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable **Authentication** → Google Sign-In provider
3. Enable **Firestore Database** in production mode
4. Add your domain to **Authorized domains** in Authentication settings
5. Generate service account: Project Settings → Service accounts → Generate new private key
6. Apply Firestore security rules (block all direct client access):

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

All Firestore operations run server-side via Admin SDK, bypassing these rules.
