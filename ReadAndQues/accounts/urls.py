from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('register/verify/', views.verify_email_view, name='verify_email'),
    path('register/verify/resend/', views.resend_verification_view, name='resend_verification'),
    path('logout/', views.logout_view, name='logout'),
]
