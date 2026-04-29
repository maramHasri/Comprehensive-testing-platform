from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, reqparse

from app.services.auth_service import (
    login_super_admin as login_super_admin_svc,
    get_all_institutions as get_all_institutions_svc,
    get_all_users as get_all_users_svc,
    set_institution_admin_approval as set_institution_admin_approval_svc,
)
from app.utils.localization import get_current_lang
from app.utils.rbac import roles_required

super_admin_ns = Namespace("Super Admin", description="Super admin authentication and institution approval")

login_parser = reqparse.RequestParser()
login_parser.add_argument("email", type=str, required=True, location=("args", "json", "form"))
login_parser.add_argument("password", type=str, required=True, location=("args", "json", "form"))

approval_parser = reqparse.RequestParser()
approval_parser.add_argument("admin_approval", type=bool, required=True, location=("args", "json", "form"))


@super_admin_ns.route("/login")
class SuperAdminLogin(Resource):
    @super_admin_ns.doc(description="Login as Super Admin")
    @super_admin_ns.expect(login_parser)
    @super_admin_ns.response(401, "Invalid Super Admin credentials")
    def post(self):
        args = login_parser.parse_args()
        result, status = login_super_admin_svc(
            email=args.get("email"),
            password=args.get("password"),
            lang=get_current_lang(),
        )
        return result, status


@super_admin_ns.route("/institutions")
class SuperAdminInstitutions(Resource):
    @jwt_required()
    @roles_required("super_admin", "super admin")
    @super_admin_ns.doc(description="Get all registered institutions")
    def get(self):
        result, status = get_all_institutions_svc()
        return result, status


@super_admin_ns.route("/users")
class SuperAdminUsers(Resource):
    @jwt_required()
    @roles_required("super_admin", "super admin")
    @super_admin_ns.doc(description="Get all users in the system")
    def get(self):
        result, status = get_all_users_svc()
        return result, status


@super_admin_ns.route("/institutions/<int:institution_id>/approval")
class SuperAdminInstitutionApproval(Resource):
    @jwt_required()
    @roles_required("super_admin", "super admin")
    @super_admin_ns.expect(approval_parser)
    @super_admin_ns.doc(description="Set institution admin_approval")
    def post(self, institution_id: int):
        args = approval_parser.parse_args()
        result, status = set_institution_admin_approval_svc(
            institution_id=institution_id,
            admin_approval=bool(args.get("admin_approval")),
        )
        return result, status
