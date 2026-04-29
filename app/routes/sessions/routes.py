from datetime import datetime

from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Exam, ExamSession, ExamSessionLog

sessions_ns = Namespace("Sessions", description="Exam session tracking and proctoring logs")

start_session_parser = reqparse.RequestParser()
start_session_parser.add_argument("exam_id", type=int, required=True, location=("json", "form"))

log_event_parser = reqparse.RequestParser()
log_event_parser.add_argument("event_type", type=str, required=True, location=("json", "form"))
log_event_parser.add_argument("metadata", type=dict, required=False, location="json")


@sessions_ns.route("")
class SessionCollection(Resource):
    @jwt_required()
    @sessions_ns.expect(start_session_parser)
    def post(self):
        payload = start_session_parser.parse_args()
        exam = Exam.query.get(payload.get("exam_id"))
        if exam is None:
            return {"message": "Exam not found."}, 404
        user_id = int(get_jwt_identity())
        session = ExamSession(exam_id=exam.id, user_id=user_id, status="in_progress")
        db.session.add(session)
        db.session.commit()
        return {"id": session.id, "exam_id": session.exam_id, "user_id": session.user_id}, 201


@sessions_ns.route("/<int:session_id>/logs")
class SessionLogsCollection(Resource):
    @jwt_required()
    @sessions_ns.expect(log_event_parser)
    def post(self, session_id: int):
        payload = log_event_parser.parse_args()
        session = ExamSession.query.get(session_id)
        if session is None:
            return {"message": "Session not found."}, 404
        user_id = int(get_jwt_identity())
        if session.user_id != user_id:
            return {"message": "Forbidden. Session does not belong to current user."}, 403
        if session.status != "in_progress":
            return {"message": "Cannot log events for inactive session."}, 400
        log = ExamSessionLog(
            session_id=session.id,
            event_type=(payload.get("event_type") or "").strip().lower(),
            timestamp=datetime.utcnow(),
            event_metadata=payload.get("metadata"),
        )
        db.session.add(log)
        db.session.commit()
        return {"id": log.id, "session_id": log.session_id, "event_type": log.event_type}, 201
