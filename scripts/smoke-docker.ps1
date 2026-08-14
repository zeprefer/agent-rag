param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$AdminEmail = "admin@example.com",
    [string]$AdminPassword = "ChangeMe123!",
    [string]$TenantName = "Demo Enterprise",
    [string]$DemoDocumentPath = "sample_data/agentic_rag_acceptance.md",
    [switch]$CreateAdmin,
    [switch]$RunModelChecks,
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Uri,
        [object]$Body = $null,
        [hashtable]$Headers = @{}
    )

    $params = @{
        Method = $Method
        Uri = $Uri
        Headers = $Headers
        TimeoutSec = 20
    }

    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 20)
    }

    Invoke-RestMethod @params
}

function Invoke-MultipartUpload {
    param(
        [string]$Uri,
        [string]$FilePath,
        [hashtable]$Headers,
        [hashtable]$Fields = @{}
    )

    Add-Type -AssemblyName System.Net.Http

    $client = [System.Net.Http.HttpClient]::new()
    foreach ($header in $Headers.GetEnumerator()) {
        $client.DefaultRequestHeaders.TryAddWithoutValidation($header.Key, [string]$header.Value) | Out-Null
    }

    $content = [System.Net.Http.MultipartFormDataContent]::new()
    foreach ($field in $Fields.GetEnumerator()) {
        $content.Add([System.Net.Http.StringContent]::new([string]$field.Value), $field.Key)
    }

    $resolvedPath = (Resolve-Path $FilePath).Path
    $stream = [System.IO.File]::OpenRead($resolvedPath)
    try {
        $fileContent = [System.Net.Http.StreamContent]::new($stream)
        $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("text/markdown")
        $content.Add($fileContent, "file", [System.IO.Path]::GetFileName($FilePath))

        $response = $client.PostAsync($Uri, $content).GetAwaiter().GetResult()
        $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            throw "Upload failed with HTTP $([int]$response.StatusCode): $body"
        }
        return $body | ConvertFrom-Json
    }
    finally {
        $stream.Dispose()
        $content.Dispose()
        $client.Dispose()
    }
}

function Wait-Ready {
    param([string]$Uri, [int]$TimeoutSeconds)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $ready = Invoke-RestMethod -Uri $Uri -TimeoutSec 5
            if ($ready.status -eq "ready") {
                return $ready
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)

    throw "API readiness check timed out: $Uri"
}

if (-not (Test-Path $DemoDocumentPath)) {
    throw "Demo document not found: $DemoDocumentPath"
}

if ($CreateAdmin) {
    Write-Step "Ensure admin user exists"
    docker compose exec api python -m app.cli create-admin --email $AdminEmail --password $AdminPassword --tenant-name $TenantName --if-not-exists
}

Write-Step "Wait for API readiness"
$ready = Wait-Ready -Uri "$BaseUrl/api/v1/ready" -TimeoutSeconds $TimeoutSeconds
Write-Host ($ready | ConvertTo-Json -Depth 10)

Write-Step "Login"
$tokenResponse = Invoke-Json -Method "POST" -Uri "$BaseUrl/api/v1/auth/login" -Body @{
    email = $AdminEmail
    password = $AdminPassword
}
$headers = @{ Authorization = "Bearer $($tokenResponse.access_token)" }
Write-Host "Logged in as $($tokenResponse.user.email)"

Write-Step "Create demo knowledge base"
$suffix = Get-Date -Format "yyyyMMddHHmmss"
$kb = Invoke-Json -Method "POST" -Uri "$BaseUrl/api/v1/admin/knowledge-bases" -Headers $headers -Body @{
    name = "Docker Smoke KB $suffix"
    description = "Synthetic, non-sensitive acceptance data created by scripts/smoke-docker.ps1"
    visibility = "tenant"
}
Write-Host "Knowledge base: $($kb.id)"

Write-Step "Upload demo document"
$document = Invoke-MultipartUpload -Uri "$BaseUrl/api/v1/admin/knowledge-bases/$($kb.id)/documents" -FilePath $DemoDocumentPath -Headers $headers -Fields @{
    title = "Synthetic Agentic RAG Acceptance Policy"
    tags = "demo,smoke"
}
Write-Host "Document: $($document.id)"

