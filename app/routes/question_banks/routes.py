"""
 Question Banks — Create and manage question banks (public / protected / private).
Uses form-style inputs in Swagger so question text with quotes/newlines is safe.
"""
# TODO: This module mixes HTTP handlers with DB querying and access rules.
# TODO: Move business logic to services/bank_service.py and keep only route wiring here.
import json

from flask_restx import Namespace, Resource, fields, reqparse, inputs
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from flask import request
from sqlalchemy import or_

from app.extensions import db
from app.models import QuestionBank, Question, Choice, User
from app.models.question_bank import ACCESS_PUBLIC, ACCESS_PROTECTED, ACCESS_PRIVATE, ACCESS_TYPES
from app.utils.request_validation import (
    trim_str,
    validate_required_str,
    MIN_QUESTION_TEXT_LENGTH,
    MAX_QUESTION_TEXT_LENGTH,
)
from app.routes.question_banks.service import (
    create_question_with_answers,
    ValidationError,
    PermissionError,
    NotFoundError,
)
from app.repositories.bank_version_repository import get_versions_by_bank
from app.repositories.question_repository import get_questions_by_version
from app.services.question_bank.bank_access_service import (
    BankAccessError,
    get_user_accessible_version,
    upgrade_bank,
)
from app.services.question_bank.bank_version_service import (
    BankVersionServiceError,
    create_new_version,
)

question_bank_ns = Namespace(
    " Question Banks",
    description="Create and manage question banks. Use form fields below (no raw JSON).",
)


def _current_user_id():
    try:
        uid = get_jwt_identity()
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None


def _can_view_bank(bank, current_user_id):
    if bank.access_type == ACCESS_PUBLIC or bank.access_type == ACCESS_PROTECTED:
        return True
    if bank.access_type == ACCESS_PRIVATE:
        return current_user_id is not None and bank.owner_id == current_user_id
    return False


def _show_owner_in_response(bank, current_user_id):
    if bank.access_type == ACCESS_PROTECTED:
        return True
    if bank.access_type == ACCESS_PRIVATE and current_user_id is not None and bank.owner_id == current_user_id:
        return True
    return False


def _ensure_can_edit_bank(bank_id):
    bank = QuestionBank.query.get(bank_id)
    if not bank:
        return None, ({"message": "Question bank not found."}, 404)
    current_user_id = _current_user_id()
    if current_user_id is None:
        return None, ({"message": "Authentication required."}, 401)
    if bank.owner_id != current_user_id:
        return None, ({"message": "Only the owner can edit or delete this question bank."}, 403)
    return bank, None


# ----- Form parsers (form-style in Swagger) -----
bank_create_parser = reqparse.RequestParser()
bank_create_parser.add_argument("title", type=str, required=True, location="form", help="Bank title (required)")
bank_create_parser.add_argument("access_type", type=str, default="private", location="form", choices=("public", "protected", "private"), help="public | protected | private")

bank_update_parser = reqparse.RequestParser()
bank_update_parser.add_argument("title", type=str, location="form", help="New title")
bank_update_parser.add_argument("access_type", type=str, location="form", choices=("public", "protected", "private"), help="public | protected | private")


def _merge_version_create_inputs():
    """Merge form, query, then JSON (JSON wins). reqparse multi-location is unreliable in Swagger."""
    merged = {}
    merged.update(request.form.to_dict())
    merged.update(request.args.to_dict())
    body = request.get_json(silent=True)
    if isinstance(body, dict):
        merged.update(body)
    elif body is None and request.data:
        try:
            raw = json.loads(request.data.decode("utf-8-sig"))
            if isinstance(raw, dict):
                merged.update(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, AttributeError):
            pass
    if not merged.get("update_type"):
        forced = request.get_json(force=True, silent=True)
        if isinstance(forced, dict):
            merged.update(forced)
    return merged


