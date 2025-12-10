import discord
from discord.ext import commands
import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def load_cogs():
    """Carga todos los cogs"""
    cogs = [
        "cogs.economy",
        "cogs.blackjack", 
        "cogs.slots",
        "cogs.ruleta",
        "cogs.dados",
        "cogs.revolver",
        "cogs.games",
        "cogs.carrera",
        "cogs.rangos",
        "cogs.moneda",
        "cogs.gacha",
        "cogs.ruletadiaria",
        "cogs.poker",
        "cogs.videopoker",
        "cogs.vincular"

    ]
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Cog cargado: {cog}")
        except Exception as e:
            print(f"❌ Error cargando {cog}: {e}")

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    print(f"📊 Conectado a {len(bot.guilds)} servidores")
    await bot.change_presence(activity=discord.Game(name="!blackjack | Casino Bot"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Comando no encontrado. Usa `!help` para ver los comandos disponibles.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Faltan argumentos. Revisa la sintaxis del comando.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Argumento inválido. Asegúrate de usar números para las apuestas.")
    else:
        await ctx.send("❌ Ha ocurrido un error inesperado.")
        print(f"Error no manejado: {error}")

@bot.command()
@commands.is_owner()
async def reload(ctx, cog: str = None):
    """Recarga un cog (solo owner)"""
    if cog:
        try:
            await bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"✅ Cog `{cog}` recargado.")
        except Exception as e:
            await ctx.send(f"❌ Error recargando `{cog}`: {e}")
    else:
        await ctx.send("❌ Especifica un cog para recargar.")

async def main():
    async with bot:
        await load_cogs()
        from config import TOKEN
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())