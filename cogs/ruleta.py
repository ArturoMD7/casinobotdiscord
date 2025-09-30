import discord
from discord.ext import commands
import random
from db.database import Database

db = Database()

class Ruleta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.numbers = list(range(0, 37))  # 0-36
        self.colors = {
            **{i: "rojo" for i in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]},
            **{i: "negro" for i in [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]},
            0: "verde"
        }

    @commands.command(name="ruleta", aliases=["roulette"])
    async def ruleta(self, ctx, bet: int, tipo: str, apuesta: str):
        tipos_validos = ["color", "par", "docena", "numero"]
        if tipo not in tipos_validos:
            await ctx.send(f"❌ Tipos válidos: {', '.join(tipos_validos)}")
            return

        if bet < 10:
            await ctx.send("❌ Apuesta mínima: 10 créditos")
            return

        credits = db.get_credits(ctx.author.id)
        if bet > credits:
            await ctx.send(f"❌ No tienes suficientes créditos. Balance: {credits:,}")
            return

        # Girar ruleta
        numero_ganador = random.choice(self.numbers)
        color_ganador = self.colors[numero_ganador]

        # Verificar ganancia
        gano = False
        multiplicador = 1

        if tipo == "color":
            gano = apuesta.lower() == color_ganador
            multiplicador = 2
        elif tipo == "par":
            es_par = numero_ganador % 2 == 0 and numero_ganador != 0
            gano = apuesta.lower() == "par" and es_par or apuesta.lower() == "impar" and not es_par
            multiplicador = 2
        elif tipo == "docena":
            docena = (numero_ganador - 1) // 12 + 1 if numero_ganador > 0 else 0
            gano = int(apuesta) == docena
            multiplicador = 3
        elif tipo == "numero":
            gano = int(apuesta) == numero_ganador
            multiplicador = 36

        # Calcular pago
        if gano:
            ganancia = bet * multiplicador
            resultado_texto = f"🎉 **GANASTE** {ganancia:,} créditos!"
        else:
            ganancia = -bet
            resultado_texto = f"❌ **Perdiste** {bet:,} créditos"

        db.update_credits(ctx.author.id, ganancia, "win" if gano else "loss", "ruleta", 
                         f"Ruleta: {tipo} {apuesta} -> {numero_ganador}")

        # Embed
        embed = discord.Embed(
            title="🎡 Ruleta",
            color=discord.Color.green() if gano else discord.Color.red()
        )
        
        embed.add_field(name="Número ganador", value=f"**{numero_ganador}** {color_ganador.title()}", inline=True)
        embed.add_field(name="Tu apuesta", value=f"{tipo.title()}: {apuesta}", inline=True)
        embed.add_field(name="Multiplicador", value=f"{multiplicador}x", inline=True)
        embed.add_field(name="Resultado", value=resultado_texto, inline=False)
        embed.add_field(name="Balance nuevo", value=f"{db.get_credits(ctx.author.id):,} créditos", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="ruletainfo")
    async def ruleta_info(self, ctx):
        embed = discord.Embed(
            title="🎡 Información de Ruleta",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Tipos de apuesta",
            value="```"
                  "color rojo/negro - 2x\n"
                  "par/impar - 2x\n" 
                  "docena 1/2/3 - 3x\n"
                  "numero 0-36 - 36x\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="Ejemplos",
            value="```"
                  "!ruleta 100 color rojo\n"
                  "!ruleta 50 par impar\n"
                  "!ruleta 25 docena 2\n"
                  "!ruleta 10 numero 17\n"
                  "```",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Ruleta(bot))