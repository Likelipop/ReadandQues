import datetime
import random
import re
import time

from database.Mongo.crud import get_articles_by_user, get_completed_articles
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (authenticate, login, logout,
                                 update_session_auth_hash)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import EmailVerification


def home_view(request):
    trending_articles = get_completed_articles(limit=6)
    user_articles = []

    if request.user.is_authenticated:
        user_articles = get_articles_by_user(request.user.id)
        profile = request.user.profile
        profile.total_articles_imported = len(user_articles)
        profile.save()

    context = {
        "trending_articles": trending_articles,
        "user_articles": user_articles,
    }
    return render(request, "accounts/home.html", context)


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
            errors["general"] = (
                "Request processed too fast. Please try again in a moment."
            )
        else:
            request.session["last_submit_at"] = now

        # 2. Honeypot check (Spatial Trap)
        website_honeypot = request.POST.get("website", "")
        if website_honeypot:
            errors["general"] = "Invalid request."

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
                errors["username"] = "Username cannot be empty."
            elif not re.match(r"^[a-zA-Z0-9_]+$", username):
                errors["username"] = (
                    "Username can only contain letters, numbers, and underscores."
                )
            elif len(username) < 4:
                errors["username"] = "Username must be at least 4 characters long."
            elif User.objects.filter(username=username, is_active=True).exists():
                errors["username"] = "Username already exists."

            # Email check
            if not email:
                errors["email"] = "Email cannot be empty."
            elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                errors["email"] = "Invalid email format."
            elif User.objects.filter(email=email, is_active=True).exists():
                errors["email"] = "Email is already in use."

            # Password check
            if not password:
                errors["password"] = "Password cannot be empty."
            elif len(password) < 6:
                errors["password"] = "Password must be at least 6 characters long."

            # Confirm password check
            if not confirm_password:
                errors["confirm_password"] = "Please confirm your password."
            elif password != confirm_password:
                errors["confirm_password"] = "Passwords do not match."

        # 5. Success gate
        if not errors:
            # Clean up any existing inactive accounts to avoid collision
            User.objects.filter(username=username, is_active=False).delete()
            User.objects.filter(email=email, is_active=False).delete()

            # Create inactive user
            user = User.objects.create_user(
                username=username, email=email, password=password
            )
            user.is_active = False
            user.save()

            # Generate 6-digit code
            code = f"{random.randint(100000, 999999):06d}"
            expires_at = timezone.now() + datetime.timedelta(minutes=5)

            # Save verification record
            EmailVerification.objects.update_or_create(
                user=user, defaults={"code": code, "expires_at": expires_at}
            )

            # Send code via email with safe fallback
            try:
                send_mail(
                    "Account Registration Verification Code",
                    f"Your verification code is: {code}. The code is valid for 5 minutes.",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                # Fallback print to terminal console
                print(f"\n[EMAIL FALLBACK] Failed to send email via SMTP: {e}")
                print(f"Account Registration Verification Code")
                print(f"To: {email}")
                print(f"Your verification code is: {code}. The code is valid for 5 minutes.\n")
                messages.warning(
                    request,
                    "System encountered an error sending verification email. Please check the terminal console for the OTP.",
                )

            request.session["verification_user_id"] = user.id
            messages.success(
                request, "A verification code has been sent to your email. Please verify."
            )
            return redirect("verify_email")

    return render(
        request, "accounts/register.html", {"errors": errors, "sticky": sticky}
    )


def verify_email_view(request):
    user_id = request.session.get("verification_user_id")
    if not user_id:
        messages.error(request, "Please register before verifying.")
        return redirect("register")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "Account does not exist.")
        return redirect("register")

    if user.is_active:
        messages.info(request, "Account has already been activated.")
        return redirect("login")

    errors = {}
    sticky = {}

    if request.method == "POST":
        # 1. Temporal Trap (Rate Limiting)
        last_submit = request.session.get("last_submit_at")
        now = time.time()
        if last_submit and now - last_submit < 3:
            errors["general"] = (
                "Request processed too fast. Please try again in a moment."
            )
        else:
            request.session["last_submit_at"] = now

        # 2. Honeypot check (Spatial Trap)
        website_honeypot = request.POST.get("website", "")
        if website_honeypot:
            errors["general"] = "Invalid request."

        code = request.POST.get("code", "").strip()
        sticky["code"] = code

        if not errors:
            if not code:
                errors["code"] = "Please enter the verification code."
            elif len(code) != 6 or not code.isdigit():
                errors["code"] = "The verification code must be 6 digits."

        if not errors:
            try:
                verification = user.verification
                if verification.is_expired():
                    errors["general"] = (
                        "The verification code has expired. Please resend a new code."
                    )
                elif verification.code != code:
                    errors["code"] = "Incorrect verification code."
            except EmailVerification.DoesNotExist:
                errors["general"] = (
                    "Verification request not found. Please resend a new code."
                )

        if not errors:
            user.is_active = True
            user.save()
            user.verification.delete()

            # Login the user
            login(request, user, backend="accounts.backends.UsernameOrEmailBackend")
            del request.session["verification_user_id"]
            messages.success(request, "Account successfully verified! Welcome.")
            return redirect("home")

    return render(
        request,
        "accounts/verify.html",
        {"errors": errors, "sticky": sticky, "user_email": user.email},
    )


