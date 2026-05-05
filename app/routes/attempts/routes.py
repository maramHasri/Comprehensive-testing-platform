"""
 Attempts / Submissions — Start and list quiz attempts (student submissions).
User journey: students take quizzes and submit attempts; teachers view results.
"""
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Quiz, QuizAttempt, User
from app.utils.iam_helpers import user_has_any_role

attempt_ns = Namespace(
    " Attempts / Submissions",
    description="Start a quiz attempt and list attempts. Students submit answers; results are stored here.",
)

attempt_response_model = attempt_ns.model(
    "AttemptResponse",
    {
        "id": fields.Integer,
        "quiz_id": fields.Integer,
        "student_id": fields.Integer,
        "started_at": fields.DateTime,
        "submitted_at": fields.DateTime,
        "status": fields.String,
        "score": fields.Float,
    },
)


def _current_user_id():
    try:
        uid = get_jwt_identity()
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None


# ----- Create: Start attempt -----
@attempt_ns.route("/<int:quiz_id>/attempts")
class QuizAttemptsList(Resource):
    @attempt_ns.response(201, "Attempt started", attempt_response_model)
    @attempt_ns.response(401, "Not authenticated")
    @attempt_ns.response(404, "Quiz not found")
    @jwt_required()
    def post(self, quiz_id):
        """Start a new quiz attempt (student). Creates an in_progress attempt. Use JWT as student."""
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return {"message": "Quiz not found."}, 404
        if quiz.status != "published":
            return {"message": "Quiz is not published."}, 400
        current_user_id = _current_user_id()
        if current_user_id is None:
            return {"message": "Authentication required."}, 401
        user = User.query.get(current_user_id)
        if not user or not user_has_any_role(user, "student"):
            return {"message": "Only students can start quiz attempts."}, 403
        total_seconds = quiz.total_time_seconds or 0
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            student_id=current_user_id,
            status="in_progress",
            remaining_time=total_seconds,
        )
        db.session.add(attempt)
        db.session.commit()
        return {
            "id": attempt.id,
            "quiz_id": attempt.quiz_id,
            "student_id": attempt.student_id,
            "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
            "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
            "status": attempt.status,
            "score": attempt.score,
        }, 201

    @attempt_ns.response(404, "Quiz not found")
    def get(self, quiz_id):
        """List attempts for this quiz. (Teachers see all; students could be limited to own — extend as needed.)"""
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return {"message": "Quiz not found."}, 404
        attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id).order_by(QuizAttempt.started_at.desc()).all()
        return [
            {
                "id": a.id,
                "quiz_id": a.quiz_id,
                "student_id": a.student_id,
                "started_at": a.started_at.isoformat() if a.started_at else None,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                "status": a.status,
                "score": a.score,
            }
            for a in attempts
        ], 200
