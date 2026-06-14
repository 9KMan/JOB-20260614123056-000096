# Specification: Python/AI Developer: Workflow Automations & Data Analyses

Posted 17 hours ago | Worldwide

About the project
We run account management for e-commerce/dropshipping clients. A large part of the work is recurring workflows: order checks, delay and compensation handling, disputes, stock control, and reporting. We're automating these. You'll be responsible for the workflow automations and data analyses end-to-end — a mix of regular automation and AI-driven actions. This is one of two parallel tracks. A separate developer is building a WhatsApp workspace ("skin") for our account managers, and your automations will ultimately surface inside that workspace. The two tracks are built separately but must integrate cleanly, so well-defined interfaces and good coordination matter.

Who you are
- AI-first developer, strong in both Python and AI, with real coding skills under the hood.
- You build microservice-based, not monolithic. Our hard requirement: each automation and service is isolated so that if one breaks, the rest keeps running.
- Comfortable with a mix of regular automation and AI actions — rule-based approach vs AI judgment.
- Able to work with APIs and handle real data volumes efficiently.
- Responsible for work end-to-end: architecture, build, testing, delivery.
- Good communicator.

What you'll build
- Workflow automations: rule-based work like filtering, status checks, reminders, reporting.
- AI actions and data analyses: judgment-based tasks over large datasets.
- Clean, maintainable, microservice-based setup that plugs into a WhatsApp workspace.
- AI needs to run hosted (via API) to start, built behind clean adapters for later self-hosted.

How we work
- Task-by-task roadmap, detailed workflow docs, no sprints.
- Reports to project lead who coordinates everything.

Screening questions:
1. Describe a project where you mixed rule-based automation with AI actions. How did you decide which parts were rules and which needed AI?
2. Have you worked with both hosted AI APIs and self-hosted/local open-source models? Briefly, what's your experience with each?
3. Describe a microservice-based system you built. How did you handle one service failing without breaking the rest?
4. Include a link to your GitHub and/or a Python/data project you owned end-to-end.

## 1. Project Overview

**Project:** Python/AI Developer: Workflow Automations & Data Analyses

Posted 17 hours ago | Worldwide

About the project
We run account management for e-commerce/dropshipping clients. A large part of the work is recurring workflows: order checks, delay and compensation handling, disputes, stock control, and reporting. We're automating these. You'll be responsible for the workflow automations and data analyses end-to-end — a mix of regular automation and AI-driven actions. This is one of two parallel tracks. A separate developer is building a WhatsApp workspace ("skin") for our account managers, and your automations will ultimately surface inside that workspace. The two tracks are built separately but must integrate cleanly, so well-defined interfaces and good coordination matter.

Who you are
- AI-first developer, strong in both Python and AI, with real coding skills under the hood.
- You build microservice-based, not monolithic. Our hard requirement: each automation and service is isolated so that if one breaks, the rest keeps running.
- Comfortable with a mix of regular automation and AI actions — rule-based approach vs AI judgment.
- Able to work with APIs and handle real data volumes efficiently.
- Responsible for work end-to-end: architecture, build, testing, delivery.
- Good communicator.

What you'll build
- Workflow automations: rule-based work like filtering, status checks, reminders, reporting.
- AI actions and data analyses: judgment-based tasks over large datasets.
- Clean, maintainable, microservice-based setup that plugs into a WhatsApp workspace.
- AI needs to run hosted (via API) to start, built behind clean adapters for later self-hosted.

How we work
- Task-by-task roadmap, detailed workflow docs, no sprints.
- Reports to project lead who coordinates everything.

Screening questions:
1. Describe a project where you mixed rule-based automation with AI actions. How did you decide which parts were rules and which needed AI?
2. Have you worked with both hosted AI APIs and self-hosted/local open-source models? Briefly, what's your experience with each?
3. Describe a microservice-based system you built. How did you handle one service failing without breaking the rest?
4. Include a link to your GitHub and/or a Python/data project you owned end-to-end.
**GitHub Repo:** https://github.com/9KMan/JOB-20260614123056-000096
**Lead:** https://www.upwork.com/jobs/~022065866015463736607
**Client:** N/A
**Tier:** STANDARD
**Budget:** $20-$35/hr
**Rate:** N/A
**Timeline:** 4-8 weeks

## 2. Technical Stack

Python · Data Analysis · Data Science · API · Artificial Intelligence · Machine Learning · Automation

## 3. Architecture

- Backend: Python (FastAPI/Flask/Django) REST API
- AI/ML: Model integration (OpenAI/Anthropic API or self-hosted)

### API Design
- RESTful endpoints with JSON request/response
- Authentication via JWT (HS256) or bcrypt
- Middleware for logging, error handling, CORS
- Versioned routes (/api/v1/...) where applicable

### Data Layer
- PostgreSQL as primary datastore
- Connection pooling via PGBouncer or similar
- Migration management via Alembic or raw SQL
- Indexes on foreign keys and high-cardinality columns

### Frontend (if applicable)
- Single-page application or server-rendered pages
- Responsive UI with modern CSS/JS framework
- State management for complex client-side logic

## 4. Data Model

### Core Entities
- Define entity schema based on job requirements
- Use UUIDs for primary keys (not auto-increment)
- Add created_at / updated_at timestamps to all tables
- Soft-delete pattern where appropriate

### Relationships
- Foreign key constraints with ON DELETE CASCADE
- Many-to-many via junction tables
- Eager loading for nested relationships in API

## 5. Project Structure

```
├── api/                  # FastAPI / Express routes + schemas
├── models/               # DB models / SQLAlchemy / Prisma
├── services/             # Business logic layer
├── workers/              # Background jobs (Celery, BullMQ, etc.)
├── migrations/           # DB migrations (Alembic / Flyway)
├── tests/                # Unit + integration tests
├── Dockerfile            # Production container
├── docker-compose.yml    # Local dev environment
└── README.md             # Setup instructions
```

## 6. Out of Scope

- Mobile apps (web only unless explicitly specified)
- Multi-tenant / white-label customization
- Performance optimization at 1M+ user scale

## 7. Acceptance Criteria

- [ ] REST API with all planned endpoints implemented and returning JSON
- [ ] Frontend UI implemented, responsive, and functional
- [ ] Unit tests covering core functionality
- [ ] AI/ML pipeline integrated and functional

**GitHub Repo:** https://github.com/9KMan/JOB-20260614123056-000096
