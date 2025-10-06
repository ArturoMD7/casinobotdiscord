# Fichero: cogs/poker.py

import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
from typing import Dict, Optional
from game.poker_game import PokerGame

poker_games: Dict[str, PokerGame] = {}

class PokerLobbyView(View):
    # ... (código sin cambios)
    def __init__(self, game_id: str, creator_id: int):
        super().__init__(timeout=300.0)
        self.game_id = game_id
        self.creator_id = creator_id

    async def update_lobby_embed(self, interaction: discord.Interaction):
        game = poker_games.get(self.game_id)
        if not game:
            await interaction.message.edit(content="Este juego ha sido cancelado.", embed=None, view=None)
            return
        embed = self.create_lobby_embed(game)
        await interaction.message.edit(embed=embed)

    @discord.ui.button(label="Unirse al Juego", style=discord.ButtonStyle.primary, emoji="🎮")
    async def join_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        if not game: return await interaction.response.send_message("❌ Este juego ya no existe.", ephemeral=True)
        if game.game_started: return await interaction.response.send_message("❌ El juego ya comenzó.", ephemeral=True)
        if interaction.user.id in game.players: return await interaction.response.send_message("❌ Ya estás en este juego.", ephemeral=True)
        
        success = game.add_player(interaction.user.id, interaction.user.display_name)
        if success:
            await interaction.response.defer()
            await self.update_lobby_embed(interaction)
        else:
            await interaction.response.send_message("❌ No te puedes unir (límite de jugadores o fichas insuficientes).", ephemeral=True)

    @discord.ui.button(label="Iniciar Juego", style=discord.ButtonStyle.success, emoji="🚀")
    async def start_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.creator_id:
            return await interaction.response.send_message("❌ Solo el creador puede iniciar.", ephemeral=True)
        
        game = poker_games.get(self.game_id)
        if not game or len(game.players) < 2:
            return await interaction.response.send_message("❌ Se necesitan al menos 2 jugadores.", ephemeral=True)
        
        game.start_game()
        
        # Enviar cartas por Mensaje Directo al inicio
        for player_id, player_data in game.players.items():
            user = self.bot.get_user(player_id) if hasattr(self, 'bot') else interaction.client.get_user(player_id)
            if user:
                try:
                    hand_str = " ".join(player_data['hand'])
                    await user.send(f"**Juego de Poker en `{interaction.guild.name}`**\n> Tu mano inicial: **{hand_str}**")
                except discord.Forbidden:
                    await interaction.channel.send(f"⚠️ No pude enviarle las cartas por MD a {user.mention}. Asegúrate de tener los MDs abiertos.", delete_after=10)

        game_view = PokerGameView(self.game_id)
        embed = game_view.create_game_embed(game.get_game_state())
        
        await interaction.response.edit_message(embed=embed, view=game_view)
        game_view.message = await interaction.original_response()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        # ... (código sin cambios)
        if interaction.user.id != self.creator_id:
            return await interaction.response.send_message("❌ Solo el creador puede cancelar.", ephemeral=True)
        if self.game_id in poker_games: del poker_games[self.game_id]
        await interaction.response.edit_message(content="Juego cancelado por el creador.", embed=None, view=None)
    
    def create_lobby_embed(self, game: PokerGame) -> discord.Embed:
        # ... (código sin cambios)
        embed = discord.Embed(
            title="🎲 Sala de Poker Texas Hold'em",
            description=f"**Creador:** <@{game.creator_id}>\n**Apuesta Mínima:** `{game.min_bet}` fichas",
            color=discord.Color.green())
        players_info = "\n".join([f"• {p['name']} (`{p['chips']}` fichas)" for p in game.players.values()])
        embed.add_field(name=f"👥 Jugadores ({len(game.players)}/6)", value=players_info or "Esperando jugadores...", inline=False)
        embed.set_footer(text="Presiona 'Unirse' para entrar a la partida.")
        return embed

