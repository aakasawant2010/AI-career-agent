# 🤖 AI Career Agent

> **An AI-powered, human-in-the-loop career automation platform designed to streamline the job search and application lifecycle.**

The **AI Career Agent** is a full-stack AI application that helps candidates automate repetitive job-search and application tasks while keeping the candidate **in control of important decisions**.

The platform is designed around a modular backend architecture using **Python, FastAPI, SQLAlchemy, Alembic and PostgreSQL**, with an agentic AI layer planned around **LLMs and LangGraph**.

Instead of simply generating text, the goal of the system is to create an end-to-end career assistant capable of understanding a candidate's profile, processing job opportunities, assisting with application decisions, and preparing personalized application content.

---

## 🎯 Project Vision

Job searching involves a large amount of repetitive work:

- Searching for relevant jobs
- Understanding job descriptions
- Comparing jobs with a candidate's profile
- Identifying skill gaps
- Preparing application information
- Maintaining application status
- Tracking multiple opportunities
- Repeating similar tasks across different job portals

The goal of AI Career Agent is to bring these activities into a single intelligent workflow.

### Core principle

> **Automate repetitive work, but keep the human in control of important decisions.**

The agent can analyze information and prepare actions, while potentially sensitive or consequential actions can be presented to the user for approval before execution.

---

# ✨ Key Features

## 🧠 AI-Assisted Career Workflow

The platform is designed to use LLM-powered agents to assist with career-related workflows.

Potential capabilities include:

- Job description analysis
- Candidate profile analysis
- Job-to-candidate matching
- Skill-gap identification
- Resume optimization
- Application content generation
- Job prioritization
- Application tracking
- Human approval before important actions

---

## 👤 Human-in-the-Loop

One of the key architectural principles of the project is **Human-in-the-Loop (HITL)**.

Instead of allowing an AI agent to automatically perform every action, the system can pause at important decision points.

### Example

```text
Job Found
    ↓
AI analyzes Job Description
    ↓
Compare with Candidate Profile
    ↓
Calculate / determine suitability
    ↓
Generate application recommendation
    ↓
┌─────────────────────────────┐
│      HUMAN APPROVAL         │
│                             │
│  Approve / Reject / Edit    │
└─────────────────────────────┘
    ↓
Application Workflow
```

This approach makes the system safer and gives the user control over actions that may have real-world consequences.

---

# 🏗️ High-Level Architecture

```text
                         ┌──────────────────────┐
                         │       USER           │
                         │                      │
                         │ Career Preferences   │
                         │ Resume / Profile     │
                         │ Job Requirements     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      FRONTEND        │
                         │                      │
                         │ Career Dashboard     │
                         │ Job Management       │
                         │ Application Review   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │         FASTAPI API          │
                    │                              │
                    │ REST Endpoints               │
                    │ Request Validation           │
                    │ Business Logic               │
                    └──────────────┬───────────────┘
                                   │
                 ┌─────────────────┼──────────────────┐
                 │                 │                  │
                 ▼                 ▼                  ▼
        ┌────────────────┐ ┌───────────────┐ ┌─────────────────┐
        │ AI / Agent     │ │ Application   │ │ Data Layer      │
        │ Layer          │ │ Services      │ │                 │
        │                │ │               │ │ SQLAlchemy      │
        │ LLM            │ │ Jobs          │ │ PostgreSQL      │
        │ LangGraph      │ │ Applications  │ │ Alembic         │
        │ Agent State    │ │ Candidates    │ │ Migrations      │
        └───────┬────────┘ └───────────────┘ └─────────────────┘
                │
                ▼
        ┌─────────────────┐
        │ Human Approval  │
        │                 │
        │ Approve         │
        │ Reject          │
        │ Modify          │
        └─────────────────┘
```

---

# 🔄 End-to-End Workflow

A typical career workflow can look like this:

```text
                    START
                      │
                      ▼
             Candidate Profile
                      │
                      ▼
               Job Discovery
                      │
                      ▼
             Job Description
                      │
                      ▼
              AI Job Analysis
                      │
                      ▼
          Candidate ↔ Job Matching
                      │
                      ▼
              Skill Gap Analysis
                      │
                      ▼
            Application Decision
                      │
                      ▼
             ┌────────────────┐
             │ Human Review   │
             └───────┬────────┘
                     │
            ┌────────┴────────┐
            │                 │
          Reject            Approve
            │                 │
            ▼                 ▼
          END          Application Workflow
                              │
                              ▼
                       Track Application
                              │
                              ▼
                           END
```

