import time
import re
import random
import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from articles.utils.db import get_articles_by_user
from .models import EmailVerification


def home_view(request):
    if request.user.is_authenticated:
        articles = get_articles_by_user(request.user.id)
        profile = request.user.profile
        profile.total_articles_imported = len(articles)
        profile.save()
        
        return render(request, "accounts/home.html", {"articles": articles})
    else:
        return render(request, "accounts/home.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    errors = {}
    sticky = {}

    if request.method == "POST":
        # 1. Temporal Trap (Rate Limiting)
        last_submit = request.session.get("last_submit_at")
        now = time.time()
        if last_submit and now - last_submit < 3:
            errors["general"] = "Yêu cầu xử lý quá nhanh. Vui lòng thử lại sau giây lát."
        else:
            request.session["last_submit_at"] = now

        # 2. Honeypot check (Spatial Trap)
        website_honeypot = request.POST.get("website", "")
        if website_honeypot:
            errors["general"] = "Yêu cầu không hợp lệ."

        # 3. Read and normalize inputs
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        sticky["username"] = username
        sticky["email"] = email

        # 4. Perform sequential validation
        if not errors:
            # Username check
            if not username:
                errors["username"] = "Tên đăng nhập không được để trống."
            elif not re.match(r"^[a-zA-Z0-9_]+$", username):
                errors["username"] = "Tên đăng nhập chỉ chứa chữ cái, chữ số và dấu gạch dưới."
            elif len(username) < 4:
                errors["username"] = "Tên đăng nhập phải dài ít nhất 4 ký tự."
            elif User.objects.filter(username=username, is_active=True).exists():
                errors["username"] = "Tên đăng nhập đã tồn tại."

            # Email check
            if not email:
                errors["email"] = "Email không được để trống."
            elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                errors["email"] = "Email không đúng định dạng."
            elif User.objects.filter(email=email, is_active=True).exists():
                errors["email"] = "Email đã được sử dụng."

            # Password check
            if not password:
                errors["password"] = "Mật khẩu không được để trống."
            elif len(password) < 6:
                errors["password"] = "Mật khẩu phải dài ít nhất 6 ký tự."

            # Confirm password check
            if not confirm_password:
                errors["confirm_password"] = "Vui lòng xác nhận mật khẩu."
            elif password != confirm_password:
                errors["confirm_password"] = "Mật khẩu xác nhận không khớp."

        # 5. Success gate
        if not errors:
            # Clean up any existing inactive accounts to avoid collision
            User.objects.filter(username=username, is_active=False).delete()
            User.objects.filter(email=email, is_active=False).delete()

            # Create inactive user
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_active = False
            user.save()

            # Generate 6-digit code
            code = f"{random.randint(100000, 999999):06d}"
            expires_at = timezone.now() + datetime.timedelta(minutes=5)

            # Save verification record
            EmailVerification.objects.update_or_create(
                user=user,
                defaults={"code": code, "expires_at": expires_at}
            )

            # Send code via email with safe fallback
            try:
                send_mail(
                    "Mã xác thực đăng ký tài khoản",
                    f"Mã xác thực của bạn là: {code}. Mã có hiệu lực trong 5 phút.",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False
                )
            except Exception as e:
                # Fallback print to terminal console
                print(f"\n[EMAIL FALLBACK] Failed to send email via SMTP: {e}")
                print(f"Mã xác thực đăng ký tài khoản")
                print(f"To: {email}")
                print(f"Mã xác thực của bạn là: {code}. Mã có hiệu lực trong 5 phút.\n")
                messages.warning(request, "Hệ thống gặp sự cố khi gửi email xác thực. Vui lòng kiểm tra terminal console để lấy mã OTP.")

            request.session["verification_user_id"] = user.id
            messages.success(request, "Mã xác thực đã được gửi tới email của bạn. Vui lòng xác thực.")
            return redirect("verify_email")

    return render(request, "accounts/register.html", {"errors": errors, "sticky": sticky})


def verify_email_view(request):
    user_id = request.session.get("verification_user_id")
    if not user_id:
        messages.error(request, "Vui lòng đăng ký trước khi xác thực.")
        return redirect("register")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "Tài khoản không tồn tại.")
        return redirect("register")

    if user.is_active:
        messages.info(request, "Tài khoản đã được kích hoạt.")
        return redirect("login")

    errors = {}
    sticky = {}

    if request.method == "POST":
        # 1. Temporal Trap (Rate Limiting)
        last_submit = request.session.get("last_submit_at")
        now = time.time()
        if last_submit and now - last_submit < 3:
            errors["general"] = "Yêu cầu xử lý quá nhanh. Vui lòng thử lại sau giây lát."
        else:
            request.session["last_submit_at"] = now

        # 2. Honeypot check (Spatial Trap)
        website_honeypot = request.POST.get("website", "")
        if website_honeypot:
            errors["general"] = "Yêu cầu không hợp lệ."

        code = request.POST.get("code", "").strip()
        sticky["code"] = code

        if not errors:
            if not code:
                errors["code"] = "Vui lòng nhập mã xác thực."
            elif len(code) != 6 or not code.isdigit():
                errors["code"] = "Mã xác thực phải gồm 6 chữ số."

        if not errors:
            try:
                verification = user.verification
                if verification.is_expired():
                    errors["general"] = "Mã xác thực đã hết hạn. Vui lòng gửi lại mã mới."
                elif verification.code != code:
                    errors["code"] = "Mã xác thực không chính xác."
            except EmailVerification.DoesNotExist:
                errors["general"] = "Không tìm thấy yêu cầu xác thực. Vui lòng gửi lại mã mới."

        if not errors:
            user.is_active = True
            user.save()
            user.verification.delete()
            
            # Login the user
            login(request, user, backend="accounts.backends.UsernameOrEmailBackend")
            del request.session["verification_user_id"]
            messages.success(request, "Xác thực tài khoản thành công! Chào mừng bạn.")
            return redirect("home")

    return render(request, "accounts/verify.html", {"errors": errors, "sticky": sticky, "user_email": user.email})


