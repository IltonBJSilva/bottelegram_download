# Ativa o ambiente virtual
if (Test-Path -Path ".\venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Aviso: Ambiente virtual não encontrado. O bot rodará com o Python do sistema." -ForegroundColor Yellow
}

# Define a pasta raiz no PYTHONPATH para o Python encontrar o pacote 'app'
$env:PYTHONPATH = (Get-Location).Path

# Roda a aplicação
Write-Host "Iniciando o Ingestor de Mídia via Telegram..." -ForegroundColor Green
python -m app.main
