import discord
from discord.ext import commands
from discord.ui import Button, View
from game.poker_game import PokerGame
import asyncio
import random

# Diccionario para guardar juegos activos
poker_games = {}

class PokerLobbyView(View):
    def __init__(self, game_id, creator_id):
        super().__init__(timeout=120.0)
        self.game_id = game_id
        self.creator_id = creator_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True  # Cualquiera puede unirse
    
    @discord.ui.button(label="🎮 Unirse al Juego", style=discord.ButtonStyle.primary)
    async def join_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        if not game:
            await interaction.response.send_message("❌ Este juego ya no existe.", ephemeral=True)
            return
        
        if game.game_started:
            await interaction.response.send_message("❌ El juego ya comenzó.", ephemeral=True)
            return
        
        success = game.agregar_jugador(interaction.user.id, interaction.user.display_name)
        if success:
            await interaction.response.send_message(f"✅ {interaction.user.mention} se unió al juego!", ephemeral=True)
            
            # Actualizar embed
            embed = self.crear_embed_lobby(game)
            await interaction.message.edit(embed=embed)
        else:
            await interaction.response.send_message("❌ No se pudo unir al juego (límite alcanzado o ya está unido).", ephemeral=True)
    
    @discord.ui.button(label="🚀 Iniciar Juego", style=discord.ButtonStyle.success)
    async def start_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("❌ Solo el creador puede iniciar el juego.", ephemeral=True)
            return
        
        game = poker_games.get(self.game_id)
        if not game:
            await interaction.response.send_message("❌ Este juego ya no existe.", ephemeral=True)
            return
        
        if len(game.players) < 2:
            await interaction.response.send_message("❌ Se necesitan al menos 2 jugadores.", ephemeral=True)
            return
        
        success = game.empezar_juego()
        if success:
            # Cambiar a vista de juego
            estado = game.obtener_estado_juego()
            embed = self.crear_embed_juego(estado)
            view = PokerGameView(self.game_id)
            
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("❌ Error al iniciar el juego.", ephemeral=True)
    
    @discord.ui.button(label="❌ Cancelar Juego", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("❌ Solo el creador puede cancelar el juego.", ephemeral=True)
            return
        
        if self.game_id in poker_games:
            del poker_games[self.game_id]
        
        embed = discord.Embed(
            title="🎮 Poker - Juego Cancelado",
            description="El juego ha sido cancelado por el creador.",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=None)
    
    def crear_embed_lobby(self, game: PokerGame) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Poker Texas Hold'em - Sala de Espera",
            description=f"**Apuesta mínima:** {game.min_bet} fichas\n**Jugadores:** {len(game.players)}/6",
            color=0x00ff00
        )
        
        if game.players:
            jugadores_texto = "\n".join([f"• {p['name']} ({p['chips']} fichas)" for p in game.players.values()])
            embed.add_field(name="👥 Jugadores Conectados", value=jugadores_texto, inline=False)
        else:
            embed.add_field(name="👥 Jugadores Conectados", value="Esperando jugadores...", inline=False)
        
        embed.add_field(
            name="🎯 Instrucciones",
            value="1. Presiona **Unirse al Juego** para participar\n2. El creador inicia cuando haya 2+ jugadores\n3. Cada jugador recibe 1000 fichas iniciales",
            inline=False
        )
        
        return embed
    
    def crear_embed_juego(self, estado: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"🎮 Poker Texas Hold'em - {estado['phase'].upper()}",
            color=0xff9900
        )
        
        embed.add_field(name="💰 Bote", value=f"**{estado['pot']}** fichas", inline=True)
        embed.add_field(name="📈 Apuesta Actual", value=f"**{estado['current_bet']}** fichas", inline=True)
        
        if estado['community_cards']:
            cartas_comunidad = " ".join(estado['community_cards'])
            embed.add_field(name="🎴 Cartas Comunitarias", value=cartas_comunidad, inline=False)
        
        # Información de jugadores
        jugadores_texto = []
        for pid, player in estado['players'].items():
            estado_jugador = "🃏 Tu turno" if player['is_turn'] else ""
            estado_jugador += " 🛑 Retirado" if player['folded'] else ""
            estado_jugador += " 💰 All-In" if player['all_in'] else ""
            
            jugadores_texto.append(
                f"**{player['name']}** - {player['chips']} fichas | Apuesta: {player['bet']} {estado_jugador}"
            )
        
        embed.add_field(name="👥 Jugadores", value="\n".join(jugadores_texto), inline=False)
        
        return embed

