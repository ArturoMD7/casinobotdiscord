import discord
from discord.ext import commands
from db.database import Database
from config import STARTING_CREDITS
import time
import random

db = Database()

# Diccionario para guardar los últimos daily de cada usuario
last_daily = {}

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="balance", aliases=["bal", "credits"])
    async def balance(self, ctx):
        """Muestra el balance de créditos del usuario"""
        credits = db.get_credits(ctx.author.id)
        await ctx.send(f"💰 {ctx.author.mention}, tienes **{credits:,}** créditos.")

    @commands.command(name="stats")
    async def stats(self, ctx):
        """Muestra las estadísticas del usuario"""
        stats = db.get_user_stats(ctx.author.id)
        
        if stats:
            win_rate = (stats['games_won'] / stats['games_played'] * 100) if stats['games_played'] > 0 else 0
            
            embed = discord.Embed(
                title=f"📊 Estadísticas de {ctx.author.display_name}",
                color=discord.Color.blue()
            )
            embed.add_field(name="🎮 Partidas Jugadas", value=f"{stats['games_played']:,}", inline=True)
            embed.add_field(name="🏆 Partidas Ganadas", value=f"{stats['games_won']:,}", inline=True)
            embed.add_field(name="📈 Ratio de Victorias", value=f"{win_rate:.1f}%", inline=True)
            embed.add_field(name="💰 Ganancias Totales", value=f"{stats['total_winnings']:,} créditos", inline=True)
            embed.add_field(name="💳 Créditos Actuales", value=f"{stats['credits']:,} créditos", inline=True)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ No se pudieron cargar tus estadísticas.")

    @commands.command(name="daily")
    async def daily(self, ctx):
        """Reclama créditos diarios (solo una vez cada 24 horas)"""
        user_id = ctx.author.id
        current_time = time.time()
        daily_amount = 500  # Cantidad de créditos diarios
        
        # Verificar si ya reclamó el daily hoy
        if user_id in last_daily:
            last_claim = last_daily[user_id]
            time_since_last_claim = current_time - last_claim
            hours_since = time_since_last_claim / 3600
            
            if hours_since < 24:
                hours_remaining = 24 - hours_since
                await ctx.send(
                    f"⏰ {ctx.author.mention} ya reclamaste tu daily hoy.\n"
                    f"**Tiempo restante:** {hours_remaining:.1f} horas"
                )
                return
        
        # Dar los créditos diarios
        db.update_credits(user_id, daily_amount, "bonus", "daily", "Recompensa diaria")
        last_daily[user_id] = current_time
        
        embed = discord.Embed(
            title="🎁 Recompensa Diaria",
            description=f"¡Has reclamado tu recompensa diaria!",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 Créditos obtenidos", value=f"**+{daily_amount:,}** créditos", inline=True)
        embed.add_field(name="💳 Balance actual", value=f"**{db.get_credits(user_id):,}** créditos", inline=True)
        embed.add_field(name="⏰ Próximo daily", value="En 24 horas", inline=False)
        embed.set_footer(text="Vuelve mañana para otra recompensa")
        
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["top", "ranking"])
    async def leaderboard(self, ctx):
        """Muestra el ranking de los 10 jugadores más ricos"""
        try:
            # Obtener top 10 usuarios por créditos
            cursor = db.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT user_id, credits, games_played, games_won 
                FROM users 
                ORDER BY credits DESC 
                LIMIT 10
            """)
            top_users = cursor.fetchall()
            cursor.close()
            
            embed = discord.Embed(
                title="🏆 Leaderboard - Top 10 Más Ricos",
                color=discord.Color.gold()
            )
            
            if top_users:
                leaderboard_text = ""
                for i, user_data in enumerate(top_users, 1):
                    user_id = user_data['user_id']
                    
                    # Intentar obtener el usuario de Discord
                    user = self.bot.get_user(user_id)
                    if user:
                        username = f"@{user.display_name}"
                    else:
                        # Si no está en cache, intentar buscarlo
                        try:
                            user = await self.bot.fetch_user(user_id)
                            username = f"@{user.display_name}"
                        except:
                            username = f"Usuario {user_id}"
                    
                    medal = ""
                    if i == 1:
                        medal = "🥇 "
                    elif i == 2:
                        medal = "🥈 "
                    elif i == 3:
                        medal = "🥉 "
                    
                    leaderboard_text += f"**{medal}{i}. {username}** - {user_data['credits']:,} créditos\n"
                
                embed.description = leaderboard_text
            else:
                embed.description = "No hay datos todavía. ¡Sé el primero en jugar!"
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ Error al cargar el leaderboard.")
            print(f"Error en leaderboard: {e}")

    @commands.command(name="transfer", aliases=["pay"])
    async def transfer(self, ctx, member: discord.Member, amount: int):
        """Transfiere créditos a otro usuario"""
        if amount <= 0:
            await ctx.send("❌ La cantidad debe ser mayor a 0.")
            return
        
        if member.id == ctx.author.id:
            await ctx.send("❌ No puedes transferirte créditos a ti mismo.")
            return
        
        sender_credits = db.get_credits(ctx.author.id)
        if amount > sender_credits:
            await ctx.send(f"❌ No tienes suficientes créditos. Tu balance: {sender_credits:,}")
            return
        
        # Realizar transferencia
        db.update_credits(ctx.author.id, -amount, "transfer", "transfer", f"Transferido a {member.display_name}")
        db.update_credits(member.id, amount, "transfer", "transfer", f"Recibido de {ctx.author.display_name}")
        
        embed = discord.Embed(
            title="💸 Transferencia Exitosa",
            color=discord.Color.green()
        )
        embed.add_field(name="De", value=ctx.author.mention, inline=True)
        embed.add_field(name="Para", value=member.mention, inline=True)
        embed.add_field(name="Cantidad", value=f"{amount:,} créditos", inline=True)
        embed.add_field(name="Tu nuevo balance", value=f"{db.get_credits(ctx.author.id):,} créditos", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="rob")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hora de cooldown
    async def rob(self, ctx, member: discord.Member):
        """Intenta robar créditos a otro usuario (50% de éxito)"""
        if member.id == ctx.author.id:
            await ctx.send("❌ No puedes robarte a ti mismo.")
            return
        
        target_credits = db.get_credits(member.id)
        if target_credits < 100:
            await ctx.send("❌ El usuario objetivo no tiene suficientes créditos (mínimo 100).")
            return
        
        # 50% de probabilidad de éxito
        success = random.random() < 0.5
        max_rob = min(target_credits // 4, 1000)  # Robar hasta 25% o 1000 créditos
        amount = random.randint(100, max_rob)
        
        if success:
            # Robo exitoso
            db.update_credits(ctx.author.id, amount, "bonus", "rob", f"Robado a {member.display_name}")
            db.update_credits(member.id, -amount, "loss", "rob", f"Robado por {ctx.author.display_name}")
            
            embed = discord.Embed(
                title="🎭 Robo Exitoso!",
                description=f"¡Le robaste {amount:,} créditos a {member.mention}!",
                color=discord.Color.green()
            )
        else:
            # Robo fallido - multa
            fine = amount // 2
            db.update_credits(ctx.author.id, -fine, "loss", "rob", f"Intento fallido contra {member.display_name}")
            
            embed = discord.Embed(
                title="🚨 Robo Fallido!",
                description=f"¡Te atraparon intentando robar a {member.mention}! Multa: {fine:,} créditos.",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)

    @rob.error
    async def rob_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            remaining = error.retry_after
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await ctx.send(f"⏰ Puedes intentar robar again en {hours}h {minutes}m")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Debes mencionar a un usuario: `!rob @usuario`")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Usuario no encontrado. Asegúrate de mencionar a un usuario válido.")

async def setup(bot):
    await bot.add_cog(Economy(bot))