#!/bin/bash
# Wrapper để chạy nanobot custom từ /root/projects/nanobot
# Tách biệt config với bản official bằng HOME override

export HOME="/root"
cd /root/projects/nanobot

# Đảm bảo thư mục config tồn tại
mkdir -p "$HOME/.nanobot"

# Chạy với python3.11, inject home patch qua PYTHONSTARTUP
export PYTHONSTARTUP=/tmp/nanobot_home_patch.py

# Tạo Python startup script để patch Path.home()
cat > /tmp/nanobot_home_patch.py << 'PYEOF'
import os
from pathlib import Path

_orig_home = os.environ.get("HOME", "/root/.nanobot-sh")
_DefaultPath_home = Path.home
Path.home = classmethod(lambda cls: Path(_orig_home))
PYEOF

/usr/bin/python3.11 -m nanobot "$@"