"""
 Answers — Add and list answers (choices) for a question.
Uses form-style inputs so answer text with quotes/newlines is safe.
"""
from flask_restx import Namespace, Resource, reqparse, inputs

from app.extensions import db
from app.models import Question, Choice
from app.services.answer_service import create_bulk_answers
from app.utils.request_validation import trim_str, parse_form_bool

answer_ns = Namespace(
    " Answers",
    description="Add and list answers (choices) for questions. Use form fields below (no raw JSON).",
)

# ----- Form parsers -----
answer_create_parser = reqparse.RequestParser()
answer_create_parser.add_argument("text", type=str, required=True, location="form", help="Answer text (required)")
answer_create_parser.add_argument("is_correct", type=inputs.boolean, default=False, location="form", help="Is this the correct answer?")

def _bulk_answers_parser():
    p = reqparse.RequestParser()
    for i in range(1, 6):
        p.add_argument(f"text_{i}", type=str, location="form", help=f"Answer {i} text (leave empty to skip)")
        p.add_argument(f"is_correct_{i}", type=inputs.boolean, default=False, location="form", help=f"Answer {i} is correct?")
    return p
bulk_answers_parser = _bulk_answers_parser()


# ----- Read: List answers -----
@answer_ns.route("/<int:question_id>/answers")
class QuestionAnswers(Resource):
    @answer_ns.response(404, "Question not found")
    def get(self, question_id):
        """List answers (choices) for this question."""
        question = Question.query.get_or_404(question_id)
        return [
            {"id": c.id, "question_id": c.question_id, "text": c.text, "is_correct": c.is_correct}
            for c in question.choices
        ], 200

    @answer_ns.expect(answer_create_parser)
    @answer_ns.response(201, "Created")
    @answer_ns.response(400, "Validation error")
    @answer_ns.response(404, "Question not found")
    def post(self, question_id):
        """Add one answer. Use form fields; text can contain quotes and newlines safely."""
        question = Question.query.get_or_404(question_id)
        args = answer_create_parser.parse_args()
        text = trim_str(args.get("text"))
        if not text:
            return {"message": "Answer text is required."}, 400
        if question.type == "essay":
            return {"message": "Essay questions must not have answers."}, 400
        if question.type == "true_false" and len(question.choices) >= 2:
            return {"message": "True/False question must have exactly two answers."}, 400
        choice = Choice(
            question_id=question.id,
            text=text,
            is_correct=parse_form_bool(args.get("is_correct")),
        )
        db.session.add(choice)
        db.session.commit()
        return {
            "id": choice.id,
            "question_id": choice.question_id,
            "text": choice.text,
            "is_correct": choice.is_correct,
        }, 201


# ----- Create: Bulk answers -----
@answer_ns.route("/<int:question_id>/answers/bulk")
class QuestionAnswersBulk(Resource):
    @answer_ns.expect(bulk_answers_parser)
    @answer_ns.response(201, "Created")
    @answer_ns.response(400, "Validation error")
    @answer_ns.response(404, "Question not found")
    def post(self, question_id):
        """Add multiple answers using form fields: text_1, is_correct_1, text_2, is_correct_2, ... (up to 5). Replaces existing."""
        question = Question.query.get_or_404(question_id)
        args = bulk_answers_parser.parse_args()
        answers_payload = []
        for i in range(1, 6):
            text = trim_str(args.get(f"text_{i}"))
            if text is None or text == "":
                continue
            answers_payload.append({
                "text": text,
                "is_correct": parse_form_bool(args.get(f"is_correct_{i}")),
            })
        result, status = create_bulk_answers(question, answers_payload)
        return result, status
