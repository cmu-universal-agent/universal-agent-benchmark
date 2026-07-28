param(
    [string]$PythonExecutable = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($PythonExecutable) {
    if (-not (Test-Path -LiteralPath $PythonExecutable)) {
        throw "Python executable not found: $PythonExecutable"
    }
    $pythonCommand = $PythonExecutable
    $pythonPrefixArgs = @()
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCommand = "py"
    $pythonPrefixArgs = @("-3")
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCommand = "python"
    $pythonPrefixArgs = @()
}
else {
    throw "No Python interpreter found. Pass -PythonExecutable with a Python 3 path."
}

function Setup-Environment {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Requirements
    )

    Write-Host "Creating $Name..."
    & $pythonCommand @pythonPrefixArgs -m venv $Name
    & ".\$Name\Scripts\python.exe" -m pip install -r $Requirements
}

Setup-Environment ".venv-openai" "frameworks\openai_agents_sdk\requirements.txt"
Setup-Environment ".venv-langgraph" "frameworks\langgraph_agent\requirements.txt"
Setup-Environment ".venv-crewai" "frameworks\crewai_agent\requirements.txt"

Write-Host "All framework environments are ready."
