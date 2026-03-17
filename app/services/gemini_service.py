"""
Backward-compatible service alias.

The project originally referenced `app.services.gemini_service.generate_questions`.
We now use Qwen via Hugging Face in `app.services.ai_qwen_service`, but keep this
module to avoid breaking imports across the codebase.
"""

from app.services.ai_qwen_service import generate_questions  # re-export

