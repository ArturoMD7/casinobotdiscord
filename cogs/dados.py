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

        credits = db.get_credits(ctx.author.id)
        if bet > credits:
            await ctx.send(f"❌ No tienes suficientes créditos. Balance: {credits:,}")
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

        # Calcular ganancia base
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
                    ganancia_neto = ganancia_final - bet  # Ganancia neta después de restar la apuesta
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

        # Actualizar créditos en la base de datos
        db.update_credits(ctx.author.id, ganancia_neto, "win" if gano else "loss", "dados", 
                         f"Dados: {dado1}+{dado2}={total}")

        # Crear embed
        embed = discord.Embed(
            title="🎲 Juego de Dados",
            color=discord.Color.green() if gano else discord.Color.orange() if multiplicador_base == 0 else discord.Color.red()
        )
        
        embed.add_field(name="🎲 Dados", value=f"**{dado1}** + **{dado2}** = **{total}**", inline=False)
        embed.add_field(name="📊 Resultado", value=resultado, inline=False)
        embed.add_field(name="💰 Apuesta", value=f"**{bet:,}** créditos", inline=True)
        embed.add_field(name="📈 Multiplicador juego", value=f"**{multiplicador_base}x**", inline=True)
        
        # Mostrar información de ganancia con multiplicador si aplica
        if gano:
            if multiplicador_gacha > 1.0:
                embed.add_field(name="💎 Ganancia base", value=f"**{ganancia_base:,}** créditos", inline=True)
                embed.add_field(name="✨ Ganancia final", value=f"**{ganancia_final:,}** créditos (x{multiplicador_gacha})", inline=True)
                embed.add_field(name="💰 Ganancia neta", value=f"**+{ganancia_neto:,}** créditos", inline=True)
            else:
                embed.add_field(name="💰 Ganancia", value=f"**+{ganancia_neto:,}** créditos", inline=True)
        else:
            embed.add_field(name="💸 Pérdida", value=f"**-{bet:,}** créditos", inline=True)
            
        embed.add_field(name="💳 Balance nuevo", value=f"**{db.get_credits(ctx.author.id):,}** créditos", inline=True)
        
        # Mostrar información del multiplicador si está activo
        if multiplicador_gacha > 1.0 and gano:
            embed.add_field(
                name="🎰 Multiplicador Gacha Activo", 
                value=f"**x{multiplicador_gacha}** aplicado a tu ganancia", 
                inline=False
            )
        elif multiplicador_gacha > 1.0 and not gano:
            embed.add_field(
                name="💡 Multiplicador Disponible", 
                value=f"Tienes **x{multiplicador_gacha}** activo para tu próxima ganancia", 
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Dados(bot))