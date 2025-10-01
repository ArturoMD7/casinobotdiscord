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
        multiplicador_base = 1

        if tipo == "color":
            gano = apuesta.lower() == color_ganador
            multiplicador_base = 2
        elif tipo == "par":
            es_par = numero_ganador % 2 == 0 and numero_ganador != 0
            gano = apuesta.lower() == "par" and es_par or apuesta.lower() == "impar" and not es_par
            multiplicador_base = 2
        elif tipo == "docena":
            docena = (numero_ganador - 1) // 12 + 1 if numero_ganador > 0 else 0
            gano = int(apuesta) == docena
            multiplicador_base = 3
        elif tipo == "numero":
            gano = int(apuesta) == numero_ganador
            multiplicador_base = 36

        # Calcular pago base
        if gano:
            ganancia_base = bet * multiplicador_base
            
            # APLICAR MULTIPLICADOR DEL GACHA
            multiplicador_gacha = 1.0
            gacha_cog = self.bot.get_cog('Gacha')
            
            if gacha_cog:
                multiplicador_gacha = gacha_cog.obtener_multiplicador_activo(ctx.author.id)
                if multiplicador_gacha > 1.0:
                    # Aplicar multiplicador del Gacha a la ganancia
                    ganancia_final = gacha_cog.aplicar_multiplicador_ganancias(ctx.author.id, ganancia_base)
                else:
                    ganancia_final = ganancia_base
            else:
                ganancia_final = ganancia_base
                
            resultado_texto = f"🎉 **GANASTE** {ganancia_base:,} créditos!"
            
            # Añadir información del multiplicador si aplica
            if multiplicador_gacha > 1.0:
                resultado_texto += f"\n✨ **BONO GACHA:** {ganancia_base:,} → **{ganancia_final:,}** créditos (x{multiplicador_gacha})"
                ganancia_neto = ganancia_final
            else:
                ganancia_neto = ganancia_base
                
        else:
            ganancia_neto = -bet
            ganancia_final = 0
            resultado_texto = f"❌ **Perdiste** {bet:,} créditos"

        # Actualizar créditos en la base de datos
        db.update_credits(ctx.author.id, ganancia_neto, "win" if gano else "loss", "ruleta", 
                         f"Ruleta: {tipo} {apuesta} -> {numero_ganador}")

        # Crear embed
        embed = discord.Embed(
            title="🎡 Ruleta",
            color=discord.Color.green() if gano else discord.Color.red()
        )
        
        embed.add_field(name="🎯 Número ganador", value=f"**{numero_ganador}** {color_ganador.title()}", inline=True)
        embed.add_field(name="💰 Tu apuesta", value=f"{bet:,}cr | {tipo.title()}: {apuesta}", inline=True)
        embed.add_field(name="📈 Multiplicador", value=f"{multiplicador_base}x", inline=True)
        
        # Mostrar información del multiplicador Gacha si aplica
        if gano and multiplicador_gacha > 1.0:
            embed.add_field(
                name="✨ Multiplicador Gacha Activo", 
                value=f"**x{multiplicador_gacha}** aplicado a tu ganancia", 
                inline=False
            )
        
        embed.add_field(name="🎰 Resultado", value=resultado_texto, inline=False)
        embed.add_field(name="💳 Balance nuevo", value=f"{db.get_credits(ctx.author.id):,} créditos", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="ruletainfo")
    async def ruleta_info(self, ctx):
        embed = discord.Embed(
            title="🎡 Información de Ruleta",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Tipos de apuesta",
            value="```"
                  "color rojo/negro - 2x\n"
                  "par/impar - 2x\n" 
                  "docena 1/2/3 - 3x\n"
                  "numero 0-36 - 36x\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="💡 Ejemplos",
            value="```"
                  "!ruleta 100 color rojo\n"
                  "!ruleta 50 par impar\n"
                  "!ruleta 25 docena 2\n"
                  "!ruleta 10 numero 17\n"
                  "```",
            inline=False
        )
        
        # Información sobre multiplicadores Gacha
        embed.add_field(
            name="✨ Sistema de Multiplicadores",
            value="Los multiplicadores obtenidos en el Gacha se aplican automáticamente a tus ganancias en la ruleta",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Ruleta(bot))