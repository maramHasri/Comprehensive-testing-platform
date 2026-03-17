
import json
import os
from dotenv import load_dotenv
from pathlib import Path
from huggingface_hub import InferenceClient

# ==============================
# تحميل .env من جذر المشروع
# ==============================
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=True)

# ==============================
# إنشاء عميل Hugging Face مباشر
# ==============================
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
        model=os.getenv("HF_QUIZ_MODEL", "Qwen/Qwen2.5-7B-Instruct"),  # ❌ بدون :together
        token=token,
    )

# ==============================
# توليد الأسئلة من نص
# ==============================
def generate_questions(
    text: str,
    question_type: str = "multiple-choice",
    max_questions: int = 10
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
- Generate up to {max_questions} questions of type "{question_type}".
- You MUST return ONLY valid JSON. No explanations, no extra text.

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
            max_tokens=2000,
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

    try:
        data = json.loads(raw_text)
        if isinstance(data, dict) and "questions" in data:
            return data
        if isinstance(data, list):
            return {"questions": data}
        return {"questions": [], "raw": raw_text}
    except json.JSONDecodeError:
        return {"questions": [], "error": "Model did not return valid JSON.", "raw": raw_text}

# ==============================
# مثال على الاستخدام
# ==============================
if __name__ == "__main__":
    sample_text = "ضغط البيانات هو عملية تقليل حجم الملف عن طريق إزالة المعلومات المتكررة."
    questions = generate_questions(sample_text, max_questions=3, question_type="multiple-choice")
    print(json.dumps(questions, indent=2, ensure_ascii=False))