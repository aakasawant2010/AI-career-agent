from dotenv import load_dotenv

load_dotenv()

import json
import os
import re

from openai import OpenAI


MODEL = "gpt-6-luna"


def normalize_experience_years(value):
    """
    Convert AI-generated experience values into a float.

    Examples:
        3          -> 3.0
        3.5        -> 3.5
        "3 years"  -> 3.0
        "3+ years" -> 3.0
        "3.5 years" -> 3.5
        None       -> None
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        value = value.strip().lower()

        match = re.search(r"\d+(?:\.\d+)?", value)

        if match:
            return float(match.group())

    return None


def extract_resume_intelligence(
    parsed_text: str,
) -> dict:
    """
    Extract structured intelligence from parsed resume text
    using OpenAI.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is not configured"
        )

    if not parsed_text or not parsed_text.strip():
        raise ValueError(
            "Resume text is empty"
        )

    client = OpenAI(
        api_key=api_key,
    )

    prompt = f"""
You are an expert resume intelligence extraction system.

Analyze the resume below and extract ONLY information
that is explicitly supported by the resume.

Do not invent, assume, or hallucinate information.

Return ONLY valid JSON.

The JSON must contain exactly these fields:

{{
    "skills": [],
    "experience": [],
    "education": [],
    "projects": [],
    "certifications": [],
    "job_titles": [],
    "technologies": [],
    "total_experience_years": null,
    "summary": ""
}}

Extraction rules:

1. skills
   - Technical skills
   - Soft skills
   - Domain skills

2. experience
   - Extract each professional experience entry.
   - Preserve company, role, dates, and responsibilities
     when explicitly available.

3. education
   - Extract degree, institution, dates, and relevant details.

4. projects
   - Extract project name, description, technologies,
     and role when available.

5. certifications
   - Include only explicitly mentioned certifications.

6. job_titles
   - Include explicitly mentioned professional/job titles.

7. technologies
   - Programming languages
   - Frameworks
   - Libraries
   - Databases
   - Cloud platforms
   - DevOps tools
   - AI/ML technologies

8. total_experience_years
   - Return a NUMBER only.
   - Example: 3, 3.5, 4.
   - Do NOT return strings such as "3 years" or "3+ years".
   - Use an explicitly stated value when available.
   - Otherwise estimate only when the employment dates clearly
     support the calculation.
   - Otherwise return null.

9. summary
   - Write a concise factual summary based only on the resume.

Important:
- Do not invent missing information.
- Do not duplicate information unnecessarily.
- Do not include markdown.
- Return JSON only.

RESUME:

{parsed_text}
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt,
    )

    output = response.output_text.strip()

    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "OpenAI returned invalid JSON"
        ) from exc

    # Normalize experience so the database always receives
    # a numeric value or None.
    data["total_experience_years"] = normalize_experience_years(
        data.get("total_experience_years")
    )

    # Ensure all expected fields exist.
    expected_fields = {
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
        "job_titles": [],
        "technologies": [],
        "total_experience_years": None,
        "summary": "",
    }

    for field, default_value in expected_fields.items():
        if field not in data:
            data[field] = default_value

    return data