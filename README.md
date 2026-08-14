# Sistema de Ingestão de Mídia via Telegram

Sistema automatizado projetado para receber fotos e vídeos diretamente de cinegrafistas através de chats do Telegram, realizar o download para um servidor local (suportando arquivos gigantes) e organizar tudo em pastas com suporte a retomada em caso de falhas e queda de energia.

## Arquitetura (Fase Atual)

O sistema atual (Fase 2 completa) utiliza:
- **aiogram**: Comunicação veloz e assíncrona com o Telegram.
- **aiosqlite**: Banco de dados não bloqueante que garante que mensagens não sejam perdidas.
- **Fila em Memória**: Arquivos vão para uma fila de download; se a energia cair, o sistema lê o banco no boot e volta a baixar de onde parou.
- **Telegram Local API Server** (Recomendado): Permite contornar a limitação de 20MB de download do Telegram, autorizando o bot a puxar arquivos de vídeo pesados (até 2GB por arquivo).

---

## 🚀 Como Instalar e Rodar (O Jeito Fácil)

Para não precisar instalar o Python ou configurar terminais nos computadores do evento, nós empacotamos o bot inteiro via **Docker**. Isso também permite baixar vídeos maiores que 20MB!

1. Baixe e instale o [Docker Desktop](https://www.docker.com/products/docker-desktop/) na máquina.
2. Copie a pasta inteira do projeto para o PC.
3. Copie o arquivo `.env.example` e renomeie para `.env`.
4. Preencha o `.env` com suas credenciais (Veja o passo "Obtendo API_ID" abaixo).
5. Dê dois cliques no arquivo `start_docker.bat`.

Pronto! O bot vai baixar tudo e salvar na pasta `media/`.
Para parar o bot, dê dois cliques em `stop_docker.bat`.

---

### 🔑 Obtendo TELEGRAM_API_ID e TELEGRAM_API_HASH
Para baixar arquivos grandes (via servidor local), o Telegram exige essas duas chaves (elas são gratuitas):
1. Acesse [my.telegram.org](https://my.telegram.org) e faça login.
2. Vá em **API development tools**.
3. Crie um novo aplicativo (pode colocar qualquer nome) e copie o `api_id` e `api_hash`.
4. Cole esses valores no seu arquivo `.env`!

---

### 💻 Como Instalar (Modo Desenvolvedor)

Se você quiser rodar sem o Docker (limite de 20MB):
Abra o **PowerShell** na pasta raiz e execute:

```powershell
.\setup.ps1
cp .env.example .env
# Edite o .env e depois rode:
.\run.ps1
```

### 3. Rodar a Aplicação

Para iniciar o seu bot Ingestor, execute:
```powershell
.\run.ps1
```

---

## 🐳 Suporte a Vídeos Grandes (Local API Server)

Para vídeos grandes (> 20MB), a API padrão do Telegram não é suficiente. 

Para resolver isso, você deve subir o servidor local oficial do Telegram (via Docker) na mesma rede da aplicação. 

1. Tenha o Docker instalado.
2. Adicione `TELEGRAM_API_ID` e `TELEGRAM_API_HASH` (obtidos em my.telegram.org) no seu arquivo `.env`.
3. Adicione também `TELEGRAM_API_SERVER=http://localhost:8081` no seu `.env`.
4. Rode:
```powershell
docker-compose up -d
```
Após o container subir, abra outro terminal e execute o Ingestor (`.\run.ps1`). Ele passará automaticamente a baixar arquivos através do limite irrestrito do seu Local Server.

---

## 🔄 Roadmap e Funcionalidades

- [x] Fase 1: Setup Inicial, Banco SQLite e Captação de Mensagens
- [x] Fase 2: Workers Paralelos, Filas de Recuperação e Retry Progressivo
- [ ] Fase 3: Organização de Pastas Dinâmicas por Data, Verificação HASH SHA-256 e Comandos.
- [ ] Fase 4: Métricas avançadas, interface de acompanhamento local (opcional).