class PokerGameView(View):
    def __init__(self, game_id):
        super().__init__(timeout=30.0)
        self.game_id = game_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        game = poker_games.get(self.game_id)
        if not game:
            await interaction.response.send_message("❌ Este juego ya no existe.", ephemeral=True)
            return False
        
        current_player = list(game.players.keys())[game.current_player_index]
        return interaction.user.id == current_player
    
    @discord.ui.button(label="🛑 Retirarse", style=discord.ButtonStyle.danger)
    async def fold_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        if not game:
            return
        
        success = game.fold(interaction.user.id)
        if success:
            await self.procesar_turno(interaction)
        else:
            await interaction.response.send_message("❌ Error al retirarse.", ephemeral=True)
    
    @discord.ui.button(label="✅ Pagar", style=discord.ButtonStyle.primary)
    async def call_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        if not game:
            return
        
        success = game.call(interaction.user.id)
        if success:
            await self.procesar_turno(interaction)
        else:
            await interaction.response.send_message("❌ No tienes suficientes fichas para pagar.", ephemeral=True)
    
    @discord.ui.button(label="📈 Subir", style=discord.ButtonStyle.success)
    async def raise_button(self, interaction: discord.Interaction, button: Button):
        # Por simplicidad, subir el doble de la apuesta actual
        game = poker_games.get(self.game_id)
        if not game:
            return
        
        raise_amount = game.current_bet * 2 if game.current_bet > 0 else game.min_bet
        success = game.raise_bet(interaction.user.id, raise_amount)
        
        if success:
            await self.procesar_turno(interaction)
        else:
            await interaction.response.send_message("❌ No puedes subir esa cantidad.", ephemeral=True)
    
    async def procesar_turno(self, interaction: discord.Interaction):
        game = poker_games.get(self.game_id)
        if not game:
            return
        
        resultado = game.siguiente_turno()
        
        if resultado is True:
            # Turno normal, actualizar interfaz
            estado = game.obtener_estado_juego()
            embed = self.crear_embed_juego(estado)
            await interaction.response.edit_message(embed=embed, view=self)
            
        elif resultado is False:
            # Juego terminado (todos fold)
            await self.finalizar_juego(interaction, None)
            
        else:
            # Hay un ganador
            await self.finalizar_juego(interaction, resultado)
    
    async def finalizar_juego(self, interaction: discord.Interaction, resultados: List[Tuple[int, int]]):
        game = poker_games.get(self.game_id)
        if not game:
            return
        
        if resultados:
            # Obtener información de las manos
            info_manos = game.obtener_info_manos()
            
            embed = discord.Embed(
                title="🎉 ¡Showdown! - Resultados Finales",
                color=0x00ff00
            )
            
            # Mostrar información de cada mano
            for nombre, nombre_mano, cartas in info_manos:
                embed.add_field(
                    name=f"🎴 {nombre}",
                    value=f"Mano: {' '.join(cartas)}\n**{nombre_mano}**",
                    inline=False
                )
            
            # Mostrar ganadores
            ganadores_texto = []
            for ganador_id, premio in resultados:
                ganador = game.players[ganador_id]
                ganadores_texto.append(f"**{ganador['name']}** - {premio:,} créditos")
            
            embed.add_field(
                name="🏆 Ganadores",
                value="\n".join(ganadores_texto) if ganadores_texto else "No hay ganadores",
                inline=False
            )
            
        else:
            embed = discord.Embed(
                title="🎮 Juego Terminado",
                description="El juego ha finalizado sin ganadores.",
                color=0xff9900
            )
        
        # Eliminar juego
        if self.game_id in poker_games:
            del poker_games[self.game_id]
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    def crear_embed_juego(self, estado: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"🎮 Poker Texas Hold'em - {estado['phase'].upper()}",
            color=0xff9900
        )
        
        embed.add_field(name="💰 Bote", value=f"**{estado['pot']}** fichas", inline=True)
        embed.add_field(name="📈 Apuesta Actual", value=f"**{estado['current_bet']}** fichas", inline=True)
        
        if estado['community_cards']:
            cartas_comunidad = " ".join(estado['community_cards'])
            embed.add_field(name="🎴 Cartas Comunitarias", value=cartas_comunidad, inline=False)
        
        # Información de jugadores
        jugadores_texto = []
        for pid, player in estado['players'].items():
            estado_jugador = "🎯 **TU TURNO**" if player['is_turn'] else ""
            estado_jugador += " 🛑 Retirado" if player['folded'] else ""
            estado_jugador += " 💰 All-In" if player['all_in'] else ""
            
            jugadores_texto.append(
                f"**{player['name']}** - {player['chips']} fichas | Apuesta: {player['bet']} {estado_jugador}"
            )
        
        embed.add_field(name="👥 Jugadores", value="\n".join(jugadores_texto), inline=False)
        
        # Mostrar mano del jugador actual
        current_player = estado['current_player']
        if current_player and current_player in estado['players']:
            mano = estado['players'][current_player]['hand']
            embed.add_field(name="🎴 Tu Mano", value=" ".join(mano), inline=False)
        
        return embed