---

# 🧠 AI / Agentic AI Layer

The long-term objective of the project is to use an **agentic workflow** rather than a single LLM call.

An agent can:

1. Understand the user's career objective.
2. Analyze job requirements.
3. Compare those requirements against the candidate profile.
4. Determine whether a job is relevant.
5. Identify missing skills.
6. Generate personalized application content.
7. Ask for human approval where required.
8. Continue the workflow based on the user's decision.

### Why Agentic AI?

A traditional LLM application might look like:

```text
User → Prompt → LLM → Response
```

The AI Career Agent is designed around a more structured workflow:

```text
User
 ↓
Agent
 ↓
Understand Task
 ↓
Choose Action
 ↓
Use Tools / Services
 ↓
Evaluate Result
 ↓
Human Approval
 ↓
Continue Workflow
```

This makes the application more suitable for complex, multi-step career automation.

---

# 🕸️ LangGraph

**LangGraph** is intended to provide the orchestration layer for stateful agent workflows.

Instead of keeping all logic inside one large function, the workflow can be represented as a graph.

Example:

```text
                 ┌──────────────┐
                 │ User Request │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │ Analyze Task │
                 └──────┬───────┘
                        ↓
              ┌────────────────────┐
              │ Select Next Action │
              └─────────┬──────────┘
                        ↓
          ┌─────────────┼──────────────┐
          ↓             ↓              ↓
     Job Analysis   Resume Work   Application
          │             │              │
          └─────────────┼──────────────┘
                        ↓
                ┌───────────────┐
                │ Human Review  │
                └───────┬───────┘
                        ↓
                  Continue Flow
```

LangGraph is useful because it provides a structured way to represent:

- Agent state
- Nodes
- Edges
- Conditional routing
- Multi-step workflows
- Human-in-the-loop interruptions
- Stateful execution

---

# 🛡️ Why Human-in-the-Loop?

Fully autonomous job application systems can make mistakes.

For example, an agent could:

- Apply to the wrong position
- Misinterpret a job requirement
- Generate incorrect candidate information
- Submit an application without user approval

Therefore, the architecture separates **AI decision support** from **human authorization**.

The AI can prepare the action:

```text
AI:
"This job appears to be a 91% match.
I prepared the application information."
```

The user then decides:

```text
[ Approve ]   [ Edit ]   [ Reject ]
```

This makes the system more practical for real-world use.

---

# ⚙️ Backend Architecture

The backend is built using:

| Component | Technology |
|---|---|
| Programming Language | Python |
| API Framework | FastAPI |
| Validation | Pydantic |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Database Migrations | Alembic |
| Agent Orchestration | LangGraph |
| AI Layer | LLM-based agent architecture |
| Server | Uvicorn |
| Containerization | Docker |
| Local Infrastructure | Docker Compose |
| Testing | Pytest |
| CI/CD | GitHub Actions |

The current repository contains the backend implementation for **phases 1–10**, with frontend development continuing separately.

---

# 🗄️ Database Architecture

PostgreSQL is used as the primary relational database.

The application uses SQLAlchemy as the database abstraction layer and Alembic for schema migrations.

```text
                    FastAPI
                       │
                       ▼
                 Service Layer
                       │
                       ▼
                  SQLAlchemy
                       │
                       ▼
                  PostgreSQL
                       │
                       ▲
                       │
                    Alembic
                  Migrations
```

### Why PostgreSQL?

PostgreSQL is well suited for the structured data involved in a career platform:

- Users / candidates
- Jobs
- Applications
- Application statuses
- Candidate profiles
- Job requirements
- Agent state
- Human approval states

It also provides strong relational consistency for application-tracking workflows.

---

# 🔄 Database Migrations

The project uses **Alembic** for database schema management.

Instead of manually modifying the database schema, changes can be represented as version-controlled migrations.

Example:

