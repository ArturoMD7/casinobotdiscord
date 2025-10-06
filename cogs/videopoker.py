import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import asyncio
from typing import Optional, List, Tuple, Dict

from db.database import Database

PAY_TABLE: Dict[str, int] = {
    "Escalera Real": 800,
    "Escalera de Color": 50,
    "Póker": 25,
    "Full House": 9,
    "Color": 6,
    "Escalera": 4,
    "Trío": 3,
    "Doble Pareja": 2,
    "Jotas o Mejor": 1,
}

# Rangos numéricos para las manos, para facilitar la evaluación
HAND_RANKS: Dict[str, int] = {
    "Escalera Real": 10, "Escalera de Color": 9, "Póker": 8, "Full House": 7,
    "Color": 6, "Escalera": 5, "Trío": 4, "Doble Pareja": 3,
    "Jotas o Mejor": 2, "Nada": 1
}

# Valores de las cartas para la evaluación
CARD_VALUES = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}

# --- Lógica de la Vista del Juego ---

class VideoPokerGameView(View):
    def __init__(self, ctx: commands.Context, bet: int):
        super().__init__(timeout=180.0)
        self.ctx = ctx
        self.bet = bet
        
        self.deck: List[str] = self.create_deck()
        self.hand: List[str] = [self.deck.pop() for _ in range(5)]
        self.held_indices: set[int] = set()

        # Añadimos los botones de control de cartas
        self.add_item(self.create_hold_button(0))
        self.add_item(self.create_hold_button(1))
        self.add_item(self.create_hold_button(2))
        self.add_item(self.create_hold_button(3))
        self.add_item(self.create_hold_button(4))
        self.add_item(self.create_draw_button())
        
    def create_deck(self) -> List[str]:
        """Crea y baraja un mazo de 52 cartas."""
        suits = ['♠', '♥', '♦', '♣']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [f"{value}{suit}" for value in values for suit in suits]
        random.shuffle(deck)
        return deck

    def create_game_embed(self, title: str, result_text: str = "") -> discord.Embed:
        """Crea el embed que muestra el estado del juego."""
        embed = discord.Embed(title=f"🃏 Video Poker - {title}", color=discord.Color.gold())
        embed.add_field(name="Tu Mano", value=f"**{' '.join(self.hand)}**", inline=False)
        embed.set_footer(text=f"Apuesta: {self.bet} créditos")
        
        # Mostrar multiplicador activo si existe
        gacha_cog = self.ctx.bot.get_cog('Gacha')
        if gacha_cog:
            multiplicador = gacha_cog.obtener_multiplicador_activo(self.ctx.author.id)
            if multiplicador > 1.0:
                # Obtener usos restantes
                usos_restantes = 0
                if self.ctx.author.id in gacha_cog.bonos_activos and "multiplicador" in gacha_cog.bonos_activos[self.ctx.author.id]:
                    usos_restantes = gacha_cog.bonos_activos[self.ctx.author.id]["multiplicador"]["usos_restantes"]
                
                embed.add_field(
                    name="✨ Multiplicador Activo",
                    value=f"**x{multiplicador}** - Se aplicará si ganas | Usos restantes: **{usos_restantes}**",
                    inline=False
                )
        
        if result_text:
            embed.add_field(name="Resultado", value=result_text, inline=False)
        return embed

    def create_hold_button(self, index: int) -> Button:
        """Crea un botón para conservar una carta."""
        async def hold_callback(interaction: discord.Interaction):
            if interaction.user.id != self.ctx.author.id:
                return await interaction.response.send_message("No eres el jugador de esta partida.", ephemeral=True)
            
            button = self.children[index]
            if index in self.held_indices:
                self.held_indices.remove(index)
                button.style = discord.ButtonStyle.secondary
            else:
                self.held_indices.add(index)
                button.style = discord.ButtonStyle.success
            
            await interaction.response.edit_message(view=self)

        button = Button(label=f"Conservar {index + 1}", style=discord.ButtonStyle.secondary, row=0)
        button.callback = hold_callback
        return button

    def create_draw_button(self) -> Button:
        """Crea el botón para repartir las cartas finales."""
        async def draw_callback(interaction: discord.Interaction):
            if interaction.user.id != self.ctx.author.id:
                return await interaction.response.send_message("No eres el jugador de esta partida.", ephemeral=True)

            # Desactivar todos los botones
            for child in self.children:
                child.disabled = True
            
            # Repartir nuevas cartas para las no conservadas
            for i in range(5):
                if i not in self.held_indices:
                    self.hand[i] = self.deck.pop()

            # Evaluar la mano final y calcular el premio
            hand_name, _ = self.evaluate_hand(self.hand)
            payout_multiplier = PAY_TABLE.get(hand_name, 0)
            prize_base = self.bet * payout_multiplier
            
            # APLICAR MULTIPLICADOR DEL GACHA SI GANA
            multiplicador_gacha = 1.0
            usos_restantes = 0
            gacha_cog = self.ctx.bot.get_cog('Gacha')
            
            if prize_base > 0 and gacha_cog:
                multiplicador_gacha = gacha_cog.obtener_multiplicador_activo(self.ctx.author.id)
                if multiplicador_gacha > 1.0:
                    # Aplicar multiplicador del Gacha a la ganancia (esto consume usos automáticamente)
                    prize_final = gacha_cog.aplicar_multiplicador_ganancias(self.ctx.author.id, prize_base)
                    
                    # Obtener usos restantes
                    if self.ctx.author.id in gacha_cog.bonos_activos and "multiplicador" in gacha_cog.bonos_activos[self.ctx.author.id]:
                        usos_restantes = gacha_cog.bonos_activos[self.ctx.author.id]["multiplicador"]["usos_restantes"]
                else:
                    prize_final = prize_base
            else:
                prize_final = prize_base

            # Registrar el premio en la base de datos
            db = Database()
            if prize_final > 0:
                db.update_credits(self.ctx.author.id, prize_final, "win", "videopoker", f"Gana con {hand_name}")
            
            # Crear el embed final
            result_text = f"**Conseguiste: {hand_name}!**\n"
            
            if prize_final > 0:
                if multiplicador_gacha > 1.0:
                    result_text += f"Premio base: **{prize_base:,}** créditos (Apuesta: {self.bet:,} x{payout_multiplier})\n"
                    result_text += f"✨ **BONO GACHA:** {prize_base:,} → **{prize_final:,}** créditos (x{multiplicador_gacha})"
                    if usos_restantes > 0:
                        result_text += f" | Usos restantes: {usos_restantes}"
                else:
                    result_text += f"Premio: **{prize_final:,}** créditos. (Apuesta: {self.bet:,} x{payout_multiplier})"
            else:
                result_text += f"**No ganaste créditos.** (Apuesta: {self.bet:,} créditos)"
            
            final_embed = self.create_game_embed("Mano Final", result_text)
            
            await interaction.response.edit_message(embed=final_embed, view=self)
            self.stop()

        return Button(label="Repartir", style=discord.ButtonStyle.primary, row=1)

    def evaluate_hand(self, hand: List[str]) -> Tuple[str, int]:
        """Evalúa una mano de 5 cartas y devuelve su nombre y rango."""
        values = sorted([CARD_VALUES[card[:-1]] for card in hand], reverse=True)
        suits = [card[-1] for card in hand]
        
        is_flush = len(set(suits)) == 1
        is_straight = (values[0] - values[4] == 4 and len(set(values)) == 5) or (values == [14, 5, 4, 3, 2])

        if is_straight and is_flush:
            return ("Escalera Real" if values[0] == 14 else "Escalera de Color", HAND_RANKS["Escalera de Color"])

        counts = {v: values.count(v) for v in set(values)}
        sorted_counts = sorted(counts.values(), reverse=True)
        
        if sorted_counts[0] == 4: return ("Póker", HAND_RANKS["Póker"])
        if sorted_counts == [3, 2]: return ("Full House", HAND_RANKS["Full House"])
        if is_flush: return ("Color", HAND_RANKS["Color"])
        if is_straight: return ("Escalera", HAND_RANKS["Escalera"])
        if sorted_counts[0] == 3: return ("Trío", HAND_RANKS["Trío"])
        if sorted_counts == [2, 2, 1]: return ("Doble Pareja", HAND_RANKS["Doble Pareja"])
        if sorted_counts[0] == 2:
            pair_value = [v for v, count in counts.items() if count == 2][0]
            if pair_value >= 11:  # Jota, Reina, Rey o As
                return ("Jotas o Mejor", HAND_RANKS["Jotas o Mejor"])

        return ("Nada", HAND_RANKS["Nada"])

