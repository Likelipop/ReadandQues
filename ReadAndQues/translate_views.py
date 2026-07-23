import os
import glob

replacements = {
    "Vui lòng đăng ký trước khi xác thực.": "Please register before verifying.",
    "Tài khoản không tồn tại.": "Account does not exist.",
    "Tài khoản đã được kích hoạt.": "Account has already been activated.",
    "Xác thực tài khoản thành công! Chào mừng bạn.": "Account successfully verified! Welcome.",
    "Vui lòng đăng ký trước khi gửi lại mã.": "Please register before resending the code.",
    "Mã xác thực mới đã được gửi tới email của bạn.": "A new verification code has been sent to your email.",
    "Chào mừng {} quay trở lại!": "Welcome back, {}!",
    "Chào mừng {user.username} quay trở lại!": "Welcome back, {user.username}!",
    "Đăng xuất tài khoản thành công!": "Successfully logged out!",
    "Mật khẩu của bạn đã được cập nhật thành công!": "Your password has been successfully updated!",
    "Vui lòng sửa các lỗi bên dưới để đổi mật khẩu.": "Please fix the errors below to change your password.",
    "Không tìm thấy bài báo yêu cầu!": "Requested article not found!",
}

# specific complex ones:
replacements_accounts = {
    "Email này đã được sử dụng. Vui lòng đăng nhập hoặc dùng email khác.": "This email is already in use. Please log in or use a different email.",
    "Đăng ký tài khoản thành công! Vui lòng kiểm tra email để lấy mã xác thực.": "Registration successful! Please check your email for the verification code.",
    "Bạn đã yêu cầu gửi lại mã quá nhiều lần. Vui lòng thử lại sau 1 giờ.": "You have requested a code resend too many times. Please try again in 1 hour."
}

files = ['accounts/views.py', 'articles/views.py']

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for k, v in replacements.items():
        content = content.replace(k, v)
        
    for k, v in replacements_accounts.items():
        content = content.replace(k, v)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