def resend_verification_view(request):
    user_id = request.session.get("verification_user_id")
    if not user_id:
        messages.error(request, "Vui lòng đăng ký trước khi gửi lại mã.")
        return redirect("register")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "Tài khoản không tồn tại.")
        return redirect("register")

    if user.is_active:
        messages.info(request, "Tài khoản đã được kích hoạt.")
        return redirect("login")

    try:
        verification = user.verification
        time_diff = timezone.now() - verification.created_at
        if time_diff.total_seconds() < 60:
            wait_seconds = int(60 - time_diff.total_seconds())
            messages.error(request, f"Vui lòng đợi {wait_seconds} giây trước khi gửi lại mã.")
            return redirect("verify_email")
    except EmailVerification.DoesNotExist:
        verification = None

    code = f"{random.randint(100000, 999999):06d}"
    expires_at = timezone.now() + datetime.timedelta(minutes=5)

    if verification:
        verification.code = code
        verification.created_at = timezone.now()
        verification.expires_at = expires_at
        verification.save()
    else:
        EmailVerification.objects.create(user=user, code=code, expires_at=expires_at)

    try:
        send_mail(
            "Mã xác thực đăng ký tài khoản (Gửi lại)",
            f"Mã xác thực mới của bạn là: {code}. Mã có hiệu lực trong 5 phút.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )
    except Exception as e:
        # Fallback print to terminal console
        print(f"\n[EMAIL FALLBACK] Failed to send email via SMTP (Resend): {e}")
        print(f"Mã xác thực đăng ký tài khoản (Gửi lại)")
        print(f"To: {user.email}")
        print(f"Mã xác thực mới của bạn là: {code}. Mã có hiệu lực trong 5 phút.\n")
        messages.warning(request, "Hệ thống gặp sự cố khi gửi email xác thực. Vui lòng kiểm tra terminal console để lấy mã OTP.")

    messages.success(request, "Mã xác thực mới đã được gửi tới email của bạn.")
    return redirect("verify_email")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    errors = {}
    sticky = {}

    if request.method == "POST":
        # 1. Temporal Trap (Rate Limiting)
        last_submit = request.session.get("last_submit_at")
        now = time.time()
        if last_submit and now - last_submit < 3:
            errors["general"] = "Vui lòng đợi vài giây trước khi thử lại."
        else:
            request.session["last_submit_at"] = now

        # 2. Honeypot check
        website_honeypot = request.POST.get("website", "")
        if website_honeypot:
            errors["general"] = "Yêu cầu không hợp lệ."

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        sticky["username"] = username

        if not errors:
            if not username:
                errors["username"] = "Vui lòng nhập tên đăng nhập hoặc email."
            if not password:
                errors["password"] = "Vui lòng nhập mật khẩu."

        if not errors:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Chào mừng {user.username} quay trở lại!")
                return redirect("home")
            else:
                errors["general"] = "Tên đăng nhập/Email hoặc mật khẩu không chính xác."

    return render(request, "accounts/login.html", {"errors": errors, "sticky": sticky})


def logout_view(request):
    logout(request)
    messages.success(request, "Đăng xuất tài khoản thành công!")
    return redirect("home")
