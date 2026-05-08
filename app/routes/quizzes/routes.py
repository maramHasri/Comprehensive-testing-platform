"""
 Quizzes — Create and manage quizzes (draft → publish).
Includes auto-create quiz from a question bank (user's or shared).
"""
# TODO: This routes module contains validation and DB orchestration.
# TODO: Move this business logic to services/question_service.py and services/bank_service.py.
from flask import make_response, jsonify
from flask_restx import Namespace, Resource, fields, reqparse, inputs
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
import uuid
import logging

from app.extensions import db
from app.models import Quiz, Question
from app.repositories.user_repository import get_user_by_id
from app.services.quiz_service import (
    recalculate_question_scores,
    validate_quiz_for_publish,
)
from app.utils.localization import get_current_lang
from app.utils.request_validation import trim_str
from app.utils.iam_helpers import user_has_any_role


def jwt_allows_exam_provider(jwt_data: dict) -> bool:
    primary = jwt_data.get("role")
    extra = jwt_data.get("roles") or []
    bucket: set[str] = set()
    if isinstance(primary, str):
        bucket.add(primary.strip().lower())
    bucket.update(str(r).strip().lower() for r in extra if isinstance(r, str))
    return not bucket.isdisjoint({"provider", "exam provider", "instructor"})

logger = logging.getLogger(__name__)

quiz_ns = Namespace(
    " Quizzes",
    description="Create and manage quizzes. Use form fields. Auto-create from a question bank below.",
)

# ----- Form parsers -----
quiz_create_parser = reqparse.RequestParser()
quiz_create_parser.add_argument("title", type=str, required=True, location="form", help="Quiz title (required)")
quiz_create_parser.add_argument("description", type=str, location="form", help="Optional description")
quiz_create_parser.add_argument("start_at", type=str, location="form", help="When quiz becomes available (ISO 8601)")
quiz_create_parser.add_argument("end_at", type=str, location="form", help="When quiz closes (ISO 8601)")
quiz_create_parser.add_argument("total_time_seconds", type=int, location="form", help="Global duration in seconds")
quiz_create_parser.add_argument("total_score", type=int, required=True, location="form", help="Total points e.g. 80 (required)")
quiz_create_parser.add_argument("equally_weighted", type=inputs.boolean, default=True, location="form", help="Backend recalculates scores")
quiz_create_parser.add_argument("free_navigation", type=inputs.boolean, default=True, location="form", help="Jump any question")
quiz_create_parser.add_argument("timed_scope", type=str, default="quiz", location="form", choices=("quiz", "question", "none"), help="quiz | question | none")

# Create quiz FROM question bank (accept form, JSON body, or query params)
from_bank_parser = reqparse.RequestParser()
from_bank_parser.add_argument("question_bank_id", type=int, required=True, location=("form", "json", "query"), help="Question bank ID (required)")
from_bank_parser.add_argument("title", type=str, required=True, location=("form", "json", "query"), help="Quiz title (required)")
from_bank_parser.add_argument("description", type=str, location=("form", "json", "query"), help="Optional description")
from_bank_parser.add_argument("total_score", type=int, default=100, location=("form", "json", "query"), help="Total points (default 100)")
from_bank_parser.add_argument("equally_weighted", type=inputs.boolean, default=True, location=("form", "json", "query"), help="Equally weight questions")
from_bank_parser.add_argument("free_navigation", type=inputs.boolean, default=True, location=("form", "json", "query"), help="Free navigation")
from_bank_parser.add_argument("timed_scope", type=str, default="quiz", location=("form", "json", "query"), choices=("quiz", "question", "none"), help="Timed scope")
from_bank_parser.add_argument("total_time_seconds", type=int, location=("form", "json", "query"), help="Total time in seconds (optional)")
from_bank_parser.add_argument("number_of_questions", type=int, required=True, location=("form", "json", "query"), help="How many questions from the bank to add (required)")

quiz_patch_parser = reqparse.RequestParser()
quiz_patch_parser.add_argument("status", type=str, required=True, location="form", choices=("draft", "published"), help="draft or published")

question_create_parser = reqparse.RequestParser()
question_create_parser.add_argument("text", type=str, required=True, location="form", help="Question text (required)")
question_create_parser.add_argument("type", type=str, required=True, location="form", choices=("mcq", "true_false", "essay"), help="mcq | true_false | essay")
question_create_parser.add_argument("score", type=float, location="form", help="Points (ignored if quiz equally_weighted)")
question_create_parser.add_argument("time_limit_seconds", type=int, location="form", help="Per-question time limit")
question_create_parser.add_argument("order_index", type=int, required=True, location="form", help="Order in quiz (1, 2, 3...)")

quiz_response_model = quiz_ns.model(
    "QuizResponse",
    {
        "id": fields.Integer,
        "title": fields.String,
        "description": fields.String,
        "status": fields.String,
        "access_code": fields.String,
        "quiz_url": fields.String,
        "total_score": fields.Integer,
        "equally_weighted": fields.Boolean,
        "free_navigation": fields.Boolean,
        "timed_scope": fields.String,
    },
)
error_model = quiz_ns.model("Error", {"message": fields.String, "error": fields.String})