# ----- Response / request models -----
answer_response_model = question_bank_ns.model(
    "AnswerInBank",
    {"id": fields.Integer, "text": fields.String, "is_correct": fields.Boolean},
)

answer_create_model = question_bank_ns.model(
    "AnswerCreateInBank",
    {
        "text": fields.String(required=True, description="Answer text"),
        "is_correct": fields.Boolean(
            required=False, description="Is this the correct answer?"
        ),
    },
)

question_create_model = question_bank_ns.model(
    "QuestionCreateInBank",
    {
        "text": fields.String(required=True, description="Question text"),
        "question_type": fields.String(
            required=True, description="Question type: mcq | true_false | essay"
        ),
        "answers": fields.List(
            fields.Nested(answer_create_model),
            required=False,
            description="Optional list of answers for MCQ / true_false questions",
        ),
    },
)

version_create_model = question_bank_ns.model(
    "VersionCreate",
    {
        "update_type": fields.String(
            required=True,
            description="minor or major",
            enum=["minor", "major"],
        ),
        "price": fields.Float(
            required=False,
            description="Price for this version (default 0)",
        ),
    },
)

question_in_bank_model = question_bank_ns.model(
    "QuestionInBank",
    {
        "id": fields.Integer,
        "type": fields.String,
        "content": fields.String,
        "created_by": fields.Integer,
        "original_question_id": fields.Integer,
        "hint": fields.Raw,
        "points": fields.Float,
        "base_time": fields.Raw,
        "answers": fields.List(fields.Nested(answer_response_model)),
    },
)
bank_response_model = question_bank_ns.model(
    "QuestionBankResponse",
    {
        "id": fields.Integer,
        "title": fields.String,
        "access_type": fields.String,
        "owner_id": fields.Integer(description="Present only for protected or own private"),
        "owner_name": fields.String,
        "created_at": fields.DateTime,
        "questions_count": fields.Integer,
    },
)
# ----- Create -----
@question_bank_ns.route("")
class QuestionBankList(Resource):
    @question_bank_ns.expect(bank_create_parser)
    @question_bank_ns.marshal_with(bank_response_model, code=201)
    @question_bank_ns.response(400, "Validation error")
    @question_bank_ns.response(401, "Not authenticated")
    @jwt_required()
    def post(self):
        """Create a new question bank. Fill in form fields; owner is the authenticated user."""
        args = bank_create_parser.parse_args()
        current_user_id = _current_user_id()
        if current_user_id is None:
            return {"message": "Authentication required."}, 401
        title, err = validate_required_str(args.get("title"), "Title", min_len=1)
        if err:
            return {"message": err}, 400
        access_type = (trim_str(args.get("access_type")) or ACCESS_PRIVATE).lower()
        if access_type not in ACCESS_TYPES:
            access_type = ACCESS_PRIVATE
        bank = QuestionBank(
            title=title,
            owner_id=current_user_id,
            access_type=access_type,
            is_public=(access_type == ACCESS_PUBLIC),
        )
        db.session.add(bank)
        db.session.commit()
        # Initialize first version for the new bank.
        create_new_version(
            bank_id=bank.id,
            price=float(bank.base_price or 0.0),
            update_type="major" if bank.is_paid else "minor",
        )
        owner = User.query.get(bank.owner_id)
        return {
            "id": bank.id,
            "title": bank.title,
            "access_type": bank.access_type,
            "owner_id": bank.owner_id,
            "owner_name": owner.name if owner else None,
            "created_at": bank.created_at,
            "questions_count": 0,
        }, 201

    @question_bank_ns.doc(params={"owner_id": "Filter by owner user ID (after visibility)"})
    @question_bank_ns.response(200, "List of banks visible to current user")
    @jwt_required(optional=True)
    def get(self):
        """List question banks. Public/protected visible to all; private only to owner. Auth optional."""
        current_user_id = _current_user_id()
        owner_id_filter = request.args.get("owner_id", type=int)
        query = QuestionBank.query
        if current_user_id is None:
            query = query.filter(QuestionBank.access_type == ACCESS_PUBLIC)
        else:
            query = query.filter(
                or_(
                    QuestionBank.access_type == ACCESS_PUBLIC,
                    QuestionBank.access_type == ACCESS_PROTECTED,
                    (QuestionBank.access_type == ACCESS_PRIVATE) & (QuestionBank.owner_id == current_user_id),
                )
            )
        if owner_id_filter is not None:
            query = query.filter_by(owner_id=owner_id_filter)
        banks = query.order_by(QuestionBank.created_at.desc()).all()
        out = []
        for b in banks:
            show_owner = _show_owner_in_response(b, current_user_id)
            owner = b.owner if hasattr(b, "owner") else User.query.get(b.owner_id)
            out.append({
                "id": b.id,
                "title": b.title,
                "access_type": b.access_type,
                "owner_id": b.owner_id if show_owner else None,
                "owner_name": owner.name if show_owner and owner else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "questions_count": len(b.questions),
            })
        return out, 200


