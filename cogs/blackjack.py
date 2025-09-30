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
        
        db.update_credits(self.user_id, game.payout, "win" if game.payout > 0 else "loss" if game.payout < 0 else "draw", "blackjack", f"Blackjack: {result}")
        db.save_blackjack_game(self.user_id, game.bet, game.result, game.payout, game.player_hand, game.dealer_hand)
        del games[game_key]
        
        result_text = self.get_result_text(game)
        
        embed = self.create_game_embed(state, "🏁 Partida Terminada")
        embed.add_field(name="Resultado", value=result_text, inline=False)
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
            
            db.update_credits(self.user_id, game.payout, "win" if game.payout > 0 else "loss", "blackjack", f"Blackjack: double {result}")
            db.save_blackjack_game(self.user_id, game.bet, game.result, game.payout, game.player_hand, game.dealer_hand)
            del games[game_key]
            
            result_text = self.get_result_text(game)
            embed = self.create_game_embed(state, "🏁 Partida Terminada - Doble Apuesta")
            embed.add_field(name="Resultado", value=result_text, inline=False)
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
        
        embed = view.create_game_embed(state, "Nueva Partida de Blackjack")
        message = await ctx.send(embed=embed, view=view)
        
        # Actualizar el view con el message_id real y guardar el juego
        view.message_id = message.id
        game_key = f"{user_id}_{message.id}"
        games[game_key] = game

    @commands.command(name="pedir", aliases=["hit"])
    async def hit(self, ctx):
        """Pide una carta (comando de texto alternativo)"""
        user_id = ctx.author.id
        
        # Buscar partida activa del usuario
        user_active_games = [k for k in games.keys() if k.startswith(f"{user_id}_")]
        if not user_active_games:
            await ctx.send("❌ No tienes una partida de Blackjack en curso. Usa `!blackjack <apuesta>` para empezar.")
            return
        
        # Tomar la primera partida activa (en caso de múltiples)
        game_key = user_active_games[0]
        game = games.get(game_key)
        
        if not game or game.finished:
            await ctx.send("❌ Esta partida ya ha terminado.")
            return
        
        result, value, finished = game.player_hit()
        state = game.get_game_state()
        
        if finished:
            db.update_credits(user_id, game.payout, "loss" if game.payout < 0 else "win", "blackjack", f"Blackjack: {result}")
            db.save_blackjack_game(user_id, game.bet, game.result, game.payout, game.player_hand, game.dealer_hand)
            del games[game_key]
            
            embed = discord.Embed(title="💥 Te has pasado!", color=discord.Color.red())
            embed.add_field(name="Tus cartas", value=f"{game.player_hand} ({value})", inline=False)
            embed.add_field(name="Resultado", value=f"Has perdido {abs(game.payout):,} créditos", inline=False)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="📥 Has pedido carta", color=discord.Color.blue())
            embed.add_field(name="Tus cartas", value=f"{game.player_hand} ({value})", inline=False)
            await ctx.send(embed=embed)

    @commands.command(name="plantarse", aliases=["stand"])
    async def stand(self, ctx):
        """Te plantas con tu mano actual (comando de texto alternativo)"""
        user_id = ctx.author.id
        
        # Buscar partida activa del usuario
        user_active_games = [k for k in games.keys() if k.startswith(f"{user_id}_")]
        if not user_active_games:
            await ctx.send("❌ No tienes una partida de Blackjack en curso. Usa `!blackjack <apuesta>` para empezar.")
            return
        
        game_key = user_active_games[0]
        game = games.get(game_key)
        
        if not game or game.finished:
            await ctx.send("❌ Esta partida ya ha terminado.")
            return
        
        result = game.player_stand()
        state = game.get_game_state()
        
        # Procesar resultado
        db.update_credits(user_id, game.payout, "win" if game.payout > 0 else "loss" if game.payout < 0 else "draw", "blackjack", f"Blackjack: {result}")
        db.save_blackjack_game(user_id, game.bet, game.result, game.payout, game.player_hand, game.dealer_hand)
        del games[game_key]
        
        result_text = ""
        if game.result == "blackjack":
            result_text = f"🎉 **BLACKJACK!** Ganas {game.payout:,} créditos (3:2)"
        elif game.result == "win":
            result_text = f"🎉 **Ganaste!** Ganas {game.payout:,} créditos"
        elif game.result == "loss":
            result_text = f"❌ **Perdiste** {abs(game.payout):,} créditos"
        else:
            result_text = "🤝 **Empate**, recuperas tu apuesta"
        
        embed = discord.Embed(title="🏁 Partida Terminada", color=discord.Color.green())
        embed.add_field(name="Tus cartas", value=f"{game.player_hand} ({game.hand_value(game.player_hand)[0]})", inline=False)
        embed.add_field(name="Cartas de la banca", value=f"{game.dealer_hand} ({game.hand_value(game.dealer_hand)[0]})", inline=False)
        embed.add_field(name="Resultado", value=result_text, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="doblar", aliases=["double"])
    async def double(self, ctx):
        """Dobla tu apuesta (comando de texto alternativo)"""
        user_id = ctx.author.id
        
        # Buscar partida activa del usuario
        user_active_games = [k for k in games.keys() if k.startswith(f"{user_id}_")]
        if not user_active_games:
            await ctx.send("❌ No tienes una partida de Blackjack en curso.")
            return
        
        game_key = user_active_games[0]
        game = games.get(game_key)
        
        credits = db.get_credits(user_id)
        if game.bet * 2 > credits:
            await ctx.send("❌ No tienes suficientes créditos para doblar.")
            return
        
        result, value = game.player_double_down()
        state = game.get_game_state()
        
        if result == "cannot_double":
            await ctx.send("❌ Solo puedes doblar en tu primera jugada con 2 cartas.")
            return
        
        if result == "bust":
            db.update_credits(user_id, game.payout, "loss", "blackjack", "Blackjack: double bust")
            db.save_blackjack_game(user_id, game.bet, game.result, game.payout, game.player_hand, game.dealer_hand)
            del games[game_key]
            
            embed = discord.Embed(title="💥 Te has pasado!", color=discord.Color.red())
            embed.add_field(name="Tus cartas", value=f"{game.player_hand} ({value})", inline=False)
            embed.add_field(name="Resultado", value=f"Has perdido {abs(game.payout):,} créditos", inline=False)
            await ctx.send(embed=embed)
        else:
            result = game.player_stand()
            state = game.get_game_state()
            
            db.update_credits(user_id, game.payout, "win" if game.payout > 0 else "loss", "blackjack", f"Blackjack: double {result}")
            db.save_blackjack_game(user_id, game.bet, game.result, game.payout, game.player_hand, game.dealer_hand)
            del games[game_key]
            
            result_text = ""
            if game.result == "blackjack":
                result_text = f"🎉 **BLACKJACK!** Ganas {game.payout:,} créditos"
            elif game.result == "win":
                result_text = f"🎉 **Ganaste!** Ganas {game.payout:,} créditos"
            elif game.result == "loss":
                result_text = f"❌ **Perdiste** {abs(game.payout):,} créditos"
            else:
                result_text = "🤝 **Empate**, recuperas tu apuesta"
            
            embed = discord.Embed(title="🏁 Partida Terminada - Doble Apuesta", color=discord.Color.green())
            embed.add_field(name="Tus cartas", value=f"{game.player_hand} ({game.hand_value(game.player_hand)[0]})", inline=False)
            embed.add_field(name="Cartas de la banca", value=f"{game.dealer_hand} ({game.hand_value(game.dealer_hand)[0]})", inline=False)
            embed.add_field(name="Resultado", value=result_text, inline=False)
            
            await ctx.send(embed=embed)

    @commands.command(name="rendirse", aliases=["surrender"])
    async def surrender(self, ctx):
        """Te rindes (comando de texto alternativo)"""
        user_id = ctx.author.id
        
        # Buscar partida activa del usuario
        user_active_games = [k for k in games.keys() if k.startswith(f"{user_id}_")]
        if not user_active_games:
            await ctx.send("❌ No tienes una partida de Blackjack en curso.")
            return
        
        game_key = user_active_games[0]
        game = games.get(game_key)
        
        if len(game.player_hand) > 2:
            await ctx.send("❌ Solo puedes rendirte en tu primera jugada.")
            return
        
        refund = game.bet // 2
        db.update_credits(user_id, -refund, "loss", "blackjack", "Blackjack: surrender")
        db.save_blackjack_game(user_id, game.bet, "surrender", -refund, game.player_hand, game.dealer_hand)
        del games[game_key]
        
        await ctx.send(f"🏳️ {ctx.author.mention} te has rendido. Recuperas **{refund}** créditos de tu apuesta de {game.bet}.")

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
        
        for i, game_key in enumerate(user_active_games, 1):
            game = games[game_key]
            state = game.get_game_state()
            embed.add_field(
                name=f"Partida {i}",
                value=f"Apuesta: {state['bet']:,} | Cartas: {len(state['player_hand'])} | Valor: {state['player_value']}",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Blackjack(bot))