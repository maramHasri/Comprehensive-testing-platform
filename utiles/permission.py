from functools import wraps
from flask import abort
from flask_login import current_user

def teacher_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role != "teacher":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper
