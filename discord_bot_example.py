"""
EXEMPLO DE BOT DISCORD PARA GERAR KEYS PRIVADAS
Instale: pip install discord.py requests

Configure as variáveis:
- DISCORD_BOT_TOKEN: Token do seu bot Discord
- API_URL: URL do seu servidor (ex: https://seu-app.replit.app)
- API_SECRET: Sua chave secreta da API
"""

import discord
from discord.ext import commands
import requests
import os

# Configurações
DISCORD_BOT_TOKEN = "SEU_BOT_TOKEN_AQUI"
API_URL = "https://seu-app.replit.app"  # Substitua pela URL do seu app
API_SECRET = "your-secret-api-key-here"  # Mesmo valor do app.py

# Configuração do bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} conectado ao Discord!')

@bot.command(name='gerarkey')
async def gerar_key(ctx):
    """Comando /gerarkey - Gera uma key privada para o usuário"""
    
    # Verificar se está no canal correto
    if ctx.channel.name != 'keys':
        await ctx.send("❌ Este comando só funciona no canal #keys")
        return
    
    try:
        # Dados do usuário
        user_data = {
            'user_id': str(ctx.author.id),
            'username': ctx.author.display_name
        }
        
        # Headers com autenticação
        headers = {
            'Authorization': f'Bearer {API_SECRET}',
            'Content-Type': 'application/json'
        }
        
        # Fazer requisição para gerar key privada
        response = requests.post(
            f'{API_URL}/api/generate-private-key',
            json=user_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            key = data['key']
            expires = data['expires_formatted']
            
            # Enviar key por DM
            # Enviar key por DM usando webhook (mais confiável)
            dm_message = (
                f"🔑 **Sua Key Privada UNITED HUB**\n\n"
                f"**🎯 Key:** `{key}`\n"
                f"**⏰ Expira:** {expires}\n"
                f"**🕒 Duração:** 24 horas\n\n"
                f"**🌐 Site:** https://seu-app.replit.app\n\n"
                f"⚠️ **IMPORTANTE:** Mantenha sua key em segredo!\n"
                f"👤 **Gerada para:** {ctx.author.display_name}"
            )
            
            try:
                # Tentar enviar DM primeiro
                await ctx.author.send(dm_message)
                
                # Responder no canal que a key foi enviada por DM
                await ctx.send(f"✅ {ctx.author.mention}, sua key privada foi enviada por DM!")
                
            except discord.Forbidden:
                # Se não conseguir enviar DM, avisar no canal
                await ctx.send(
                    f"❌ {ctx.author.mention}, não consegui te enviar DM. "
                    f"Abra suas mensagens diretas e tente novamente."
                )
                
        else:
            await ctx.send("❌ Erro ao gerar key. Tente novamente.")
            
    except requests.exceptions.RequestException as e:
        print(f"Erro na API: {e}")
        await ctx.send("❌ Erro de conexão com o servidor. Tente novamente.")
    except Exception as e:
        print(f"Erro geral: {e}")
        await ctx.send("❌ Erro interno. Contate o administrador.")

@bot.command(name='limparkeys')
@commands.has_permissions(administrator=True)
async def limpar_keys(ctx):
    """Comando para administradores limparem keys expiradas"""
    
    try:
        response = requests.get(f'{API_URL}/cleanup-keys', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            count = data['cleaned_keys']
            await ctx.send(f"🗑️ {count} keys expiradas foram removidas do banco.")
        else:
            await ctx.send("❌ Erro ao limpar keys expiradas.")
            
    except requests.exceptions.RequestException:
        await ctx.send("❌ Erro de conexão com o servidor.")

# Comando adicional para status do sistema
@bot.command(name='status')
@commands.has_permissions(administrator=True)
async def status_sistema(ctx):
    """Comando para verificar status do sistema"""
    
    try:
        # Testar conexão com API
        response = requests.get(f'{API_URL}/admin', timeout=5)
        
        if response.status_code == 200:
            await ctx.send("✅ Sistema UNITED HUB online e funcionando!")
        else:
            await ctx.send(f"⚠️ Sistema retornou status: {response.status_code}")
            
    except requests.exceptions.RequestException:
        await ctx.send("❌ Sistema UNITED HUB offline ou inacessível.")

if __name__ == "__main__":
    # IMPORTANTE: Configure suas variáveis de ambiente ou substitua os valores
    if DISCORD_BOT_TOKEN == "SEU_BOT_TOKEN_AQUI":
        print("❌ Configure o DISCORD_BOT_TOKEN antes de executar!")
        exit(1)
    
    print("Iniciando bot Discord...")
    bot.run(DISCORD_BOT_TOKEN)