```text
Migration 001
     ↓
Initial database schema
     ↓
Migration 002
     ↓
Add candidate profile
     ↓
Migration 003
     ↓
Add application status
     ↓
Migration 004
     ↓
Add AI workflow state
```

This makes database changes reproducible across development, testing and deployment environments.

---

# 🐳 Docker Architecture

The repository includes a `docker-compose.yml` that runs the backend together with PostgreSQL.

The current Compose configuration defines:

```text
┌─────────────────────────┐
│      Docker Compose     │
│                         │
│  ┌──────────────────┐   │
│  │     Backend      │   │
│  │    FastAPI       │   │
│  │     :8000        │   │
│  └────────┬─────────┘   │
│           │             │
│           ▼             │
│  ┌──────────────────┐   │
│  │   PostgreSQL     │   │
│  │      :5432       │   │
│  └──────────────────┘   │
│                         │
└─────────────────────────┘
```

The Compose file configures a PostgreSQL 16 Alpine container and the backend service, with persistent volumes for database and uploaded resume data.

---

# 📁 Project Structure

```text
AI-career-agent/
│
├── .github/
│   └── workflows/
│       └── CI/CD workflows
│
├── backend/
│   ├── application code
│   ├── database layer
│   ├── models
│   ├── services
│   ├── API routes
│   └── tests
│
├── frontend/
│   └── Frontend application
│
├── docs/
│   ├── DEPLOYMENT.md
│   ├── PHASES_8_10.md
│   └── Additional project documentation
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
└── ...
```

---

# 🚀 Quick Start

## Prerequisites

Make sure you have:

- Python 3.11+
- Git
- Docker Desktop
- Docker Compose
- PostgreSQL knowledge
- Required LLM/API credentials

---

## 1. Clone the repository

```bash
git clone https://github.com/aakasawant2010/AI-career-agent.git
```

```bash
cd AI-career-agent
```

---

## 2. Create the environment file

Copy the example environment file:

### Linux / macOS

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Then update `.env` with the required configuration and secrets.

> **Never commit `.env` to GitHub.**

---

# 🐳 Run with Docker

The easiest way to start the backend and PostgreSQL locally is:

```bash
docker compose up --build
```

Once the containers are running:

### API

```text
http://localhost:8000
```

### Swagger API Documentation

```text
http://localhost:8000/docs
```

### Readiness endpoint

```text
http://localhost:8000/health/ready
```

The repository's current Docker Compose setup exposes the API on port `8000` and PostgreSQL on localhost port `5432`.

---

# 🐍 Run Backend Locally

Create a virtual environment:

```bash
python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Configure your `.env` file.

Then start FastAPI with Uvicorn.

```bash
uvicorn backend.main:app --reload
```

> The exact application module may vary as the backend evolves. Refer to the backend documentation for the current entry point.

---

# 🧪 Testing

The backend uses **pytest** for automated testing.

Run:

```bash
cd backend
pytest -q
```

The repository also supports running tests against PostgreSQL by providing `TEST_DATABASE_URL`.

Example:

```bash
TEST_DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/career_agent pytest -q
```

---

# 📚 API Documentation

FastAPI automatically provides interactive API documentation.

After starting the backend, open:

```text
http://localhost:8000/docs
```

You can use Swagger UI to:

- View available endpoints
- Inspect request schemas
- Inspect response schemas
- Execute API requests
- Test backend functionality

This is particularly useful during development and debugging.

---

# 🔐 Environment Variables

The project uses environment variables for configuration and secrets.

Example:

```env
DATABASE_URL=postgresql+psycopg://...
POSTGRES_USER=career
POSTGRES_PASSWORD=your_password
POSTGRES_DB=career_agent

# LLM / AI provider configuration
LLM_API_KEY=your_api_key

# Other application configuration
...
```

The exact variables should be taken from:

```text
.env.example
```

### Security rule

Never commit:

```text
.env
```

to GitHub.

Instead commit:

```text
.env.example
```

with placeholder values.

---

# 🔁 Typical Application Flow

A typical workflow looks like this:

### Step 1 — Candidate Profile

The candidate provides:

- Resume
- Skills
- Experience
- Preferred role
- Preferred location
- Salary expectations
- Career preferences

### Step 2 — Job Processing

The system receives or discovers a job.

### Step 3 — Job Analysis

The AI analyzes:

- Required skills
- Experience requirements
- Responsibilities
- Technology stack
- Seniority
- Location
- Other relevant requirements

### Step 4 — Candidate Matching

The system compares:

```text
Candidate Profile
        +
