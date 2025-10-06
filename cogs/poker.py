import discord
from discord.ext import commands
from discord.ui import Button, View
from game.poker_game import PokerGame
import asyncio
import random
from typing import List, Dict, Tuple

# Diccionario para guardar juegos activos
poker_games = {}

# Mapeo de cartas a emojis (opcional)
CARD_EMOJIS = {
    '♠': '♠️',
    '♥': '♥️', 
    '♦': '♦️',
    '♣': '♣️'
}

def formatear_carta(carta: str) -> str:
    """Formatea una carta para mostrar con emojis"""
    if len(carta) == 2:
        valor, palo = carta[0], carta[1]
    else:  # 10
        valor, palo = carta[:2], carta[2]
    
    emoji_palo = CARD_EMOJIS.get(palo, palo)
    return f"{valor}{emoji_palo}"

class PokerLobbyView(View):
    def __init__(self, game_id, creator_id):
        super().__init__(timeout=120.0)
        self.game_id = game_id
        self.creator_id = creator_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True
    
    @discord.ui.button(label="🎮 Unirse al Juego", style=discord.ButtonStyle.primary)
    async def join_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        if not game:
            await interaction.response.send_message("❌ Este juego ya no existe.", ephemeral=True)
            return
        
        if game.game_started:
            await interaction.response.send_message("❌ El juego ya comenzó.", ephemeral=True)
            return
        
        # Verificar si ya está en el juego
        if interaction.user.id in game.players:
            await interaction.response.send_message("❌ Ya estás en este juego.", ephemeral=True)
            return
        
        success = game.agregar_jugador(interaction.user.id, interaction.user.display_name)
        if success:
            await interaction.response.send_message(f"✅ {interaction.user.mention} se unió al juego!", ephemeral=True)
            
            # Enviar mensaje privado con instrucciones
            try:
                embed_privado = discord.Embed(
                    title="🎮 Poker Texas Hold'em",
                    description="Te has unido a una partida de poker. Recibirás tus cartas cuando el juego comience.",
                    color=0x00ff00
                )
                embed_privado.add_field(
                    name="📋 Instrucciones",
                    value="• Espera a que el creador inicie el juego\n• Recibirás un mensaje privado con tus cartas\n• Toma decisiones en el canal principal",
                    inline=False
                )
                await interaction.user.send(embed=embed_privado)
            except:
                pass  # El usuario tiene los DMs cerrados
            
            # Actualizar embed del lobby
            embed = self.crear_embed_lobby(game)
            await interaction.message.edit(embed=embed)
        else:
            await interaction.response.send_message("❌ No se pudo unir al juego. Verifica que tengas suficientes créditos y no estés ya en el juego.", ephemeral=True)
    
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
            # Enviar cartas a cada jugador por DM
            for player_id, player_data in game.players.items():
                try:
                    user = await interaction.guild.fetch_member(player_id)
                    mano = player_data["hand"]
                    cartas_formateadas = " ".join([formatear_carta(carta) for carta in mano])
                    
                    embed_mano = discord.Embed(
                        title="🎴 Tus Cartas de Poker",
                        description=f"**Tus cartas:** {cartas_formateadas}",
                        color=0xff9900
                    )
                    embed_mano.add_field(
                        name="💡 Información",
                        value="• Tus cartas son privadas\n• Toma decisiones en el canal principal\n• ¡Buena suerte!",
                        inline=False
                    )
                    await user.send(embed=embed_mano)
                except Exception as e:
                    print(f"No se pudo enviar DM a {player_data['name']}: {e}")
            
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
            cartas_comunidad = " ".join([formatear_carta(carta) for carta in estado['community_cards']])
            embed.add_field(name="🎴 Cartas Comunitarias", value=cartas_comunidad, inline=False)
        
        # Información de jugadores
        jugadores_texto = []
        for pid, player in estado['players'].items():
            estado_jugador = "🃏 **TURNO ACTUAL**" if player['is_turn'] else ""
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
        
        current_player_id = list(game.players.keys())[game.current_player_index] if game.players else None
        if not current_player_id or interaction.user.id != current_player_id:
            await interaction.response.send_message("❌ No es tu turno.", ephemeral=True)
            return False
        
        return True
    
    @discord.ui.button(label="🛑 Retirarse", style=discord.ButtonStyle.danger)
    async def fold_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        if not game:
            return
        
        success = game.fold(interaction.user.id)
        if success:
            await interaction.response.send_message(f"🎯 {interaction.user.mention} se retira de la mano!", ephemeral=False)
            await self.procesar_turno(interaction)
        else:
            await interaction.response.send_message("❌ Error al retirarse.", ephemeral=True)
    
    @discord.ui.button(label="✅ Pagar", style=discord.ButtonStyle.primary)
    async def call_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        if not game:
            return
        
        player = game.players[interaction.user.id]
        cantidad_a_pagar = game.current_bet - player["bet"]
        
        success = game.call(interaction.user.id)
        if success:
            await interaction.response.send_message(f"💰 {interaction.user.mention} paga {cantidad_a_pagar} fichas!", ephemeral=False)
            await self.procesar_turno(interaction)
        else:
            await interaction.response.send_message("❌ No tienes suficientes fichas para pagar.", ephemeral=True)
    
    @discord.ui.button(label="📈 Subir", style=discord.ButtonStyle.success)
    async def raise_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        if not game:
            return
        
        # Por simplicidad, subir el doble de la apuesta actual o la mínima
        raise_amount = game.current_bet * 2 if game.current_bet > 0 else game.min_bet
        success = game.raise_bet(interaction.user.id, raise_amount)
        
        if success:
            await interaction.response.send_message(f"📈 {interaction.user.mention} sube a {game.current_bet} fichas!", ephemeral=False)
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
            await interaction.message.edit(embed=embed, view=self)
            
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
                cartas_formateadas = " ".join([formatear_carta(carta) for carta in cartas])
                embed.add_field(
                    name=f"🎴 {nombre}",
                    value=f"Mano: {cartas_formateadas}\n**{nombre_mano}**",
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
        
        await interaction.message.edit(embed=embed, view=None)
    
    def crear_embed_juego(self, estado: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"🎮 Poker Texas Hold'em - {estado['phase'].upper()}",
            color=0xff9900
        )
        
        embed.add_field(name="💰 Bote", value=f"**{estado['pot']}** fichas", inline=True)
        embed.add_field(name="📈 Apuesta Actual", value=f"**{estado['current_bet']}** fichas", inline=True)
        
        if estado['community_cards']:
            cartas_comunidad = " ".join([formatear_carta(carta) for carta in estado['community_cards']])
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
        
        # Mostrar mano del jugador actual si es su turno
        current_player = estado['current_player']
        if current_player and current_player in estado['players'] and estado['players'][current_player]['is_turn']:
            mano = estado['players'][current_player]['hand']
            cartas_formateadas = " ".join([formatear_carta(carta) for carta in mano])
            embed.add_field(name="🎴 Tu Mano (Privada)", value=cartas_formateadas, inline=False)
            embed.set_footer(text="Tus cartas son privadas. Solo tú puedes verlas aquí.")
        
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
        success = poker_games[game_id].agregar_jugador(ctx.author.id, ctx.author.display_name)
        if not success:
            await ctx.send("❌ No tienes suficientes créditos para jugar.")
            return
        
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
            value="1. Presiona **Unirse al Juego** para participar\n2. El creador inicia cuando haya 2+ jugadores\n3. Cada jugador recibe 1000 fichas iniciales\n4. Recibirás tus cartas por mensaje privado",
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
    
    @commands.command(name="micartas", aliases=["mismanos", "mimano"])
    async def mis_cartas(self, ctx):
        """Muestra tus cartas actuales en el juego de poker"""
        for game_id, game in poker_games.items():
            if ctx.author.id in game.players and game.game_started:
                mano = game.obtener_mano_jugador(ctx.author.id)
                if mano:
                    cartas_formateadas = " ".join([formatear_carta(carta) for carta in mano])
                    
                    embed = discord.Embed(
                        title="🎴 Tus Cartas de Poker",
                        description=f"**Tus cartas:** {cartas_formateadas}",
                        color=0xff9900
                    )
                    embed.add_field(
                        name="💡 Recordatorio",
                        value="Tus cartas son privadas. No las compartas con otros jugadores.",
                        inline=False
                    )
                    await ctx.author.send(embed=embed)
                    await ctx.send("✅ Te he enviado tus cartas por mensaje privado.", delete_after=10)
                else:
                    await ctx.send("❌ No tienes cartas repartidas o el juego no ha comenzado.", delete_after=10)
                return
        
        await ctx.send("❌ No estás en una partida de poker activa.", delete_after=10)

async def setup(bot):
    await bot.add_cog(Poker(bot))