# --- Cog de Discord ---

class VideoPoker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @commands.command(name="videopoker", aliases=["vp"])
    async def videopoker(self, ctx, bet: Optional[int] = None):
        """Inicia un juego de Video Poker (Jacks or Better)."""

        # Si no se proporciona apuesta, mostrar la ayuda
        if bet is None:
            embed = discord.Embed(
                title="🃏 Video Poker (Jacks or Better)",
                description="¡Consigue la mejor mano de poker de 5 cartas para ganar!\nUsa `!videopoker <apuesta>` para jugar.",
                color=discord.Color.gold()
            )
            payout_info = "\n".join([f"**{hand}**: {multiplier}x" for hand, multiplier in PAY_TABLE.items()])
            embed.add_field(name="📋 Tabla de Pagos", value=payout_info)
            
            # Información sobre multiplicadores Gacha
            embed.add_field(
                name="✨ Sistema de Multiplicadores",
                value="Los multiplicadores obtenidos en el Gacha se aplican automáticamente a tus ganancias",
                inline=False
            )
            
            embed.add_field(
                name="📝 Cómo Jugar",
                value="1. Haces tu apuesta.\n"
                      "2. Recibes 5 cartas.\n"
                      "3. Eliges qué cartas **conservar**.\n"
                      "4. Las cartas no conservadas se cambian.\n"
                      "5. Si tu mano final es un par de Jotas o mejor, ¡ganas!",
                inline=False
            )
            return await ctx.send(embed=embed)

        # Validar la apuesta
        if bet <= 0:
            return await ctx.send("❌ La apuesta debe ser un número positivo.")
        
        user_credits = self.db.get_credits(ctx.author.id)
        if user_credits < bet:
            return await ctx.send(f"❌ No tienes suficientes créditos. Tienes {user_credits} créditos.")

        # Iniciar el juego
        self.db.update_credits(ctx.author.id, -bet, "bet", "videopoker", f"Apuesta inicial: {bet}")
        
        view = VideoPokerGameView(ctx, bet)
        initial_embed = view.create_game_embed("Mano Inicial")
        await ctx.send(embed=initial_embed, view=view)

    @commands.command(name="videopokermulti", aliases=["vpmulti"])
    async def videopoker_multi(self, ctx):
        """Muestra tu multiplicador activo de Gacha para Video Poker"""
        gacha_cog = self.bot.get_cog('Gacha')
        
        if not gacha_cog:
            await ctx.send("❌ El sistema de Gacha no está disponible.")
            return
            
        multiplicador = gacha_cog.obtener_multiplicador_activo(ctx.author.id)
        
        embed = discord.Embed(
            title="✨ Tu Multiplicador Activo - Video Poker",
            color=discord.Color.gold()
        )
        
        if multiplicador > 1.0:
            usos_restantes = 0
            if ctx.author.id in gacha_cog.bonos_activos and "multiplicador" in gacha_cog.bonos_activos[ctx.author.id]:
                usos_restantes = gacha_cog.bonos_activos[ctx.author.id]["multiplicador"]["usos_restantes"]
            
            embed.add_field(
                name="🎰 Multiplicador Activo",
                value=f"**x{multiplicador}** - Se aplicará automáticamente a tus ganancias",
                inline=False
            )
            embed.add_field(
                name="🔢 Usos Restantes", 
                value=f"**{usos_restantes}** usos", 
                inline=True
            )
            embed.add_field(
                name="💡 Cómo funciona",
                value="Se aplica cuando ganas en Video Poker",
                inline=True
            )
            
            # Mostrar ejemplo de ganancia
            ejemplo_apuesta = 100
            ejemplo_mano = "Jotas o Mejor"
            premio_base = ejemplo_apuesta * PAY_TABLE[ejemplo_mano]
            premio_con_multi = int(premio_base * multiplicador)
            
            embed.add_field(
                name="📊 Ejemplo",
                value=f"Con apuesta de {ejemplo_apuesta:,} y {ejemplo_mano}:\n"
                      f"Base: {premio_base:,} → Con multiplicador: **{premio_con_multi:,}**",
                inline=False
            )
        else:
            embed.add_field(
                name="❌ Sin Multiplicador Activo",
                value="No tienes multiplicadores activos del Gacha\n¡Abre cajas del Gacha para obtener multiplicadores!",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VideoPoker(bot))