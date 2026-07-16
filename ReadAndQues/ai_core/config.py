import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI  # <-- Đổi từ AzureChatOpenAI thành ChatOpenAI
from pydantic import SecretStr
# Nạp các biến môi trường từ file .env
load_dotenv()

# Cập nhật các biến khớp 100% với thông tin từ Azure AI Foundry của bạn
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
# URL Endpoint phải giữ nguyên cụm /openai/v1 ở cuối như mẫu Microsoft cấp
AZURE_INFERENCE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://myfirstazureproject-614-resource.services.ai.azure.com/openai/v1")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-5-mini")

if not AZURE_OPENAI_API_KEY:
    raise ValueError("Lỗi: Không tìm thấy AZURE_OPENAI_API_KEY trong file .env hoặc biến môi trường!")

def get_llm():
    """
    Khởi tạo kết nối với mô hình Serverless trên Azure AI Foundry 
    bằng cách đánh lừa SDK sử dụng chuẩn OpenAI gốc.
    """
    return ChatOpenAI(
        base_url=AZURE_INFERENCE_ENDPOINT,  # Ép SDK gọi tới cổng Azure của bạn
        api_key=SecretStr(AZURE_OPENAI_API_KEY),
        model=AZURE_DEPLOYMENT_NAME,        # Tên deployment_name (ví dụ: gpt-5-mini)
        temperature=0.3,
    )