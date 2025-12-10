import discord
from discord.ext import commands
import httpx
import os
import logging
import datetime

logging.basicConfig(level=logging.INFO)  # Cambia a INFO para menos ruido
logger = logging.getLogger(__name__)

class Vincular(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="vincular")
    async def vincular(self, ctx, codigo: str):
        """
        Comando del bot: /vincular 12345
        """
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE")
        
        logger.info(f"Vincular código: {codigo}")
        
        try:
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            
            async with httpx.AsyncClient() as client:
                # 1. Buscar código
                url = f"{SUPABASE_URL}/rest/v1/vinculaciones_pendientes"
                params = {'codigo': f'eq.{codigo}', 'select': '*'}
                
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    logger.error(f"HTTP error: {response.status_code}")
                    await ctx.reply("❌ Error al verificar el código.")
                    return
                
                data = response.json()
                
                if not data:
                    logger.warning(f"Código no encontrado: {codigo}")
                    await ctx.reply("❌ Código inválido o expirado.")
                    return
                
                registro = data[0]
                profile_id = registro['profile_id']
                codigo_real = registro['codigo']
                expira = registro['expira']
                
                # 2. Verificar expiración (manejo simple)
                if expira:
                    from dateutil import parser
                    expira_dt = parser.isoparse(expira)
                    ahora = datetime.datetime.now(datetime.timezone.utc)
                    
                    # Si expira_dt no tiene timezone, agregar UTC
                    if expira_dt.tzinfo is None:
                        expira_dt = expira_dt.replace(tzinfo=datetime.timezone.utc)
                    
                    if ahora > expira_dt:
                        logger.warning(f"Código expirado: {codigo}")
                        await ctx.reply("❌ Código expirado. Genera uno nuevo.")
                        return
                
                # 3. Vincular Discord
                update_url = f"{SUPABASE_URL}/rest/v1/profiles"
                update_params = {'id': f'eq.{profile_id}'}
                update_data = {'discord_id': str(ctx.author.id)}
                
                update_response = await client.patch(
                    update_url,
                    headers=headers,
                    params=update_params,
                    json=update_data
                )
                
                if update_response.status_code not in [200, 204]:
                    logger.error(f"Error al vincular: {update_response.text}")
                    await ctx.reply("❌ Error al vincular la cuenta.")
                    return
                
                # 4. Eliminar código usado
                delete_url = f"{SUPABASE_URL}/rest/v1/vinculaciones_pendientes"
                delete_params = {'codigo': f'eq.{codigo_real}'}
                
                delete_response = await client.delete(
                    delete_url,
                    headers=headers,
                    params=delete_params
                )
                
                logger.info(f"Vincular exitoso para {ctx.author.id}")
                await ctx.reply(f"✅ ¡Vinculación exitosa! Tu cuenta está ahora vinculada a Discord.")
                
        except Exception as e:
            logger.error(f"Error en comando vincular: {str(e)}")
            await ctx.reply("❌ Ocurrió un error al procesar tu solicitud.")

async def setup(bot):
    await bot.add_cog(Vincular(bot))