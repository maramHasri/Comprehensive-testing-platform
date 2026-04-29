from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Exam, Provider
from app.utils.rbac import roles_required

exams_ns = Namespace("Exams", description="Provider-owned exams")

exam_parser = reqparse.RequestParser()
exam_parser.add_argument("provider_id", type=int, required=True, location=("json", "form"))
exam_parser.add_argument("title", type=str, required=True, location=("json", "form"))
exam_parser.add_argument("description", type=str, required=False, location=("json", "form"))
exam_parser.add_argument("duration", type=int, required=True, location=("json", "form"))


@exams_ns.route("")
class ExamCollection(Resource):
    @jwt_required()
    @roles_required("provider_admin", "instructor", "admin")
    @exams_ns.expect(exam_parser)
    def post(self):
        payload = exam_parser.parse_args()
        provider = Provider.query.get(payload.get("provider_id"))
        if provider is None:
            return {"message": "Provider not found."}, 404
        exam = Exam(
            provider_id=provider.id,
            title=(payload.get("title") or "").strip(),
            description=(payload.get("description") or "").strip() or None,
            duration=int(payload.get("duration")),
        )
        db.session.add(exam)
        db.session.commit()
        return {"id": exam.id, "provider_id": exam.provider_id, "title": exam.title}, 201
