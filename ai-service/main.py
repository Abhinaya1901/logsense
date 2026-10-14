"""LogSense AI diagnosis service.

POST /api/explain  {"log": "...", "context": "odata|abap|ui5|other"}
  -> {"severity", "summary", "likely_cause", "fix_steps", "where_to_look", "source"}

Uses an LLM through Groq when GROQ_API_KEY is set; otherwise (or if the LLM
call fails) falls back to an offline rule base of common SAP errors.
Secrets in the log are masked before anything is sent to the LLM.
"""
import json
import os
import re

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rules import diagnose

load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")

CONTEXT_LABELS = {
    "odata": "an SAP OData / SAP Gateway service consumed by a UI5 app",
    "abap": "an SAP ABAP runtime error (short dump)",
    "ui5": "an SAP UI5 / Fiori front-end application",
    "other": "an SAP system",
}

SYSTEM_PROMPT = """You are a senior SAP developer helping a junior colleague troubleshoot.
You analyse logs from SAP ABAP, SAP Gateway / OData and SAP UI5 / Fiori applications.
Reply ONLY with a JSON object with exactly these keys:
  "severity": one of "High", "Medium", "Low",
  "summary": one sentence describing what went wrong,
  "likely_cause": two or three sentences on the most probable root cause,
  "fix_steps": an array of 2 to 5 short, concrete steps,
  "where_to_look": SAP transactions, tools or files to inspect (e.g. ST22, /IWFND/ERROR_LOG, SU53, $metadata).
Be specific to the log. If the log is ambiguous, say what extra information would confirm the cause.
Never invent transaction codes."""

SECRET_PATTERNS = [
    (re.compile(r"(authorization:\s*)(basic|bearer)\s+\S+", re.IGNORECASE), r"\1\2 ***"),
    (re.compile(r"((?:password|passwd|pwd|secret|api[_-]?key|token)\s*[=:]\s*)\S+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(x-csrf-token:\s*)(?!fetch)\S+", re.IGNORECASE), r"\1***"),
]

app = FastAPI(title="LogSense AI diagnosis service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ExplainRequest(BaseModel):
    log: str = Field(..., min_length=1, max_length=20000)
    context: str = "odata"


class ExplainResponse(BaseModel):
    severity: str
    summary: str
    likely_cause: str
    fix_steps: list[str]
    where_to_look: str
    source: str


def mask_secrets(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def explain_with_llm(log: str, context: str, api_key: str) -> dict:
    user_prompt = (
        f"The following log comes from {CONTEXT_LABELS.get(context, CONTEXT_LABELS['other'])}.\n\n"
        f"LOG:\n{log}"
    )
    response = httpx.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": GROQ_MODEL,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = json.loads(response.json()["choices"][0]["message"]["content"])
    steps = data.get("fix_steps") or []
    if isinstance(steps, str):
        steps = [steps]
    return {
        "severity": str(data.get("severity", "Medium")),
        "summary": str(data.get("summary", "")),
        "likely_cause": str(data.get("likely_cause", "")),
        "fix_steps": [str(s) for s in steps],
        "where_to_look": str(data.get("where_to_look", "")),
        "source": f"Groq LLM ({GROQ_MODEL})",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_enabled": bool(os.getenv("GROQ_API_KEY"))}


@app.post("/api/explain", response_model=ExplainResponse)
def explain(request: ExplainRequest) -> dict:
    log = mask_secrets(request.log)
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            return explain_with_llm(log, request.context, api_key)
        except (httpx.HTTPError, KeyError, ValueError) as error:
            result = diagnose(log)
            result["source"] += f" (LLM unavailable: {type(error).__name__})"
            return result
    return diagnose(log)
