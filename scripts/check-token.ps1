# Check if SASSYMCP_AUTH_TOKEN is set at User scope
if ([Environment]::GetEnvironmentVariable("SASSYMCP_AUTH_TOKEN", "User")) {
    exit 0
} else {
    exit 1
}
