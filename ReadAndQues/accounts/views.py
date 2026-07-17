import time
import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from articles.utils.db import get_articles_by_user


def home_view(request):
    if request.user.is_authenticated:
        # User is logged in, show dashboard
        articles = get_articles_by_user(request.user.id)
        # Update user's profile stats dynamically
        profile = request.user.profile
        profile.total_articles_imported = len(articles)
        profile.save()
        
        return render(request, "accounts/home.html", {"articles": articles})
    else:
        # User is not logged in, show landing page
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
            elif User.objects.filter(username=username).exists():
                errors["username"] = "Tên đăng nhập đã tồn tại."

            # Email check
            if not email:
                errors["email"] = "Email không được để trống."
            elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                errors["email"] = "Email không đúng định dạng."
            elif User.objects.filter(email=email).exists():
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
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, "Đăng ký tài khoản thành công!")
            return redirect("home")

    return render(request, "accounts/register.html", {"errors": errors, "sticky": sticky})


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
                errors["username"] = "Vui lòng nhập tên đăng nhập."
            if not password:
                errors["password"] = "Vui lòng nhập mật khẩu."

        if not errors:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Chào mừng {user.username} quay trở lại!")
                return redirect("home")
            else:
                errors["general"] = "Tên đăng nhập hoặc mật khẩu không chính xác."

    return render(request, "accounts/login.html", {"errors": errors, "sticky": sticky})


def logout_view(request):
    logout(request)
    messages.success(request, "Đăng xuất tài khoản thành công!")
    return redirect("home")
