import os
import glob

replacements = {
    "Đăng nhập - IELTS AI Reading Quiz": "Login - AI Reading Practice Quiz",
    "Đăng ký tài khoản - IELTS AI Reading Quiz": "Register - AI Reading Practice Quiz",
    "Xác thực tài khoản - IELTS AI Reading Quiz": "Verify Account - AI Reading Practice Quiz",
    "Tài khoản của tôi - IELTS AI Reading Quiz": "My Profile - AI Reading Practice Quiz",
    "Trang chủ - IELTS AI Reading Quiz": "Home - AI Reading Practice Quiz",
    "Đăng nhập": "Login",
    "Đăng ký ngay": "Register now",
    "Đăng ký tài khoản": "Create Account",
    "Đăng ký": "Register",
    "Xác thực Email": "Email Verification",
    "Xác thực tài khoản": "Account Verification",
    "Tài khoản của tôi": "My Profile",
    "Quản lý thông tin cá nhân, theo dõi tiến trình học tập và đổi mật khẩu.": "Manage your personal information, track your progress, and change your password.",
    "Thành viên từ ngày": "Member since",
    "Địa chỉ Email": "Email Address",
    "Trạng thái xác thực": "Verification Status",
    "Đã xác thực": "Verified",
    "Chưa xác thực": "Not Verified",
    "Chưa cập nhật": "Not updated",
    "Mật khẩu hiện tại": "Current Password",
    "Mật khẩu mới": "New Password",
    "Xác nhận mật khẩu mới": "Confirm New Password",
    "Mật khẩu": "Password",
    "Nhập mật khẩu": "Enter password",
    "Nhập lại mật khẩu": "Confirm password",
    "Đổi mật khẩu": "Change Password",
    "Đăng xuất": "Logout",
    "Gửi lại mã": "Resend Code",
    "Kích hoạt tài khoản": "Activate Account",
    "Vui lòng nhập mã để hoàn tất đăng ký.": "Please enter the code to complete registration.",
    "Chúng tôi đã gửi mã xác thực gồm 6 chữ số đến email": "We have sent a 6-digit verification code to the email",
    "Không nhận được mã xác thực?": "Didn't receive the code?",
    "Nhập mã 6 chữ số": "Enter 6-digit code",
    "Chưa có tài khoản?": "Don't have an account?",
    "Đã có tài khoản?": "Already have an account?",
    "Chào mừng trở lại!": "Welcome back!",
    "Vui lòng đăng nhập để tiếp tục.": "Please login to continue.",
    "Tạo tài khoản mới": "Create a new account",
    "Trải nghiệm tính năng phân tích bài đọc IELTS cá nhân hóa cùng AI LangGraph.": "Experience personalized reading analysis with LangGraph AI.",
    "Tên đăng nhập": "Username",
    "Nhập tên đăng nhập": "Enter username",
    "Tiến trình làm bài": "Progress",
    "Lưu thay đổi": "Save Changes",
    "Hoàn thành": "Completed",
    "Số bài thi đã nộp": "Tests submitted",
    "Tỷ lệ đúng trung bình": "Average accuracy",
    "Điểm mạnh": "Strengths",
    "Điểm yếu": "Weaknesses",
    "Không có dữ liệu": "No data",
    "Đang phân tích": "Analyzing",
    "Chưa có thông tin phân tích": "No analysis available",
    "Thống kê tổng quan": "Overview Statistics",
    "Số sao hiện tại": "Current Stars",
    "Dùng để sinh bài tập mới": "Used to generate new practice tests",
    "Mua thêm sao": "Buy more stars",
    "Hệ thống phân tích điểm mạnh/yếu dựa trên lịch sử làm bài.": "The system analyzes your strengths/weaknesses based on your history.",
    "Tổng số câu hỏi đã làm": "Total questions answered",
    "Tổng thời gian làm bài": "Total time spent",
    "Tỷ lệ hoàn thành": "Completion rate",
    "Số bài đang làm": "Tests in progress",
    "IELTS AI Reading Quiz": "AI Reading Practice Quiz",
    "IELTS": "Reading",
    "giờ": "hours",
    "phút": "minutes",
    "giây": "seconds"
}

files = glob.glob('/home/likelipop/Project/ReadandQues/ReadAndQues/accounts/templates/accounts/*.html')

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for k, v in replacements.items():
        content = content.replace(k, v)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