def _parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    else:
        return None
    if dt.tzinfo is not None:
        from datetime import timezone
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _current_user_id():
    try:
        uid = get_jwt_identity()
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None


# ----- Create quiz from question bank (auto) -----
@quiz_ns.route("/from-bank")
class CreateQuizFromBank(Resource):
    @jwt_required()
    @quiz_ns.expect(from_bank_parser)
    @quiz_ns.response(201, "Quiz created", quiz_response_model)
    @quiz_ns.response(400, "Validation error or bank empty", error_model)
    @quiz_ns.response(401, "Not authenticated", error_model)
    @quiz_ns.response(403, "Exam providers only", error_model)
    @quiz_ns.response(404, "Question bank not found", error_model)
    def post(self):
        """Create quiz from bank. Send question_bank_id, title, number_of_questions. Responses follow Accept-Language (en/ar). Exam provider only."""
        from app.services.create_quiz_service import create_quiz_from_bank as create_from_bank_svc

        lang = get_current_lang()
        user_id_str = get_jwt_identity()
        if not user_id_str:
            return {"message": get_message("COMMON_AUTH_REQUIRED", lang)}, 401
        jwt_data = get_jwt()
        if not jwt_allows_exam_provider(jwt_data):
            return {"message": get_message("QUIZ_TEACHERS_ONLY", lang)}, 403
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            return {"message": get_message("COMMON_INVALID_TOKEN", lang)}, 401
        creator = get_user_by_id(user_id)
        if not creator or not user_has_any_role(creator, "provider", "exam provider", "instructor"):
            return {"message": get_message("QUIZ_TEACHERS_ONLY", lang)}, 403

        args = from_bank_parser.parse_args()
        result, status = create_from_bank_svc(
            creator_id=creator.id,
            bank_id=args.get("question_bank_id"),
            title=trim_str(args.get("title")),
            number_of_questions=args.get("number_of_questions"),
            description=trim_str(args.get("description")) or None,
            total_score=args.get("total_score"),
            equally_weighted=args.get("equally_weighted") if args.get("equally_weighted") is not None else True,
            free_navigation=args.get("free_navigation") if args.get("free_navigation") is not None else True,
            timed_scope=(trim_str(args.get("timed_scope")) or "quiz").lower(),
            total_time_seconds=args.get("total_time_seconds"),
            lang=lang,
        )
        return result, status


# ----- Create quiz (manual) -----
@quiz_ns.route("")
class QuizCreate(Resource):
    @jwt_required()
    @quiz_ns.expect(quiz_create_parser)
    @quiz_ns.marshal_with(quiz_response_model, code=201)
    @quiz_ns.response(400, "Validation error", error_model)
    @quiz_ns.response(401, "Unauthorized", error_model)
    @quiz_ns.response(403, "Forbidden (not an exam provider)", error_model)
    @quiz_ns.response(500, "Server error", error_model)
    def post(self):
        """Create a new empty quiz (Exam provider only). Add questions manually or use POST /from-bank to create from a question bank."""
        try:
            lang = get_current_lang()
            user_id_str = get_jwt_identity()
            if not user_id_str:
                return {"message": get_message("COMMON_AUTH_REQUIRED", lang)}, 401
            jwt_data = get_jwt()
            if not jwt_allows_exam_provider(jwt_data):
                return {"message": get_message("QUIZ_TEACHERS_ONLY", lang)}, 403
            try:
                user_id = int(user_id_str)
            except (ValueError, TypeError):
                return {"message": get_message("COMMON_INVALID_TOKEN", lang)}, 401
            creator = get_user_by_id(user_id)
            if not creator or not user_has_any_role(creator, "provider", "exam provider", "instructor"):
                return {"message": get_message("QUIZ_TEACHERS_ONLY", lang)}, 403
            args = quiz_create_parser.parse_args()
            total_score = int(args.get("total_score") or 0)
            if total_score <= 0:
                return {"message": get_message("QUIZ_TOTAL_SCORE_INVALID", lang)}, 400
            timed_scope = (trim_str(args.get("timed_scope")) or "quiz").lower()
            if timed_scope not in ("quiz", "question", "none"):
                timed_scope = "quiz"
            title = trim_str(args.get("title"))
            if not title:
                return {"message": get_message("QUIZ_TITLE_REQUIRED", lang)}, 400
            quiz = Quiz(
                title=title,
                description=trim_str(args.get("description")) or None,
                creator_id=creator.id,
                start_at=_parse_dt(args.get("start_at")),
                end_at=_parse_dt(args.get("end_at")),
                total_time_seconds=args.get("total_time_seconds"),
                total_score=total_score,
                equally_weighted=args.get("equally_weighted") if args.get("equally_weighted") is not None else True,
                free_navigation=args.get("free_navigation") if args.get("free_navigation") is not None else True,
                timed_scope=timed_scope,
                status="draft",
                access_code=str(uuid.uuid4()),
            )
            db.session.add(quiz)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.exception("Error creating quiz: %s", str(e))
            return make_response(jsonify({"message": "Quiz creation failed.", "error": str(e)}), 500)
        return {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "status": quiz.status,
            "access_code": quiz.access_code,
            "quiz_url": f"http://localhost:5000/quiz/{quiz.access_code}",
            "total_score": quiz.total_score,
            "equally_weighted": quiz.equally_weighted,
            "free_navigation": quiz.free_navigation,
            "timed_scope": quiz.timed_scope,
        }, 201


