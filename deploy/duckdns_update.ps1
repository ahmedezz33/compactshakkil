# محدّث DuckDNS التلقائيّ — يقرأ التوكِن من deploy\duckdns_token.txt
$ErrorActionPreference = "Stop"
$token  = (Get-Content "$PSScriptRoot\duckdns_token.txt" -Raw).Trim()
$domain = "shakkil"
try {
  $r = Invoke-RestMethod "https://www.duckdns.org/update?domains=$domain&token=$token&ip="
  "$(Get-Date -Format s)  $r" | Out-File "$PSScriptRoot\duckdns_last.txt" -Encoding ascii
} catch {
  "$(Get-Date -Format s)  ERROR $_" | Out-File "$PSScriptRoot\duckdns_last.txt" -Encoding ascii
}
