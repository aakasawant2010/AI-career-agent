"""Phase 9 – interview agent logic (pure functions, no DB, no network).

Question generation and answer evaluation work fully offline using a skill
question bank plus keyword rubrics. ``app.services.interview_service`` layers
the optional LLM on top and falls back to this module when it is unavailable.

Everything here is advisory practice feedback. Nothing is sent to an employer.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass

CATEGORIES = ("technical", "system_design", "project", "behavioral", "role_fit", "gap")
RATINGS = ((85, "strong"), (70, "good"), (50, "fair"), (0, "needs_work"))


def _p(label: str, *keywords: str) -> dict:
    return {"label": label, "keywords": list(keywords)}


# ------------------------------------------------------------------ question bank

SKILL_BANK: dict[str, list[tuple[str, list[dict]]]] = {
    "python": [
        (
            "How do you structure a larger Python service so it stays testable, and how do you handle concurrency in it?",
            [
                _p("Separates layers / dependency injection", "layer", "dependency", "inject", "module", "service"),
                _p("Testing approach", "pytest", "unit test", "mock", "fixture", "test"),
                _p("Concurrency model (async, threads, processes)", "async", "asyncio", "thread", "process", "gil"),
                _p("Typing / linting / quality tooling", "type hint", "mypy", "ruff", "lint", "typing"),
            ],
        ),
    ],
    "fastapi": [
        (
            "Walk me through how a request flows through a FastAPI app, and how you would handle auth, validation and database sessions.",
            [
                _p("Dependency injection for auth/db", "depends", "dependency"),
                _p("Pydantic validation / schemas", "pydantic", "schema", "validation"),
                _p("Auth approach (JWT/OAuth)", "jwt", "oauth", "token", "bearer"),
                _p("Async vs sync endpoints / DB session lifecycle", "async", "session", "sync", "lifecycle"),
            ],
        ),
    ],
    "langchain": [
        (
            "When would you use LangChain versus calling the model API directly, and what problems have you hit with it in production?",
            [
                _p("Clear criteria for using it", "chain", "abstraction", "integration", "tool"),
                _p("Awareness of trade-offs / overhead", "overhead", "trade-off", "tradeoff", "complex", "debug"),
                _p("Observability / tracing", "trac", "langsmith", "log", "observab"),
                _p("Concrete example from experience", "i built", "we built", "project", "for example"),
            ],
        ),
    ],
    "langgraph": [
        (
            "Explain how you would model an agent workflow in LangGraph. When is a graph better than a simple chain?",
            [
                _p("State and nodes/edges", "state", "node", "edge"),
                _p("Conditional routing / loops", "conditional", "loop", "branch", "route", "cycle"),
                _p("Human-in-the-loop or checkpoints", "human", "checkpoint", "interrupt", "approval", "persist"),
                _p("Failure handling / retries", "retry", "error", "fallback", "timeout"),
            ],
        ),
    ],
    "rag": [
        (
            "Design a RAG pipeline for answering questions over a company's documents. How do you decide chunking, retrieval and evaluation?",
            [
                _p("Chunking strategy and size/overlap", "chunk", "overlap", "split"),
                _p("Embeddings and vector store", "embedding", "vector", "faiss", "pgvector", "chroma", "pinecone"),
                _p("Retrieval quality (hybrid, rerank, top-k)", "rerank", "hybrid", "top-k", "top k", "bm25", "retriev"),
                _p("Evaluation (recall, faithfulness, golden set)", "evaluat", "recall", "faithful", "ragas", "golden", "metric"),
                _p("Grounding / hallucination control", "ground", "hallucinat", "citation", "source"),
            ],
        ),
        (
            "Your RAG system returns confident but wrong answers. How do you debug it?",
            [
                _p("Separates retrieval failures from generation failures", "retriev", "generation", "context"),
                _p("Inspects retrieved chunks / logs", "inspect", "log", "trace", "chunk"),
                _p("Improves chunking, reranking or prompts", "rerank", "chunk", "prompt", "query"),
                _p("Adds evaluation to prevent regressions", "evaluat", "test set", "regression", "metric"),
            ],
        ),
    ],
    "generative ai": [
        (
            "How do you evaluate and reduce hallucinations in an LLM-powered feature before shipping it?",
            [
                _p("Evaluation set / metrics", "evaluat", "metric", "benchmark", "golden", "test set"),
                _p("Grounding with retrieval or tools", "ground", "retriev", "rag", "tool", "citation"),
                _p("Prompting / output constraints", "prompt", "schema", "constrain", "json", "validate"),
                _p("Human review or monitoring in production", "human", "monitor", "feedback", "review", "guardrail"),
            ],
        ),
    ],
    "llm": [
        (
            "How do you control cost, latency and quality when building on top of a hosted LLM?",
            [
                _p("Cost levers (caching, smaller models, token limits)", "cach", "smaller model", "token", "cost", "batch"),
                _p("Latency levers (streaming, parallelism)", "stream", "parallel", "latency", "async"),
                _p("Quality measurement", "evaluat", "metric", "quality", "test"),
                _p("Fallbacks / retries / rate limits", "fallback", "retry", "rate limit", "timeout"),
            ],
        ),
    ],
    "prompt engineering": [
        (
            "Describe how you iterate on a prompt for a task where output has to be structured and reliable.",
            [
                _p("Clear instructions / examples", "example", "few-shot", "few shot", "instruction"),
                _p("Structured output / schema validation", "json", "schema", "validate", "pydantic", "structured"),
                _p("Systematic evaluation of variants", "evaluat", "compare", "test set", "ab test", "metric"),
            ],
        ),
    ],
    "aws": [
        (
            "Which AWS services would you use to deploy and run an API with a database, and how would you secure and monitor it?",
            [
                _p("Compute choice (ECS/Lambda/EC2)", "ecs", "lambda", "ec2", "fargate", "eks"),
                _p("Managed database / storage", "rds", "s3", "dynamo", "aurora"),
                _p("Security (IAM, secrets, VPC)", "iam", "secret", "vpc", "security group", "kms"),
                _p("Monitoring / logging", "cloudwatch", "log", "alarm", "monitor", "metric"),
            ],
        ),
    ],
    "docker": [
        (
            "How do you build a small, secure, reproducible Docker image for a Python service?",
            [
                _p("Slim base / multi-stage builds", "slim", "multi-stage", "multistage", "alpine", "base image"),
                _p("Layer caching / dependency pinning", "cache", "layer", "pin", "requirements", "lock"),
                _p("Non-root user / secrets handling", "non-root", "root", "secret", "env"),
                _p("Health checks / runtime config", "healthcheck", "health", "config", "env"),
            ],
        ),
    ],
    "kubernetes": [
        (
            "Explain how you would deploy a stateless API on Kubernetes and roll out a change safely.",
            [
                _p("Deployment / replicas / services", "deployment", "replica", "service", "ingress"),
                _p("Probes (readiness/liveness)", "readiness", "liveness", "probe"),
                _p("Rolling update / rollback", "rolling", "rollback", "canary", "blue"),
                _p("Config and secrets", "configmap", "secret", "env"),
            ],
        ),
    ],
    "postgresql": [
        (
            "A query on a large Postgres table became slow. How do you diagnose and fix it?",
            [
                _p("Uses EXPLAIN / query plans", "explain", "plan", "analyze"),
                _p("Indexing strategy", "index", "composite", "btree", "partial"),
                _p("Considers schema/query rewrite or partitioning", "rewrite", "partition", "denormal", "join"),
                _p("Measures before/after", "measure", "benchmark", "latency", "before"),
            ],
        ),
    ],
    "sql": [
        (
            "Explain the difference between INNER and LEFT JOIN, and how you would find duplicate rows in a table.",
            [
                _p("Join semantics", "inner", "left", "null", "unmatched"),
                _p("Duplicate detection (GROUP BY/HAVING/window)", "group by", "having", "row_number", "count"),
            ],
        ),
    ],
    "redis": [
        (
            "Where would you use Redis in a web backend and what are the pitfalls?",
            [
                _p("Use cases (cache, rate limit, queue, session)", "cache", "rate limit", "queue", "session"),
                _p("Expiry / eviction", "ttl", "expire", "evict"),
                _p("Consistency / invalidation pitfalls", "invalidat", "stale", "consisten"),
            ],
        ),
    ],
    "react": [
        (
            "How do you manage server state and avoid unnecessary re-renders in a React app?",
            [
                _p("Server-state tooling / caching", "react query", "swr", "cache", "fetch"),
                _p("Memoization / state placement", "memo", "usememo", "usecallback", "state"),
                _p("Component structure", "component", "split", "lazy"),
            ],
        ),
    ],
    "vector databases": [
        (
            "How do you choose between a dedicated vector database and pgvector, and how do you keep search quality up as data grows?",
            [
                _p("Scale/ops trade-offs", "scale", "operational", "trade-off", "tradeoff", "latency"),
                _p("Index types (HNSW/IVF)", "hnsw", "ivf", "index"),
                _p("Filtering / hybrid search", "filter", "hybrid", "metadata"),
                _p("Re-embedding / evaluation", "re-embed", "evaluat", "recall"),
            ],
        ),
    ],
    "embeddings": [
        (
            "How do you choose an embedding model and verify it works for your domain?",
            [
                _p("Model selection criteria", "dimension", "multilingual", "domain", "benchmark", "mteb"),
                _p("Evaluation on own data", "evaluat", "recall", "test set", "golden"),
                _p("Cost/latency trade-offs", "cost", "latency", "local", "api"),
            ],
        ),
    ],
}

SKILL_ALIASES = {
    "gen ai": "generative ai",
    "genai": "generative ai",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "llms": "llm",
    "large language models": "llm",
    "retrieval augmented generation": "rag",
    "retrieval-augmented generation": "rag",
    "vector database": "vector databases",
    "vector db": "vector databases",
    "embedding": "embeddings",
}

GENERIC_SKILL_POINTS = [
    _p("Concrete use case", "project", "built", "used", "implemented", "example"),
    _p("Trade-offs / limitations", "trade-off", "tradeoff", "limitation", "downside", "however", "but"),
    _p("How you tested or validated it", "test", "validate", "measure", "monitor", "evaluat"),
]

SYSTEM_DESIGN = {
    "genai": (
        "Design an AI assistant that answers customer questions using internal documents, with human review for risky answers. Walk me through the components.",
        [
            _p("Ingestion and retrieval pipeline", "ingest", "chunk", "embedding", "retriev", "vector"),
            _p("LLM orchestration / guardrails", "guardrail", "prompt", "orchestrat", "agent", "validate"),
            _p("Human-in-the-loop for risky outputs", "human", "review", "approval", "escalat"),
            _p("Evaluation and monitoring", "evaluat", "monitor", "feedback", "metric", "log"),
            _p("Scaling, cost and latency", "scale", "cache", "latency", "cost", "queue"),
        ],
    ),
    "backend": (
        "Design a job-application tracking service for 100k users: data model, APIs, background work and how it scales.",
        [
            _p("Data model / storage choice", "table", "schema", "postgres", "database", "index"),
            _p("API design", "rest", "endpoint", "api", "pagination"),
            _p("Background jobs / queues", "queue", "worker", "celery", "async", "cron"),
            _p("Scaling and caching", "scale", "cache", "replica", "shard", "load balanc"),
            _p("Reliability / observability", "monitor", "log", "retry", "alert", "backup"),
        ],
    ),
}

STAR_POINTS = [
    _p("Situation: sets the context", "situation", "when i", "at my", "in my", "we were", "project", "team"),
    _p("Task: your responsibility or goal", "responsible", "goal", "needed to", "task", "objective", "my role"),
    _p("Action: what *you* did", "i built", "i implemented", "i designed", "i decided", "i wrote", "i led", "i created", "i proposed", "i "),
    _p("Result: measurable outcome", "result", "reduced", "improved", "increased", "saved", "%", "outcome", "learned"),
]

BEHAVIORAL = [
    ("Tell me about a time a project you owned did not go as planned. What did you do?", "ownership"),
    ("Describe a technical disagreement with a teammate and how it was resolved.", "collaboration"),
    ("Tell me about a time you had to learn a new technology quickly to deliver something.", "learning"),
    ("Describe a situation where you had to meet a tight deadline. How did you prioritise?", "prioritisation"),
    ("Tell me about a bug or incident you had to debug under pressure.", "debugging"),
    ("Give an example of when you improved a process or system without being asked.", "initiative"),
]


# ----------------------------------------------------------------- data classes


@dataclass
class GeneratedQuestion:
    category: str
    question: str
    expected_points: list[dict]
    skill: str | None = None
    source: str = "template"


def norm_skill(value: str) -> str:
    v = (value or "").strip().lower()
    return SKILL_ALIASES.get(v, v)


def question_fingerprint(text: str) -> str:
    return hashlib.sha1(re.sub(r"\W+", " ", text.lower()).strip().encode()).hexdigest()[:16]


def _unique(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        n = norm_skill(item)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _hard_probe(q: GeneratedQuestion, difficulty: str) -> GeneratedQuestion:
    if difficulty == "hard" and q.category in {"technical", "system_design", "project"}:
        q.question += " Also explain what breaks first at 10x scale and how you would detect it."
        q.expected_points = q.expected_points + [
            _p("Failure modes at scale", "scale", "bottleneck", "fail", "break", "monitor", "load")
        ]
    return q


# -------------------------------------------------------------------- generation


def generate_questions(
    *,
    job_title: str,
    company: str,
    job_skills: list[str],
    candidate_skills: list[str],
    missing_skills: list[str],
    projects: list[dict],
    mode: str,
    difficulty: str,
    count: int,
    exclude: set[str] | None = None,
) -> list[GeneratedQuestion]:
    """Rule-based question set tailored to the job, the candidate and their gaps."""
    exclude = exclude or set()
    cand = set(_unique(candidate_skills))
    required = _unique(job_skills)
    gaps = [s for s in _unique(missing_skills) if s in required] or [s for s in required if s not in cand]
    strengths = [s for s in required if s in cand] or required

    technical: list[GeneratedQuestion] = []
    for skill in strengths + [s for s in required if s not in strengths]:
        entries = SKILL_BANK.get(skill)
        if entries:
            for text, points in entries:
                technical.append(GeneratedQuestion("technical", text, list(points), skill))
        else:
            technical.append(
                GeneratedQuestion(
                    "technical",
                    f"Tell me about a real situation where you used {skill}. What trade-offs did you make and how did you verify it worked?",
                    list(GENERIC_SKILL_POINTS),
                    skill,
                )
            )

    genai_role = bool({"rag", "llm", "generative ai", "langchain", "langgraph"} & set(required)) or bool(
        re.search(r"\b(ai|ml|llm|gen)", job_title.lower())
    )
    design_text, design_points = SYSTEM_DESIGN["genai" if genai_role else "backend"]
    design = [GeneratedQuestion("system_design", design_text, list(design_points), None)]

    project_qs = []
    for proj in projects or []:
        name = (proj.get("name") or "").strip() if isinstance(proj, dict) else ""
        if not name:
            continue
        tech = ", ".join((proj.get("technologies") or [])[:4]) if isinstance(proj, dict) else ""
        project_qs.append(
            GeneratedQuestion(
                "project",
                f"Walk me through your project \"{name}\"{f' ({tech})' if tech else ''}. What was your role, the hardest technical decision, and what would you change today?",
                [
                    _p("Explains your specific role", "i built", "i designed", "i implemented", "my role", "i was responsible", "i "),
                    _p("Names a concrete technical decision", "decid", "chose", "because", "instead of", "trade-off", "tradeoff"),
                    _p("Reflects on improvements", "would change", "improve", "next", "differently", "learned"),
                    _p("Outcome / impact", "result", "users", "latency", "accuracy", "reduced", "improved", "%"),
                ],
                None,
            )
        )

    behavioral = [GeneratedQuestion("behavioral", q, list(STAR_POINTS), topic) for q, topic in BEHAVIORAL]
    role_fit = [
        GeneratedQuestion(
            "role_fit",
            f"Why are you interested in the {job_title} role at {company}, and how does your experience prepare you for it?",
            [
                _p("Specific to the role/company", company.lower().split()[0] if company else "company", "role", "team", "product", "mission"),
                _p("Links real experience to requirements", "experience", "built", "project", "worked", "skills"),
                _p("Clear motivation / growth", "grow", "learn", "excited", "interested", "impact"),
            ],
            None,
        )
    ]
    gap_qs = [
        GeneratedQuestion(
            "gap",
            f"This role asks for {skill}, which isn't prominent in your background. How would you get productive with it in your first 30 days?",
            [
                _p("Honest about current level", "limited", "haven't", "have not", "no direct", "adjacent", "familiar", "basic"),
                _p("Concrete learning plan", "plan", "learn", "course", "docs", "build", "prototype", "week"),
                _p("Transfers related experience", "similar", "related", "transfer", "experience with", "like"),
            ],
            skill,
        )
        for skill in gaps[:3]
    ]

    if mode == "technical":
        pools = [technical, design, project_qs, gap_qs]
    elif mode == "behavioral":
        pools = [role_fit, behavioral, gap_qs]
    else:  # mixed: interleave so the session feels like a real interview
        pools = [role_fit, technical, behavioral, design, project_qs, gap_qs]

    chosen: list[GeneratedQuestion] = []
    used: set[str] = set()

    def drain(pools: list[list[GeneratedQuestion]]) -> None:
        """Round-robin across pools so a session mixes categories like a real interview."""
        index = 0
        while len(chosen) < count and any(pools):
            pool = pools[index % len(pools)]
            index += 1
            while pool:
                q = pool.pop(0)
                fp = question_fingerprint(q.question)
                if fp not in used:
                    used.add(fp)
                    chosen.append(_hard_probe(q, difficulty))
                    break

    fresh = [[q for q in pool if question_fingerprint(q.question) not in exclude] for pool in pools]
    drain(fresh)
    if len(chosen) < count and exclude:
        # Not enough unseen questions for this job: reuse earlier ones rather than return fewer.
        drain([[q for q in pool if question_fingerprint(q.question) in exclude] for pool in pools])
    return chosen[:count]


# -------------------------------------------------------------------- evaluation

_NUMBER = re.compile(r"\d")
_EXAMPLE_CUES = ("for example", "for instance", "e.g", "such as", "in my", "at my", "we ", "i built", "i used")
_REASONING_CUES = ("because", "trade-off", "tradeoff", "however", "instead", "so that", "therefore", "which means")


def _kw_hit(text: str, keyword: str) -> bool:
    kw = keyword.lower()
    if kw.strip() == "i":  # first-person marker, avoid matching inside words
        return re.search(r"\bi\b", text) is not None
    if not kw[:1].isalnum() or kw.endswith(" "):
        return kw in text  # symbols like "%" and phrases with explicit trailing space
    return re.search(r"(?<![a-z0-9])" + re.escape(kw), text) is not None


def evaluate_answer(answer: str, expected_points: list[dict], category: str) -> dict:
    """Score an answer 0-100 against its rubric. Deterministic and explainable."""
    text = (answer or "").strip().lower()
    words = re.findall(r"[a-z0-9']+", text)
    n_words = len(words)

    matched, missing = [], []
    for point in expected_points:
        if any(_kw_hit(text, k) for k in point.get("keywords", [])):
            matched.append(point["label"])
        else:
            missing.append(point["label"])
    coverage = len(matched) / len(expected_points) if expected_points else 0.5

    if n_words < 15:
        depth = n_words / 15 * 0.4
    elif n_words < 60:
        depth = 0.4 + (n_words - 15) / 45 * 0.6
    elif n_words <= 300:
        depth = 1.0
    else:
        depth = max(0.7, 1.0 - (n_words - 300) / 1000)

    specificity = 0.0
    if _NUMBER.search(text):
        specificity += 0.5
    if any(cue in text for cue in _EXAMPLE_CUES):
        specificity += 0.5

    reasoning = min(1.0, sum(1 for cue in _REASONING_CUES if cue in text) / 2)

    score = (coverage * 60 + depth * 20 + specificity * 10 + reasoning * 10) if n_words else 0.0
    if n_words < 8:
        score = min(score, 25.0)
    score = round(max(0.0, min(100.0, score)), 1)

    strengths, improvements = [], []
    if matched:
        strengths.append("Covered: " + "; ".join(matched[:3]))
    if specificity >= 1.0:
        strengths.append("Backed the answer with specifics (numbers and a real example)")
    if reasoning >= 1.0:
        strengths.append("Explained the reasoning behind your choices")
    if n_words < 15:
        improvements.append("Answer is too short – aim for 4-8 sentences with a concrete example")
    if missing:
        label = "Cover" if category != "behavioral" else "Add"
        improvements.extend(f"{label}: {m}" for m in missing[:3])
    if specificity < 0.5 and n_words >= 15:
        improvements.append("Add a concrete example or a number (latency, users, accuracy, time saved)")
    if reasoning < 0.5 and category in {"technical", "system_design", "project"} and n_words >= 15:
        improvements.append("Explain why you chose that approach and the trade-offs")
    if n_words > 300:
        improvements.append("Tighten the answer – interviewers lose the thread after about two minutes")

    return {
        "score": score,
        "rating": rating_for(score),
        "matched_points": matched,
        "missing_points": missing,
        "strengths": strengths,
        "improvements": improvements,
        "word_count": n_words,
        "evaluator": "rule_based",
    }


def rating_for(score: float) -> str:
    for threshold, label in RATINGS:
        if score >= threshold:
            return label
    return "needs_work"


# ------------------------------------------------------------------------ report


def build_report(questions: list[dict], job_missing_skills: list[str] | None = None) -> dict:
    """Aggregate answered questions into the end-of-session report."""
    answered = [q for q in questions if q.get("score") is not None]
    skipped = len(questions) - len(answered)
    if not answered:
        raise ValueError("Answer at least one question before completing the session")

    overall = round(sum(q["score"] for q in answered) / len(answered), 1)

    by_category: dict[str, list[float]] = {}
    by_skill: dict[str, list[float]] = {}
    themes: Counter[str] = Counter()
    for q in answered:
        by_category.setdefault(q["category"], []).append(q["score"])
        if q.get("skill"):
            by_skill.setdefault(q["skill"], []).append(q["score"])
        for label in (q.get("feedback") or {}).get("missing_points", []):
            themes[label] += 1

    cat_scores = {k: round(sum(v) / len(v), 1) for k, v in by_category.items()}
    skill_scores = {k: round(sum(v) / len(v), 1) for k, v in by_skill.items()}
    weak_skills = [k for k, v in sorted(skill_scores.items(), key=lambda kv: kv[1]) if v < 60][:5]
    strong_skills = [k for k, v in sorted(skill_scores.items(), key=lambda kv: -kv[1]) if v >= 75][:5]

    next_steps = [f"Revisit {s} – your answer missed key points" for s in weak_skills[:3]]
    next_steps += [
        f"Prepare a short story for the gap: {s}" for s in (job_missing_skills or [])[:2] if s not in weak_skills
    ]
    weakest_cat = min(cat_scores, key=cat_scores.get)
    if cat_scores[weakest_cat] < 70:
        next_steps.append(f"Practise more {weakest_cat.replace('_', ' ')} questions")
    if not next_steps:
        next_steps.append("Run a harder session or try a different job to keep sharpening")

    readiness = "ready" if overall >= 75 else "almost_ready" if overall >= 60 else "needs_practice"
    return {
        "overall_score": overall,
        "rating": rating_for(overall),
        "readiness": readiness,
        "answered": len(answered),
        "skipped": skipped,
        "by_category": cat_scores,
        "by_skill": skill_scores,
        "strong_skills": strong_skills,
        "weak_skills": weak_skills,
        "top_improvement_themes": [label for label, _ in themes.most_common(5)],
        "next_steps": next_steps[:6],
    }
