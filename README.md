# 🚀 COMS — Cloud Orchestrator and Management System

COMS is an AI-powered cloud orchestration platform that converts natural language into automated cloud actions. It simplifies DevOps by combining LLM intelligence, policy enforcement, and risk-aware execution in one seamless pipeline.

---

## 🔥 Features

* 🧠 Natural Language → Cloud Commands
* ⚙️ End-to-End Orchestration (Parse → Validate → Execute)
* 🔐 Policy Enforcement (RBAC, region, limits)
* ⚠️ Risk Classification (Auto vs Approval-based actions)
* ☁️ AWS Simulation using LocalStack (₹0 cost)
* 📊 Interactive Dashboard with Streamlit
* 🔁 Multi-LLM Support (Groq + Gemini fallback)

---

## 🧩 Tech Stack

* **Frontend:** Streamlit
* **Backend:** Python
* **AI/LLM:** Groq (Llama 3), Google Gemini
* **Cloud SDK:** boto3
* **Simulation:** LocalStack (Docker)
* **Validation:** Pydantic

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/bhyresh-dev/COMS---Cloud-Orchestrator-and-Management-System.git
cd COMS---Cloud-Orchestrator-and-Management-System
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate     # Linux/Mac
# venv\Scripts\activate      # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install streamlit groq boto3 python-dotenv pydantic google-genai
```

### 4️⃣ Run LocalStack (AWS Simulation)

```bash
docker run -d --name localstack -p 4566:4566 \
-e SERVICES=s3,ec2,iam -e DEFAULT_REGION=ap-south-1 \
localstack/localstack
```

### 5️⃣ Add Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=your_key
GOOGLE_API_KEY=your_key

AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=ap-south-1
```

### 6️⃣ Run the App

```bash
streamlit run app.py
```

---

## 🧠 How It Works

1. User gives natural language input
2. NLP Agent converts it into structured intent
3. Policy Engine validates permissions
4. Risk Classifier evaluates safety
5. Executor performs cloud action via LocalStack

---

## 🎯 Use Cases

* DevOps automation using natural language
* AI-powered cloud assistants (AIOps)
* Rapid infrastructure setup
* Risk-aware deployment systems

---

## 🏁 Hackathon Project

Built for **Innovitus 1.0**
Theme: *Autonomous Cloud Orchestration & AIOps*

---

## 📜 License

This project is for educational and hackathon purposes.
