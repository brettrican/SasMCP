# Build the MCP auth header value from env var
$t = [Environment]::GetEnvironmentVariable("SASSYMCP_AUTH_TOKEN", "User")
if (-not $t) { $t = $env:SASSYMCP_AUTH_TOKEN }
if (-not $t) { return $null }
return ("Bearer " + $t)