Write-Step "Trigger async indexing"
$job = Invoke-Json -Method "POST" -Uri "$BaseUrl/api/v1/admin/documents/$($document.id)/index" -Headers $headers
Write-Host "Index job: $($job.id), status: $($job.status)"

Write-Step "Read index jobs"
$jobs = Invoke-Json -Method "GET" -Uri "$BaseUrl/api/v1/admin/index-jobs?document_id=$($document.id)" -Headers $headers
Write-Host "Job count for document: $($jobs.items.Count)"

if ($RunModelChecks) {
    Write-Step "Wait for indexing completion"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        Start-Sleep -Seconds 3
        $jobs = Invoke-Json -Method "GET" -Uri "$BaseUrl/api/v1/admin/index-jobs?document_id=$($document.id)" -Headers $headers
        $latest = $jobs.items | Select-Object -First 1
        Write-Host "Latest job status: $($latest.status)"
        if ($latest.status -eq "success") {
            break
        }
        if ($latest.status -eq "failed") {
            throw "Indexing failed: $($latest.error_message)"
        }
    } while ((Get-Date) -lt $deadline)

    if ($latest.status -ne "success") {
        throw "Indexing did not complete before timeout"
    }

    Write-Step "Read generated chunks"
    $chunks = Invoke-Json -Method "GET" -Uri "$BaseUrl/api/v1/admin/documents/$($document.id)/chunks" -Headers $headers
    if ($chunks.Count -lt 1) {
        throw "Expected at least one indexed chunk"
    }
    Write-Host "Chunk count returned: $($chunks.Count)"

    Write-Step "Create chat session and ask RAG question"
    $session = Invoke-Json -Method "POST" -Uri "$BaseUrl/api/v1/chat/sessions" -Headers $headers -Body @{
        title = "Docker smoke RAG"
        knowledge_base_ids = @($kb.id)
    }
    $answer = Invoke-Json -Method "POST" -Uri "$BaseUrl/api/v1/chat/sessions/$($session.id)/messages" -Headers $headers -Body @{
        content = "What is the critical incident initial response time?"
        knowledge_base_ids = @($kb.id)
    }
    Write-Host "Assistant answer:"
    Write-Host $answer.assistant_message.content
    Write-Host "Citation count: $($answer.assistant_message.citations.Count)"

    if ($answer.assistant_message.content -notmatch "17") {
        throw "Expected the synthetic answer to contain the value 17"
    }
    if ($answer.assistant_message.citations.Count -lt 1) {
        throw "Expected the Agentic RAG answer to contain at least one persisted citation"
    }
    $agentRun = $answer.assistant_message.extra_metadata.agent_run
    if ($null -eq $agentRun -or $agentRun.tool_calls.Count -lt 1) {
        throw "Expected the Agent to execute at least one knowledge_search tool call"
    }
    Write-Host "Agent iterations: $($agentRun.iterations), tool calls: $($agentRun.tool_calls.Count)"

    Write-Step "Ask a follow-up question to verify conversation memory and grounded correction"
    $followUp = Invoke-Json -Method "POST" -Uri "$BaseUrl/api/v1/chat/sessions/$($session.id)/messages" -Headers $headers -Body @{
        content = "What is the synthetic escalation code mentioned in that same policy?"
    }
    Write-Host "Follow-up answer:"
    Write-Host $followUp.assistant_message.content
    $followUpMetadata = $followUp.assistant_message.extra_metadata
    if ($followUp.assistant_message.content -notmatch "ORBIT-742") {
        throw "Expected the follow-up answer to contain ORBIT-742"
    }
    if ($followUp.assistant_message.citations.Count -lt 1) {
        throw "Expected the follow-up answer to contain persisted citations"
    }
    if ($followUpMetadata.memory.message_count -lt 2) {
        throw "Expected at least two previous messages in conversation memory"
    }
    if ($followUpMetadata.agent_run.tool_calls.Count -lt 1) {
        throw "Expected the follow-up to execute knowledge_search"
    }
    Write-Host "Follow-up memory messages: $($followUpMetadata.memory.message_count)"
    Write-Host "Follow-up tool calls: $($followUpMetadata.agent_run.tool_calls.Count)"
}
else {
    Write-Host ""
    Write-Host "Base smoke test passed. Use -RunModelChecks after setting DASHSCOPE_API_KEY to verify vectorization and RAG answers."
}
