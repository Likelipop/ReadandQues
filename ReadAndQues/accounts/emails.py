import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def get_otp_email_html(code: str) -> str:
    """
    Generates an elegant, modern HTML email template for ReadQues verification OTP.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ReadQues Verification Code</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f8fafc; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 520px; background-color: #ffffff; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01); border: 1px solid #e2e8f0;">
          
          <!-- Brand Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%); padding: 36px 32px; text-align: center;">
              <h1 style="color: #ffffff; font-size: 28px; font-weight: 800; margin: 0; tracking: -0.5px;">ReadQues</h1>
              <p style="color: #c7d2fe; font-size: 13px; font-weight: 500; margin-top: 6px; margin-bottom: 0; text-transform: uppercase; letter-spacing: 1px;">AI Reading Practice Quiz</p>
            </td>
          </tr>

          <!-- Main Body -->
          <tr>
            <td style="padding: 40px 32px 32px 32px; text-align: center;">
              <h2 style="color: #0f172a; font-size: 20px; font-weight: 700; margin: 0 0 12px 0;">Mã Xác Minh Tài Khoản</h2>
              <p style="color: #64748b; font-size: 14px; line-height: 1.6; margin: 0 0 28px 0;">
                Cảm ơn bạn đã đăng ký tài khoản tại <strong>ReadQues</strong>. Dưới đây là mã xác thực OTP của bạn để hoàn tất quá trình đăng ký.
              </p>

              <!-- OTP Display Card -->
              <div style="background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%); border: 2px dashed #cbd5e1; border-radius: 16px; padding: 20px; margin: 0 auto 28px auto; max-width: 320px;">
                <span style="font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: 800; letter-spacing: 10px; color: #4338ca; display: block; text-indent: 10px;">
                  {code}
                </span>
              </div>

              <!-- Expiry Warning -->
              <p style="color: #ef4444; font-size: 13px; font-weight: 600; margin: 0 0 20px 0; display: inline-flex; align-items: center; gap: 4px;">
                ⏱️ Mã này có hiệu lực trong vòng <strong>5 phút</strong>.
              </p>

              <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 24px 0;" />

              <p style="color: #94a3b8; font-size: 12px; line-height: 1.5; margin: 0;">
                Nếu bạn không yêu cầu mã này, vui lòng bỏ qua email này. Vui lòng không chia sẻ mã OTP cho bất kỳ ai.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #f8fafc; padding: 20px 32px; text-align: center; border-top: 1px solid #f1f5f9;">
              <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                &copy; ReadQues Platform. Powered by LangGraph AI.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def send_verification_email(to_email: str, code: str, is_resend_action: bool = False) -> bool:
    """
    Sends the verification email via Resend HTTP API.
    Falls back gracefully to printing to terminal console if Resend fails or key is unconfigured.
    """
    api_key = getattr(settings, "RESEND_API_KEY", "")
    from_email = getattr(settings, "RESEND_FROM_EMAIL", "noreply@readques.app")
    subject_prefix = "(Resend) " if is_resend_action else ""
    subject = f"{subject_prefix}Account Registration Verification Code - ReadQues"

    if api_key:
        try:
            import resend
            resend.api_key = api_key
            
            response = resend.Emails.send({
                "from": from_email,
                "to": to_email,
                "subject": subject,
                "html": get_otp_email_html(code),
            })
            resend_id = response.get("id", "N/A") if isinstance(response, dict) else getattr(response, "id", "N/A")
            logger.info(f"Successfully sent OTP email via Resend to {to_email}. Response ID: {resend_id}")
            print(f"[RESEND SUCCESS] Sent OTP verification code to {to_email}. Resend ID: {resend_id}")
            return True
        except Exception as e:
            logger.warning(f"Resend API error sending email to {to_email}: {e}")
            print(f"\n[RESEND FALLBACK] Failed to send email via Resend API: {e}")

    # Fallback to terminal console print if API key is missing or request failed
    print(f"[EMAIL FALLBACK] Account Registration Verification Code {subject_prefix}")
    print(f"To: {to_email}")
    print(f"Your verification code is: {code}. The code is valid for 5 minutes.\n")
    return False
