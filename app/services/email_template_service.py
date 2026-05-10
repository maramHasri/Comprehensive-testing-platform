from app.services.email_service import send_email


def send_activation_email(to_email: str, activation_url: str, app_name: str = "quiz management system") -> bool:
    subject = "Activate your account"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 640px; margin: 0 auto; color: #1f2937;">
      <h2 style="margin-bottom: 8px;">Activate your account</h2>
      <p style="margin-top: 0;">Welcome to {app_name}.</p>
      <p>Please click the button below to verify your email and activate your account:</p>
      <p style="margin: 24px 0;">
        <a href="{activation_url}" style="
          display:inline-block;
          padding:12px 20px;
          background-color:#4CAF50;
          color:white;
          text-decoration:none;
          border-radius:5px;
        ">Activate Account</a>
      </p>
      <p style="font-size: 13px; color: #6b7280;">
        If the button does not work, copy and paste this link into your browser:<br>
        <a href="{activation_url}">{activation_url}</a>
      </p>
      <p style="font-size: 13px; color: #6b7280;">
        This link expires soon for your security. If you did not create this account, you can ignore this email.
      </p>
    </div>
    """
    return send_email(to_email=to_email, subject=subject, html_content=html)


def send_password_reset_otp_email(
    to_email: str,
    otp_code: str,
    expiry_minutes: int,
    app_name: str = "quiz management system",
) -> bool:
    subject = "Password reset verification code"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 640px; margin: 0 auto; color: #1f2937;">
      <h2 style="margin-bottom: 8px;">Reset your password</h2>
      <p style="margin-top: 0;">You requested a password reset for your {app_name} account.</p>
      <p>Use this verification code:</p>
      <p style="font-size: 28px; letter-spacing: 6px; font-weight: bold; margin: 24px 0;">{otp_code}</p>
      <p style="font-size: 13px; color: #6b7280;">
        This code expires in <strong>{expiry_minutes}</strong> minutes.
        If you did not request a reset, you can ignore this email.
      </p>
    </div>
    """
    return send_email(to_email=to_email, subject=subject, html_content=html)
