$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Setup-Environment {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Requirements
    )

    Write-Host "Creating $Name..."
    py -3 -m venv $Name
    & ".\$Name\Scripts\python.exe" -m pip install -r $Requirements
}

Setup-Environment ".venv-openai" "frameworks\openai_agents_sdk\requirements.txt"
Setup-Environment ".venv-langgraph" "frameworks\langgraph_agent\requirements.txt"
Setup-Environment ".venv-crewai" "frameworks\crewai_agent\requirements.txt"

Write-Host "All framework environments are ready."
