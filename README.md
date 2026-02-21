# Midia Downloader Bot (Telegram)

Bot de Telegram para baixar mídia a partir de URL com `yt-dlp`, com fluxo de confirmação:

1. Usuário escolhe `Video` ou `MP3`
2. Usuário envia URL
3. Bot mostra resumo da mídia (título, autor, duração)
4. Bot pede confirmação (`Sim`/`Nao`)
5. Bot baixa e envia o arquivo no chat

## Funcionalidades

- Fluxo guiado com confirmação antes do download
- Escolha de formato por download (`Video` ou `MP3`)
- Formato padrão por usuário via `/format`
- Renomeação automática opcional via `/rename` (com botões `ON/OFF`)
- Limite de concorrência com fila automática (3 downloads simultâneos)
- Comandos de monitoramento: `/ping`, `/status`, `/queue`
- Comando `/feedback` para enviar sugestões/erros ao criador (via `ADMIN_CHAT_ID`)
- Tratamento de falhas de rede e erros inesperados com mensagens amigáveis

## Estrutura do projeto

```text
app/
  config.py                # Carrega variáveis de ambiente
  constants.py             # Estados e constantes da conversa
  main.py                  # Criação e execução da aplicação Telegram
  handlers/
    conversation.py        # Fluxo de conversa com o usuário
  services/
    media_service.py       # Integração com yt-dlp (resumo e download)
  utils/
    text_utils.py          # Normalização e helpers de texto
bot.py                     # Entrypoint simples
```

## Requisitos

- Python 3.10+
- `ffmpeg` instalado no sistema (obrigatório para saída em MP3)

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuração

1. Copie `.env.example` para `.env`
2. Defina `TELEGRAM_BOT_TOKEN` com o token do BotFather
3. (Opcional) Defina `ADMIN_CHAT_ID` com o chat id que receberá mensagens do comando `/feedback`
4. (Opcional) Defina `FFMPEG_LOCATION` apontando para a pasta `bin` do ffmpeg se o MP3 falhar por PATH

```powershell
Copy-Item .env.example .env
```

## Executar

```powershell
python bot.py
```

## Executar com Docker Compose

Primeira execução (ou após mudar dependências/Dockerfile):

```powershell
docker compose up -d --build
```

Execuções seguintes (sem rebuild):

```powershell
docker compose up -d
```

Logs:

```powershell
docker compose logs -f
```

Este projeto já está configurado com rotação de logs no `docker-compose.yml`:

- `max-size: 10m`
- `max-file: 3`

Parar:

```powershell
docker compose down
```

Reiniciar rápido (sem rebuild):

```powershell
docker compose restart
```

## Comandos do bot

- `/start`: inicia o fluxo
- `/help`: mostra ajuda e passo a passo
- `/about`: descricao do bot
- `/settings`: mostra configuracoes atuais
- `/format <video|mp3>`: define formato padrao do usuario
- `/rename`: ativa/desativa renomeacao automatica (com teclado de botoes)
- `/ping`: verifica se o bot esta online
- `/status`: mostra status da sessao do usuario
- `/queue`: mostra fila e downloads em andamento
- `/feedback`: envia sugestao/erro para o criador do bot
- `/cancel`: cancela o fluxo atual

## Observações

- O bot usa `yt-dlp` com `noplaylist=True` para processar um item por vez.
- Para MP3, o áudio é extraído em `192kbps`.
- O bot limita para no máximo `3` downloads simultâneos (fila automática acima disso).
- Em casos de bloqueio do Instagram (rate-limit/login), o bot responde com mensagem genérica amigável.
- Em instabilidade de conexão com Telegram, os comandos fazem nova tentativa automática antes de falhar.
- O arquivo `.env` está ignorado no Git via `.gitignore`. Use `.env.example` como base.