# ----- Read one, Update, Delete -----
@question_bank_ns.route("/<int:bank_id>")
class QuestionBankDetail(Resource):
    @question_bank_ns.response(404, "Bank not found or not visible")
    @jwt_required(optional=True)
    def get(self, bank_id):
        """Get one question bank with all questions and answers. Private banks only visible to owner."""
        bank = QuestionBank.query.get(bank_id)
        if not bank:
            return {"message": "Question bank not found."}, 404
        current_user_id = _current_user_id()
        if not _can_view_bank(bank, current_user_id):
            return {"message": "Question bank not found."}, 404
        accessible_version = get_user_accessible_version(current_user_id, bank.id)
        if accessible_version is None:
            return {"message": "No accessible version found for this user."}, 403
        questions = get_questions_by_version(accessible_version.id)
        questions_data = [
            {
                "id": q.id,
                "type": q.type,
                "content": q.content,
                "created_by": q.created_by,
                "original_question_id": q.original_question_id,
                "hint": q.hint,
                "points": q.points,
                "base_time": q.base_time,
                "bank_version_id": q.bank_version_id,
                "answers": [{"id": c.id, "text": c.text, "is_correct": c.is_correct} for c in q.choices],
            }
            for q in questions
        ]
        show_owner = _show_owner_in_response(bank, current_user_id)
        owner = bank.owner if hasattr(bank, "owner") else User.query.get(bank.owner_id)
        return {
            "id": bank.id,
            "title": bank.title,
            "access_type": bank.access_type,
            "owner_id": bank.owner_id if show_owner else None,
            "owner_name": owner.name if show_owner and owner else None,
            "created_at": bank.created_at.isoformat() if bank.created_at else None,
            "accessible_version": {
                "id": accessible_version.id,
                "version_number": accessible_version.version_number,
                "update_type": accessible_version.update_type,
                "price": accessible_version.price,
            },
            "questions": questions_data,
        }, 200

    @question_bank_ns.expect(bank_update_parser)
    @question_bank_ns.response(401, "Not authenticated")
    @question_bank_ns.response(403, "Only owner can update")
    @jwt_required()
    def patch(self, bank_id):
        """Update a question bank. Use form fields for title and/or access_type."""
        bank, err = _ensure_can_edit_bank(bank_id)
        if err:
            return err
        args = bank_update_parser.parse_args()
        if args.get("title") is not None and trim_str(args["title"]):
            bank.title = trim_str(args["title"])
        if args.get("access_type") is not None:
            at = trim_str(args["access_type"]).lower()
            if at in ACCESS_TYPES:
                bank.access_type = at
                bank.is_public = at == ACCESS_PUBLIC
        db.session.commit()
        return {
            "id": bank.id,
            "title": bank.title,
            "access_type": bank.access_type,
            "owner_id": bank.owner_id,
        }, 200

    @question_bank_ns.response(401, "Not authenticated")
    @question_bank_ns.response(403, "Only owner can delete")
    @jwt_required()
    def delete(self, bank_id):
        """Delete a question bank and all its questions. Only the owner can delete."""
        bank, err = _ensure_can_edit_bank(bank_id)
        if err:
            return err
        db.session.delete(bank)
        db.session.commit()
        return {"message": "Question bank deleted."}, 200


