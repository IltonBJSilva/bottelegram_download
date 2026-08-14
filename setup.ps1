# Cria o ambiente virtual se não existir
if (-not (Test-Path -Path "venv")) {
    Write-Host "Criando ambiente virtual (venv)..." -ForegroundColor Green
    python -m venv venv
}

# Ativa o ambiente virtual
Write-Host "Ativando ambiente virtual..." -ForegroundColor Green
.\venv\Scripts\Activate.ps1

# Atualiza pip
Write-Host "Atualizando pip..." -ForegroundColor Green
python -m pip install --upgrade pip

# Instala os requisitos
Write-Host "Instalando dependências..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host "Configuração concluída! Crie ou edite seu arquivo .env, e depois use .\run.ps1 para iniciar o bot." -ForegroundColor Cyan
