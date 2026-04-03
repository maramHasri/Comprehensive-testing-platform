
import json
import os
import re
from dotenv import load_dotenv
from pathlib import Path
from huggingface_hub import InferenceClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=True)

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

def generate_questions(
    text: str,
    question_type: str = "multiple-choice",
    max_questions: int = 10,
    retry_count: int = 0,
) -> dict:
    """
    توليد أسئلة من نص باستخدام موديل Hugging Face مباشرة.
    """
    if not text or not text.strip():
        return {"questions": []}

    prompt = f"""
You are an exam question generator.

TASK:
- Read the following text.
- Generate exactly {max_questions} questions of type "{question_type}".
- You MUST return ONLY valid JSON.
- Do NOT wrap the JSON in markdown code fences (```json ... ```).
- No explanations, no extra text.
- The first character of your reply must be '{{' and the last character must be '}}'.

QUALITY CONSTRAINTS (to prevent truncation):
- Keep each "question" short (<= 12 words).
- Keep each choice short (<= 4 words).
- No code blocks, no markdown, no extra symbols outside JSON.

JSON FORMAT EXACTLY:
{{
  "questions": [
    {{
      "question": "string",
      "type": "multiple-choice|true/false|short-answer|essay",
      "choices": ["A","B","C","D"],
      "correct_answer": "string"
    }}
  ]
}}

Text:
{text}
""".strip()

    client = _get_hf_client()
    try:
        # استدعاء الموديل بأسلوب محادثة (conversational)
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            # Increased to reduce truncation; JSON must still fit.
            max_tokens=3500,
            temperature=0.3,
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
            if retry_count == 0 and max_questions > 3:
                smaller = max(3, max_questions // 2)
                try:
                    return generate_questions(
                        text=text,
                        question_type=question_type,
                        max_questions=smaller,
                        retry_count=1,
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