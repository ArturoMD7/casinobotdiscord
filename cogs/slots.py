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

        credits = db.get_saldo(ctx.author.id)
        if bet > credits:
            await ctx.send(f"❌ No tienes suficientes créditos. Balance: {credits:,}")
            return

        # Girar los rodillos
        reels = [random.choice(self.symbols) for _ in range(3)]
        result = "".join(reels)
        
        # Calcular ganancia base
        payout_base = 0
        win_type = "❌ Sin premio"
        
        for pattern, multiplier in self.payouts.items():
            if pattern in result:
                payout_base = int(bet * multiplier)
                win_type = f"🎉 {pattern}"
                break

        # APLICAR MULTIPLICADOR DEL GACHA
        multiplicador_activo = 1.0
        multiplicador_texto = ""
        
        # Obtener el multiplicador del sistema Gacha
        gacha_cog = self.bot.get_cog('Gacha')
        if gacha_cog:
            multiplicador_activo = gacha_cog.obtener_multiplicador_activo(ctx.author.id)
            if multiplicador_activo > 1.0:
                multiplicador_texto = f" (x{multiplicador_activo})"
                # Aplicar multiplicador solo si hay ganancia
                if payout_base > 0:
                    payout_final = gacha_cog.aplicar_multiplicador_ganancias(ctx.author.id, payout_base)
                else:
                    payout_final = payout_base
            else:
                payout_final = payout_base
        else:
            payout_final = payout_base

        # Calcular ganancia/pérdida neta
        net_win = payout_final - bet
        
        # Actualizar créditos en la base de datos
        if net_win > 0:
            db.update_saldo(ctx.author.id, net_win, "win", "slots", f"Slots: {result}{multiplicador_texto}")
        else:
            db.update_saldo(ctx.author.id, -bet, "loss", "slots", f"Slots: {result}")

        # Crear embed
        embed = discord.Embed(
            title="🎰 Tragamonedas",
            color=discord.Color.gold() if payout_final > 0 else discord.Color.red()
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
        
        # Mostrar información del premio con multiplicador si aplica
        if multiplicador_activo > 1.0 and payout_base > 0:
            embed.add_field(
                name="Premio",
                value=f"{payout_base:,} → **{payout_final:,}** créditos {multiplicador_texto}",
                inline=True
            )
        else:
            embed.add_field(
                name="Premio",
                value=f"{payout_final:,} créditos",
                inline=True
            )
        
        embed.add_field(
            name="Combinación",
            value=win_type,
            inline=True
        )
        
        # Mostrar información del multiplicador activo
        if multiplicador_activo > 1.0:
            embed.add_field(
                name="✨ Multiplicador Activo",
                value=f"**x{multiplicador_activo}** aplicado a tus ganancias",
                inline=False
            )
        
        embed.set_footer(text=f"Jugador: {ctx.author.display_name}")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Slots(bot))