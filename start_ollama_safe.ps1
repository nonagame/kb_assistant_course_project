# === 1. 强制限制 Ollama 资源占用 ===
$env:OLLAMA_NUM_PARALLEL = "1"          # 只允许同时处理1个请求
$env:OLLAMA_MAX_LOADED_MODELS = "1"     # 内存里只保留1个模型
$env:OLLAMA_NUM_THREAD = "4"            # 限制使用4个CPU线程（i5-11300H是4核）
$env:OLLAMA_MAX_RAM = "8G"              # 限制Ollama最大内存占用为8GB

# === 2. 启动 Ollama 服务（后台运行）===
Write-Host "正在启动 Ollama 服务..." -ForegroundColor Green
Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden

# 等待服务就绪
Start-Sleep -Seconds 3

# === 3. 启动你的 FastAPI 项目（自动限制上下文窗口）===
Write-Host "正在启动 FastAPI 项目 (上下文窗口已限制为2048)..." -ForegroundColor Green
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

# === 4. 退出时自动清理 ===
Write-Host "按 Ctrl+C 停止服务..." -ForegroundColor Yellow