class PokerGameView(View):
    def __init__(self, game_id: str):
        super().__init__(timeout=None)
        self.game_id = game_id
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        game = poker_games.get(self.game_id)
        if not game: return False
        
        # Permite la interacción si el usuario es un jugador (para el botón "Ver Mi Mano")
        if interaction.user.id not in game.players:
            await interaction.response.send_message("No eres parte de este juego.", ephemeral=True)
            return False
        
        # Para botones de acción, verifica si es su turno
        custom_id = interaction.data.get("custom_id")
        action_buttons = ["fold_button", "check_button", "call_button", "raise_button"]
        if custom_id in action_buttons:
            if interaction.user.id != game.get_game_state().get("current_player_id"):
                await interaction.response.send_message("No es tu turno.", ephemeral=True)
                return False
        return True

    async def process_turn(self, interaction: discord.Interaction):
        game = poker_games.get(self.game_id)
        if not game: return

        if game.is_round_over():
            active_players = [p for p in game.players.values() if not p["folded"]]
            if len(active_players) <= 1:
                return await self.end_game(interaction)

            game.advance_to_next_phase()
            if game.game_phase == "showdown":
                return await self.end_game(interaction)
        else:
            game.get_next_player()
        
        state = game.get_game_state()
        embed = self.create_game_embed(state)
        await interaction.response.edit_message(embed=embed, view=self)

    async def end_game(self, interaction: discord.Interaction):
        game = poker_games.get(self.game_id)
        if not game: return
        
        results = game.determine_winner()
        game.game_phase = "showdown"
        state = game.get_game_state()
        
        embed = self.create_game_embed(state)
        winners_text = [f"🏆 **{game.players[wid]['name']}** gana `{prize}` con **{hname}**!" for wid, prize, hname in results]
        embed.add_field(name="🎉 Resultados", value="\n".join(winners_text), inline=False)
        embed.set_footer(text="La mano ha terminado.")
        
        if self.game_id in poker_games: del poker_games[self.game_id]
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Retirarse", style=discord.ButtonStyle.danger, row=0, custom_id="fold_button")
    async def fold_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        game.player_action(interaction.user.id, "fold")
        await self.process_turn(interaction)

    @discord.ui.button(label="Pasar", style=discord.ButtonStyle.secondary, row=0, custom_id="check_button")
    async def check_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        if not game.player_action(interaction.user.id, "check"):
            return await interaction.response.send_message("No puedes pasar, la apuesta ha subido.", ephemeral=True)
        await self.process_turn(interaction)

    @discord.ui.button(label="Igualar", style=discord.ButtonStyle.primary, row=0, custom_id="call_button")
    async def call_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        game.player_action(interaction.user.id, "call")
        await self.process_turn(interaction)

    @discord.ui.button(label="Subir", style=discord.ButtonStyle.success, row=1, custom_id="raise_button")
    async def raise_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        if not game.player_action(interaction.user.id, "raise", game.big_blind):
            return await interaction.response.send_message("No puedes subir esa cantidad o no tienes suficientes fichas.", ephemeral=True)
        await self.process_turn(interaction)

    # --- NUEVO BOTÓN PARA VER CARTAS ---
    @discord.ui.button(label="Ver Mi Mano", style=discord.ButtonStyle.secondary, emoji="🃏", row=1, custom_id="show_hand_button")
    async def show_hand_button(self, interaction: discord.Interaction, button: Button):
        game = poker_games.get(self.game_id)
        # La comprobación de que el usuario está en el juego ya la hace interaction_check
        player_hand = game.players[interaction.user.id].get("hand")
        if player_hand:
            hand_str = " ".join(player_hand)
            await interaction.response.send_message(f"Tus cartas privadas son: **{hand_str}**", ephemeral=True)
        else:
            await interaction.response.send_message("No se encontraron tus cartas.", ephemeral=True)
    
    def create_game_embed(self, state: dict) -> discord.Embed:
        # ... (código sin cambios, crea el embed del juego)
        phase_map = {
            "preflop": "Pre-Flop", "flop": "Flop", "turn": "Turn", "river": "River", "showdown": "Showdown"
        }
        embed = discord.Embed(title=f"🎲 Poker - {phase_map.get(state['phase'], 'En curso')}", color=discord.Color.blue())
        embed.add_field(name="💰 Bote", value=f"`{state['pot']}`", inline=True)
        embed.add_field(name="📈 Apuesta", value=f"`{state['current_bet']}`", inline=True)
        
        community_str = " ".join(state['community_cards']) if state['community_cards'] else "..."
        embed.add_field(name="🎴 Mesa", value=community_str, inline=False)
        
        players_info = []
        for pid, p in state['players'].items():
            status = ""
            if p['is_turn']: status = "▶️ **(Tu Turno)**"
            if p['folded']: status = "🛑 (Retirado)"
            if p['all_in']: status = "💰 (All-In)"

            hand_display = f" Mano: `{' '.join(p['hand'])}`" if state['phase'] == 'showdown' and not p['folded'] else ''
            
            player_line = f"**{p['name']}** | Fichas: `{p['chips']}` | Apuesta: `{p['bet']}` {status}{hand_display}"
            players_info.append(player_line)

        embed.add_field(name="👥 Jugadores", value="\n".join(players_info), inline=False)
        
        if state['current_player_id'] and state['phase'] != 'showdown':
            current_player_name = state['players'][state['current_player_id']]['name']
            embed.set_footer(text=f"Es el turno de {current_player_name}.")
        return embed

class Poker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="poker", aliases=["holdem"])
    async def poker(self, ctx, min_bet: int = 50):
        # Le pasa el bot a la vista para que pueda obtener usuarios
        game_id = f"poker_{ctx.channel.id}"
        if game_id in poker_games:
            return await ctx.send("❌ Ya hay una partida de poker activa en este canal.")

        # ... (resto del código sin cambios)
        for game in poker_games.values():
            if ctx.author.id in game.players:
                return await ctx.send("❌ Ya estás en una partida de poker activa.")
        
        game = PokerGame(game_id, ctx.author.id, min_bet)
        poker_games[game_id] = game
        game.add_player(ctx.author.id, ctx.author.display_name)
        
        view = PokerLobbyView(game_id, ctx.author.id)
        view.bot = self.bot # Pasa la instancia del bot
        embed = view.create_lobby_embed(game)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Poker(bot))