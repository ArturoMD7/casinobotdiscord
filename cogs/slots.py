import discord
from discord.ext import commands
import random
from db.database import Database

db = Database()

class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "⭐", "💎", "7️⃣"]
        self.payouts = {
            "7️⃣7️⃣7️⃣": 50,
            "💎💎💎": 25,
            "⭐⭐⭐": 15,
            "🔔🔔🔔": 10,
            "🍇🍇🍇": 8,
            "🍊🍊🍊": 5,
            "🍋🍋🍋": 3,
            "🍒🍒🍒": 2,
            "🍒🍒": 1.5,
            "🍒": 1
        }

    @commands.command(name="slots", aliases=["traga", "slot"])
    async def slots(self, ctx, bet: int = None):
        if bet is None:
            embed = discord.Embed(
                title="🎰 Tragamonedas",
                description="Usa: `!slots <apuesta>`\nApuesta mínima: 10 créditos",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        if bet < 10:
            await ctx.send("❌ Apuesta mínima: 10 créditos")
            return

        credits = db.get_credits(ctx.author.id)
        if bet > credits:
            await ctx.send(f"❌ No tienes suficientes créditos. Balance: {credits:,}")
            return

        # Girar los rodillos
        reels = [random.choice(self.symbols) for _ in range(3)]
        result = "".join(reels)
        
        # Calcular ganancia
        payout = 0
        win_type = "❌ Sin premio"
        
        for pattern, multiplier in self.payouts.items():
            if pattern in result:
                payout = int(bet * multiplier)
                win_type = f"🎉 {pattern}"
                break

        # Actualizar créditos
        net_win = payout - bet
        db.update_credits(ctx.author.id, net_win, "win" if net_win > 0 else "loss", "slots", f"Slots: {result}")

        # Crear embed
        embed = discord.Embed(
            title="🎰 Tragamonedas",
            color=discord.Color.gold() if payout > 0 else discord.Color.red()
        )
        
        embed.add_field(
            name="Resultado",
            value=f"```\n{reels[0]} | {reels[1]} | {reels[2]}\n```",
            inline=False
        )
        
        embed.add_field(
            name="Apuesta",
            value=f"{bet:,} créditos",
            inline=True
        )
        
        embed.add_field(
            name="Premio",
            value=f"{payout:,} créditos" if payout > 0 else "0 créditos",
            inline=True
        )
        
        embed.add_field(
            name="Resultado",
            value=win_type,
            inline=False
        )
        
        embed.set_footer(text=f"Jugador: {ctx.author.display_name}")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Slots(bot))