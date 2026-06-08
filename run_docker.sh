#!/bin/bash

# 確保本機 X11 顯示服務授權給 Docker 容器
echo "=================================================="
if command -v xhost >/dev/null 2>&1; then
    echo "正在授權 Docker 容器存取本機 X11 顯示服務..."
    xhost +local:docker
else
    echo "[資訊] 未偵測到 xhost 指令，跳過本機 X11 顯示授權設定（若不需圖形界面或 X11 已就緒可忽略）"
fi
echo "=================================================="

# 啟動 docker-compose 編譯並執行
echo "正在啟動 Docker 容器並執行監控程式..."
docker compose up --build

# 結束時撤銷 X11 授權以策安全
if command -v xhost >/dev/null 2>&1; then
    echo ""
    echo "=================================================="
    echo "正在撤銷 X11 顯示服務的 Docker 存取授權..."
    xhost -local:docker
    echo "=================================================="
fi
