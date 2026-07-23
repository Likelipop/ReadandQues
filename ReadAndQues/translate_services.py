import os

replacements = {
    "Đang tải tiêu đề...": "Loading title...",
    "Lỗi cơ sở dữ liệu khi tạo bài báo mới.": "Database error while creating new article.",
    "Lỗi hệ thống khi cập nhật số lượng Star.": "System error while updating stars."
}

files = ['articles/services/pipeline_orchestrator.py', 'articles/services/user_stars.py']

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for k, v in replacements.items():
        content = content.replace(k, v)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

