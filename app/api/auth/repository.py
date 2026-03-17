"""
Auth repository facade for the API layer.

Delegates to the shared data-access functions in app.repositories.authentication
to keep a clear separation between API package and repositories package.
"""

from app.repositories.authentication import (
    get_user_by_email,
    create_user,
    create_session,
    delete_session_by_jti,
)

