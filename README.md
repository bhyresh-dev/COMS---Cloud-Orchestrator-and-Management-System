# COMS — Cloud Orchestration and Management System

COMS is an enterprise cloud resource management platform that lets teams provision AWS resources using natural language. Requests are parsed by an LLM, validated against configurable policy rules, classified by risk tier, and either executed immediately or routed to an admin approval queue. Every action is recorded in an append-only audit log.

---

## Features

- **Natural language provisioning** — describe the resource you need in plain English; the NLP pipeline parses intent, validates policy, and executes or escalates automatically.
- **Firebase Authentication** — Google Sign-In with server-side ID token verification on every request. No passwords stored.
- **Role-based access control** — two roles (`user`, `admin`) stored in Firestore. New accounts default to `user`. Admins are promoted manually.
- **AI scope restriction** — the NLP automation layer is limited strictly to S3 bucket creation. All other AWS operations require explicit API calls.
- **Policy enforcement** — configurable per-resource limits (buckets, instances, functions) checked against live Firestore counts before any AWS API call.
- **Risk-tiered approvals** — high-risk operations are held in an approval queue; admins can approve or reject with a reason.
- **Append-only audit log** — every create, delete, approve, reject, and policy denial is written to Firestore. No delete endpoint exists for log entries.
- **React frontend** — professional enterprise UI with Google Sign-In, request form, bucket table, admin dashboard, and security documentation page.

---

## Security Architecture

### Token Verification

Every protected API endpoint extracts the `Authorization: Bearer <token>` header and verifies it using the Firebase Admin SDK (`firebase_admin.auth.verify_id_token`). Revoked and expired tokens are rejected with `401`. There is no anonymous access path and no fallback to a weaker auth mechanism.

### Role Separation

| Role  | Can request | Admin endpoints |
|-------|-------------|-----------------|
| user  | S3 only     | 403             |
| admin | All services | Allowed         |

Role values are read from Firestore on every verified request. Token claims are not trusted for role information. If Firebase fails to initialize, the process exits rather than degrading silently.

### AI Automation Scope

The `POST /api/nlp/process` endpoint runs the full NLP → policy → risk → execute pipeline. After the LLM parses the user's message, the server inspects the resolved intent. If it is anything other than `create_s3_bucket`, the request is rejected with `403` and an `ai_scope_violation` entry is written to the audit log. This prevents the AI layer from listing bucket contents, deleting resources, accessing IAM or EC2, or acting on any other AWS account.

### Policy Enforcement

Before any resource is created, the policy engine queries Firestore for the user's current active resource count and compares it to the limits in `config/policies.json`. Requests that exceed the limit are denied before any AWS API call is made. Limits are checked on every request — there is no caching.

### Audit Logging

All mutating operations write to the `audit_logs` Firestore collection: action name, status, user UID, email, role, and UTC timestamp. The collection is append-only. No API endpoint exposes a delete operation for log entries. Admin users read the full log via `GET /api/admin/audit`; regular users read only their own entries via `GET /api/audit`.

### Credentials

No AWS credentials, Firebase service account keys, or API tokens are hardcoded in the source. All secrets are loaded from environment variables at startup. Missing required credentials cause an immediate `sys.exit` with a descriptive message.

---

## Environment Variables

### Backend (`.env` in project root)

| Variable | Required | Description |
|----------|----------|-------------|
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `FIREBASE_SERVICE_ACCOUNT_KEY` | One of | Path to Firebase service account JSON file |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | One of | Full service account JSON as a string (for deployment) |
| `GROQ_API_KEY` | Yes | Groq API key for Llama 3.3 70B (NLP parsing) |
| `GOOGLE_API_KEY` | No | Google Gemini API key (NLP fallback) |
| `AWS_ACCESS_KEY_ID` | Prod | AWS access key (required in real AWS mode) |
| `AWS_SECRET_ACCESS_KEY` | Prod | AWS secret key (required in real AWS mode) |
| `AWS_DEFAULT_REGION` | Yes | Default AWS region (e.g. `ap-south-1`) |
| `AWS_ENDPOINT_URL` | Dev | LocalStack endpoint (e.g. `http://localhost:4566`). Leave unset for real AWS. |
| `LAMBDA_EXECUTION_ROLE_ARN` | Prod | IAM role ARN for Lambda functions (required in real AWS mode) |
| `APP_ENV` | No | `development` (default) or `production` |
| `CORS_ORIGIN` | Prod | Frontend domain (e.g. `https://coas.example.com`). Required when `APP_ENV=production`. |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_FIREBASE_API_KEY` | Yes | Firebase web app API key |
| `VITE_FIREBASE_AUTH_DOMAIN` | Yes | Firebase auth domain (e.g. `project.firebaseapp.com`) |
| `VITE_FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `VITE_API_BASE_URL` | Prod | Backend API URL. Leave empty in development (Vite proxy handles it). |

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- [LocalStack](https://github.com/localstack/localstack) (optional, for local AWS emulation)
- A Firebase project with Authentication (Google provider) and Firestore enabled

### Backend Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd COAS

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your Firebase and AWS credentials
```

### Frontend Setup

```bash
cd frontend
npm install

# Copy and fill in Firebase config
cp .env.example .env
# Edit .env with your Firebase web app credentials
```

---

## Running the Application

### API server

```bash
# Development (auto-reload)
uvicorn server:app --reload --port 8000

# Production
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

API documentation is available at `http://localhost:8000/docs` in development mode only.

### Frontend

```bash
cd frontend
npm run dev
# Open http://localhost:5173
```

### Legacy Streamlit UI (available during migration)

```bash
streamlit run app.py
```

### Security tests

```bash
python tests/security_test.py
```

No running server or real Firebase credentials are required. All external calls are mocked.

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check |
| POST | `/api/auth/me` | user | Verify token, return profile |
| POST | `/api/nlp/process` | user | AI-scoped S3 creation pipeline |
| GET | `/api/buckets` | user | List caller's buckets |
| DELETE | `/api/buckets/{name}` | user | Delete a bucket |
| GET | `/api/resources` | user | List all active resources |
| GET | `/api/approvals` | user | List pending approvals |
| POST | `/api/approvals/{id}/approve` | admin | Approve and execute |
| POST | `/api/approvals/{id}/reject` | admin | Reject with reason |
| GET | `/api/audit` | user | Audit log (own entries) |
| GET | `/api/admin/users` | admin | All users with resource counts |
| GET | `/api/admin/buckets` | admin | All buckets across all users |
| GET | `/api/admin/audit` | admin | Full audit log |
| GET | `/api/admin/stats` | admin | Aggregate resource and audit stats |

---

## Deployment

### Backend

The API server is a standard ASGI app runnable on any platform that supports Python.

**Render / Railway / Fly.io**

1. Set all required environment variables in the platform dashboard.
2. Set `APP_ENV=production` and `CORS_ORIGIN=https://your-frontend-domain.com`.
3. Use `FIREBASE_SERVICE_ACCOUNT_JSON` (the full JSON as a string) instead of a file path.
4. Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT --workers 2`

**Docker**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend

```bash
cd frontend
npm run build
# Outputs to frontend/dist/ — deploy as a static site
```

Deploy `frontend/dist/` to Vercel, Netlify, Cloudflare Pages, or any static host. Set environment variables in the hosting platform's dashboard before building.

For Vercel:

```bash
cd frontend
npx vercel --prod
```

Set `VITE_API_BASE_URL` to your deployed API URL in the Vercel project settings.

### Firebase Setup

1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com).
2. Enable **Authentication** and add **Google** as a sign-in provider.
3. Enable **Firestore Database** in production mode.
4. Add your frontend domain to the **Authorized domains** list in Authentication settings.
5. Create a service account: Project Settings → Service accounts → Generate new private key.
6. Use the downloaded JSON as `FIREBASE_SERVICE_ACCOUNT_KEY` (file path) or `FIREBASE_SERVICE_ACCOUNT_JSON` (stringified JSON for deployment).

### Firestore Security Rules

Apply these rules in the Firebase console to prevent direct client writes:

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

All Firestore operations are performed server-side using the Admin SDK, which bypasses these rules. Client access is blocked entirely.
