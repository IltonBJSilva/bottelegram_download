@echo off
echo ==============================================
echo Iniciando Ingestor de Midia Catsu via Docker
echo ==============================================
echo.

if not exist ".env" (
    echo [ERRO] O arquivo .env nao foi encontrado!
    echo Copie o arquivo .env.example para .env e coloque seu token antes de iniciar.
    pause
    exit /b
)

docker-compose up -d --build

echo.
echo ==============================================
echo Tudo pronto! O Bot esta rodando em segundo plano.
echo Para ver os logs, digite: docker-compose logs -f
echo Para parar, digite: docker-compose down
echo ==============================================
pause
