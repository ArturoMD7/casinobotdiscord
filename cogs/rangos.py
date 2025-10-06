import asyncio
import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from db.database import Database
from config import RANGOS, BONOS_RANGO, STARTING_CREDITS

db = Database()

# Sistema de Marcos Disponibles (el mismo que tienes)
MARCOS_DISPONIBLES = {
    "default": {
        "nombre": "🏷️ Marco Básico",
        "precio": 0,
        "color": 0x808080,
        "descripcion": "Marco predeterminado para todos los jugadores",
        "emoji": "🏷️",
        "rareza": "comun"
    },
    "bronce": {
        "nombre": "🥉 Marco de Bronce",
        "precio": 5000,
        "color": 0xcd7f32,
        "descripcion": "Elegante marco de bronce para mostrar tu progreso",
        "emoji": "🥉",
        "rareza": "raro"
    },
    # ... (todos los demás marcos igual)
}

class MarcoSelectView(View):
    def __init__(self, user_id, marcos_poseidos):
        super().__init__(timeout=60.0)
        self.user_id = user_id
        self.marcos_poseidos = marcos_poseidos
        
        # Crear selector de marcos
        select = Select(
            placeholder="🎨 Selecciona un marco para equipar...",
            min_values=1,
            max_values=1
        )
        
        for marco_id, marco_info in MARCOS_DISPONIBLES.items():
            if marco_id in marcos_poseidos:
                emoji = marco_info["emoji"]
                label = marco_info["nombre"]
                description = f"Equipar este marco"
                select.add_option(
                    label=label,
                    value=marco_id,
                    description=description,
                    emoji=emoji
                )
        
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ No puedes usar este menú.", ephemeral=True)
            return
        
        marco_id = interaction.data['values'][0]
        marco_info = MARCOS_DISPONIBLES[marco_id]
        
        # Equipar el marco
        cursor = db.conn.cursor()
        cursor.execute("""
            INSERT INTO user_frames (user_id, equipped_frame, owned_frames) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE equipped_frame = %s
        """, (self.user_id, marco_id, ','.join(self.marcos_poseidos), marco_id))
        db.conn.commit()
        cursor.close()
        
        embed = discord.Embed(
            title="✅ Marco Equipado",
            description=f"Has equipado: **{marco_info['nombre']}** {marco_info['emoji']}",
            color=marco_info['color']
        )
        embed.add_field(
            name="💡 ¿Cómo se ve?",
            value="Tu nuevo marco aparecerá en tu perfil cuando uses `!rank`",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class TiendaMarcosView(View):
    def __init__(self, user_id, credits):
        super().__init__(timeout=60.0)
        self.user_id = user_id
        self.credits = credits

    @discord.ui.button(label="🛒 Comprar Marcos", style=discord.ButtonStyle.success, emoji="🛒")
    async def comprar_button(self, interaction: discord.Interaction, button: Button):
        await self.mostrar_tienda(interaction)

    async def mostrar_tienda(self, interaction: discord.Interaction):
        # Obtener marcos ya poseídos
        cursor = db.conn.cursor()
        cursor.execute("SELECT owned_frames FROM user_frames WHERE user_id = %s", (self.user_id,))
        resultado = cursor.fetchone()
        marcos_poseidos = resultado[0].split(',') if resultado and resultado[0] else ['default']
        cursor.close()

        embed = discord.Embed(
            title="🛍️ Tienda de Marcos - Disponibles para Comprar",
            description=f"**Tus créditos:** {self.credits:,} 💰\n\nSelecciona un marco para comprar:",
            color=0x00ff00
        )

        # Crear botones para cada marco disponible
        view = View(timeout=60.0)
        
        for marco_id, marco_info in MARCOS_DISPONIBLES.items():
            if marco_id not in marcos_poseidos and marco_id != "default":
                # Crear botón para cada marco - CORREGIDO: usar lambda para capturar marco_id correctamente
                button = Button(
                    label=f"{marco_info['nombre']} - {marco_info['precio']:,}cr",
                    style=discord.ButtonStyle.primary,
                    emoji=marco_info["emoji"]
                )
                
                # CORREGIDO: Usar functools.partial o capturar el marco_id correctamente
                async def buy_callback(interaction: discord.Interaction, marco_id=marco_id):
                    await self.comprar_marco(interaction, marco_id)
                
                button.callback = buy_callback
                view.add_item(button)

        if len(view.children) == 0:
            embed.add_field(
                name="🎉 ¡Felicidades!",
                value="Ya tienes todos los marcos disponibles.",
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=view)

    async def comprar_marco(self, interaction: discord.Interaction, marco_id: str):
        marco_info = MARCOS_DISPONIBLES[marco_id]
        
        if self.credits < marco_info["precio"]:
            await interaction.response.send_message(
                f"❌ No tienes suficientes créditos. Necesitas: {marco_info['precio']:,}",
                ephemeral=True
            )
            return
        
        # Obtener marcos actuales
        cursor = db.conn.cursor()
        cursor.execute("SELECT owned_frames FROM user_frames WHERE user_id = %s", (self.user_id,))
        resultado = cursor.fetchone()
        
        if resultado:
            marcos_poseidos = resultado[0].split(',')
            if marco_id not in marcos_poseidos:
                marcos_poseidos.append(marco_id)
            nuevos_marcos = ','.join(marcos_poseidos)
            
            cursor.execute("""
                UPDATE user_frames 
                SET owned_frames = %s 
                WHERE user_id = %s
            """, (nuevos_marcos, self.user_id))
        else:
            cursor.execute("""
                INSERT INTO user_frames (user_id, equipped_frame, owned_frames) 
                VALUES (%s, %s, %s)
            """, (self.user_id, 'default', f'default,{marco_id}'))
        
        db.conn.commit()
        cursor.close()
        
        # Restar créditos
        db.update_credits(self.user_id, -marco_info["precio"], "compra", "marco_perfil", f"Compra marco: {marco_info['nombre']}")
        
        embed = discord.Embed(
            title="🎊 ¡Marco Comprado!",
            description=f"Has adquirido: **{marco_info['nombre']}** {marco_info['emoji']}",
            color=marco_info['color']
        )
        embed.add_field(name="💰 Precio", value=f"{marco_info['precio']:,} créditos", inline=True)
        embed.add_field(name="🎨 Rareza", value=marco_info["rareza"].title(), inline=True)
        embed.add_field(name="💳 Créditos restantes", value=f"{self.credits - marco_info['precio']:,}", inline=True)
        embed.add_field(
            name="🔧 ¿Qué sigue?",
            value="Usa `!marcos equipar` para ponerte este marco",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class Rangos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def obtener_marco_usuario(self, user_id: int) -> dict:
        """Obtiene el marco equipado de un usuario"""
        try:
            cursor = db.conn.cursor()
            cursor.execute("SELECT equipped_frame FROM user_frames WHERE user_id = %s", (user_id,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                marco_id = resultado[0]
                return MARCOS_DISPONIBLES.get(marco_id, MARCOS_DISPONIBLES["default"])
            else:
                # Crear entrada por defecto
                cursor = db.conn.cursor()
                cursor.execute("""
                    INSERT IGNORE INTO user_frames (user_id, equipped_frame, owned_frames) 
                    VALUES (%s, %s, %s)
                """, (user_id, 'default', 'default'))
                db.conn.commit()
                cursor.close()
                return MARCOS_DISPONIBLES["default"]
                
        except Exception as e:
            print(f"Error obteniendo marco: {e}")
            return MARCOS_DISPONIBLES["default"]

    def calcular_rango(self, creditos: int) -> int:
        """Calcula el rango basado en los créditos"""
        rango_actual = 0
        for rango_id, datos in RANGOS.items():
            if creditos >= datos["min_creditos"]:
                rango_actual = rango_id
            else:
                break
        return rango_actual

    def actualizar_rango_usuario(self, user_id: int) -> int:
        """Actualiza el rango de un usuario si es necesario y devuelve el nuevo rango"""
        try:
            credits = db.get_credits(user_id)
            nuevo_rango = self.calcular_rango(credits)
            
            # Obtener el rango actual desde la base de datos
            cursor = db.conn.cursor()
            cursor.execute("SELECT rango FROM users WHERE user_id = %s", (user_id,))
            resultado = cursor.fetchone()
            rango_actual = resultado[0] if resultado else 0
            
            # Solo actualizar si el rango cambió
            if nuevo_rango != rango_actual:
                cursor.execute("UPDATE users SET rango = %s WHERE user_id = %s", (nuevo_rango, user_id))
                db.conn.commit()
                
                # Si subió de rango, aplicar bono de bienvenida (opcional)
                if nuevo_rango > rango_actual:
                    bono = BONOS_RANGO.get(nuevo_rango, {}).get('bono_subida', 0)
                    if bono > 0:
                        db.update_credits(user_id, bono, "bonus", "rango_up", f"Bono por subir a rango {nuevo_rango}")
            
            cursor.close()
            return nuevo_rango
            
        except Exception as e:
            print(f"Error actualizando rango: {e}")
            return 0

    def obtener_progreso_rango(self, creditos: int, rango_actual: int) -> tuple:
        """Calcula el progreso hacia el siguiente rango"""
        if rango_actual >= max(RANGOS.keys()):
            return 100, 0, 0  # Rango máximo alcanzado
        
        siguiente_rango = rango_actual + 1
        if siguiente_rango not in RANGOS:
            return 100, 0, 0
        
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
        """Muestra tu rango actual y progreso con marco personalizado"""
        if usuario is None:
            usuario = ctx.author
        
        user_id = usuario.id
        
        # Forzar actualización del rango antes de mostrar
        rango_actual = self.actualizar_rango_usuario(user_id)
        credits = db.get_credits(user_id)
        
        # Obtener marco del usuario
        marco_usuario = self.obtener_marco_usuario(user_id)
        rango_info = RANGOS[rango_actual]
        porcentaje, credito_objetivo, progreso_actual = self.obtener_progreso_rango(credits, rango_actual)
        barra_progreso = self.crear_barra_progreso(porcentaje)
        
        # Crear embed con el color del marco
        embed = discord.Embed(
            title=f"{marco_usuario['emoji']} {rango_info['nombre']} - {usuario.display_name}",
            color=marco_usuario['color']
        )
        
        # Añadir información del marco
        embed.add_field(
            name="🎨 Marco de Perfil",
            value=f"{marco_usuario['nombre']}",
            inline=True
        )
        
        embed.add_field(
            name="💰 Créditos",
            value=f"**{credits:,}** créditos",
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
        
        # Añadir botones de interacción si es el propio usuario
        if usuario.id == ctx.author.id:
            view = View(timeout=60.0)
            
            tienda_button = Button(label="🛍️ Tienda de Marcos", style=discord.ButtonStyle.primary, emoji="🛍️")
            equipar_button = Button(label="🎨 Cambiar Marco", style=discord.ButtonStyle.secondary, emoji="🎨")
            
            async def tienda_callback(interaction: discord.Interaction):
                # CORREGIDO: Llamar al método correcto
                await self.marcos_tienda_context(interaction)
            
            async def equipar_callback(interaction: discord.Interaction):
                # CORREGIDO: Llamar al método correcto  
                await self.marcos_equipar_context(interaction)
            
            tienda_button.callback = tienda_callback
            equipar_button.callback = equipar_callback
            
            view.add_item(tienda_button)
            view.add_item(equipar_button)
            
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(embed=embed)

    # CORREGIDO: Métodos auxiliares para los callbacks
    async def marcos_tienda_context(self, interaction: discord.Interaction):
        """Versión del comando marcos_tienda para usar en callbacks"""
        credits = db.get_credits(interaction.user.id)
        
        embed = discord.Embed(
            title="🛍️ Tienda de Marcos de Perfil",
            description=f"**Tus créditos:** {credits:,} 💰\n\n"
                      "Compra marcos exclusivos para personalizar tu perfil:",
            color=0x00ff00
        )
        
        # Agrupar marcos por rareza
        marcos_por_rareza = {}
        for marco_id, marco_info in MARCOS_DISPONIBLES.items():
            if marco_id != "default":
                rareza = marco_info["rareza"]
                if rareza not in marcos_por_rareza:
                    marcos_por_rareza[rareza] = []
                marcos_por_rareza[rareza].append(marco_info)
        
        for rareza, marcos in marcos_por_rareza.items():
            texto_marcos = ""
            for marco in marcos:
                texto_marcos += f"{marco['emoji']} **{marco['nombre']}** - {marco['precio']:,}cr\n"
            
            embed.add_field(
                name=f"{rareza.title()} ({len(marcos)})",
                value=texto_marcos,
                inline=True
            )
        
        embed.set_footer(text="Usa los botones de abajo para comprar o gestionar tus marcos")
        
        view = TiendaMarcosView(interaction.user.id, credits)
        await interaction.response.edit_message(embed=embed, view=view)

    async def marcos_equipar_context(self, interaction: discord.Interaction):
        """Versión del comando marcos_equipar para usar en callbacks"""
        # Obtener marcos poseídos
        cursor = db.conn.cursor()
        cursor.execute("SELECT owned_frames FROM user_frames WHERE user_id = %s", (interaction.user.id,))
        resultado = cursor.fetchone()
        cursor.close()
        
        if not resultado or not resultado[0]:
            embed = discord.Embed(
                title="❌ No tienes marcos",
                description="Compra marcos en la tienda primero usando `!marcos tienda`",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        marcos_poseidos = resultado[0].split(',')
        
        if len(marcos_poseidos) == 1 and marcos_poseidos[0] == "default":
            embed = discord.Embed(
                title="❌ Solo tienes el marco básico",
                description="Compra más marcos en la tienda usando `!marcos tienda`",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        embed = discord.Embed(
            title="🎨 Equipar Marco de Perfil",
            description="Selecciona el marco que quieres equipar:",
            color=0x00ff00
        )
        
        view = MarcoSelectView(interaction.user.id, marcos_poseidos)
        await interaction.response.edit_message(embed=embed, view=view)

    @commands.command(name="marcos", aliases=["frames", "marcoperfil"])
    async def marcos(self, ctx, accion: str = None):
        """Sistema de marcos de perfil - Tienda y gestión"""
        if accion is None:
            embed = discord.Embed(
                title="🎨 Sistema de Marcos de Perfil",
                description="**Personaliza tu perfil con marcos exclusivos**\n\n"
                          "**Comandos disponibles:**\n"
                          "`!marcos tienda` - Ver y comprar marcos\n"
                          "`!marcos equipar` - Cambiar marco equipado\n"
                          "`!marcos lista` - Ver tus marcos poseídos\n"
                          "`!marcos info <nombre>` - Información de un marco",
                color=0x00ff00
            )
            
            # Mostrar algunos marcos destacados
            marcos_destacados = list(MARCOS_DISPONIBLES.values())[:3]
            for marco in marcos_destacados:
                embed.add_field(
                    name=f"{marco['emoji']} {marco['nombre']}",
                    value=f"{marco['precio']:,} créditos",
                    inline=True
                )
            
            await ctx.send(embed=embed)
            return
        
        if accion.lower() == "tienda":
            await self.marcos_tienda(ctx)
        elif accion.lower() == "equipar":
            await self.marcos_equipar(ctx)
        elif accion.lower() == "lista":
            await self.marcos_lista(ctx)
        else:
            await ctx.send("❌ Acción no válida. Usa: `!marcos tienda`, `!marcos equipar` o `!marcos lista`")

    async def marcos_tienda(self, ctx):
        """Muestra la tienda de marcos"""
        credits = db.get_credits(ctx.author.id)
        
        embed = discord.Embed(
            title="🛍️ Tienda de Marcos de Perfil",
            description=f"**Tus créditos:** {credits:,} 💰\n\n"
                      "Compra marcos exclusivos para personalizar tu perfil:",
            color=0x00ff00
        )
        
        # Agrupar marcos por rareza
        marcos_por_rareza = {}
        for marco_id, marco_info in MARCOS_DISPONIBLES.items():
            if marco_id != "default":
                rareza = marco_info["rareza"]
                if rareza not in marcos_por_rareza:
                    marcos_por_rareza[rareza] = []
                marcos_por_rareza[rareza].append(marco_info)
        
        for rareza, marcos in marcos_por_rareza.items():
            texto_marcos = ""
            for marco in marcos:
                texto_marcos += f"{marco['emoji']} **{marco['nombre']}** - {marco['precio']:,}cr\n"
            
            embed.add_field(
                name=f"{rareza.title()} ({len(marcos)})",
                value=texto_marcos,
                inline=True
            )
        
        embed.set_footer(text="Usa los botones de abajo para comprar o gestionar tus marcos")
        
        view = TiendaMarcosView(ctx.author.id, credits)
        await ctx.send(embed=embed, view=view)

    async def marcos_equipar(self, ctx):
        """Permite equipar un marco de los que posee el usuario"""
        # Obtener marcos poseídos
        cursor = db.conn.cursor()
        cursor.execute("SELECT owned_frames FROM user_frames WHERE user_id = %s", (ctx.author.id,))
        resultado = cursor.fetchone()
        cursor.close()
        
        if not resultado or not resultado[0]:
            embed = discord.Embed(
                title="❌ No tienes marcos",
                description="Compra marcos en la tienda primero usando `!marcos tienda`",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        marcos_poseidos = resultado[0].split(',')
        
        if len(marcos_poseidos) == 1 and marcos_poseidos[0] == "default":
            embed = discord.Embed(
                title="❌ Solo tienes el marco básico",
                description="Compra más marcos en la tienda usando `!marcos tienda`",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🎨 Equipar Marco de Perfil",
            description="Selecciona el marco que quieres equipar:",
            color=0x00ff00
        )
        
        view = MarcoSelectView(ctx.author.id, marcos_poseidos)
        await ctx.send(embed=embed, view=view)

    async def marcos_lista(self, ctx):
        """Muestra los marcos que posee el usuario"""
        # Obtener marcos poseídos y marco equipado
        cursor = db.conn.cursor()
        cursor.execute("SELECT equipped_frame, owned_frames FROM user_frames WHERE user_id = %s", (ctx.author.id,))
        resultado = cursor.fetchone()
        cursor.close()
        
        if not resultado or not resultado[1]:
            marcos_poseidos = ['default']
            marco_equipado = 'default'
        else:
            marcos_poseidos = resultado[1].split(',')
            marco_equipado = resultado[0]
        
        embed = discord.Embed(
            title="📚 Tus Marcos de Perfil",
            description=f"**Marcos poseídos:** {len(marcos_poseidos)}\n",
            color=0x00ff00
        )
        
        for marco_id in marcos_poseidos:
            marco_info = MARCOS_DISPONIBLES[marco_id]
            equipado = " ✅" if marco_id == marco_equipado else ""
            embed.add_field(
                name=f"{marco_info['emoji']} {marco_info['nombre']}{equipado}",
                value=f"{marco_info['descripcion']}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="top", aliases=["leaderboard", "ranking"])
    async def top(self, ctx, tipo: str = "creditos"):
        """Muestra el leaderboard de jugadores"""
        try:
            # Primero, actualizar todos los rangos de los usuarios en el top
            if tipo.lower() in ["creditos", "credits", "money"]:
                cursor = db.conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT user_id, credits, rango 
                    FROM users 
                    WHERE credits > 0 
                    ORDER BY credits DESC 
                    LIMIT 15
                """)
                top_users = cursor.fetchall()
                cursor.close()
                
                # Actualizar rangos antes de mostrar
                for user_data in top_users:
                    self.actualizar_rango_usuario(user_data['user_id'])
                
                # Volver a obtener los datos actualizados
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
                    ORDER BY credits DESC 
                    LIMIT 15
                """)
                top_users = cursor.fetchall()
                cursor.close()
                
                # Actualizar rangos antes de mostrar
                for user_data in top_users:
                    self.actualizar_rango_usuario(user_data['user_id'])
                
                # Volver a obtener los datos actualizados ordenados por rango
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

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """Actualiza el rango después de cualquier comando que modifique créditos"""
        if ctx.command and ctx.command.name in ['daily', 'apostar', 'transferir', 'ruletarusa']:
            # Pequeña demora para asegurar que los créditos se actualizaron
            await asyncio.sleep(1)
            self.actualizar_rango_usuario(ctx.author.id)

async def setup(bot):
    await bot.add_cog(Rangos(bot))