def resend_verification_view(request):
    user_id = request.session.get("verification_user_id")
    if not user_id:
        messages.error(request, "Please register before resending the code.")
        return redirect("register")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "Account does not exist.")
        return redirect("register")

    if user.is_active:
        messages.info(request, "Account has already been activated.")
        return redirect("login")

    try:
        verification = user.verification
        time_diff = timezone.now() - verification.created_at
        if time_diff.total_seconds() < 60:
            wait_seconds = int(60 - time_diff.total_seconds())
            messages.error(
                request, f"Please wait {wait_seconds} seconds before resending the code."
            )
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
            "Account Registration Verification Code (Resend)",
            f"Your new verification code is: {code}. The code is valid for 5 minutes.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        # Fallback print to terminal console
        print(f"\n[EMAIL FALLBACK] Failed to send email via SMTP (Resend): {e}")
        print(f"Account Registration Verification Code (Resend)")
        print(f"To: {user.email}")
        print(f"Your new verification code is: {code}. The code is valid for 5 minutes.\n")
        messages.warning(
            request,
            "System encountered an error sending verification email. Please check the terminal console for the OTP.",
        )

    messages.success(request, "A new verification code has been sent to your email.")
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
            errors["general"] = "Please wait a few seconds before trying again."
        else:
            request.session["last_submit_at"] = now

        # 2. Honeypot check
        website_honeypot = request.POST.get("website", "")
        if website_honeypot:
            errors["general"] = "Invalid request."

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        sticky["username"] = username

        if not errors:
            if not username:
                errors["username"] = "Please enter your username or email."
            if not password:
                errors["password"] = "Please enter your password."

        if not errors:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect("home")
            else:
                errors["general"] = "Incorrect Username/Email or password."

    return render(request, "accounts/login.html", {"errors": errors, "sticky": sticky})


def logout_view(request):
    logout(request)
    messages.success(request, "Successfully logged out!")
    return redirect("home")


@login_required(login_url="login")
def profile_view(request):
    profile = request.user.profile
    articles = get_articles_by_user(request.user.id)
    total_articles = len(articles)

    if request.method == "POST":
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been successfully updated!")
            return redirect("profile")
        else:
            messages.error(request, "Please fix the errors below to change your password.")
    else:
        password_form = PasswordChangeForm(request.user)

    context = {
        "profile": profile,
        "total_articles": total_articles,
        "password_form": password_form,
    }
    return render(request, "accounts/profile.html", context)
