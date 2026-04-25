# MCP initialize JSON-RPC body
@{
    jsonrpc = "2.0"
    id      = 1
    method  = "initialize"
    params  = @{
        protocolVersion = "2024-11-05"
        capabilities    = @{}
        clientInfo      = @{ name = "sc"; version = "1" }
    }
} | ConvertTo-Json -Depth 5 -Compress
