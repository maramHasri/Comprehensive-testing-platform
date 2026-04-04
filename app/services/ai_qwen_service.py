
import json
import os
import re
from dotenv import load_dotenv
from pathlib import Path
from huggingface_hub import InferenceClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=True)

# Upper bound for POST /api/ai/generate-quiz and generate_quiz_from_text (clamp).
MAX_QUIZ_QUESTIONS = 30


def _get_hf_client() -> InferenceClient:
    token = (os.getenv("HF_TOKEN") or "").strip()

    # إزالة علامات الاقتباس إذا وجدت
    if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
        token = token[1:-1].strip()

    if not token:
        raise RuntimeError("HF_TOKEN is not set.")

    if not token.startswith("hf_"):
        raise RuntimeError("Invalid Hugging Face token.")

    return InferenceClient(
        model=os.getenv("HF_QUIZ_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        token=token,
    )


def _max_output_tokens() -> int:
    """HF caps vary by model; default sized for up to ~30 MCQs in JSON (raise if truncated)."""
    try:
        return int(os.getenv("HF_QUIZ_MAX_TOKENS", "16384"))
    except ValueError:
        return 16384


def _scaled_question_target(text: str, requested_cap: int) -> int:
    """
    Choose how many questions to ask for based on source length so short texts
    do not force repetitive questions. Client's requested_cap is still the ceiling.
    """
    t = (text or "").strip()
    words = len(t.split())
    cap = max(1, min(int(requested_cap), MAX_QUIZ_QUESTIONS))
    if words < 10:
        return 1
    if words <= 60:
        n = max(1, min(5, (words + 10) // 13))
    else:
        n = max(3, (words + 25) // 30)
    return max(1, min(n, cap))


def _salvage_questions_from_partial_json(raw_text: str) -> dict | None:
    """
    If the model truncates mid-JSON or corrupts a string, full json.loads fails.
    Parse each array element with JSONDecoder.raw_decode so we keep complete
    question objects and drop only the broken tail.
    """
    t = (raw_text or "").strip()
    if "```" in t:
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    key_at = t.find('"questions"')
    if key_at == -1:
        return None
    lb = t.find("[", key_at)
    if lb == -1:
        return None
    i = lb + 1
    n = len(t)
    questions: list = []
    decoder = json.JSONDecoder()
    while i < n:
        while i < n and t[i] in " \t\n\r,":
            i += 1
        if i >= n or t[i] != "{":
            break
        try:
            obj, end = decoder.raw_decode(t, i)
            if isinstance(obj, dict) and "question" in obj:
                questions.append(obj)
            i = end
        except json.JSONDecodeError:
            break
    if not questions:
        return None
    return {"questions": questions}


def generate_questions(
    text: str,
    question_type: str = "multiple-choice",
    max_questions: int = MAX_QUIZ_QUESTIONS,
    retry_count: int = 0,
) -> dict:
    """
    توليد أسئلة من نص باستخدام موديل Hugging Face مباشرة.
    """
    if not text or not text.strip():
        return {"questions": []}

    try:
        raw_n = int(max_questions)
    except (TypeError, ValueError):
        raw_n = MAX_QUIZ_QUESTIONS
    client_cap = max(1, min(raw_n, MAX_QUIZ_QUESTIONS))
    mq = _scaled_question_target(text, client_cap)
    word_count = len(text.split())
    qtype = (question_type or "multiple-choice").strip() or "multiple-choice"

    prompt = f"""You are an advanced AI module inside an educational assessment generation system.

Your role is NOT only to generate questions, but to simulate a full question-generation pipeline that includes:

1. Concept extraction
2. Semantic representation (embeddings simulation)
3. Similarity detection using cosine similarity
4. Deduplication
5. Final optimized question output

Do all reasoning internally. The user sees ONLY the final JSON (STEP 7).

========================================================
STEP 1: CONCEPT EXTRACTION (Semantic Layer)
========================================================
Read the INPUT TEXT at the end carefully.

Extract ONLY distinct educational concepts.

Rules:
- Merge semantically similar ideas into ONE concept.
- Ignore surface-level differences in wording.
- Focus on meaning, not sentences.
- Build a clean internal concept list (do not output this list).

========================================================
STEP 2: SEMANTIC EMBEDDING REPRESENTATION (SIMULATED)
========================================================
For each extracted concept:

- Assume each concept is converted into a high-dimensional embedding vector:
  concept → vector representation in semantic space

You do NOT output vectors, but you MUST behave as if you are comparing them.

========================================================
STEP 3: COSINE SIMILARITY CHECK (DEDUP LOGIC)
========================================================
Before generating questions:

For any two concepts C1 and C2:

Compute conceptual similarity (mentally / implicitly):

cosine_similarity(C1, C2) = (C1 · C2) / (||C1|| * ||C2||)

Rules:
- If similarity > 0.85 → treat as DUPLICATE concepts → MERGE them
- If similarity ≤ 0.85 → treat as DISTINCT concepts

Apply the same logic later for generated questions.

========================================================
STEP 4: QUESTION GENERATION RULES
========================================================
For EACH final unique concept after merging:

- Generate EXACTLY ONE question only.
- Do NOT generate multiple questions per concept.
- Ensure the question tests understanding of meaning, not phrasing.
- Preferred question "type" for this request: "{qtype}" (if "mixed", vary types across questions).

Multiple-choice specifics:
- "choices": four substantive full-text answers (not A/B/C/D or أ/ب/ج/د only).
- "correct_answer": must match one "choices" entry **exactly** (verbatim).

Output size hint (from server, based on text length):
- Source ~**{word_count}** words; client cap **{client_cap}**; target at most **{mq}** questions after pipeline.
- If fewer distinct concepts survive STEP 3 than {mq}, output fewer questions (no padding with duplicates).
- Never output more than {mq} questions.

========================================================
STEP 5: QUESTION-LEVEL DEDUPLICATION
========================================================
After generating questions:

For every pair of questions Q1 and Q2:

- Compare implied meaning as if cosine similarity on their semantics.
- If similarity > 0.85:
    - KEEP only the stronger, clearer question
    - DELETE the redundant one

========================================================
STEP 6: QUALITY OPTIMIZATION
========================================================
Ensure:
- Each question maps to a unique concept
- No repeated cognitive target
- No paraphrased duplicates
- Balanced difficulty across questions
- One language per question; match the INPUT TEXT language
- Do not use unescaped double quotes inside JSON string values (use apostrophes inside text if needed)

========================================================
STEP 7: FINAL OUTPUT FORMAT (ONLY THIS TO THE USER)
========================================================
Return ONLY valid JSON. No markdown fences. First non-whitespace char '{{', valid JSON.parse().

{{
  "questions": [
    {{
      "question": "...",
      "type": "multiple-choice",
      "choices": ["...", "...", "...", "..."],
      "correct_answer": "..."
    }}
  ]
}}

========================================================
HARD CONSTRAINTS
========================================================
- No duplicate concepts in the internal pipeline
- No semantically similar questions in final output
- No repeated cognitive targets
- Strict one-question-per-concept rule
- If duplication is detected, fix internally before output — never emit duplicates

FAIL-SAFE: If you cannot produce valid JSON, return: {{"questions": []}}

========================================================
INPUT TEXT:
{text}
""".strip()

    client = _get_hf_client()
    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=_max_output_tokens(),
            temperature=0.2,
        )
        raw_text = response.choices[0].message.content or ""
    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg:
            raise RuntimeError(
                "Hugging Face returned 401 Unauthorized. "
                "Ensure HF_TOKEN is valid and has inference permissions."
            ) from e
        raise

    def _extract_json_candidate(s: str) -> str:
       
        candidate = (s or "").strip()

        if "```" in candidate:
            candidate = re.sub(r"^```[a-zA-Z]*\s*", "", candidate)
            candidate = re.sub(r"\s*```$", "", candidate)

        # Slice to the first {...} block as a last resort.
        first_brace = candidate.find("{")
        last_brace = candidate.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = candidate[first_brace:last_brace + 1]

        return candidate.strip()

    try:
        data = json.loads(raw_text)
        if isinstance(data, dict) and "questions" in data:
            return data
        if isinstance(data, list):
            return {"questions": data}
        return {"questions": [], "raw": raw_text}
    except json.JSONDecodeError:
        try:
            cleaned = _extract_json_candidate(raw_text)
            data = json.loads(cleaned)
            if isinstance(data, dict) and "questions" in data:
                return data
            if isinstance(data, list):
                return {"questions": data}
            return {"questions": [], "raw": raw_text}
        except Exception:
            salvaged = _salvage_questions_from_partial_json(raw_text)
            if salvaged and salvaged.get("questions"):
                return salvaged
            try:
                salvaged2 = _salvage_questions_from_partial_json(_extract_json_candidate(raw_text))
                if salvaged2 and salvaged2.get("questions"):
                    return salvaged2
            except Exception:
                pass
            if retry_count == 0 and mq > 2:
                smaller = max(2, mq // 2)
                try:
                    return generate_questions(
                        text=text,
                        question_type=question_type,
                        max_questions=smaller,
                        retry_count=retry_count + 1,
                    )
                except Exception:
                    pass

            return {
                "questions": [],
                "error": "Model did not return valid JSON (even after cleanup).",
                "raw": raw_text,
            }

if __name__ == "__main__":
    sample_text = "ضغط البيانات هو عملية تقليل حجم الملف عن طريق إزالة المعلومات المتكررة."
    questions = generate_questions(sample_text, max_questions=3, question_type="multiple-choice")
    print(json.dumps(questions, indent=2, ensure_ascii=False))