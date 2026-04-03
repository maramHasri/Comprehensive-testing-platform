"""
Answers API — Handles HTTP layer only.
Delegates all logic to services.
"""

from flask_restx import Namespace, Resource, reqparse, inputs
from flask import request, jsonify

from app.services.answer_service import (
    add_single_answer,
    create_bulk_answers,
    get_answers,
    update_question_answers,
)
from app.utils.request_validation import trim_str, parse_form_bool

answer_ns = Namespace(
    "answers",
    description="Manage question answers (choices)."
)

# ---------------- Parsers ----------------
single_answer_parser = reqparse.RequestParser()
single_answer_parser.add_argument("text", type=str, required=True, location="form")
single_answer_parser.add_argument("is_correct", type=inputs.boolean, default=False, location="form")


def bulk_parser():
    p = reqparse.RequestParser()
    for i in range(1, 6):
        p.add_argument(f"text_{i}", type=str, location="form")
        p.add_argument(f"is_correct_{i}", type=inputs.boolean, default=False, location="form")
    return p

bulk_answers_parser = bulk_parser()

# ---------------- Routes ----------------

@answer_ns.route("/<int:question_id>/answers")
class QuestionAnswers(Resource):

    def get(self, question_id):
        """
        List all answers for a question
        """
        return get_answers(question_id)

    @answer_ns.expect(single_answer_parser)
    def post(self, question_id):
        """
        Add single answer
        """
        args = single_answer_parser.parse_args()

        result, status = add_single_answer(
            question_id=question_id,
            text=trim_str(args.get("text")),
            is_correct=parse_form_bool(args.get("is_correct")),
        )

        return result, status


@answer_ns.route("/<int:question_id>/answers/bulk")
class QuestionAnswersBulk(Resource):

    @answer_ns.expect(bulk_answers_parser)
    def post(self, question_id):
        """
        Bulk replace answers (max 5)
        """
        args = bulk_answers_parser.parse_args()

        answers = []
        for i in range(1, 6):
            text = trim_str(args.get(f"text_{i}"))
            if text:
                answers.append({
                    "text": text,
                    "is_correct": parse_form_bool(args.get(f"is_correct_{i}")),
                })

        result, status = create_bulk_answers(question_id, answers)

        return result, status


@answer_ns.route("/<int:question_id>/answers/update")
class QuestionAnswersUpdate(Resource):

    def put(self, question_id):
        """
        Replace answers using JSON body
        """
        data = request.json or []

        result = update_question_answers(question_id, data)

        return jsonify(result), 200