import discord
from discord.ext import commands
import random
from db.database import Database

db = Database()

class Dados(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dados", aliases=["craps"])
    async def dados(self, ctx, bet: int = None):

        # ===== SIN CAMBIOS EN LA LÓGICA DE JUEGO =====

        if bet is None:
            embed = discord.Embed(
                title="🎲 Juego de Dados",
                description="Tira 2 dados. Ganas con 7 u 11, pierdes con 2, 3 o 12.",
                color=discord.Color.blue()
            )
            embed.add_field(name="🎯 Reglas", value="• **7 u 11**: Ganas 2x\n• **2, 3 o 12**: Pierdes\n• **Otros números**: Punto (otro turno)", inline=False)
            embed.add_field(name="💰 Pagos", value="Ganas 2x tu apuesta", inline=True)
            embed.add_field(name="✨ Multiplicadores", value="Los multiplicadores del Gacha se aplican a tus ganancias", inline=True)
            embed.add_field(name="🎮 Uso", value="`!dados <apuesta>`", inline=False)
            await ctx.send(embed=embed)
            return

        if bet < 10:
            await ctx.send("❌ Apuesta mínima: 10 créditos")
            return

        # ============================
        # CAMBIO A SUPABASE
        # ============================
        saldo = db.get_saldo(ctx.author.id)

        if bet > saldo:
            await ctx.send(f"❌ No tienes suficientes créditos. Balance: {saldo:,}")
            return

        # Tirar dados
        dado1 = random.randint(1, 6)
        dado2 = random.randint(1, 6)
        total = dado1 + dado2

        # Determinar resultado
        gano = False
        if total in [7, 11]:
            gano = True
            resultado = "🎉 **GANASTE!**"
            multiplicador_base = 2
        elif total in [2, 3, 12]:
            gano = False  
            resultado = "💥 **CRAPS! Pierdes**"
            multiplicador_base = 0
        else:
            gano = False
            resultado = f"📊 **Punto: {total}** (Necesitas otro turno)"
            multiplicador_base = 0

        # Cálculos
        if gano:
            ganancia_base = bet * multiplicador_base

            multiplicador_gacha = 1.0
            gacha_cog = self.bot.get_cog('Gacha')

            if gacha_cog:
                multiplicador_gacha = gacha_cog.obtener_multiplicador_activo(ctx.author.id)
                if multiplicador_gacha > 1.0:
                    ganancia_final = gacha_cog.aplicar_multiplicador_ganancias(ctx.author.id, ganancia_base)
                    ganancia_neto = ganancia_final - bet
                else:
                    ganancia_final = ganancia_base
                    ganancia_neto = ganancia_base - bet
            else:
                ganancia_final = ganancia_base
                ganancia_neto = ganancia_base - bet
        else:
            ganancia_neto = -bet
            ganancia_base = 0
            ganancia_final = 0

        # ============================
        # CAMBIO A SUPABASE
        # ============================
        db.update_saldo(ctx.author.id, ganancia_neto, "win" if gano else "loss", "dados", 
                        f"Dados: {dado1}+{dado2}={total}")

        # Crear embed
        embed = discord.Embed(
            title="🎲 Juego de Dados",
            color=discord.Color.green() if gano else discord.Color.red()
        )
        
        embed.add_field(name="🎲 Dados", value=f"**{dado1}** + **{dado2}** = **{total}**", inline=False)
        embed.add_field(name="📊 Resultado", value=resultado, inline=False)
        embed.add_field(name="💰 Apuesta", value=f"**{bet:,}** créditos", inline=True)

        if gano:
            embed.add_field(name="💎 Ganancia base", value=f"**{ganancia_base:,}**", inline=True)
            embed.add_field(name="✨ Ganancia final", value=f"**{ganancia_final:,}**", inline=True)
            embed.add_field(name="💰 Ganancia neta", value=f"**+{ganancia_neto:,}**", inline=True)
        else:
            embed.add_field(name="💸 Pérdida", value=f"**-{bet:,}** créditos", inline=True)

        # ============================
        # CAMBIO A SUPABASE
        # ============================
        nuevo_saldo = db.get_saldo(ctx.author.id)
        embed.add_field(name="💳 Balance nuevo", value=f"**{nuevo_saldo:,}** créditos", inline=True)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Dados(bot))
