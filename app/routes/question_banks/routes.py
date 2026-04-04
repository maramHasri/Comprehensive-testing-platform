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
from sqlalchemy import func, or_

from app.extensions import db
from app.models import QuestionBank, Question, Choice, User, Purchase, BankVersion, BankTopic
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
    resolve_topic_id_for_bank,
    _question_to_dict,
)
from app.repositories.bank_version_repository import get_versions_by_bank, sync_topic_counts_for_bank
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


def _serialize_question_for_bank(q, include_bank_version_id=False):
    t = q.topic
    row = {
        "id": q.id,
        "type": q.type,
        "content": q.content,
        "created_by": q.created_by,
        "original_question_id": q.original_question_id,
        "hint": q.hint,
        "points": q.points,
        "base_time": q.base_time,
        "topic_id": q.topic_id,
        "topic": {"id": t.id, "name": t.name} if t else None,
        "answers": [{"id": c.id, "text": c.text, "is_correct": c.is_correct} for c in q.choices],
    }
    if include_bank_version_id:
        row["bank_version_id"] = q.bank_version_id
    return row


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


def _merge_question_create_inputs():
    """Merge form, query, then JSON for POST .../questions (single object body)."""
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
    return merged


def _merge_topic_create_inputs():
    """Merge form, query, then JSON so Swagger form posts and JSON bodies both work."""
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
    return merged


def _topic_questions_count(bank_id: int, topic_id: int) -> int:
    return Question.query.filter_by(bank_id=bank_id, topic_id=topic_id).count()


def _dedupe_positive_question_ids(ids: list[int]) -> list[int]:
    """Keep only valid question primary keys (> 0), unique, order preserved."""
    seen: set[int] = set()
    out: list[int] = []
    for i in ids:
        if i > 0 and i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _question_ids_for_topic_assign(merged: dict) -> list[int]:
    """Parse optional question_ids: real Question.id values in this bank (not a count). Omit to create topic only."""
    raw = merged.get("question_ids")
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        out = []
        for x in raw:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                raise ValueError("Each question_ids entry must be an integer.")
        return _dedupe_positive_question_ids(out)
    if isinstance(raw, str):
        out = []
        for part in raw.replace(" ", "").split(","):
            if not part:
                continue
            try:
                out.append(int(part))
            except ValueError:
                raise ValueError("question_ids string must be comma-separated integers.")
        return _dedupe_positive_question_ids(out)
    try:
        return _dedupe_positive_question_ids([int(raw)])
    except (TypeError, ValueError):
        raise ValueError("question_ids must be a list of integers, a comma-separated string, or omitted.")


