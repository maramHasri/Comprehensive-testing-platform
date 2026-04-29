from typing import Any

from flask_restx import Namespace, Resource, reqparse

from app.extensions import db
from app.models import Institution

educational_institutions_ns = Namespace("Educational Institutions", description="Educational institution trust and verification")

institution_profile_parser = reqparse.RequestParser()
institution_profile_parser.add_argument("name", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("type", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("country", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("city", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("email", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("password", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("phone", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("responsible_person_name", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("short_description", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("official_website_domain", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("institutional_email", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("logo", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("year_of_establishment", type=int, required=False, location=("json", "form"))
institution_profile_parser.add_argument("additional_program_details", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("social_links", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("official_document", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("active_website", type=str, required=False, location=("json", "form"))
institution_profile_parser.add_argument("government_reference_link", type=str, required=False, location=("json", "form"))

institution_approval_parser = reqparse.RequestParser()
institution_approval_parser.add_argument("admin_approval", type=bool, required=True, location=("json", "form"))


def evaluate_institution_trust_level(institution: Institution) -> str:
    required_values: list[Any] = [
        institution.name,
        institution.type,
        institution.country,
        institution.city,
        institution.email,
        institution.password,
        institution.phone,
        institution.responsible_person_name,
        institution.short_description,
    ]
    has_basic_fields: bool = all(value not in (None, "") for value in required_values)
    optional_values: list[Any] = [
        institution.official_website_domain,
        institution.institutional_email,
        institution.logo,
        institution.year_of_establishment,
        institution.additional_program_details,
        institution.social_links,
    ]
    optional_count: int = sum(1 for value in optional_values if value not in (None, ""))
    has_trusted_fields: bool = optional_count >= 2
    has_verified_fields: bool = all(
        [
            bool(institution.official_document),
            bool(institution.institutional_email),
            bool(institution.phone),
            bool(institution.active_website),
            bool(institution.government_reference_link),
            bool(institution.admin_approval),
        ]
    )
    if has_verified_fields:
        return "VERIFIED"
    if has_basic_fields and has_trusted_fields:
        return "TRUSTED"
    return "BASIC"


@educational_institutions_ns.route("/<string:institution_email>/profile")
class EducationalInstitutionProfile(Resource):
    @educational_institutions_ns.expect(institution_profile_parser)
    def put(self, institution_email: str):
        institution: Institution | None = Institution.query.get(institution_email)
        if institution is None:
            return {"message": "Institution not found."}, 404
        payload = institution_profile_parser.parse_args()
        for field_name in payload:
            field_value = payload.get(field_name)
            if field_value is None:
                continue
            setattr(institution, field_name, field_value)
        institution.trust_level = evaluate_institution_trust_level(institution)
        db.session.commit()
        return {"email": institution.email, "trust_level": institution.trust_level}, 200


@educational_institutions_ns.route("/<string:institution_email>/trust-level")
class EducationalInstitutionTrustLevel(Resource):
    def get(self, institution_email: str):
        institution: Institution | None = Institution.query.get(institution_email)
        if institution is None:
            return {"message": "Institution not found."}, 404
        institution.trust_level = evaluate_institution_trust_level(institution)
        db.session.commit()
        return {"email": institution.email, "trust_level": institution.trust_level}, 200


@educational_institutions_ns.route("/<string:institution_email>/admin-approval")
class EducationalInstitutionAdminApproval(Resource):
    @educational_institutions_ns.expect(institution_approval_parser)
    def put(self, institution_email: str):
        institution: Institution | None = Institution.query.get(institution_email)
        if institution is None:
            return {"message": "Institution not found."}, 404
        payload = institution_approval_parser.parse_args()
        institution.admin_approval = bool(payload.get("admin_approval"))
        institution.trust_level = evaluate_institution_trust_level(institution)
        db.session.commit()
        return {"email": institution.email, "admin_approval": institution.admin_approval, "trust_level": institution.trust_level}, 200