Job Requirements
        ↓
AI Matching
        ↓
Suitability / Gap Analysis
```

### Step 5 — Application Preparation

The AI can assist with:

- Resume customization
- Cover letter generation
- Application answers
- Recruiter messages

### Step 6 — Human Approval

Before an important external action:

```text
AI Recommendation
       ↓
Human Review
       ↓
Approve / Edit / Reject
```

### Step 7 — Application Tracking

The application can then be tracked through different states.

Example:

```text
Saved
  ↓
Reviewed
  ↓
Ready to Apply
  ↓
Applied
  ↓
Interview
  ↓
Offer
  ↓
Rejected / Accepted
```

---

# 💡 Example Use Case

Imagine a candidate is looking for a:

> **Generative AI Developer — 3+ years experience**

The system can process the job description and identify:

```text
Required Skills
────────────────────────
Python             ✓
FastAPI            ✓
LangChain          ✓
LangGraph          ✓
RAG                ✓
Vector Databases   ✓
AWS                ✓
Kubernetes         ✗
```

The agent can then produce a high-level recommendation:

```text
Match: Strong

Strengths:
✓ Python
✓ FastAPI
✓ LangGraph
✓ RAG
✓ LLM applications

Potential Gap:
• Kubernetes production experience

Recommendation:
Proceed to human review.
```

The user remains responsible for the final decision.

---

# 🧩 Why This Is an Agentic AI Project

The project goes beyond a simple chatbot.

A chatbot:

```text
Question
   ↓
LLM
   ↓
Answer
```

An agentic system:

```text
Goal
 ↓
Understand
 ↓
Plan
 ↓
Select action
 ↓
Use tools / data
 ↓
Evaluate
 ↓
Ask for approval if required
 ↓
Continue
```

This architecture is better suited for workflows where the AI needs to perform multiple steps rather than simply generate text.

---

# 📊 Design Principles

The project follows several important AI engineering principles.

### 1. Human Control

AI should assist with decisions rather than blindly execute every action.

### 2. Separation of Concerns

The system separates:

```text
API
↓
Business Logic
↓
AI / Agent
↓
Database
```

### 3. Typed Data

Pydantic and SQLAlchemy provide structured application data instead of relying entirely on unstructured dictionaries.

### 4. Persistent Data

PostgreSQL provides durable storage for application state.

### 5. Versioned Database Changes

Alembic ensures database schema changes are reproducible.

### 6. Containerized Development

Docker makes local development and deployment environments more consistent.

---

# 📈 Current Project Status

| Area | Status |
|---|---|
| Backend | ✅ Phases 1–10 |
| FastAPI | ✅ |
| SQLAlchemy | ✅ |
| PostgreSQL | ✅ |
| Alembic | ✅ |
| Docker Compose | ✅ |
| Environment Configuration | ✅ |
| Backend Tests | ✅ |
| API Documentation | ✅ |
| AI / Agent Architecture | 🚧 Ongoing |
| Frontend | 🚧 Next Phase |
| Production Deployment | 🚧 Ongoing |

The repository currently describes the backend as phases **1–10 complete**, with the frontend listed as the next major area.

---

# 🗺️ Roadmap

## Phase 1–10 — Backend Foundation

- [x] Project structure
- [x] FastAPI application
- [x] Pydantic schemas
- [x] SQLAlchemy integration
- [x] PostgreSQL integration
- [x] Alembic migrations
- [x] Database models
- [x] API layer
- [x] Testing foundation
- [x] Docker Compose
- [x] Deployment documentation

## Next

- [ ] Complete frontend
- [ ] Candidate dashboard
- [ ] Job dashboard
- [ ] Job matching UI
- [ ] AI agent workflow
- [ ] LangGraph orchestration
- [ ] Resume analysis
- [ ] Skill-gap analysis
- [ ] Personalized resume generation
- [ ] Human approval interface
- [ ] Application tracking dashboard
- [ ] Job discovery integrations
- [ ] Production deployment
- [ ] Monitoring and observability
- [ ] AI evaluation framework

---

# 🔮 Future Architecture

The long-term architecture can evolve toward:

```text
                         USER
                           │
                           ▼
                  ┌─────────────────┐
                  │ Career Dashboard │
                  └────────┬────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   FastAPI   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  LangGraph  │
                    │ Agent       │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    Job Analysis      Resume Agent    Application Agent
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
                    Human Approval
                           │
                           ▼
                  Application Workflow
                           │
                           ▼
                     PostgreSQL
