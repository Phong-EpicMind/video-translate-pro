#!/bin/bash

# Define terminal colors for beautiful macOS console logging
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
BLUE='\033[0;34m'
NC='\033[0;37m' # No Color

clear

echo -e "${PURPLE}=========================================================================${NC}"
echo -e "${CYAN}                    V I D E O   T R A N S L A T E   P R O${NC}"
echo -e "${BLUE}                         Lồng Tiếng & Phụ Đề AI${NC}"
echo -e "${PURPLE}=========================================================================${NC}"
echo ""

# Get the script directory path
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 1. Check Python installation
echo -e "${CYAN}[1/4] Kiểm tra môi trường Python trên macOS...${NC}"
if ! command -v python3 &> /dev/null
then
    echo -e "${RED}Lỗi: Không tìm thấy Python3 trên máy của bạn.${NC}"
    echo -e "Vui lòng cài đặt Python bằng Homebrew: 'brew install python' hoặc tải tại python.org"
    exit 1
fi
echo -e "${GREEN}✓ Đã phát hiện Python: $(python3 --version)${NC}"
echo ""

# 2. Check virtual environment
echo -e "${CYAN}[2/4] Thiết lập môi trường ảo (venv)...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Chưa phát hiện venv. Đang khởi tạo môi trường ảo mới...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Lỗi khi tạo venv.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Môi trường ảo đã sẵn sàng.${NC}"
echo ""

# Activate environment
source venv/bin/activate

# 3. Check and install dependencies
echo -e "${CYAN}[3/4] Đồng bộ và kiểm tra thư viện bổ trợ...${NC}"
pip install --upgrade pip &> /dev/null
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}Lỗi khi cài đặt các thư viện trong requirements.txt.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Thư viện hỗ trợ đã được cài đặt đầy đủ.${NC}"
echo ""

# 4. Start Server
echo -e "${CYAN}[4/4] Khởi chạy máy chủ nội bộ (FastAPI Local Server)...${NC}"
echo -e "${YELLOW}Mở trình duyệt tại địa chỉ: http://127.0.0.1:8000${NC}"
echo -e "${BLUE}Nhấn Ctrl+C để dừng ứng dụng.${NC}"
echo ""

# Function to open browser after uvicorn starts
sleep 1.5 && open "http://127.0.0.1:8000" &

# Run uvicorn server
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
