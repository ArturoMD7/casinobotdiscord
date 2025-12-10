import discord
from discord.ext import commands
from discord.ui import Button, View
from db.database import Database
import random
import asyncio

db = Database()

# Diccionario para carreras activas
carreras_activas = {}

class CarreraView(View):
    def __init__(self, carrera_id, creador_id):
        super().__init__(timeout=120.0)  # 2 minutos para unirse
        self.carrera_id = carrera_id
        self.creador_id = creador_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True  # Todos pueden unirse
    
    @discord.ui.button(label="🚌 Unirse a la Carrera", style=discord.ButtonStyle.success, emoji="🎮")
    async def unirse_button(self, interaction: discord.Interaction, button: Button):
        carrera = carreras_activas.get(self.carrera_id)
        if not carrera:
            await interaction.response.send_message("❌ Esta carrera ya no está disponible.", ephemeral=True)
            return
        
        if carrera['estado'] != 'esperando':
            await interaction.response.send_message("❌ La carrera ya empezó.", ephemeral=True)
            return
        
        if interaction.user.id in carrera['jugadores']:
            await interaction.response.send_message("❌ Ya estás en esta carrera.", ephemeral=True)
            return
        
        if len(carrera['jugadores']) >= 5:
            await interaction.response.send_message("❌ La carrera está llena (máximo 5 jugadores).", ephemeral=True)
            return
        
        # Verificar créditos
        credits = db.get_saldo(interaction.user.id)
        if credits < carrera['apuesta']:
            await interaction.response.send_message(f"❌ No tienes suficientes créditos. Necesitas: {carrera['apuesta']:,}", ephemeral=True)
            return
        
        # Unir jugador
        carrera['jugadores'][interaction.user.id] = {
            'nombre': interaction.user.display_name,
            'posicion': 0,
            'bus_emoji': random.choice(['🚌', '🚎', '🚍', '🚐', '🚋']),
            'apostado': False
        }
        
        # Actualizar embed
        embed = self.crear_embed_carrera(carrera)
        await interaction.response.edit_message(embed=embed)
        
        await interaction.followup.send(
            f"🎮 {interaction.user.mention} se unió a la carrera! Apuesta: {carrera['apuesta']:,} créditos",
            ephemeral=False
        )
    
    @discord.ui.button(label="🎯 Apostar e Iniciar", style=discord.ButtonStyle.primary, emoji="💰")
    async def iniciar_button(self, interaction: discord.Interaction, button: Button):
        carrera = carreras_activas.get(self.carrera_id)
        if not carrera:
            await interaction.response.send_message("❌ Esta carrera ya no está disponible.", ephemeral=True)
            return
        
        if interaction.user.id != self.creador_id:
            await interaction.response.send_message("❌ Solo el creador puede iniciar la carrera.", ephemeral=True)
            return
        
        if len(carrera['jugadores']) < 1:
            await interaction.response.send_message("❌ Necesitas al menos 2 jugadores para empezar.", ephemeral=True)
            return
        
        if carrera['estado'] != 'esperando':
            await interaction.response.send_message("❌ La carrera ya empezó.", ephemeral=True)
            return
        
        # Cobrar apuestas a todos los jugadores
        for jugador_id in list(carrera['jugadores'].keys()):
            db.update_saldo(jugador_id, -carrera['apuesta'], "bet", "carrera", "Apuesta carrera de buses")
            carrera['jugadores'][jugador_id]['apostado'] = True
        
        # Iniciar carrera
        carrera['estado'] = 'corriendo'
        embed = self.crear_embed_carrera(carrera)
        
        # Cambiar botones
        self.clear_items()
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Iniciar animación de la carrera
        await self.iniciar_carrera(interaction, carrera)
    
    @discord.ui.button(label="❌ Cancelar Carrera", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def cancelar_button(self, interaction: discord.Interaction, button: Button):
        carrera = carreras_activas.get(self.carrera_id)
        if not carrera:
            await interaction.response.send_message("❌ Esta carrera ya no está disponible.", ephemeral=True)
            return
        
        if interaction.user.id != self.creador_id:
            await interaction.response.send_message("❌ Solo el creador puede cancelar la carrera.", ephemeral=True)
            return
        
        # Eliminar carrera
        del carreras_activas[self.carrera_id]
        
        await interaction.response.edit_message(
            content="❌ Carrera cancelada por el creador.",
            embed=None,
            view=None
        )
    
    def crear_embed_carrera(self, carrera):
        embed = discord.Embed(
            title="🏁 **CARRERA DE BUSES** 🏁",
            description="*¡Que empiece la carrera más épica de la historia!*",
            color=0x00ff00
        )
        
        embed.add_field(
            name="💰 Apuesta por jugador",
            value=f"**{carrera['apuesta']:,}** créditos",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Jugadores",
            value=f"**{len(carrera['jugadores'])}/5**",
            inline=True
        )
        
        embed.add_field(
            name="📊 Premio total",
            value=f"**{carrera['apuesta'] * len(carrera['jugadores']):,}** créditos",
            inline=True
        )
        
        # Lista de jugadores
        if carrera['jugadores']:
            jugadores_text = ""
            for jugador_id, datos in carrera['jugadores'].items():
                jugadores_text += f"{datos['bus_emoji']} **{datos['nombre']}**\n"
            embed.add_field(name="🚌 Participantes", value=jugadores_text, inline=False)
        else:
            embed.add_field(name="🚌 Participantes", value="*Ningún jugador aún...*", inline=False)
        
        # Instrucciones
        if carrera['estado'] == 'esperando':
            embed.add_field(
                name="📝 Cómo jugar",
                value="1. 🎮 **Únete** con el botón\n2. 💰 **El creador inicia** cuando estén todos\n3. 🏁 **Los buses corren** 10 espacios\n4. 🥇 **El ganador se lleva todo!**",
                inline=False
            )
        
        embed.set_footer(text="Basado en el meme de carreras de buses 🚌")
        return embed
    
    async def iniciar_carrera(self, interaction: discord.Interaction, carrera):
        message = await interaction.original_response()
        pista_largo = 10
        
        # Animación de la carrera
        for vuelta in range(1, pista_largo + 1):
            # Mover cada bus aleatoriamente
            for jugador_id in carrera['jugadores']:
                avance = random.randint(1, 3)  # Avance aleatorio de 1-3 espacios
                carrera['jugadores'][jugador_id]['posicion'] = min(
                    carrera['jugadores'][jugador_id]['posicion'] + avance, 
                    pista_largo
                )
            
            # Crear embed de progreso
            embed = self.crear_embed_progreso(carrera, vuelta, pista_largo)
            await message.edit(embed=embed)
            
            # Esperar entre vueltas
            await asyncio.sleep(2)
        
        # Determinar ganador
        ganador_id = self.determinar_ganador(carrera)
        await self.finalizar_carrera(message, carrera, ganador_id)
    
    def crear_embed_progreso(self, carrera, vuelta_actual, pista_largo):
        embed = discord.Embed(
            title="🏁 **CARRERA EN CURSO!** 🏁",
            description=f"**Vuelta {vuelta_actual}/{pista_largo}**",
            color=0xff9900
        )
        
        # Mostrar progreso de cada jugador
        for jugador_id, datos in carrera['jugadores'].items():
            posicion = datos['posicion']
            progreso = "⬜" * posicion + "🚌" + "⬜" * (pista_largo - posicion - 1)
            if posicion >= pista_largo:
                progreso = "✅" * pista_largo + " 🏁"
            
            embed.add_field(
                name=f"{datos['bus_emoji']} {datos['nombre']}",
                value=f"`{progreso}`",
                inline=False
            )
        
        embed.set_footer(text="¡Los buses están en movimiento!")
        return embed
    
    def determinar_ganador(self, carrera):
        # Encontrar jugador con mayor posición
        max_posicion = -1
        ganador_id = None
        
        for jugador_id, datos in carrera['jugadores'].items():
            if datos['posicion'] > max_posicion:
                max_posicion = datos['posicion']
                ganador_id = jugador_id
            elif datos['posicion'] == max_posicion:
                # Empate - elegir aleatoriamente
                if random.random() < 0.5:
                    ganador_id = jugador_id
        
        return ganador_id
    
    async def finalizar_carrera(self, message, carrera, ganador_id):
        if ganador_id:
            ganador = carrera['jugadores'][ganador_id]
            premio = carrera['apuesta'] * len(carrera['jugadores'])
            
            # Pagar al ganador
            db.update_saldo(ganador_id, premio, "win", "carrera", f"Ganó carrera de buses")
            
            embed = discord.Embed(
                title="🏆 **¡TENEMOS GANADOR!** 🏆",
                description=f"## {ganador['bus_emoji']} **{ganador['nombre']}** GANA LA CARRERA!",
                color=0xffd700
            )
            
            embed.add_field(
                name="💰 Premio",
                value=f"**{premio:,}** créditos",
                inline=True
            )
            
            embed.add_field(
                name="🎮 Participantes",
                value=f"**{len(carrera['jugadores'])}** buses",
                inline=True
            )
            
            # Mostrar posiciones finales
            posiciones = ""
            jugadores_ordenados = sorted(
                carrera['jugadores'].items(), 
                key=lambda x: x[1]['posicion'], 
                reverse=True
            )
            
            for i, (jugador_id, datos) in enumerate(jugadores_ordenados, 1):
                medalla = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔹"
                posiciones += f"{medalla} {datos['bus_emoji']} **{datos['nombre']}** - Posición: {datos['posicion']}\n"
            
            embed.add_field(name="📊 Resultados Finales", value=posiciones, inline=False)
            embed.set_image(url="https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif")
            
        else:
            embed = discord.Embed(
                title="🤔 **CARRERA TERMINADA**",
                description="Algo salió mal... no hay ganador.",
                color=0xff0000
            )
        
        # Eliminar carrera
        del carreras_activas[self.carrera_id]
        
        await message.edit(embed=embed)

class Carrera(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="carrera", aliases=["race", "buses"])
    async def carrera(self, ctx, apuesta: int = None):
        """Inicia una carrera de buses - 1-5 jugadores, el ganador se lleva todo"""
        
        if apuesta is None:
            embed = discord.Embed(
                title="🏁 CARRERA DE BUSES",
                description="**¡La carrera más épica basada en el meme!**\n\n1-5 jugadores, el ganador se lleva todas las apuestas.",
                color=0x00ff00
            )
            embed.add_field(
                name="🎯 Cómo funciona",
                value="• Crea una carrera con apuesta\n• Otros se unen (máx 5)\n• Los buses corren 10 espacios\n• 🥇 **El ganador se lleva TODO!**",
                inline=False
            )
            embed.add_field(
                name="💰 Apuesta mínima",
                value="**100** créditos",
                inline=True
            )
            embed.add_field(
                name="🎮 Jugadores",
                value="**1-5** por carrera",
                inline=True
            )
            embed.add_field(
                name="🚌 Uso",
                value="`!carrera <apuesta>`",
                inline=True
            )
            await ctx.send(embed=embed)
            return
        
        if apuesta < 100:
            await ctx.send("❌ Apuesta mínima: 100 créditos")
            return
        
        # Verificar créditos del creador
        credits = db.get_saldo(ctx.author.id)
        if credits < apuesta:
            await ctx.send(f"❌ No tienes suficientes créditos. Necesitas: {apuesta:,}")
            return
        
        # Crear ID único para la carrera
        carrera_id = f"{ctx.channel.id}_{ctx.message.id}"
        
        # Inicializar carrera
        carreras_activas[carrera_id] = {
            'creador': ctx.author.id,
            'apuesta': apuesta,
            'jugadores': {
                ctx.author.id: {
                    'nombre': ctx.author.display_name,
                    'posicion': 0,
                    'bus_emoji': '🚌',  # El creador siempre tiene bus normal
                    'apostado': False
                }
            },
            'estado': 'esperando',  # esperando, corriendo, terminada
            'mensaje_id': None
        }
        
        # Crear view y embed
        view = CarreraView(carrera_id, ctx.author.id)
        embed = view.crear_embed_carrera(carreras_activas[carrera_id])
        
        message = await ctx.send(embed=embed, view=view)
        carreras_activas[carrera_id]['mensaje_id'] = message.id

    @commands.command(name="carreras", aliases=["races", "busesactivas"])
    async def carreras(self, ctx):
        """Muestra las carreras de buses activas"""
        carreras_en_este_canal = {
            k: v for k, v in carreras_activas.items() 
            if k.startswith(f"{ctx.channel.id}_") and v['estado'] == 'esperando'
        }
        
        if not carreras_en_este_canal:
            embed = discord.Embed(
                title="🏁 No hay carreras activas",
                description="Usa `!carrera <apuesta>` para crear una nueva carrera de buses!",
                color=0xffff00
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🏁 CARRERAS ACTIVAS EN ESTE CANAL",
            description="Únete a una carrera con los botones del mensaje original",
            color=0x00ff00
        )
        
        for carrera_id, carrera in carreras_en_este_canal.items():
            creador = self.bot.get_user(carrera['creador'])
            creador_nombre = creador.display_name if creador else "Usuario desconocido"
            
            embed.add_field(
                name=f"🎮 Carrera de {creador_nombre}",
                value=f"**Apuesta:** {carrera['apuesta']:,} créditos\n**Jugadores:** {len(carrera['jugadores'])}/5\n**Estado:** Esperando jugadores",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="micarrera", aliases=["myrace"])
    async def micarrera(self, ctx):
        """Muestra tu carrera activa"""
        user_id = ctx.author.id
        
        # Buscar carreras donde el usuario esté participando
        carreras_usuario = []
        for carrera_id, carrera in carreras_activas.items():
            if user_id in carrera['jugadores']:
                carreras_usuario.append((carrera_id, carrera))
        
        if not carreras_usuario:
            await ctx.send("❌ No estás en ninguna carrera activa.")
            return
        
        embed = discord.Embed(
            title="🏁 TUS CARRERAS ACTIVAS",
            color=0x00ff00
        )
        
        for carrera_id, carrera in carreras_usuario:
            estado = "🏁 En curso" if carrera['estado'] == 'corriendo' else "⏳ Esperando"
            embed.add_field(
                name=f"Carrera ({estado})",
                value=f"**Apuesta:** {carrera['apuesta']:,} créditos\n**Jugadores:** {len(carrera['jugadores'])}/5\n**Tu bus:** {carrera['jugadores'][user_id]['bus_emoji']}",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Carrera(bot))