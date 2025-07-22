# Como Configurar o Bot Discord para Keys Privadas

## Passo 1: Criar o Bot no Discord

1. Acesse https://discord.com/developers/applications
2. Clique em "New Application" 
3. Dê um nome (ex: "UNITED HUB Key Bot")
4. Vá para "Bot" no menu lateral
5. Clique em "Add Bot"
6. Copie o **Token** (guarde bem!)

## Passo 2: Adicionar Bot ao Servidor

1. Vá para "OAuth2 > URL Generator"
2. Selecione:
   - **Scopes**: `bot`
   - **Bot Permissions**: 
     - Send Messages
     - Send Messages in Threads
     - Use Slash Commands
3. Copie a URL e acesse para adicionar o bot ao seu servidor

## Passo 3: Configurar a API

No seu arquivo `app.py`, a API já está configurada. Você precisa definir uma chave secreta:

```python
API_SECRET_KEY = "SUA_CHAVE_SECRETA_AQUI_123456"
```

## Passo 4: Usar a API

### Para Gerar Key Privada (POST /api/generate-private-key):

```bash
curl -X POST https://seu-app.replit.app/api/generate-private-key \
  -H "Authorization: Bearer SUA_CHAVE_SECRETA_AQUI_123456" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "123456789", "username": "NomeUsuario"}'
```

### Resposta:
```json
{
  "success": true,
  "key": "ABC123XYZ456DEF789",
  "expires_at": "2025-07-22T21:32:11.300946",
  "expires_formatted": "22/07/2025 às 21:32 UTC",
  "user_id": "123456789",
  "username": "NomeUsuario",
  "message": "Key privada gerada para NomeUsuario"
}
```

## Passo 5: Instalar e Executar o Bot

1. Instale as dependências:
```bash
pip install discord.py requests
```

2. Configure as variáveis no arquivo `discord_bot_example.py`:
```python
DISCORD_BOT_TOKEN = "seu_token_do_bot_aqui"
API_URL = "https://seu-app.replit.app"
API_SECRET = "SUA_CHAVE_SECRETA_AQUI_123456"
```

3. Execute o bot:
```bash
python discord_bot_example.py
```

## Como Usar

### No Discord:
1. No canal #keys, digite: `/gerarkey`
2. O bot enviará a key por **mensagem privada**
3. A key será válida por 24 horas

### Comandos Disponíveis:
- `/gerarkey` - Gera key privada para o usuário (só funciona no canal #keys)
- `/limparkeys` - Remove keys expiradas (só admin)
- `/status` - Verifica se o sistema está online (só admin)

## Segurança

✅ **Keys são enviadas por DM** - Outros usuários não veem
✅ **API protegida** - Precisa de chave secreta
✅ **Keys únicas** - Nunca se repetem
✅ **Expiração automática** - 24 horas
✅ **Log completo** - Tudo registrado

## URLs Importantes

- **Gerar key pública**: `GET /generate-key`
- **Gerar key privada**: `POST /api/generate-private-key` 
- **Verificar key**: `POST /verify`
- **Limpar keys**: `GET /cleanup-keys`
- **Interface principal**: `/`
- **Admin panel**: `/admin`