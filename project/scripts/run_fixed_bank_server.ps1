# PowerShell Script for Running the Fixed Mock Bank Server
# 文件：run_fixed_bank_server.ps1

# 停止现有的Python进程（如果有）
Write-Host "Stopping any existing Python processes..." -ForegroundColor Yellow
try {
    $existingProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
    if ($existingProcesses) {
        $existingProcesses | Where-Object {$_.MainWindowTitle -like "*mock_bank_server*"} | Stop-Process -Force
        Write-Host "Stopped existing mock bank server processes." -ForegroundColor Green
    }
} catch {
    Write-Host "No existing mock bank server processes found." -ForegroundColor Gray
}

# 设置Python环境（如有必要）
# 如果使用虚拟环境，可以在这里激活

# 定义项目路径和服务器脚本路径
$projectPath = "e:\EDBA\project"
$serverScript = "scripts\fixed_mock_bank_server.py"

# 切换到项目目录
Set-Location $projectPath

# 启动修复后的模拟银行服务器
Write-Host "Starting the fixed mock bank server..." -ForegroundColor Cyan
Start-Process python -ArgumentList "$serverScript" -NoNewWindow

# 等待服务器启动
Write-Host "Waiting for server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# 打印可访问的URL
Write-Host "Mock bank server is running!" -ForegroundColor Green
Write-Host "Access the server at: http://localhost:8001" -ForegroundColor Cyan
Write-Host "To test the server, run: python scripts\test_fixed_bank.py" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server when finished." -ForegroundColor Yellow

# 保持窗口打开，直到用户按下Ctrl+C
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    # 清理环境
    Write-Host "Stopping the server..." -ForegroundColor Yellow
    try {
        $processes = Get-Process -Name python -ErrorAction SilentlyContinue
        if ($processes) {
            $processes | Where-Object {$_.MainWindowTitle -like "*mock_bank_server*"} | Stop-Process -Force
            Write-Host "Server stopped." -ForegroundColor Green
        }
    } catch {
        Write-Host "No server process found to stop." -ForegroundColor Gray
    }
}