def _topic_counts_by_id_for_bank(bank_id: int) -> dict:
    rows = (
        db.session.query(Question.topic_id, func.count(Question.id))
        .filter(Question.bank_id == bank_id, Question.topic_id.isnot(None))
        .group_by(Question.topic_id)
        .all()
    )
    return {tid: c for tid, c in rows}


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
        "topic_id": fields.Integer(
            required=False,
            description="Optional BankTopic.id in this bank. Same as topicId or topic.id",
        ),
        "topicId": fields.Integer(
            required=False,
            description="camelCase alias for topic_id (mobile/JS clients)",
        ),
        "topic": fields.Raw(
            required=False,
            description='Optional {"id": <topic primary key>} to assign this question to a topic',
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

topic_brief_model = question_bank_ns.model(
    "TopicBrief",
    {"id": fields.Integer, "name": fields.String},
)

topic_create_model = question_bank_ns.model(
    "TopicCreate",
    {
        "name": fields.String(
            required=True,
            description="Topic display name. Topic id is generated by the server (omit question_ids to only create the row).",
        ),
        "sort_order": fields.Integer(
            required=False,
            default=0,
            description="Optional ordering among topics in this bank (lower first). Default 0.",
        ),
        "question_ids": fields.List(
            fields.Integer,
            required=False,
            description=(
                "Optional: existing Question.id values in this bank to tag with this topic immediately. "
                "Not a count; use real question IDs (e.g. 12, 15). Omit or [] if you only need name + server id."
            ),
        ),
    },
)

topic_response_model = question_bank_ns.model(
    "TopicResponse",
    {
        "id": fields.Integer,
        "bank_id": fields.Integer,
        "name": fields.String,
        "sort_order": fields.Integer,
        "questions_count": fields.Integer(
            description="Number of questions in this bank assigned to this topic",
        ),
        "created_at": fields.String,
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
        "topic_id": fields.Integer,
        "topic": fields.Nested(topic_brief_model, allow_null=True),
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


def _bank_ids_from_user_purchases(user_id: int) -> set:
    """Distinct question bank IDs the user has purchased (via bank_id or bank_version)."""
    ids = set()
    for p in Purchase.query.filter_by(user_id=user_id).all():
        bid = p.bank_id
        if bid is None:
            bv = BankVersion.query.get(p.bank_version_id)
            if bv is not None:
                bid = bv.bank_id
        if bid is not None:
            ids.add(bid)
    return ids


@question_bank_ns.route("/me")
class QuestionBanksRelatedToCurrentUser(Resource):
    @jwt_required()
    @question_bank_ns.response(200, "Question banks owned by or purchased by the current user")
    def get(self):
        """List all question banks related to the current user (owned and/or purchased)."""
        current_user_id = _current_user_id()
        if current_user_id is None:
            return {"message": "Authentication required."}, 401
        purchased_bank_ids = _bank_ids_from_user_purchases(current_user_id)
        owned_ids = {b.id for b in QuestionBank.query.filter_by(owner_id=current_user_id).all()}
        all_ids = owned_ids | purchased_bank_ids
        if not all_ids:
            return [], 200
        banks = (
            QuestionBank.query.filter(QuestionBank.id.in_(all_ids))
            .order_by(QuestionBank.created_at.desc())
            .all()
        )
        out = []
        for b in banks:
            owner = User.query.get(b.owner_id) if b.owner_id else None
            out.append(
                {
                    "id": b.id,
                    "title": b.title,
                    "access_type": b.access_type,
                    "owner_id": b.owner_id,
                    "owner_name": owner.name if owner else None,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                    "questions_count": len(b.questions),
                    "is_owner": b.owner_id == current_user_id,
                    "is_purchased": b.id in purchased_bank_ids,
                }
            )
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
            _serialize_question_for_bank(q, include_bank_version_id=True) for q in questions
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


# ----- Topics (classify questions within a bank) -----
@question_bank_ns.route("/<int:bank_id>/topics")
class QuestionBankTopics(Resource):
    @question_bank_ns.response(404, "Bank not found or not visible")
    @jwt_required(optional=True)
    def get(self, bank_id):
        """List topics defined for this bank. Same visibility rules as the bank."""
        bank = QuestionBank.query.get(bank_id)
        if not bank:
            return {"message": "Question bank not found."}, 404
        if not _can_view_bank(bank, _current_user_id()):
            return {"message": "Question bank not found."}, 404
        topics = (
            BankTopic.query.filter_by(bank_id=bank.id)
            .order_by(BankTopic.sort_order.asc(), BankTopic.id.asc())
            .all()
        )
        counts = _topic_counts_by_id_for_bank(bank.id)
        return [
            {
                "id": t.id,
                "bank_id": t.bank_id,
                "name": t.name,
                "sort_order": t.sort_order,
                "questions_count": counts.get(t.id, 0),
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in topics
        ], 200

    @jwt_required()
    @question_bank_ns.expect(topic_create_model, validate=False)
    @question_bank_ns.response(201, "Topic created", topic_response_model)
    @question_bank_ns.response(400, "Validation error")
    @question_bank_ns.response(401, "Not authenticated")
    @question_bank_ns.response(403, "Only owner can add topics")
    def post(self, bank_id):
        """Create a topic row (id assigned by DB). Only name is required; sort_order and question_ids are optional."""
        bank, err = _ensure_can_edit_bank(bank_id)
        if err:
            return err
        merged = _merge_topic_create_inputs()
        name = trim_str(merged.get("name") or merged.get("title") or "")
        if not name:
            return {"message": "Field 'name' is required (form field or JSON; 'title' is accepted as alias)."}, 400
        sort_raw = merged.get("sort_order", 0)
        try:
            sort_order = int(sort_raw) if sort_raw not in (None, "") else 0
        except (TypeError, ValueError):
            return {"message": "Field 'sort_order' must be an integer."}, 400
        try:
            question_ids = _question_ids_for_topic_assign(merged)
        except ValueError as e:
            return {"message": str(e)}, 400
        if BankTopic.query.filter_by(bank_id=bank.id, name=name).first():
            return {"message": "A topic with this name already exists in this bank."}, 400
        topic = BankTopic(bank_id=bank.id, name=name, sort_order=sort_order)
        db.session.add(topic)
        db.session.flush()
        for qid in question_ids:
            q = Question.query.filter_by(id=qid, bank_id=bank.id).first()
            if not q:
                db.session.rollback()
                return {"message": f"Question {qid} not found in this bank."}, 400
            q.topic_id = topic.id
        db.session.commit()
        sync_topic_counts_for_bank(bank.id)
        qcount = _topic_questions_count(bank.id, topic.id)
        return {
            "id": topic.id,
            "bank_id": topic.bank_id,
            "name": topic.name,
            "sort_order": topic.sort_order,
            "questions_count": qcount,
            "created_at": topic.created_at.isoformat() if topic.created_at else None,
        }, 201


@question_bank_ns.route("/<int:bank_id>/topics/<int:topic_id>")
class QuestionBankTopicDetail(Resource):
    @jwt_required()
    @question_bank_ns.response(200, "Topic updated")
    @question_bank_ns.response(400, "Validation error")
    @question_bank_ns.response(404, "Bank or topic not found")
    def patch(self, bank_id, topic_id):
        """Update topic name and/or sort_order. Owner only."""
        bank, err = _ensure_can_edit_bank(bank_id)
        if err:
            return err
        topic = BankTopic.query.filter_by(id=topic_id, bank_id=bank.id).first()
        if not topic:
            return {"message": "Topic not found in this bank."}, 404
        body = request.get_json(silent=True) or {}
        if "name" in body:
            name = trim_str(body.get("name") or "")
            if not name:
                return {"message": "Field 'name' cannot be empty."}, 400
            existing = BankTopic.query.filter_by(bank_id=bank.id, name=name).first()
            if existing and existing.id != topic.id:
                return {"message": "A topic with this name already exists in this bank."}, 400
            topic.name = name
        if "sort_order" in body:
            try:
                topic.sort_order = int(body["sort_order"])
            except (TypeError, ValueError):
                return {"message": "Field 'sort_order' must be an integer."}, 400
        db.session.commit()
        return {
            "id": topic.id,
            "bank_id": topic.bank_id,
            "name": topic.name,
            "sort_order": topic.sort_order,
            "questions_count": _topic_questions_count(bank.id, topic.id),
            "created_at": topic.created_at.isoformat() if topic.created_at else None,
        }, 200

    @jwt_required()
    @question_bank_ns.response(200, "Topic deleted")
    @question_bank_ns.response(404, "Bank or topic not found")
    def delete(self, bank_id, topic_id):
        """Delete a topic. Questions in this bank keep their other fields; topic_id is cleared."""
        bank, err = _ensure_can_edit_bank(bank_id)
        if err:
            return err
        topic = BankTopic.query.filter_by(id=topic_id, bank_id=bank.id).first()
        if not topic:
            return {"message": "Topic not found in this bank."}, 404
        db.session.delete(topic)
        db.session.commit()
        sync_topic_counts_for_bank(bank.id)
        return {"message": "Topic deleted."}, 200


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
        return [_serialize_question_for_bank(q) for q in questions], 200

    @question_bank_ns.doc(
        description=(
            "Create a question (and optional answers) in this bank using JSON or form fields.\n"
            "Optional topic: send topic_id, topicId, or topic: { \"id\": <number> } (must exist in this bank).\n\n"
            "Example body:\n"
            "{\n"
            '  \"text\": \"Question text\",\n'
            '  \"question_type\": \"mcq\",\n'
            '  \"topic_id\": 1,\n'
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

        raw_body = request.get_json(silent=True)
        try:
            # Bulk mode: accept a list of question objects (JSON array only).
            if isinstance(raw_body, list):
                if not raw_body:
                    return {"message": "Request list is empty."}, 400
                created_items = []
                for item in raw_body:
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

            payload = _merge_question_create_inputs()
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
    @jwt_required()
    @question_bank_ns.response(200, "Topic assignment updated")
    @question_bank_ns.response(400, "Validation error")
    @question_bank_ns.response(401, "Not authenticated")
    @question_bank_ns.response(403, "Only owner can update")
    @question_bank_ns.response(404, "Bank or question not found")
    def patch(self, bank_id, question_id):
        """Assign or clear the question's topic. JSON body: { \"topic_id\": <int> | null }."""
        bank, err = _ensure_can_edit_bank(bank_id)
        if err:
            return err
        question = Question.query.filter_by(id=question_id, bank_id=bank.id).first()
        if not question:
            return {"message": "Question not found in this bank."}, 404
        body = request.get_json(silent=True) or {}
        if "topic_id" not in body:
            return {"message": "Field 'topic_id' is required (use null to clear the topic)."}, 400
        try:
            question.topic_id = resolve_topic_id_for_bank(bank.id, body.get("topic_id"))
        except ValidationError as e:
            return {"message": str(e)}, 400
        db.session.commit()
        return _question_to_dict(question), 200

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