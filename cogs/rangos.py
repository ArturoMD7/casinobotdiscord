import discord
from discord.ext import commands
from db.database import Database
from config import RANGOS, BONOS_RANGO, STARTING_CREDITS

db = Database()

class Rangos(commands.Cog):
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

    def actualizar_rango_usuario(self, user_id: int):
        """Actualiza el rango de un usuario si es necesario"""
        try:
            credits = db.get_credits(user_id)
            rango_actual = self.calcular_rango(credits)
            
            # Actualizar en la base de datos
            cursor = db.conn.cursor()
            cursor.execute("UPDATE users SET rango = %s WHERE user_id = %s", (rango_actual, user_id))
            db.conn.commit()
            cursor.close()
            
            return rango_actual
        except Exception as e:
            print(f"Error actualizando rango: {e}")
            return 0

    def obtener_progreso_rango(self, creditos: int, rango_actual: int) -> tuple:
        """Calcula el progreso hacia el siguiente rango"""
        if rango_actual >= max(RANGOS.keys()):
            return 100, 0, 0  # Rango máximo alcanzado
        
        siguiente_rango = rango_actual + 1
        credito_actual = creditos
        credito_objetivo = RANGOS[siguiente_rango]["min_creditos"]
        credito_anterior = RANGOS[rango_actual]["min_creditos"]
        
        rango_total = credito_objetivo - credito_anterior
        progreso_actual = credito_actual - credito_anterior
        
        if rango_total > 0:
            porcentaje = min(100, int((progreso_actual / rango_total) * 100))
        else:
            porcentaje = 100
            
        return porcentaje, credito_objetivo, progreso_actual

    def crear_barra_progreso(self, porcentaje: int, longitud: int = 20) -> str:
        """Crea una barra de progreso visual"""
        bloques_llenos = int((porcentaje / 100) * longitud)
        bloques_vacios = longitud - bloques_llenos
        return "█" * bloques_llenos + "░" * bloques_vacios

    @commands.command(name="rango", aliases=["rank", "nivel"])
    async def rango(self, ctx, usuario: discord.Member = None):
        """Muestra tu rango actual y progreso"""
        if usuario is None:
            usuario = ctx.author
        
        user_id = usuario.id
        credits = db.get_credits(user_id)
        rango_actual = self.calcular_rango(credits)
        
        # Actualizar en base de datos
        self.actualizar_rango_usuario(user_id)
        
        rango_info = RANGOS[rango_actual]
        porcentaje, credito_objetivo, progreso_actual = self.obtener_progreso_rango(credits, rango_actual)
        barra_progreso = self.crear_barra_progreso(porcentaje)
        
        embed = discord.Embed(
            title=f"{rango_info['nombre']} - {usuario.display_name}",
            color=rango_info['color']
        )
        
        embed.add_field(
            name="💰 Créditos",
            value=f"**{credits:,}** créditos",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Rango Actual",
            value=f"**{rango_info['nombre']}**",
            inline=True
        )
        
        embed.add_field(
            name="📊 Progreso",
            value=f"`{barra_progreso}` {porcentaje}%",
            inline=False
        )
        
        if rango_actual < max(RANGOS.keys()):
            siguiente_rango = RANGOS[rango_actual + 1]
            faltante = credito_objetivo - credits
            
            embed.add_field(
                name="🎯 Siguiente Rango",
                value=f"**{siguiente_rango['nombre']}**\nFaltan: **{faltante:,}** créditos",
                inline=True
            )
            
            # Mostrar bono del siguiente rango
            if (rango_actual + 1) in BONOS_RANGO:
                bono = BONOS_RANGO[rango_actual + 1]
                embed.add_field(
                    name="🎁 Bono del Siguiente Rango",
                    value=f"Daily: +{bono['bono_daily']}\nMultiplicador: x{bono['multiplicador_ganancias']}",
                    inline=True
                )
        else:
            embed.add_field(
                name="🏆 ¡Rango Máximo Alcanzado!",
                value="¡Eres una leyenda del casino!",
                inline=True
            )
        
        # Mostrar bono actual si existe
        if rango_actual in BONOS_RANGO:
            bono_actual = BONOS_RANGO[rango_actual]
            embed.add_field(
                name="🎪 Beneficios Actuales",
                value=f"Daily: +{bono_actual['bono_daily']}\nMultiplicador: x{bono_actual['multiplicador_ganancias']}",
                inline=True
            )
        
        embed.set_thumbnail(url=usuario.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="top", aliases=["leaderboard", "ranking"])
    async def top(self, ctx, tipo: str = "creditos"):
        """Muestra el leaderboard de jugadores"""
        try:
            if tipo.lower() in ["creditos", "credits", "money"]:
                cursor = db.conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT user_id, credits, rango 
                    FROM users 
                    WHERE credits > 0 
                    ORDER BY credits DESC 
                    LIMIT 10
                """)
                top_users = cursor.fetchall()
                cursor.close()
                
                embed = discord.Embed(
                    title="🏆 LEADERBOARD - TOP 10 MÁS RICOS",
                    color=0xffd700
                )
                
            elif tipo.lower() in ["rango", "rank", "nivel"]:
                cursor = db.conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT user_id, credits, rango 
                    FROM users 
                    WHERE credits > 0 
                    ORDER BY rango DESC, credits DESC 
                    LIMIT 10
                """)
                top_users = cursor.fetchall()
                cursor.close()
                
                embed = discord.Embed(
                    title="🏆 LEADERBOARD - TOP 10 RANGOS",
                    color=0x00ff00
                )
            else:
                await ctx.send("❌ Tipos válidos: `creditos` o `rango`")
                return
            
            if top_users:
                leaderboard_text = ""
                for i, user_data in enumerate(top_users, 1):
                    user_id = user_data['user_id']
                    
                    # Intentar obtener el usuario de diferentes maneras
                    user = None
                    
                    # 1. Buscar en la cache del bot
                    user = self.bot.get_user(user_id)
                    
                    # 2. Si no está en cache, intentar buscarlo
                    if user is None:
                        try:
                            user = await self.bot.fetch_user(user_id)
                        except:
                            pass
                    
                    # 3. Si aún no se encuentra, usar el ID
                    if user:
                        username = f"**{user.display_name}**"
                        mention = user.mention
                    else:
                        username = f"Usuario {user_id}"
                        mention = f"<@{user_id}>"
                    
                    medal = ""
                    if i == 1: medal = "🥇 "
                    elif i == 2: medal = "🥈 "
                    elif i == 3: medal = "🥉 "
                    
                    rango_actual = user_data.get('rango', 0)
                    rango_info = RANGOS.get(rango_actual, RANGOS[0])
                    
                    if tipo.lower() in ["creditos", "credits", "money"]:
                        leaderboard_text += f"{medal}{i}. {mention} - `{user_data['credits']:,} cr` ({rango_info['nombre']})\n"
                    else:
                        leaderboard_text += f"{medal}{i}. {mention} - {rango_info['nombre']} (`{user_data['credits']:,} cr`)\n"
                
                embed.description = leaderboard_text
            else:
                embed.description = "No hay datos todavía. ¡Sé el primero en jugar!"
            
            embed.set_footer(text=f"Usa !top creditos o !top rango")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ Error al cargar el leaderboard.")
            print(f"Error en top: {e}")

async def setup(bot):
    await bot.add_cog(Rangos(bot))