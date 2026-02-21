# Midia Downloader Bot (Telegram)

Bot de Telegram para baixar mídia a partir de URL com `yt-dlp`, com fluxo de confirmação:

1. Usuário escolhe `Video` ou `MP3`
2. Usuário envia URL
3. Bot mostra resumo da mídia (título, autor, duração)
4. Bot pede confirmação (`Sim`/`Nao`)
5. Bot baixa e envia o arquivo no chat

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
3. (Opcional) Defina `FFMPEG_LOCATION` apontando para a pasta `bin` do ffmpeg se o MP3 falhar por PATH

```powershell
Copy-Item .env.example .env
```

## Executar

```powershell
python bot.py
```

## Executar com Docker Compose

```powershell
docker compose up -d
```

Logs:

```powershell
docker compose logs -f
```

Parar:

```powershell
docker compose down
```

## Comandos do bot

- `/start`: inicia o fluxo
- `/help`: mostra ajuda e passo a passo
- `/about`: descricao do bot
- `/settings`: mostra formato padrao atual
- `/format <video|mp3>`: define formato padrao do usuario
- `/cancel`: cancela o fluxo atual

## Observações

- O bot usa `yt-dlp` com `noplaylist=True` para processar um item por vez.
- Para MP3, o áudio é extraído em `192kbps`.
- O bot limita para no máximo `3` downloads simultâneos (fila automática acima disso).
- O arquivo `.env` está ignorado no Git via `.gitignore`. Use `.env.example` como base.
