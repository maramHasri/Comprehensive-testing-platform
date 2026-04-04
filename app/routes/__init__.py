"""
API layer — Flask-RESTx Api and namespaces.
Namespaces are registered in user-journey order for clear Swagger presentation:
1. Authentication → 2. Question Banks → 3. Quizzes → 4. Questions → 5. Answers → 6. Attempts
"""
from flask_restx import Api

from app.routes.auth.routes import auth_ns
from app.routes.question_banks.routes import question_bank_ns
from app.routes.quizzes.routes import quiz_ns
from app.routes.questions.routes import question_ns
from app.routes.answers.routes import answer_ns
from app.routes.attempts.routes import attempt_ns
from app.routes.files.routes import files_ns
from app.routes.processing.routes import processing_ns
from app.routes.ai_generation.routes import ai_generation_ns
from app.routes.admin_i18n.routes import admin_i18n_ns

authorizations = {
    "Bearer": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Enter your JWT token only (without 'Bearer'). Example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    }
}

api = Api(
    title="Quiz Management System API",
    version="1.0",
    description="Quiz Management System. User journey: Login → Manage banks → Create quizzes → Add questions → Submit attempts.",
    authorizations=authorizations,
    security="Bearer",
)

# Register in exact order so Swagger sections follow the user journey
api.add_namespace(auth_ns, path="/auth")
api.add_namespace(question_bank_ns, path="/api/question-banks")
api.add_namespace(quiz_ns, path="/api/quizzes")
api.add_namespace(question_ns, path="/api/questions")
api.add_namespace(answer_ns, path="/api/questions")  # routes are /<question_id>/answers, so full path /api/questions/<id>/answers
api.add_namespace(attempt_ns, path="/api/quizzes")   # routes are /<quiz_id>/attempts, so full path /api/quizzes/<id>/attempts
api.add_namespace(files_ns, path="/api/files")       # /api/files/extract_text (same extraction as /api/extract-text)
api.add_namespace(processing_ns, path="/api")        # /api/extract-text — file → plain text only
api.add_namespace(ai_generation_ns, path="/api/ai")    # /api/ai/generate-quiz — JSON questions from content_text (Qwen)
api.add_namespace(admin_i18n_ns, path="/api/admin")  # /api/admin/messages (admin JWT)
