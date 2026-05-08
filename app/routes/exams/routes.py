from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Exam, Organization, User
from app.models.membership import MembershipRole
from app.utils.iam_helpers import user_has_any_role

exams_ns = Namespace("Exams", description="Organization-owned exams")

exam_parser = reqparse.RequestParser()
exam_parser.add_argument("organization_id", type=int, required=True, location=("json", "form"))
exam_parser.add_argument("title", type=str, required=True, location=("json", "form"))
exam_parser.add_argument("description", type=str, required=False, location=("json", "form"))
exam_parser.add_argument("duration", type=int, required=True, location=("json", "form"))


@exams_ns.route("")
class ExamCollection(Resource):
    @jwt_required()
    @exams_ns.expect(exam_parser)
    def post(self):
        payload = exam_parser.parse_args()
        identity = get_jwt_identity()
        if identity is None or not str(identity).isdigit():
            return {"message": "A user-account token is required."}, 403
        user = User.query.get(int(identity))
        if user is None:
            return {"message": "User not found."}, 404
        if not user_has_any_role(user, MembershipRole.SUPER_ADMIN.value, MembershipRole.TEACHER.value):
            return {"message": "Only organization admins/teachers can create exams."}, 403
        organization = Organization.query.get(payload.get("organization_id"))
        if organization is None:
            return {"message": "Organization not found."}, 404
        exam = Exam(
            organization_id=organization.id,
            title=(payload.get("title") or "").strip(),
            description=(payload.get("description") or "").strip() or None,
            duration=int(payload.get("duration")),
        )
        db.session.add(exam)
        db.session.commit()
        return {"id": exam.id, "organization_id": exam.organization_id, "title": exam.title}, 201
