# COMS — Cloud Orchestration and Management System

> AI-powered natural language interface for provisioning and managing AWS cloud resources with enterprise-grade governance, approval workflows, and complete audit logging.

🌐 **Live Demo**: [https://coas.onrender.com](https://coas.onrender.com)

---

## The Problem

Cloud provisioning today requires developers to know CLI syntax, navigate AWS consoles, and manually enforce governance policies. In teams, this creates bottlenecks — every resource request needs verification, approval, and documentation. Mistakes are costly, audit trails are weak, and onboarding new team members is slow.

## The Solution

COMS replaces the entire manual workflow with a conversational AI interface. You describe what you need in plain English. COMS parses your intent, validates it against your organization's policies, classifies the risk, and either provisions the resource instantly or escalates it for admin approval — all in under 2 seconds.

---

## How It Works

Every request flows through a 5-stage pipeline:

```
User Message
    ↓
[1] NLP PARSING  →  Groq (Llama 3.1) converts plain English → structured intent JSON
    ↓
[2] CLARIFICATION  →  Ask for any missing required fields (bucket name, region, purpose)
    ↓
[3] POLICY VALIDATION  →  RBAC check, region whitelist, resource quotas, name validation
    ↓
[4] RISK CLASSIFICATION  →  Low risk → auto-execute | High risk → escalate to admin
    ↓
[5] AWS EXECUTION  →  boto3 calls, Firestore record, audit log entry
```

Total pipeline latency: **~1–2 seconds** (most time in Groq, not AWS)

---

## Features

### AI & NLP
- Natural language cloud provisioning — describe resources in plain English
- Multi-turn conversation with clarification questions
- Groq (Llama 3.1 8B) as primary LLM with Google Gemini 2.5 Flash as fallback
- Intent normalization to handle LLM hallucinations
- Region name fuzzy matching ("Mumbai" → `ap-south-1`, "Ireland" → `eu-west-1`)
- Explainability panel showing every agent's decision with timing

### Governance & Security
- Role-based access control (user / developer / dev-lead / admin)
- Region whitelisting (4 allowed AWS regions)
- Per-user resource quotas enforced via live Firestore queries
- Risk-based approval queue — high-risk ops require admin sign-off before execution
- AI scope enforcement — NLP endpoint restricted to creation intents only
- Rate limiting — 20 requests/minute per user (token bucket algorithm)
- Immutable audit trail — append-only Firestore collection, every action logged

### AWS Resources
19 operations across 6 AWS services — see full list below.

### UI
- Conversational chat interface with session history
- Resource inventory grouped by service type
- Admin dashboard with platform-wide stats
- Approval queue with approve/reject workflow
- Audit log with session grouping
- User profile management

---

## Supported AWS Services

| Service | Operations |
|---------|-----------|
| **S3** | Create bucket (public/private), list buckets, delete bucket |
| **EC2** | Launch instance, describe instances, terminate instance |
| **IAM** | Create role, list roles, delete role |
| **Lambda** | Create function, list functions, delete function, invoke function |
| **SNS** | Create topic, list topics, delete topic |
| **CloudWatch Logs** | Create log group, list log groups |

> **Risk tiers:** Read operations and creates (S3, Lambda, SNS, Logs) → auto-execute. IAM, EC2, and all deletes → admin approval required.

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI 0.136.0 |
| Server | Uvicorn 0.44.0 (ASGI) |
| Database | Firebase Firestore |
| Auth | Firebase Authentication |
| AWS SDK | boto3 / botocore |
| Validation | Pydantic 2.0+ |

### AI / NLP
| Component | Technology |
|-----------|-----------|
| Primary LLM | Groq — Llama 3.1 8B Instant (free, ~300ms) |
| Fallback LLM | Google Gemini 2.5 Flash (free) |
| Output | Structured JSON intent parsing |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | React 18.3.0 |
| Routing | React Router 6.26.0 |
| Styling | Tailwind CSS 3.4.0 |
| Build Tool | Vite 5.4.0 |
| State | React Context API |
| Auth | Firebase JS SDK 10.13.0 |

### Deployment
| Component | Technology |
|-----------|-----------|
| Container | Docker (multi-stage build) |
| Platform | Render.com (free tier) |
| Frontend | Embedded in FastAPI — single service, single URL |

---

## Pages & Features

### Dashboard (`/dashboard`)
The main interface. Type any cloud request and COMS handles the rest.
- Chat interface with auto-expanding input
- Quick suggestion cards for common requests
- Per-message status: `✓ Executed`, `⏳ Pending approval`, `↩ Needs clarification`, `✗ Denied`
- Pipeline stage breakdown with individual timings
- Expandable decision chain explaining every agent's reasoning
- Auto-applied defaults shown inline (e.g., `region: ap-south-1`)
- Session history in sidebar

### Approvals (`/approvals`)
- **Users**: View history of own requests and their status
- **Admins**: Full queue of pending requests with approve/reject actions
- Filter by: all / pending / approved / rejected
- Detail view with full parameters, risk tier, and violations

### Audit Log (`/audit`) — Admin only
- Immutable log of every action across the platform
- Grouped by session (15-minute windows)
- Columns: action, status, user, timestamp
- Color-coded: green (success), red (denied/error)

### Admin Dashboard (`/admin`) — Admin only
- Platform stats: total buckets, users, admin count
- Full bucket inventory with creator info
- User list with per-user resource counts

### Resources (`/resources/:type`)
- Per-service views: S3, EC2, IAM, Lambda, SNS, Logs
- Users see their own resources; admins see all
- Inline delete with confirmation
- Live counts updated in sidebar

### Security (`/security`)
- Documents the security architecture
- RBAC matrix, AI scope enforcement, audit logging, policy limits

### Profile (`/profile`)
- Edit display name
- View role, email, UID
- Sign out

---

## RBAC Roles

| Role | Services | Notes |
|------|----------|-------|
| `user` | S3, EC2, IAM, Lambda, SNS, Logs | Default for new accounts |
| `developer` | S3, EC2, Lambda, SNS, Logs | IAM restricted |
| `dev-lead` | S3, EC2, IAM, Lambda, SNS, Logs | Can create IAM roles |
| `admin` | All | Full platform access, approves requests |

Roles are stored in Firestore. Token claims are never trusted — Firestore is the source of truth.

---

## Resource Limits (per user)

| Resource | Limit | AWS Free Tier |
|----------|-------|---------------|
| S3 Buckets | 10 | 5 GB storage |
| EC2 Instances | 3 | 750 hrs/month t2.micro |
| IAM Roles | 10 | Always free |
| Lambda Functions | 20 | 1M requests/month |
| SNS Topics | 10 | 1M publishes/month |
| CloudWatch Log Groups | 20 | 5 GB ingested |

Allowed regions: `ap-south-1` · `us-east-1` · `eu-west-1` · `us-west-2`

---

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 20+
- A Firebase project with Firestore + Authentication enabled
- AWS account (or LocalStack for local testing)
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Backend Setup

```bash
# Clone and install
git clone https://github.com/bhyresh-dev/COAS.git
cd COAS
pip install -r requirements.txt

# Create .env
cp .env.example .env
# Fill in your keys (see Environment Variables section)

# Run backend
uvicorn server:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Create frontend/.env
cp .env.example .env
# Fill in your Firebase web config values

npm install
npm run dev   # Runs on http://localhost:5173
```

### LocalStack (optional — no real AWS needed)

```bash
docker run -d -p 4566:4566 localstack/localstack
# In .env, set:
# AWS_ENDPOINT_URL=http://localhost:4566
```

---

## Environment Variables

### Backend (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `FIREBASE_PROJECT_ID` | ✅ | Firebase project ID |
| `FIREBASE_SERVICE_ACCOUNT_KEY` | ✅ (local) | Path to service account JSON file |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | ✅ (Docker) | Full service account JSON as a single-line string |
| `AWS_ACCESS_KEY_ID` | ✅ | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | ✅ | AWS secret key |
| `AWS_DEFAULT_REGION` | ✅ | Default region (e.g. `ap-south-1`) |
| `GROQ_API_KEY` | ✅ | Groq API key |
| `GOOGLE_API_KEY` | ✅ | Google Gemini API key (fallback LLM) |
| `LAMBDA_EXECUTION_ROLE_ARN` | ✅ | IAM role ARN for Lambda execution |
| `CORS_ORIGIN` | ✅ (prod) | Frontend URL (e.g. `https://coas.onrender.com`) |
| `APP_ENV` | ✅ (prod) | Set to `production` |
| `AWS_ENDPOINT_URL` | ❌ | LocalStack URL (omit for real AWS) |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_FIREBASE_API_KEY` | Firebase web API key |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase auth domain |
| `VITE_FIREBASE_PROJECT_ID` | Firebase project ID |
| `VITE_API_BASE_URL` | Backend URL (leave empty if same origin) |

---

## Deployment (Render.com)

The entire app (frontend + backend) deploys as a single Docker service.

```bash
# 1. Push to GitHub
git push origin main

# 2. Create Render Web Service
#    - Runtime: Docker
#    - Auto-Deploy: On Commit

# 3. Add environment variables in Render dashboard
#    (All variables from the Backend section above)

# 4. After first deploy, set CORS_ORIGIN to your Render URL
#    Then trigger a redeploy
```

### Docker Build (what Render runs)

```dockerfile
# Stage 1: Build React frontend (Node 20)
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
RUN npm ci && npm run build

# Stage 2: Python runtime (3.12-slim)
FROM python:3.12-slim
COPY agents/ config/ utils/ server.py .
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Firestore Collections

| Collection | Contents |
|------------|----------|
| `users` | uid, email, name, role, created_at |
| `resources` | resource_type, name, region, created_by, status (active/pending/deleted) |
| `approvals` | parsed_request, risk_result, status, approver, reason, timestamp |
| `audit_logs` | action, status, user_id, user_email, user_role, details, timestamp |

---

## Security Architecture

- **Fail-closed**: Missing credentials → immediate `sys.exit()`, no silent fallback
- **Token verification**: Firebase ID token verified on every request, revoked tokens detected
- **AI scope enforcement**: NLP endpoint restricted to 6 creation intents; violations logged and rejected with 403
- **Rate limiting**: Token bucket algorithm, 20 requests/minute per user
- **Immutable audit trail**: Append-only Firestore collection, no delete endpoint exists
- **Resource ownership**: Users can only delete their own resources
- **Policy engine**: Live quota checks (no caching), region whitelist, instance type restrictions
- **No hardcoded secrets**: All credentials via environment variables only

---

## Project Structure

```
COAS/
├── server.py                  # FastAPI app, all API endpoints
├── agents/
│   ├── orchestrator.py        # Master pipeline coordinator
│   ├── nlp_agent.py           # Groq/Gemini intent parser
│   ├── executor.py            # AWS boto3 operations
│   ├── policy_engine.py       # RBAC + quota validation
│   └── risk_classifier.py     # Risk tier classification
├── utils/
│   ├── firebase_init.py       # Firebase Admin SDK init
│   ├── auth.py                # Token verification, role checks
│   ├── firestore_db.py        # All Firestore operations
│   ├── aws_client.py          # boto3 client factory
│   └── rate_limiter.py        # Token bucket rate limiter
├── config/
│   ├── policies.json          # RBAC, region whitelist, quotas
│   ├── risk_rules.json        # Low/high risk intent lists
│   └── admins.py              # Admin email whitelist
├── frontend/
│   ├── src/
│   │   ├── pages/             # Login, Dashboard, Approvals, Audit, Admin, Profile, Resources, Security
│   │   ├── components/        # Layout (sidebar + nav)
│   │   ├── contexts/          # AuthContext, ChatContext, ResourceContext
│   │   ├── api.js             # API client with auth headers
│   │   └── firebase.js        # Firebase SDK init
│   └── public/
│       └── logo.png           # Favicon
├── Dockerfile                 # Multi-stage build
├── render.yaml                # Render deployment config
└── requirements.txt           # Python dependencies
```

---

## Example Interactions

```
User:  Create an S3 bucket for storing media files

COMS:  What would you like to name the bucket, and which region?
       (Purpose: media files — noted ✓)

User:  Name it media-assets-2025, use Mumbai region

COMS:  ✓ Executed
       S3 bucket 'media-assets-2025' created in ap-south-1.
       type: S3 Bucket | access: private | region: ap-south-1
```

```
User:  Launch an EC2 instance for our backend API

COMS:  ⏳ Pending approval
       This request requires admin review before execution.
       Approval ID: apr_abc123
       Risk: Tier 2 (High) — EC2 instance creation
```

```
User:  Create an IAM role for Lambda

COMS:  ↩ Needs clarification
       What would you like to name the IAM role?

User:  Name it lambda-execution-role

COMS:  ⏳ Pending approval
       IAM role creation requires admin approval.
```

---

## Built With ❤️ for the Hackathon

**Team**: 
Bhyresh B S (github:bhyresh-dev)
K Sai Havish(github: ksaihavish)
aryav agarwal(github: Aryav-Agarwal)
veena
**Stack**: FastAPI · React · Groq · Firebase · AWS · Docker · Render  
**License**: MIT
