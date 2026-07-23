import os

replacements = {
    # accounts/templates/accounts/profile.html
    "Cần thêm Star?": "Need more Stars?",
    "Mỗi lượt import bài báo tiêu tốn 1 Star. Nếu hết, hãy liên hệ với chúng tôi để nhận thêm.": "Each article import costs 1 Star. If you run out, please contact us to receive more.",
    "<span>📊</span> Thống kê hoạt động": "<span>📊</span> Activity Statistics",
    "Stars còn lại": "Stars remaining",
    "Số ngày đăng nhập": "Login days",
    "{{ profile.login_days_count }} ngày": "{{ profile.login_days_count }} days",
    "Bài báo đã thực hiện": "Articles completed",
    "{{ total_articles }} bài": "{{ total_articles }} articles",
    "Điểm streak hiện tại": "Current streak",
    "<span>🔒</span> Bảo mật & Change Password": "<span>🔒</span> Security & Change Password",
    "Chúng tôi tuân thủ các chuẩn mã hóa bảo mật tiên tiến nhất để bảo vệ thông tin mật khẩu của bạn.": "We adhere to the most advanced security encryption standards to protect your password information.",
    "Cập nhật mật khẩu mới": "Update new password",
    
    # articles/templates/articles/all_tests.html
    "All thể loại": "All genres",

    # accounts/views.py
    "Yêu cầu xử lý quá nhanh. Vui lòng thử lại sau giây lát.": "Request processed too fast. Please try again in a moment.",
    "Yêu cầu không hợp lệ.": "Invalid request.",
    "Tên đăng nhập không được để trống.": "Username cannot be empty.",
    "Tên đăng nhập chỉ chứa chữ cái, chữ số và dấu gạch dưới.": "Username can only contain letters, numbers, and underscores.",
    "Tên đăng nhập phải dài ít nhất 4 ký tự.": "Username must be at least 4 characters long.",
    "Tên đăng nhập đã tồn tại.": "Username already exists.",
    "Email không được để trống.": "Email cannot be empty.",
    "Email không đúng định dạng.": "Invalid email format.",
    "Email đã được sử dụng.": "Email is already in use.",
    "Mật khẩu không được để trống.": "Password cannot be empty.",
    "Mật khẩu phải dài ít nhất 6 ký tự.": "Password must be at least 6 characters long.",
    "Vui lòng xác nhận mật khẩu.": "Please confirm your password.",
    "Mật khẩu xác nhận không khớp.": "Passwords do not match.",
    "Mã xác thực đăng ký tài khoản (Gửi lại)": "Account Registration Verification Code (Resend)",
    "Mã xác thực đăng ký tài khoản": "Account Registration Verification Code",
    "Mã xác thực của bạn là: {code}. Mã có hiệu lực trong 5 phút.": "Your verification code is: {code}. The code is valid for 5 minutes.",
    "Hệ thống gặp sự cố khi gửi email xác thực. Vui lòng kiểm tra terminal console để lấy mã OTP.": "System encountered an error sending verification email. Please check the terminal console for the OTP.",
    "Mã xác thực đã được gửi tới email của bạn. Vui lòng xác thực.": "A verification code has been sent to your email. Please verify.",
    "Vui lòng nhập mã xác thực.": "Please enter the verification code.",
    "Mã xác thực phải gồm 6 chữ số.": "The verification code must be 6 digits.",
    "Mã xác thực đã hết hạn. Vui lòng gửi lại mã mới.": "The verification code has expired. Please resend a new code.",
    "Mã xác thực đã hết hạn.": "The verification code has expired.",
    "Mã xác thực không chính xác.": "Incorrect verification code.",
    "Không tìm thấy yêu cầu xác thực. Vui lòng gửi lại mã mới.": "Verification request not found. Please resend a new code.",
    "Vui lòng đợi {wait_seconds} giây trước khi gửi lại mã.": "Please wait {wait_seconds} seconds before resending the code.",
    "Mã xác thực mới của bạn là: {code}. Mã có hiệu lực trong 5 phút.": "Your new verification code is: {code}. The code is valid for 5 minutes.",
    "Vui lòng đợi vài giây trước khi thử lại.": "Please wait a few seconds before trying again.",
    "Vui lòng nhập tên đăng nhập hoặc email.": "Please enter your username or email.",
    "Vui lòng nhập mật khẩu.": "Please enter your password.",
    "Tên đăng nhập/Email hoặc mật khẩu không chính xác.": "Incorrect Username/Email or password.",

    # accounts/tests.py
    "giây trước khi gửi lại mã.": "seconds before resending the code.",
    "Vui lòng sửa các lỗi bên dưới": "Please fix the errors below",
    "Bạn đã hết Star!": "You are out of Stars!",

    # articles/views.py
    "Không tìm thấy bài báo.": "Article not found.",
    
    # articles/services/cleaning.py
    "Lỗi khi cào nội dung bài báo.": "Error scraping article content."
}

files = [
    '/home/likelipop/Project/ReadandQues/ReadAndQues/accounts/templates/accounts/profile.html',
    '/home/likelipop/Project/ReadandQues/ReadAndQues/articles/templates/articles/all_tests.html',
    '/home/likelipop/Project/ReadandQues/ReadAndQues/accounts/views.py',
    '/home/likelipop/Project/ReadandQues/ReadAndQues/accounts/tests.py',
    '/home/likelipop/Project/ReadandQues/ReadAndQues/articles/views.py',
    '/home/likelipop/Project/ReadandQues/ReadAndQues/articles/services/cleaning.py'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for k, v in replacements.items():
        content = content.replace(k, v)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
