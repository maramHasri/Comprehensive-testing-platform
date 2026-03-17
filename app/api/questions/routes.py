"""
 Questions — Question resource (get by ID).
User journey: questions belong to quizzes or question banks; use this to fetch a single question.
"""
from flask_restx import Namespace, Resource, fields

from app.models import Question

question_ns = Namespace(
    " Questions",
    description="Question resource. Get a question by ID (from a quiz or question bank).",
)

question_response_model = question_ns.model(
    "QuestionResponse",
    {
        "id": fields.Integer,
        "type": fields.String,
        "content": fields.String,
        "hint": fields.Raw,
        "points": fields.Float,
        "base_time": fields.Raw,
        "bank_id": fields.Integer,
        "quiz_id": fields.Integer,
        "order_index": fields.Integer,
    },
)


# ----- Read one -----
@question_ns.route("/<int:question_id>")
class QuestionDetail(Resource):
    @question_ns.marshal_with(question_response_model)
    @question_ns.response(404, "Question not found")
    def get(self, question_id):
        """Get a single question by ID (from a quiz or question bank). Does not include answers; use Answers API."""
        question = Question.query.get(question_id)
        if not question:
            return {"message": "Question not found."}, 404
        return {
            "id": question.id,
            "type": question.type,
            "content": question.content,
            "hint": question.hint,
            "points": question.points,
            "base_time": question.base_time,
            "bank_id": question.bank_id,
            "quiz_id": question.quiz_id,
            "order_index": question.order_index,
        }, 200
