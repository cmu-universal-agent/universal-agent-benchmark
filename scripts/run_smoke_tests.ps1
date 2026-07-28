$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$tests = @(
    @{ Name = "OpenAI Agents SDK"; Python = ".venv-openai\Scripts\python.exe"; Script = "frameworks\openai_agents_sdk\run.py" },
    @{ Name = "LangGraph"; Python = ".venv-langgraph\Scripts\python.exe"; Script = "frameworks\langgraph_agent\run.py" },
    @{ Name = "CrewAI"; Python = ".venv-crewai\Scripts\python.exe"; Script = "frameworks\crewai_agent\run.py" }
)

foreach ($test in $tests) {
    Write-Host "Running $($test.Name) smoke test..."
    if (-not (Test-Path $test.Python)) {
        Write-Warning "Missing environment: $($test.Python)"
        continue
    }
    & $test.Python $test.Script
}