# ----- Read one, Update -----
@quiz_ns.route("/<int:quiz_id>")
class QuizDetail(Resource):
    @quiz_ns.marshal_with(quiz_response_model)
    @quiz_ns.response(404, "Quiz not found")
    def get(self, quiz_id):
        """Get one quiz by ID."""
        quiz = Quiz.query.get_or_404(quiz_id)
        return {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "status": quiz.status,
            "access_code": quiz.access_code,
            "quiz_url": f"http://localhost:5000/quiz/{quiz.access_code}" if quiz.access_code else None,
            "total_score": int(quiz.total_score),
            "equally_weighted": quiz.equally_weighted,
            "free_navigation": quiz.free_navigation,
            "timed_scope": quiz.timed_scope,
        }

    @quiz_ns.expect(quiz_patch_parser)
    @quiz_ns.response(404, "Quiz not found")
    def patch(self, quiz_id):
        """Update quiz. Use form field status: published or draft."""
        quiz = Quiz.query.get_or_404(quiz_id)
        args = quiz_patch_parser.parse_args()
        status = trim_str(args.get("status"))
        if status == "published":
            ok, msg = validate_quiz_for_publish(quiz)
            if not ok:
                return {"message": msg}, 400
            quiz.status = "published"
        elif status == "draft":
            quiz.status = "draft"
        db.session.commit()
        return {"id": quiz.id, "status": quiz.status}, 200


# ----- Questions under quiz -----
@quiz_ns.route("/<int:quiz_id>/questions")
class QuizQuestions(Resource):
    @quiz_ns.expect(question_create_parser)
    @quiz_ns.response(201, "Created")
    @quiz_ns.response(400, "Validation error")
    @quiz_ns.response(404, "Quiz not found")
    def post(self, quiz_id):
        """Add a question to the quiz manually."""
        quiz = Quiz.query.get_or_404(quiz_id)
        args = question_create_parser.parse_args()
        text = trim_str(args.get("text"))
        if not text:
            return {"message": "Question text is required."}, 400
        qtype = (trim_str(args.get("type")) or "").lower()
        if qtype not in ("mcq", "true_false", "essay"):
            return {"message": "Type must be mcq, true_false, or essay."}, 400
        score = args.get("score")
        if quiz.equally_weighted:
            score = None
        else:
            score = float(score) if score is not None else 1.0
        order_index = args.get("order_index")
        if order_index is None:
            return {"message": "order_index is required."}, 400
        question = Question(
            quiz_id=quiz.id,
            content=text,
            type=qtype,
            points=score or 1.0,
            base_time=args.get("time_limit_seconds"),
            order_index=int(order_index),
        )
        db.session.add(question)
        db.session.flush()
        recalculate_question_scores(quiz)
        return {
            "id": question.id,
            "quiz_id": question.quiz_id,
            "text": question.content,
            "type": question.type,
            "score": question.points,
            "time_limit_seconds": question.base_time,
            "order_index": question.order_index,
        }, 201

    @quiz_ns.response(404, "Quiz not found")
    def get(self, quiz_id):
        """List questions for this quiz."""
        quiz = Quiz.query.get_or_404(quiz_id)
        questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order_index).all()
        return [
            {
                "id": q.id,
                "quiz_id": q.quiz_id,
                "text": q.content,
                "type": q.type,
                "score": q.points,
                "time_limit_seconds": q.base_time,
                "order_index": q.order_index,
                "original_owner_id": q.attribution.original_owner_id if q.attribution else None,
                "original_bank_id": q.attribution.original_bank_id if q.attribution else None,
                "original_question_id": q.attribution.original_question_id if q.attribution else q.original_question_id,
            }
            for q in questions
        ], 200


@quiz_ns.route("/<int:quiz_id>/questions/<int:question_id>")
class QuizQuestionDetail(Resource):
    @quiz_ns.response(404, "Quiz or question not found")
    def delete(self, quiz_id, question_id):
        """Remove a question from the quiz."""
        quiz = Quiz.query.get_or_404(quiz_id)
        question = Question.query.filter_by(id=question_id, quiz_id=quiz.id).first_or_404()
        db.session.delete(question)
        db.session.commit()
        recalculate_question_scores(quiz)
        return {"message": "Question removed."}, 200