# ----- Questions in bank -----
@question_bank_ns.route("/<int:bank_id>/questions")
class QuestionBankQuestions(Resource):
    @question_bank_ns.response(404, "Bank not found or not visible")
    @jwt_required(optional=True)
    def get(self, bank_id):
        """List questions in this bank (with answers). Visible only if bank is visible to you."""
        bank = QuestionBank.query.get(bank_id)
        if not bank:
            return {"message": "Question bank not found."}, 404
        if not _can_view_bank(bank, _current_user_id()):
            return {"message": "Question bank not found."}, 404
        questions = Question.query.filter_by(bank_id=bank.id).order_by(Question.id).all()
        return [
            {
                "id": q.id,
                "type": q.type,
                "content": q.content,
                "created_by": q.created_by,
                "original_question_id": q.original_question_id,
                "hint": q.hint,
                "points": q.points,
                "base_time": q.base_time,
                "answers": [{"id": c.id, "text": c.text, "is_correct": c.is_correct} for c in q.choices],
            }
            for q in questions
        ], 200

    @question_bank_ns.doc(
        description=(
            "Create a question (and optional answers) in this bank using JSON.\n\n"
            "Example body:\n"
            "{\n"
            '  \"text\": \"Question text\",\n'
            '  \"question_type\": \"mcq\",\n'
            '  \"answers\": [\n'
            
            '    {\"text\": \"Answer 1\", \"is_correct\": false},\n'
            '    {\"text\": \"Answer 2\", \"is_correct\": true}\n'
            "  ]\n"
            "}"
        )
    )
    @question_bank_ns.expect(question_create_model, validate=False)
    @question_bank_ns.response(201, "Created", question_in_bank_model)
    @question_bank_ns.response(400, "Validation error")
    @question_bank_ns.response(401, "Not authenticated")
    @question_bank_ns.response(403, "Only owner can add questions")
    @question_bank_ns.response(404, "Question bank not found")
    @jwt_required()
    def post(self, bank_id):
        """
        Add a questions to this bank using JSON.
        """
        current_user_id = _current_user_id()
        if current_user_id is None:
            return {"message": "Authentication required."}, 401

        payload = request.get_json(silent=True) or {}
        try:
            # Bulk mode: accept a list of question objects.
            if isinstance(payload, list):
                if not payload:
                    return {"message": "Request list is empty."}, 400
                created_items = []
                for item in payload:
                    result = create_question_with_answers(
                        bank_id=bank_id,
                        owner_id=current_user_id,
                        payload=item,
                    )
                    created_items.append(result)
                return {
                    "bank_id": bank_id,
                    "created_count": len(created_items),
                    "questions": created_items,
                }, 201

            result = create_question_with_answers(
                bank_id=bank_id,
                owner_id=current_user_id,
                payload=payload,
            )
            return result, 201
        except ValidationError as e:
            return {"message": str(e)}, 400
        except PermissionError as e:
            return {"message": str(e)}, 403
        except NotFoundError as e:
            return {"message": str(e)}, 404
        except Exception:
            return {"message": "Internal server error."}, 500


