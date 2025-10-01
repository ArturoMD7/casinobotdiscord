import discord
from discord.ext import commands
from db.database import Database
from config import STARTING_CREDITS, RANGOS, BONOS_RANGO
import time
import random

db = Database()

# Diccionario para guardar los últimos daily de cada usuario
last_daily = {}

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def calcular_rango(self, creditos: int) -> int:
        """Calcula el rango basado en los créditos"""
        rango_actual = 0
        for rango_id, datos in RANGOS.items():
            if creditos >= datos["min_creditos"]:
                rango_actual = rango_id
            else:
                break
        return rango_actual

    @commands.command(name="balance", aliases=["bal", "credits"])
    async def balance(self, ctx):
        """Muestra el balance de créditos del usuario"""
        credits = db.get_credits(ctx.author.id)
        rango_actual = self.calcular_rango(credits)
        rango_info = RANGOS[rango_actual]
        
        embed = discord.Embed(
            title=f"💰 Balance de {ctx.author.display_name}",
            color=rango_info['color']
        )
        embed.add_field(name="💳 Créditos", value=f"**{credits:,}** créditos", inline=True)
        embed.add_field(name="🎯 Rango", value=f"**{rango_info['nombre']}**", inline=True)
        
        # Mostrar bono actual si existe
        if rango_actual in BONOS_RANGO:
            bono_actual = BONOS_RANGO[rango_actual]
            embed.add_field(
                name="🎁 Beneficios", 
                value=f"Daily: +{bono_actual['bono_daily']}\nMulti: x{bono_actual['multiplicador_ganancias']}", 
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="stats")
    async def stats(self, ctx):
        """Muestra las estadísticas del usuario"""
        stats = db.get_user_stats(ctx.author.id)
        
        if stats:
            win_rate = (stats['games_won'] / stats['games_played'] * 100) if stats['games_played'] > 0 else 0
            rango_actual = self.calcular_rango(stats['credits'])
            rango_info = RANGOS[rango_actual]
            
            embed = discord.Embed(
                title=f"📊 Estadísticas de {ctx.author.display_name}",
                color=rango_info['color']
            )
            embed.add_field(name="🎯 Rango", value=f"**{rango_info['nombre']}**", inline=True)
            embed.add_field(name="💳 Créditos", value=f"**{stats['credits']:,}**", inline=True)
            embed.add_field(name="🎮 Partidas", value=f"**{stats['games_played']:,}**", inline=True)
            embed.add_field(name="🏆 Victorias", value=f"**{stats['games_won']:,}**", inline=True)
            embed.add_field(name="📈 Ratio", value=f"**{win_rate:.1f}%**", inline=True)
            embed.add_field(name="💰 Ganancias Totales", value=f"**{stats['total_winnings']:,}**", inline=True)
            
            # Mostrar progreso al siguiente rango
            if rango_actual < max(RANGOS.keys()):
                siguiente_rango = RANGOS[rango_actual + 1]
                faltante = siguiente_rango['min_creditos'] - stats['credits']
                if faltante > 0:
                    embed.add_field(
                        name="🎯 Próximo Rango", 
                        value=f"**{siguiente_rango['nombre']}**\nFaltan: **{faltante:,}** créditos", 
                        inline=False
                    )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ No se pudieron cargar tus estadísticas.")

    @commands.command(name="daily")
    async def daily(self, ctx):
        """Reclama créditos diarios (con bonus por rango)"""
        user_id = ctx.author.id
        current_time = time.time()
        
        # Obtener créditos actuales y calcular rango
        credits = db.get_credits(user_id)
        rango_actual = self.calcular_rango(credits)
        
        # Calcular daily base + bono de rango
        daily_base = 500
        bono_rango = BONOS_RANGO.get(rango_actual, {"bono_daily": 0})["bono_daily"]
        daily_total = daily_base + bono_rango
        
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
        db.update_credits(user_id, daily_total, "bonus", "daily", f"Recompensa diaria + bono rango {rango_actual}")
        last_daily[user_id] = current_time
        
        rango_info = RANGOS[rango_actual]
        
        embed = discord.Embed(
            title="🎁 Recompensa Diaria",
            description=f"¡Has reclamado tu recompensa diaria!",
            color=rango_info['color']
        )
        embed.add_field(name="💰 Créditos base", value=f"**+{daily_base}** créditos", inline=True)
        
        if bono_rango > 0:
            embed.add_field(name="🎁 Bono de rango", value=f"**+{bono_rango}** créditos", inline=True)
        
        embed.add_field(name="💰 Total obtenido", value=f"**+{daily_total}** créditos", inline=True)
        embed.add_field(name="💳 Balance actual", value=f"**{db.get_credits(user_id):,}** créditos", inline=False)
        embed.add_field(name="🎯 Tu rango", value=f"**{rango_info['nombre']}**", inline=True)
        embed.add_field(name="⏰ Próximo daily", value="En 24 horas", inline=True)
        
        # Mostrar bono del siguiente rango si existe
        if rango_actual < max(RANGOS.keys()):
            siguiente_rango = rango_actual + 1
            if siguiente_rango in BONOS_RANGO:
                bono_siguiente = BONOS_RANGO[siguiente_rango]
                embed.add_field(
                    name="🎪 Próximo Beneficio", 
                    value=f"Alcanza **{RANGOS[siguiente_rango]['nombre']}** para:\nDaily: +{bono_siguiente['bono_daily']}\nMulti: x{bono_siguiente['multiplicador_ganancias']}", 
                    inline=False
                )
        
        embed.set_footer(text="Vuelve mañana para otra recompensa")
        await ctx.send(embed=embed)

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
        
        # Aplicar multiplicador de rango si es ganancia para el receptor
        rango_receptor = self.calcular_rango(db.get_credits(member.id))
        multiplicador = BONOS_RANGO.get(rango_receptor, {"multiplicador_ganancias": 1.0})["multiplicador_ganancias"]
        cantidad_final = int(amount * multiplicador) if multiplicador > 1.0 else amount
        
        # Realizar transferencia
        db.update_credits(ctx.author.id, -amount, "transfer", "transfer", f"Transferido a {member.display_name}")
        db.update_credits(member.id, cantidad_final, "transfer", "transfer", f"Recibido de {ctx.author.display_name}")
        
        embed = discord.Embed(
            title="💸 Transferencia Exitosa",
            color=discord.Color.green()
        )
        embed.add_field(name="De", value=ctx.author.mention, inline=True)
        embed.add_field(name="Para", value=member.mention, inline=True)
        embed.add_field(name="Cantidad Enviada", value=f"{amount:,} créditos", inline=True)
        
        if cantidad_final > amount:
            embed.add_field(name="🎁 Bono de Rango", value=f"Recibido: {cantidad_final:,} créditos (+{int((multiplicador-1)*100)}%)", inline=True)
        
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
        
        # Aplicar multiplicador de rango al robo exitoso
        rango_actual = self.calcular_rango(db.get_credits(ctx.author.id))
        multiplicador = BONOS_RANGO.get(rango_actual, {"multiplicador_ganancias": 1.0})["multiplicador_ganancias"]
        
        # 50% de probabilidad de éxito
        success = random.random() < 0.5
        max_rob = min(target_credits // 4, 1000)  # Robar hasta 25% o 1000 créditos
        amount = random.randint(100, max_rob)
        amount_final = int(amount * multiplicador) if success and multiplicador > 1.0 else amount
        
        if success:
            # Robo exitoso con multiplicador
            db.update_credits(ctx.author.id, amount_final, "bonus", "rob", f"Robado a {member.display_name}")
            db.update_credits(member.id, -amount, "loss", "rob", f"Robado por {ctx.author.display_name}")
            
            embed = discord.Embed(
                title="🎭 Robo Exitoso!",
                description=f"¡Le robaste {amount:,} créditos a {member.mention}!",
                color=discord.Color.green()
            )
            
            if amount_final > amount:
                embed.add_field(
                    name="🎁 Bono de Rango", 
                    value=f"Recibes: {amount_final:,} créditos (+{int((multiplicador-1)*100)}%)", 
                    inline=True
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

    @commands.command(name="rangos", aliases=["ranks", "niveles"])
    async def rangos(self, ctx):
        """Muestra todos los rangos disponibles y sus beneficios"""
        embed = discord.Embed(
            title="🎯 SISTEMA DE RANGOS DEL CASINO",
            description="Mejora tu rango acumulando créditos y desbloquea beneficios exclusivos!",
            color=0x00ff00
        )
        
        for rango_id, rango_info in RANGOS.items():
            beneficios = ""
            if rango_id in BONOS_RANGO:
                bono = BONOS_RANGO[rango_id]
                beneficios = f"🎁 **Daily:** +{bono['bono_daily']} | ✨ **Multi:** x{bono['multiplicador_ganancias']}"
            else:
                beneficios = "🎁 **Daily:** +500 | ✨ **Multi:** x1.0"
            
            embed.add_field(
                name=f"{rango_info['nombre']}",
                value=f"**Mínimo:** {rango_info['min_creditos']:,} créditos\n{beneficios}",
                inline=False
            )
        
        embed.set_footer(text="Tu rango se actualiza automáticamente al ganar créditos")
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
    