```

---

# 🧠 Skills Demonstrated

This project demonstrates practical experience with:

### Backend Development

- Python
- FastAPI
- REST APIs
- Pydantic
- SQLAlchemy
- PostgreSQL
- Alembic

### Generative AI

- LLM application architecture
- Agentic AI
- LangGraph
- Prompt engineering
- Structured AI workflows
- Human-in-the-loop AI

### Software Engineering

- Modular architecture
- Database migrations
- Automated testing
- Docker
- Docker Compose
- Environment configuration
- Git / GitHub
- CI/CD

### AI Engineering

- Agent orchestration
- Stateful workflows
- Tool-based workflows
- AI decision support
- AI safety through human approval
- Career-domain automation

---

# 🚀 Production Improvements

For a production deployment, the following improvements would be valuable:

### Security

- Authentication
- Authorization
- Role-based access control
- API rate limiting
- Secure secret management
- Input validation
- Audit logs

### AI

- LLM evaluation framework
- Prompt versioning
- Hallucination detection
- Structured outputs
- Agent tracing
- Cost monitoring
- Model fallback strategy

### Infrastructure

- Production PostgreSQL
- Redis for caching/background workloads where required
- Container registry
- Cloud deployment
- Load balancing
- HTTPS
- Monitoring
- Centralized logging

### Application

- Real job-board integrations
- Resume parser
- Email integration
- Calendar integration
- Application status automation
- Personalized recommendations

---

# 🤝 Development Philosophy

The goal of this project is not simply to demonstrate that an LLM can generate text.

The goal is to demonstrate how **AI can be integrated into a real software system**.

That means combining:

```text
LLMs
 +
Agentic Workflows
 +
APIs
 +
Databases
 +
Business Logic
 +
Human Approval
 +
Testing
 +
Deployment
```

This is the difference between a simple Gen AI demo and a more complete AI engineering application.

---

# 🛠️ Useful Commands

### Start Docker environment

```bash
docker compose up --build
```

### Stop containers

```bash
docker compose down
```

### Run backend tests

```bash
cd backend
pytest -q
```

### Run FastAPI locally

```bash
uvicorn backend.main:app --reload
```

### Check Git status

```bash
git status
```

### Commit changes

```bash
git add .
git commit -m "Describe your change"
```

### Push changes

```bash
git push
```

---

# 📖 Documentation

Additional project documentation is available in:

```text
docs/
```

Important documents include:

- `DEPLOYMENT.md`
- `PHASES_8_10.md`

These provide additional information about deployment and the later development phases.

---

# 🔒 Security

Please do not commit secrets to the repository.

Never commit:

```text
.env
API keys
Database passwords
Cloud credentials
Private tokens
```

Use:

```text
.env.example
```

for documenting required environment variables.

If a secret is accidentally committed, revoke/rotate it immediately.

---

# 📌 Project Goals

The ultimate goal is to build an intelligent career assistant that can help a candidate move from:

```text
"I am looking for a job."
```

to:

```text
Candidate Profile
        ↓
Job Discovery
        ↓
Job Understanding
        ↓
Candidate Matching
        ↓
Skill Gap Analysis
        ↓
Resume Optimization
        ↓
Application Preparation
        ↓
Human Approval
        ↓
Application
        ↓
Application Tracking
```

all within one intelligent platform.

---

# 👨‍💻 Author

**Akash Sawant**

AI / Generative AI Developer

GitHub:  
https://github.com/aakasawant2010

---

# ⭐ If You Find This Project Useful

If this project helps you understand AI agents, FastAPI, LangGraph, or AI-powered career automation, consider giving the repository a ⭐ on GitHub.

---

## 📄 License

Add an appropriate `LICENSE` file before distributing the project as an open-source package.