class Poker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="poker", aliases=["texas", "holdem"])
    async def poker(self, ctx, min_bet: int = 50):
        """Inicia una partida de Poker Texas Hold'em multijugador"""
        
        # Verificar si el usuario ya está en un juego
        for game_id, game in poker_games.items():
            if ctx.author.id in game.players:
                await ctx.send("❌ Ya estás en una partida de poker activa.")
                return
        
        # Crear nuevo juego
        game_id = f"poker_{ctx.author.id}_{int(ctx.message.created_at.timestamp())}"
        poker_games[game_id] = PokerGame(game_id, ctx.author.id, min_bet)
        
        # Agregar creador al juego
        poker_games[game_id].agregar_jugador(ctx.author.id, ctx.author.display_name)
        
        # Crear embed de lobby
        embed = discord.Embed(
            title="🎮 Poker Texas Hold'em - Sala de Espera",
            description=f"**Creador:** {ctx.author.mention}\n**Apuesta mínima:** {min_bet} fichas\n**Jugadores:** 1/6",
            color=0x00ff00
        )
        
        embed.add_field(
            name="👥 Jugadores Conectados",
            value=f"• {ctx.author.display_name} (1000 fichas)",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Instrucciones",
            value="1. Presiona **Unirse al Juego** para participar\n2. El creador inicia cuando haya 2+ jugadores\n3. Cada jugador recibe 1000 fichas iniciales",
            inline=False
        )
        
        view = PokerLobbyView(game_id, ctx.author.id)
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="pokergames", aliases=["partidaspoker"])
    async def poker_games(self, ctx):
        """Muestra las partidas de poker activas"""
        if not poker_games:
            await ctx.send("❌ No hay partidas de poker activas en este momento.")
            return
        
        embed = discord.Embed(
            title="🎮 Partidas de Poker Activas",
            color=0xff9900
        )
        
        for game_id, game in poker_games.items():
            estado = "🟢 En espera" if not game.game_started else "🟡 En juego"
            embed.add_field(
                name=f"Partida de {game.players[game.creator_id]['name']}",
                value=f"**Jugadores:** {len(game.players)}/6 | **Estado:** {estado}",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Poker(bot))