from typing import Any

from flask_restx import Namespace, Resource, reqparse

from app.extensions import db
from app.models import Provider

exam_providers_ns = Namespace("Exam Providers", description="Individual exam provider trust and verification")

provider_profile_parser = reqparse.RequestParser()
provider_profile_parser.add_argument("full_name", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("email", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("password", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("country", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("specialization", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("years_of_experience", type=int, required=False, location=("json", "form"))
provider_profile_parser.add_argument("phone", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("account_type", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("profile_picture", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("cv", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("linkedin_profile", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("educational_certificates", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("current_workplace", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("affiliated_institution_name", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("official_educational_certificate", type=str, required=False, location=("json", "form"))
provider_profile_parser.add_argument("verified_affiliation_with_institution", type=bool, required=False, location=("json", "form"))

provider_approval_parser = reqparse.RequestParser()
provider_approval_parser.add_argument("admin_approval", type=bool, required=True, location=("json", "form"))


def evaluate_provider_trust_level(provider: Provider) -> str:
    required_values: list[Any] = [
        provider.full_name,
        provider.email,
        provider.password,
        provider.country,
        provider.specialization,
        provider.years_of_experience,
        provider.phone,
        provider.account_type,
    ]
    has_basic_fields: bool = all(value not in (None, "") for value in required_values)
    optional_values: list[Any] = [
        provider.profile_picture,
        provider.cv,
        provider.linkedin_profile,
        provider.educational_certificates,
        provider.current_workplace,
        provider.affiliated_institution_name,
    ]
    optional_count: int = sum(1 for value in optional_values if value not in (None, ""))
    has_trusted_fields: bool = optional_count >= 2
    has_strong_professional_profile: bool = bool(provider.linkedin_profile) or bool(provider.current_workplace)
    has_verified_fields: bool = all(
        [
            bool(provider.official_educational_certificate),
            bool(provider.admin_approval),
            has_strong_professional_profile,
            bool(provider.verified_affiliation_with_institution),
        ]
    )
    if has_verified_fields:
        return "VERIFIED"
    if has_basic_fields and has_trusted_fields:
        return "TRUSTED"
    return "BASIC"


@exam_providers_ns.route("/<int:provider_id>/profile")
class ExamProviderProfile(Resource):
    @exam_providers_ns.expect(provider_profile_parser)
    def put(self, provider_id: int):
        provider: Provider | None = Provider.query.get(provider_id)
        if provider is None:
            return {"message": "Provider not found."}, 404
        payload = provider_profile_parser.parse_args()
        for field_name in payload:
            field_value = payload.get(field_name)
            if field_value is None:
                continue
            setattr(provider, field_name, field_value)
        provider.trust_level = evaluate_provider_trust_level(provider)
        db.session.commit()
        return {"provider_id": provider.id, "trust_level": provider.trust_level}, 200


@exam_providers_ns.route("/<int:provider_id>/trust-level")
class ExamProviderTrustLevel(Resource):
    def get(self, provider_id: int):
        provider: Provider | None = Provider.query.get(provider_id)
        if provider is None:
            return {"message": "Provider not found."}, 404
        provider.trust_level = evaluate_provider_trust_level(provider)
        db.session.commit()
        return {"provider_id": provider.id, "trust_level": provider.trust_level}, 200


@exam_providers_ns.route("/<int:provider_id>/admin-approval")
class ExamProviderAdminApproval(Resource):
    @exam_providers_ns.expect(provider_approval_parser)
    def put(self, provider_id: int):
        provider: Provider | None = Provider.query.get(provider_id)
        if provider is None:
            return {"message": "Provider not found."}, 404
        payload = provider_approval_parser.parse_args()
        provider.admin_approval = bool(payload.get("admin_approval"))
        provider.trust_level = evaluate_provider_trust_level(provider)
        db.session.commit()
        return {"provider_id": provider.id, "admin_approval": provider.admin_approval, "trust_level": provider.trust_level}, 200
