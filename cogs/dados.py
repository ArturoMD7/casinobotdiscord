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
            embed.add_field(name="Pagos", value="Ganas 2x tu apuesta", inline=False)
            embed.add_field(name="Uso", value="`!dados <apuesta>`", inline=False)
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
            multiplicador = 2
        elif total in [2, 3, 12]:
            gano = False  
            resultado = "💥 **CRAPS! Pierdes**"
            multiplicador = 0
        else:
            gano = False
            resultado = f"📊 **Punto: {total}** (Necesitas otro turno)"
            multiplicador = 0

        # Calcular ganancia
        ganancia = (bet * multiplicador) - bet if gano else -bet

        db.update_credits(ctx.author.id, ganancia, "win" if gano else "loss", "dados", 
                         f"Dados: {dado1}+{dado2}={total}")

        # Embed
        embed = discord.Embed(
            title="🎲 Juego de Dados",
            color=discord.Color.green() if gano else discord.Color.orange() if multiplicador == 0 else discord.Color.red()
        )
        
        embed.add_field(name="Dados", value=f"🎲 {dado1} + 🎲 {dado2} = **{total}**", inline=False)
        embed.add_field(name="Resultado", value=resultado, inline=False)
        
        if gano:
            embed.add_field(name="Ganancia", value=f"+{bet * multiplicador:,} créditos", inline=True)
        else:
            embed.add_field(name="Pérdida", value=f"-{bet:,} créditos", inline=True)
            
        embed.add_field(name="Balance nuevo", value=f"{db.get_credits(ctx.author.id):,} créditos", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Dados(bot))