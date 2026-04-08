"""
Central catalog of localized message keys and their translations.

Used by:
  - scripts/seed_app_messages.py — bulk insert / upsert into app_messages
  - app.repositories.message_repository — English fallback when DB row is missing

To add a new message:
  1. Add an entry here with "en" and "ar" (or more languages later).
  2. Run: python scripts/seed_app_messages.py
  3. Optionally call clear_message_cache() from message_repository after deploy.

Keys are UPPER_SNAKE_CASE for API/auth errors; educational samples can use lower_snake_case.
"""

# message_key -> { language_code: message_text }
MESSAGE_CATALOG: dict[str, dict[str, str]] = {
    # --- Educational / platform (requested examples) ---
    "login_success": {
        "en": "Signed in successfully.",
        "ar": "تم تسجيل الدخول بنجاح.",
    },
    "login_failed": {
        "en": "Sign-in failed. Check your email and password.",
        "ar": "فشل تسجيل الدخول. تحقق من البريد وكلمة المرور.",
    },
    "quiz_created": {
        "en": "Quiz created successfully.",
        "ar": "تم إنشاء الاختبار بنجاح.",
    },
    "quiz_submitted": {
        "en": "Your quiz has been submitted.",
        "ar": "تم إرسال إجاباتك للاختبار.",
    },
    "access_denied": {
        "en": "You do not have permission to perform this action.",
        "ar": "ليس لديك صلاحية لتنفيذ هذا الإجراء.",
    },
    "invalid_input": {
        "en": "Invalid input. Please check the fields and try again.",
        "ar": "مدخلات غير صالحة. راجع الحقول وحاول مرة أخرى.",
    },
    "ADMIN_I18N_MESSAGE_SAVED": {
        "en": "Localized message saved.",
        "ar": "تم حفظ الرسالة.",
    },
    # --- Auth (existing API keys) ---
    "AUTH_NAME_REQUIRED": {
        "en": "Name is required.",
        "ar": "الاسم مطلوب.",
    },
    "AUTH_EMAIL_REQUIRED": {
        "en": "Email is required.",
        "ar": "البريد الإلكتروني مطلوب.",
    },
    "AUTH_EMAIL_INVALID": {
        "en": "Email format is invalid.",
        "ar": "صيغة البريد الإلكتروني غير صحيحة.",
    },
    "AUTH_PASSWORD_TOO_SHORT": {
        "en": "Password must be at least 8 characters.",
        "ar": "يجب أن تكون كلمة المرور 8 أحرف على الأقل.",
    },
    "AUTH_ROLE_INVALID": {
        "en": "Role must be teacher, student, or admin.",
        "ar": "يجب أن يكون الدور: معلم أو طالب أو مسؤول.",
    },
    "AUTH_EMAIL_EXISTS": {
        "en": "An account with this email already exists.",
        "ar": "يوجد حساب بهذا البريد الإلكتروني بالفعل.",
    },
    "AUTH_REGISTER_SUCCESS": {
        "en": "Registration successful.",
        "ar": "تم إنشاء الحساب بنجاح.",
    },
    "AUTH_REGISTER_VERIFY_SENT": {
        "en": "Registration successful. Please check your email to activate your account.",
        "ar": "تم إنشاء الحساب بنجاح. يرجى تفقد بريدك لتفعيل الحساب.",
    },
    "AUTH_PASSWORD_REQUIRED": {
        "en": "Password is required.",
        "ar": "كلمة المرور مطلوبة.",
    },
    "AUTH_LOGIN_INVALID": {
        "en": "Invalid email or password.",
        "ar": "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
    },
    "AUTH_VERIFY_REQUIRED": {
        "en": "Please verify your email before logging in.",
        "ar": "يرجى تفعيل بريدك الإلكتروني قبل تسجيل الدخول.",
    },
    "AUTH_LOGOUT_SUCCESS": {
        "en": "Logged out successfully.",
        "ar": "تم تسجيل الخروج بنجاح.",
    },
    "AUTH_TOO_MANY_REQUESTS": {
        "en": "Too many requests. Try again later.",
        "ar": "طلبات كثيرة جداً. حاول لاحقاً.",
    },
    "AUTH_FORGOT_PASSWORD_GENERIC": {
        "en": "If an account exists for this email, you will receive reset instructions shortly.",
        "ar": "إذا كان هناك حساب لهذا البريد، ستصلك تعليمات إعادة التعيين قريباً.",
    },
    "AUTH_EMAIL_SEND_FAILED": {
        "en": "Could not send email. Please try again later.",
        "ar": "تعذر إرسال البريد الإلكتروني. حاول لاحقاً.",
    },
    "AUTH_VERIFY_TOKEN_REQUIRED": {
        "en": "Verification token is required.",
        "ar": "رمز التفعيل مطلوب.",
    },
    "AUTH_VERIFY_TOKEN_INVALID": {
        "en": "Invalid verification link.",
        "ar": "رابط التفعيل غير صالح.",
    },
    "AUTH_VERIFY_TOKEN_EXPIRED": {
        "en": "Verification link expired. Request a new one.",
        "ar": "انتهت صلاحية رابط التفعيل. اطلب رابطاً جديداً.",
    },
    "AUTH_EMAIL_VERIFIED": {
        "en": "Email verified successfully. You can now log in.",
        "ar": "تم تفعيل البريد بنجاح. يمكنك تسجيل الدخول الآن.",
    },
    "AUTH_EMAIL_ALREADY_VERIFIED": {
        "en": "Email is already verified.",
        "ar": "تم تفعيل البريد مسبقاً.",
    },
    "AUTH_RESEND_VERIFY_GENERIC": {
        "en": "If an account exists and is not verified, a new activation email has been sent.",
        "ar": "إذا كان الحساب موجوداً وغير مفعل، فقد تم إرسال رابط تفعيل جديد.",
    },
    "AUTH_EMAIL_AND_OTP_REQUIRED": {
        "en": "Email and OTP are required.",
        "ar": "البريد والرمز مطلوبان.",
    },
    "AUTH_OTP_INVALID": {
        "en": "Invalid or expired code.",
        "ar": "رمز غير صالح أو منتهٍ.",
    },
    "AUTH_OTP_VERIFIED": {
        "en": "Code verified. You can set a new password.",
        "ar": "تم التحقق من الرمز. يمكنك تعيين كلمة مرور جديدة.",
    },
    "AUTH_NEW_PASSWORD_REQUIRED": {
        "en": "New password is required.",
        "ar": "كلمة المرور الجديدة مطلوبة.",
    },
    "AUTH_RESET_SESSION_INVALID": {
        "en": "Reset session expired or invalid. Request a new code.",
        "ar": "انتهت جلسة إعادة التعيين أو أنها غير صالحة. اطلب رمزاً جديداً.",
    },
    "AUTH_RESET_SUCCESS": {
        "en": "Password updated successfully.",
        "ar": "تم تحديث كلمة المرور بنجاح.",
    },
    "AUTH_PASSWORD_NEEDS_LETTER": {
        "en": "Password must include at least one letter.",
        "ar": "يجب أن تحتوي كلمة المرور على حرف واحد على الأقل.",
    },
    "AUTH_PASSWORD_NEEDS_NUMBER": {
        "en": "Password must include at least one number.",
        "ar": "يجب أن تحتوي كلمة المرور على رقم واحد على الأقل.",
    },
    # --- Quiz / common ---
    "COMMON_AUTH_REQUIRED": {
        "en": "Authentication required.",
        "ar": "يجب تسجيل الدخول.",
    },
    "COMMON_INVALID_TOKEN": {
        "en": "Invalid or expired session. Please sign in again.",
        "ar": "جلسة غير صالحة أو منتهية. سجّل الدخول مجدداً.",
    },
    "QUIZ_TEACHERS_ONLY": {
        "en": "Only teachers can perform this action.",
        "ar": "يمكن للمعلمين فقط تنفيذ هذا الإجراء.",
    },
    "QUIZ_TITLE_REQUIRED": {
        "en": "Quiz title is required.",
        "ar": "عنوان الاختبار مطلوب.",
    },
    "QUIZ_TOTAL_SCORE_INVALID": {
        "en": "Total score must be a positive number.",
        "ar": "يجب أن يكون المجموع رقماً موجباً.",
    },
    "QUIZ_NUMBER_OF_QUESTIONS_REQUIRED": {
        "en": "Number of questions is required.",
        "ar": "عدد الأسئلة مطلوب.",
    },
    "QUIZ_NUMBER_OF_QUESTIONS_INVALID": {
        "en": "Number of questions must be a valid integer.",
        "ar": "عدد الأسئلة يجب أن يكون رقماً صحيحاً.",
    },
    "QUIZ_NUMBER_OF_QUESTIONS_MIN": {
        "en": "You must request at least one question.",
        "ar": "يجب طلب سؤال واحد على الأقل.",
    },
    "QUIZ_BANK_NOT_FOUND": {
        "en": "Question bank not found.",
        "ar": "بنك الأسئلة غير موجود.",
    },
    "QUIZ_BANK_PERMISSION_DENIED": {
        "en": "You do not have access to this question bank.",
        "ar": "ليس لديك صلاحية الوصول إلى بنك الأسئلة هذا.",
    },
    "QUIZ_BANK_NO_QUESTIONS": {
        "en": "This question bank has no questions yet.",
        "ar": "لا توجد أسئلة في بنك الأسئلة بعد.",
    },
    "QUIZ_BANK_TOO_FEW_QUESTIONS": {
        "en": "Not enough questions in the bank (available: {count}).",
        "ar": "عدد الأسئلة في البنك غير كافٍ (المتاح: {count}).",
    },
}


def english_fallbacks() -> dict[str, str]:
    """Map message_key -> English text for offline / pre-seed fallback."""
    return {k: v["en"] for k, v in MESSAGE_CATALOG.items() if "en" in v}