@question_bank_ns.route("/<int:bank_id>/questions/<int:question_id>")
class QuestionBankQuestionDetail(Resource):
    @question_bank_ns.response(200, "Question deleted")
    @question_bank_ns.response(401, "Not authenticated")
    @question_bank_ns.response(403, "Only owner can delete")
    @question_bank_ns.response(404, "Bank or question not found")
    @jwt_required()
    def delete(self, bank_id, question_id):
        """Delete a specific question from this question bank. Only the bank owner can delete. Answers (choices) are removed automatically."""
        bank, err = _ensure_can_edit_bank(bank_id)
        if err:
            return err
        question = Question.query.filter_by(id=question_id, bank_id=bank.id).first()
        if not question:
            return {"message": "Question not found in this bank."}, 404
        db.session.delete(question)
        db.session.commit()
        return {"message": "Question deleted from bank."}, 200


@question_bank_ns.route("/<int:bank_id>/versions")
class QuestionBankVersions(Resource):
    @jwt_required()
    def get(self, bank_id):
        bank = QuestionBank.query.get(bank_id)
        if not bank:
            return {"message": "Question bank not found."}, 404
        current_user_id = _current_user_id()
        claims = get_jwt() or {}
        if current_user_id != bank.owner_id and claims.get("role") != "admin":
            return {"message": "Only owner/admin can view all versions."}, 403
        versions = get_versions_by_bank(bank_id)
        return [
            {
                "id": v.id,
                "bank_id": v.bank_id,
                "version_number": v.version_number,
                "price": v.price,
                "update_type": v.update_type,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ], 200

    @jwt_required()
    @question_bank_ns.expect(version_create_model, validate=False)
    def post(self, bank_id):
        """Publish a new bank version (owner/admin). New questions added after this point attach to the new latest version. Call POST /upgrade to buy a new major version."""
        bank = QuestionBank.query.get(bank_id)
        if not bank:
            return {"message": "Question bank not found."}, 404
        current_user_id = _current_user_id()
        if current_user_id is None:
            return {"message": "Authentication required."}, 401
        claims = get_jwt() or {}
        if current_user_id != bank.owner_id and claims.get("role") != "admin":
            return {"message": "Only owner/admin can publish a new version."}, 403
        merged = _merge_version_create_inputs()
        update_type = merged.get("update_type")
        if isinstance(update_type, str):
            update_type = update_type.strip()
        if update_type not in ("minor", "major"):
            return {
                "message": "Input payload validation failed",
                "errors": {
                    "update_type": "must be 'minor' or 'major' (send JSON body or form field)",
                },
            }, 400
        price_raw = merged.get("price")
        if price_raw is None or price_raw == "":
            price = 0.0
        else:
            try:
                price = float(price_raw)
            except (TypeError, ValueError):
                return {
                    "message": "Input payload validation failed",
                    "errors": {"price": "must be a number"},
                }, 400
        try:
            v = create_new_version(
                bank_id,
                price,
                update_type,
            )
            return {
                "id": v.id,
                "bank_id": v.bank_id,
                "version_number": v.version_number,
                "price": v.price,
                "update_type": v.update_type,
            }, 201
        except BankVersionServiceError as e:
            return {"message": str(e)}, 400


@question_bank_ns.route("/<int:bank_id>/upgrade")
class QuestionBankUpgrade(Resource):
    @jwt_required()
    def post(self, bank_id):
        current_user_id = _current_user_id()
        if current_user_id is None:
            return {"message": "Authentication required."}, 401
        try:
            purchase, version = upgrade_bank(current_user_id, bank_id)
            return {
                "message": "Upgrade successful.",
                "version": {
                    "id": version.id,
                    "version_number": version.version_number,
                    "update_type": version.update_type,
                },
                "purchase": {
                    "id": purchase.id,
                    "price_paid": purchase.price_paid,
                },
            }, 200
        except BankAccessError as e:
            return {"message": str(e)}, 400

@question_bank_ns.route("")
class QuestionBankList(Resource):
    @jwt_required()
    def post(self):
        args = bank_create_parser.parse_args()
        user_id = _current_user_id()
        try:
            bank = create_bank(user_id, args.get("title"), args.get("access_type"))
            return {"id": bank.id, "title": bank.title, "access_type": bank.access_type}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400