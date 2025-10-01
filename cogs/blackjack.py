import discord
from discord.ext import commands
from discord.ui import Button, View
from db.database import Database
from game.blackjack_game import BlackjackGame
from config import MIN_BET, MAX_BET

db = Database()
games = {}

class BlackjackView(View):
    def __init__(self, game, user_id, author_name, message_id):
        super().__init__(timeout=60.0)
        self.game = game
        self.user_id = user_id
        self.author_name = author_name
        self.message_id = message_id
        self.update_buttons_state()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                f"❌ Esta partida de Blackjack pertenece a <@{self.user_id}>. "
                f"Usa `!blackjack <apuesta>` para iniciar tu propia partida.",
                ephemeral=True
            )
            return False
        return True
    
    async def on_timeout(self):
        game_key = f"{self.user_id}_{self.message_id}"
        if game_key in games:
            game = games[game_key]
            if not game.finished:
                db.update_credits(self.user_id, -game.bet, "loss", "blackjack", "Timeout")
            del games[game_key]
    
    def update_buttons_state(self):
        """Actualiza el estado de todos los botones basado en el juego actual"""
        game_key = f"{self.user_id}_{self.message_id}"
        if game_key not in games:
            return
        
        game = games[game_key]
        state = game.get_game_state()
        
        for item in self.children:
            if item.custom_id == "double":
                item.disabled = not state["can_double"]
            elif item.custom_id == "surrender":
                item.disabled = len(game.player_hand) > 2
            elif item.custom_id == "hit":
                item.disabled = state["finished"]
            elif item.custom_id == "stand":
                item.disabled = state["finished"]

    @discord.ui.button(label="📥 Pedir", style=discord.ButtonStyle.primary, custom_id="hit")
    async def hit_button(self, interaction: discord.Interaction, button: Button):
        game_key = f"{self.user_id}_{self.message_id}"
        game = games.get(game_key)
        
        if not game or game.finished:
            await interaction.response.send_message("❌ Esta partida ya terminó.", ephemeral=True)
            return
        
        result, value, finished = game.player_hit()
        state = game.get_game_state()
        
        if finished:
            # APLICAR MULTIPLICADOR DEL GACHA SI GANA
            if game.payout > 0:
                gacha_cog = interaction.client.get_cog('Gacha')
                if gacha_cog:
                    multiplicador_gacha = gacha_cog.obtener_multiplicador_activo(self.user_id)
                    if multiplicador_gacha > 1.0:
                        ganancia_base = game.payout
                        ganancia_final = gacha_cog.aplicar_multiplicador_ganancias(self.user_id, ganancia_base)
                        game.payout = ganancia_final
                        game.result_info = f"{game.result} (x{multiplicador_gacha})"
            
            db.update_credits(self.user_id, game.payout, "loss" if game.payout < 0 else "win", "blackjack", f"Blackjack: {result}")
            db.save_blackjack_game(self.user_id, game.bet, game.result, game.payout, game.player_hand, game.dealer_hand)
            del games[game_key]
            
            embed = self.create_game_embed(state, "💥 Te has pasado!")
            embed.add_field(name="Resultado", value=f"Has perdido {abs(game.payout):,} créditos", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            self.update_buttons_state()
            embed = self.create_game_embed(state, "📥 Has pedido carta")
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🛑 Plantarse", style=discord.ButtonStyle.success, custom_id="stand")
    async def stand_button(self, interaction: discord.Interaction, button: Button):
        game_key = f"{self.user_id}_{self.message_id}"
        game = games.get(game_key)
        
        if not game or game.finished:
            await interaction.response.send_message("❌ Esta partida ya terminó.", ephemeral=True)
            return
        
        result = game.player_stand()
        state = game.get_game_state()
        
        # APLICAR MULTIPLICADOR DEL GACHA SI GANA
        if game.payout > 0:
            gacha_cog = interaction.client.get_cog('Gacha')
            if gacha_cog:
                multiplicador_gacha = gacha_cog.obtener_multiplicador_activo(self.user_id)
                if multiplicador_gacha > 1.0:
                    ganancia_base = game.payout
                    ganancia_final = gacha_cog.aplicar_multiplicador_ganancias(self.user_id, ganancia_base)
                    game.payout = ganancia_final
                    game.result_info = f"{game.result} (x{multiplicador_gacha})"
        
        db.update_credits(self.user_id, game.payout, "win" if game.payout > 0 else "loss" if game.payout < 0 else "draw", "blackjack", f"Blackjack: {result}")
        db.save_blackjack_game(self.user_id, game.bet, game.result, game.payout, game.player_hand, game.dealer_hand)
        del games[game_key]
        
        result_text = self.get_result_text(game)
        
        embed = self.create_game_embed(state, "🏁 Partida Terminada")
        embed.add_field(name="Resultado", value=result_text, inline=False)
        
        # Mostrar información del multiplicador si se aplicó
        if hasattr(game, 'result_info') and 'x' in game.result_info:
            embed.add_field(
                name="✨ Multiplicador Gacha", 
                value=f"Se aplicó un multiplicador a tu ganancia", 
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="💰 Doblar", style=discord.ButtonStyle.danger, custom_id="double")
    async def double_button(self, interaction: discord.Interaction, button: Button):
        game_key = f"{self.user_id}_{self.message_id}"
        game = games.get(game_key)
        
        if not game:
            await interaction.response.send_message("❌ No tienes una partida en curso.", ephemeral=True)
            return
        
        if not game.can_double():
            await interaction.response.send_message("❌ Solo puedes doblar en tu primera jugada con 2 cartas.", ephemeral=True)
            return
        
        credits = db.get_credits(self.user_id)
        if game.bet * 2 > credits:
            await interaction.response.send_message("❌ No tienes suficientes créditos para doblar.", ephemeral=True)
            return
        
        result, value = game.player_double_down()
        state = game.get_game_state()
        
        if result == "bust":
            db.update_credits(self.user_id, game.payout, "loss", "blackjack", "Blackjack: double bust")
            db.save_blackjack_game(self.user_id, game.bet, game.result, game.payout, game.player_hand, game.dealer_hand)
            del games[game_key]
            
            embed = self.create_game_embed(state, "💥 Te has pasado!")
            embed.add_field(name="Resultado", value=f"Has perdido {abs(game.payout):,} créditos", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            result = game.player_stand()
            state = game.get_game_state()
            
            # APLICAR MULTIPLICADOR DEL GACHA SI GANA
            if game.payout > 0:
                gacha_cog = interaction.client.get_cog('Gacha')
                if gacha_cog:
                    multiplicador_gacha = gacha_cog.obtener_multiplicador_activo(self.user_id)
                    if multiplicador_gacha > 1.0:
                        ganancia_base = game.payout
                        ganancia_final = gacha_cog.aplicar_multiplicador_ganancias(self.user_id, ganancia_base)
                        game.payout = ganancia_final
                        game.result_info = f"{game.result} (x{multiplicador_gacha})"
            
            db.update_credits(self.user_id, game.payout, "win" if game.payout > 0 else "loss", "blackjack", f"Blackjack: double {result}")
            db.save_blackjack_game(self.user_id, game.bet, game.result, game.payout, game.player_hand, game.dealer_hand)
            del games[game_key]
            
            result_text = self.get_result_text(game)
            embed = self.create_game_embed(state, "🏁 Partida Terminada - Doble Apuesta")
            embed.add_field(name="Resultado", value=result_text, inline=False)
            
            # Mostrar información del multiplicador si se aplicó
            if hasattr(game, 'result_info') and 'x' in game.result_info:
                embed.add_field(
                    name="✨ Multiplicador Gacha", 
                    value=f"Se aplicó un multiplicador a tu ganancia", 
                    inline=False
                )
            
            await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="🏳️ Rendirse", style=discord.ButtonStyle.secondary, custom_id="surrender")
    async def surrender_button(self, interaction: discord.Interaction, button: Button):
        game_key = f"{self.user_id}_{self.message_id}"
        game = games.get(game_key)
        
        if not game:
            await interaction.response.send_message("❌ No tienes una partida en curso.", ephemeral=True)
            return
        
        if len(game.player_hand) > 2:
            await interaction.response.send_message("❌ Solo puedes rendirte en tu primera jugada.", ephemeral=True)
            return
        
        refund = game.bet // 2
        db.update_credits(self.user_id, -refund, "loss", "blackjack", "Blackjack: surrender")
        db.save_blackjack_game(self.user_id, game.bet, "surrender", -refund, game.player_hand, game.dealer_hand)
        del games[game_key]
        
        await interaction.response.edit_message(
            content=f"🏳️ {interaction.user.mention} te has rendido. Recuperas **{refund}** créditos de tu apuesta de {game.bet}.",
            embed=None,
            view=None
        )
    
    def create_game_embed(self, state, title):
        embed = discord.Embed(
            title=f"🎰 {title}",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="👤 Jugador",
            value=f"<@{self.user_id}>",
            inline=True
        )
        
        player_hand_str = " ".join(state["player_hand"])
        soft_text = " (soft)" if state["player_soft"] else ""
        embed.add_field(
            name=f"📋 Tu mano ({state['player_value']}{soft_text})",
            value=player_hand_str,
            inline=False
        )
        
        dealer_hand_str = " ".join(state["dealer_hand"])
        if state["finished"]:
            dealer_soft_text = " (soft)" if state["dealer_soft"] else ""
            dealer_value_text = f"({state['dealer_value']}{dealer_soft_text})"
        else:
            dealer_value_text = "(?)"
            
        embed.add_field(
            name=f"🎭 Banca {dealer_value_text}",
            value=dealer_hand_str,
            inline=False
        )
        
        embed.add_field(
            name="💰 Apuesta",
            value=f"{state['bet']:,} créditos",
            inline=True
        )
        
        # Mostrar multiplicador activo si existe
        gacha_cog = self.bot.get_cog('Gacha')
        if gacha_cog:
            multiplicador = gacha_cog.obtener_multiplicador_activo(self.user_id)
            if multiplicador > 1.0:
                embed.add_field(
                    name="✨ Multiplicador Activo",
                    value=f"**x{multiplicador}** - Se aplicará si ganas",
                    inline=True
                )
        
        if not state["finished"]:
            actions = []
            if state["can_double"]:
                actions.append("**Doblar** disponible")
            if len(state["player_hand"]) == 2:
                actions.append("**Rendirse** disponible")
            
            if actions:
                embed.add_field(
                    name="🎮 Acciones",
                    value="\n".join(actions),
                    inline=True
                )
        
        embed.set_footer(text=f"Jugador: {self.author_name}")
        return embed
    
    def get_result_text(self, game):
        if hasattr(game, 'result_info') and 'x' in game.result_info:
            # Resultado con multiplicador aplicado
            if game.result == "blackjack":
                return f"🎉 **BLACKJACK!** Ganas {game.payout:,} créditos (3:2 + multiplicador)"
            elif game.result == "win":
                return f"🎉 **Ganaste!** Ganas {game.payout:,} créditos (con multiplicador)"
            elif game.result == "loss":
                return f"❌ **Perdiste** {abs(game.payout):,} créditos"
            else:
                return "🤝 **Empate**, recuperas tu apuesta"
        else:
            # Resultado normal
            if game.result == "blackjack":
                return f"🎉 **BLACKJACK!** Ganas {game.payout:,} créditos (3:2)"
            elif game.result == "win":
                return f"🎉 **Ganaste!** Ganas {game.payout:,} créditos"
            elif game.result == "loss":
                return f"❌ **Perdiste** {abs(game.payout):,} créditos"
            else:
                return "🤝 **Empate**, recuperas tu apuesta"

class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="blackjack", aliases=["bj", "21"])
    async def blackjack(self, ctx, bet: int = None):
        """Inicia una partida de Blackjack con botones interactivos"""
        user_id = ctx.author.id
        
        # Verificar si ya tiene una partida en curso
        user_active_games = [k for k in games.keys() if k.startswith(f"{user_id}_")]
        if user_active_games:
            await ctx.send("❌ Ya tienes una partida de Blackjack en curso. Termina tu partida actual antes de empezar otra.")
            return
        
        # Validar apuesta
        if bet is None:
            embed = discord.Embed(
                title="🎰 Blackjack",
                description=f"Usa: `!blackjack <apuesta>`\nApuesta mínima: {MIN_BET}\nApuesta máxima: {MAX_BET:,}",
                color=discord.Color.blue()
            )
            embed.add_field(name="✨ Multiplicadores", value="Los multiplicadores del Gacha se aplican automáticamente a tus ganancias", inline=False)
            await ctx.send(embed=embed)
            return
        
        if bet < MIN_BET:
            await ctx.send(f"❌ Apuesta mínima: {MIN_BET} créditos")
            return
        
        if bet > MAX_BET:
            await ctx.send(f"❌ Apuesta máxima: {MAX_BET:,} créditos")
            return
        
        credits = db.get_credits(user_id)
        if bet > credits:
            await ctx.send(f"❌ No tienes suficientes créditos. Tu balance: {credits:,}")
            return
        
        # Crear nueva partida
        game = BlackjackGame(bet, user_id)
        
        # Enviar mensaje primero para obtener el ID
        state = game.get_game_state()
        view = BlackjackView(game, user_id, ctx.author.display_name, "temp")
        view.bot = self.bot  # Pasar referencia del bot al view
        
        embed = view.create_game_embed(state, "Nueva Partida de Blackjack")
        message = await ctx.send(embed=embed, view=view)
        
        # Actualizar el view con el message_id real y guardar el juego
        view.message_id = message.id
        game_key = f"{user_id}_{message.id}"
        games[game_key] = game

    # Los comandos de texto alternativos (pedir, plantarse, doblar, rendirse) 
    # se mantienen igual pero con la misma lógica de multiplicadores aplicada

    @commands.command(name="blackjackstats", aliases=["bjstats"])
    async def blackjackstats(self, ctx):
        """Muestra estadísticas de blackjack activas"""
        user_id = ctx.author.id
        user_active_games = [k for k in games.keys() if k.startswith(f"{user_id}_")]
        
        if not user_active_games:
            await ctx.send("❌ No tienes partidas de Blackjack activas.")
            return
        
        embed = discord.Embed(
            title="📊 Partidas de Blackjack Activas",
            description=f"Tienes **{len(user_active_games)}** partida(s) activa(s)",
            color=discord.Color.blue()
        )
        
        # Verificar multiplicador activo
        gacha_cog = self.bot.get_cog('Gacha')
        multiplicador_info = ""
        if gacha_cog:
            multiplicador = gacha_cog.obtener_multiplicador_activo(user_id)
            if multiplicador > 1.0:
                multiplicador_info = f" | 🎰 Multiplicador activo: **x{multiplicador}**"
        
        for i, game_key in enumerate(user_active_games, 1):
            game = games[game_key]
            state = game.get_game_state()
            embed.add_field(
                name=f"Partida {i}",
                value=f"Apuesta: {state['bet']:,} | Cartas: {len(state['player_hand'])} | Valor: {state['player_value']}{multiplicador_info}",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Blackjack(bot))