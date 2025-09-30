import discord
from discord.ext import commands

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="games", aliases=["juegos", "casino", "menu"])
    async def games(self, ctx):
        """🎰 Menú principal de juegos del casino"""
        
        embed = discord.Embed(
            title="🎰 **CASINO BOT - MENÚ PRINCIPAL** 🎰",
            description="¡Bienvenido al casino más emocionante de Discord! \nElige tu juego y demuestra tu suerte 🍀",
            color=0x00ff00
        )
        
        # Sección de Juegos de Cartas
        embed.add_field(
            name="🃏 **JUEGOS DE CARTAS**",
            value=(
                "```\n"
                "🎴 BLACKJACK (21)\n"
                "   !blackjack <apuesta>\n"
                "   !bj <apuesta>\n"
                "   Apuesta: 10 - 10,000 créditos\n"
                "```"
            ),
            inline=False
        )
        
        # Sección de Ruleta Rusa (el nuevo juego épico)
        embed.add_field(
            name="🔫 **RULETA RUSA PROGRESIVA**",
            value=(
                "```\n"
                "💀 RULETA RUSA MULTIPLICADORA\n"
                "   !ruletarusa <apuesta>\n"
                "   !rr <apuesta>\n"
                "   Apuesta: 100+ créditos\n"
                "   ¡Multiplica hasta x10!\n"
                "```"
            ),
            inline=False
        )
        
        # Sección de Juegos Clásicos
        embed.add_field(
            name="🎲 **JUEGOS CLÁSICOS**",
            value=(
                "```\n"
                "🎰 TRAGAMONEDAS\n"
                "   !slots <apuesta>\n"
                "   !traga <apuesta>\n"
                "   Apuesta: 10+ créditos\n"
                "\n"
                "🎡 RULETA\n"
                "   !ruleta <apuesta> <tipo> <valor>\n"
                "   Tipos: color, par, docena, numero\n"
                "   Apuesta: 10+ créditos\n"
                "\n"
                "🎯 DADOS (CRAPS)\n"
                "   !dados <apuesta>\n"
                "   !craps <apuesta>\n"
                "   Apuesta: 10+ créditos\n"
                "```"
            ),
            inline=False
        )
        
        # Sección de Economía y Utilidades
        embed.add_field(
            name="💰 **ECONOMÍA Y UTILIDADES**",
            value=(
                "```\n"
                "💳 BALANCE\n"
                "   !balance | !bal | !credits\n"
                "\n"
                "📊 ESTADÍSTICAS\n"
                "   !stats\n"
                "\n"
                "🎁 RECOMPENSA DIARIA\n"
                "   !daily (cada 24h)\n"
                "\n"
                "🏆 LEADERBOARD\n"
                "   !leaderboard | !top | !ranking\n"
                "\n"
                "💸 TRANSFERIR\n"
                "   !transfer @usuario <cantidad>\n"
                "   !pay @usuario <cantidad>\n"
                "\n"
                "🎭 ROBAR\n"
                "   !rob @usuario (50% éxito)\n"
                "```"
            ),
            inline=False
        )
        
        # Información adicional
        embed.add_field(
            name="ℹ️ **INFORMACIÓN IMPORTANTE**",
            value=(
                "• 💰 **Créditos iniciales:** 1,000\n"
                "• 🎯 **Todos los juegos tienen apuesta mínima**\n"
                "• ⚠️ **Juega responsablemente**\n"
                "• 🆘 **Usa** `!help <comando>` **para más info**"
            ),
            inline=False
        )
        
        # Footer con estadísticas del servidor
        embed.set_footer(
            text=f"🎮 Casino Bot | ¡Diviértete {ctx.author.display_name}!",
            icon_url=ctx.author.display_avatar.url
        )
        
        embed.set_thumbnail(url="https://media1.tenor.com/m/B_BloOGtz68AAAAd/cat-gambling.gif")
        
        await ctx.send(embed=embed)

    @commands.command(name="helpgames", aliases=["ayuda"])
    async def helpgames(self, ctx, juego: str = None):
        """Obtén ayuda específica sobre cada juego"""
        
        if juego is None:
            embed = discord.Embed(
                title="🎮 **AYUDA DE JUEGOS**",
                description="Usa `!helpgames <juego>` para ayuda específica\n\n**Juegos disponibles:** `blackjack`, `ruletarusa`, `slots`, `ruleta`, `dados`",
                color=0x0099ff
            )
            await ctx.send(embed=embed)
            return
        
        juego = juego.lower()
        
        if juego in ["blackjack", "bj", "21"]:
            embed = discord.Embed(
                title="🃏 **AYUDA - BLACKJACK**",
                description="El clásico juego de 21 contra la banca",
                color=0x00ff00
            )
            embed.add_field(
                name="🎯 **REGLAS**",
                value=(
                    "• Objetivo: Llegar a 21 o más cerca que la banca\n"
                    "• Blackjack natural (A + 10/J/Q/K) paga 3:2\n"
                    "• La banca se planta en 17\n"
                    "• Puedes pedir, plantarte, doblar o rendirte"
                ),
                inline=False
            )
            embed.add_field(
                name="💰 **COMANDOS**",
                value=(
                    "```\n"
                    "!blackjack <apuesta>  - Iniciar juego\n"
                    "!pedir               - Pedir carta\n"
                    "!plantarse           - Plantarse\n"
                    "!doblar              - Doblar apuesta\n"
                    "!rendirse            - Rendirse (pierdes mitad)\n"
                    "```"
                ),
                inline=False
            )
            embed.add_field(
                name="📊 **PAGOS**",
                value=(
                    "• **Blackjack:** 3:2 (x2.5)\n"
                    "• **Victoria normal:** 1:1 (x2)\n"
                    "• **Empate:** Recuperas apuesta\n"
                    "• **Rendición:** Pierdes mitad"
                ),
                inline=True
            )
            
        elif juego in ["ruletarusa", "rr", "rusa", "revolver"]:
            embed = discord.Embed(
                title="🔫 **AYUDA - RULETA RUSA PROGRESIVA**",
                description="Juego de alto riesgo con multiplicadores progresivos",
                color=0xff0000
            )
            embed.add_field(
                name="💀 **REGLAS**",
                value=(
                    "• **Ronda 1:** 6 cámaras, 1 bala → **x2**\n"
                    "• **Ronda 2:** 5 cámaras, 1 bala → **x3**\n"  
                    "• **Ronda 3:** 4 cámaras, 1 bala → **x4**\n"
                    "• **Ronda 4:** 3 cámaras, 1 bala → **x5**\n"
                    "• **Ronda 5:** 2 cámaras, 1 bala → **x6**\n"
                    "• **Ronda 6:** 1 cámara, 1 bala → **x10**"
                ),
                inline=False
            )
            embed.add_field(
                name="🎮 **CÓMO JUGAR**",
                value=(
                    "```\n"
                    "1. !ruletarusa <apuesta>\n"
                    "2. Usa botones para continuar o retirarte\n"
                    "3. ¡Sobrevive para multiplicar ganancias!\n"
                    "```"
                ),
                inline=False
            )
            embed.add_field(
                name="🎯 **PROBABILIDADES**",
                value=(
                    "• **R1:** 83.3% supervivencia\n"
                    "• **R2:** 80% supervivencia\n"
                    "• **R3:** 75% supervivencia\n"
                    "• **R4:** 66.7% supervivencia\n"
                    "• **R5:** 50% supervivencia\n"
                    "• **R6:** 0% supervivencia"
                ),
                inline=True
            )
            
        elif juego in ["slots", "traga", "slot"]:
            embed = discord.Embed(
                title="🎰 **AYUDA - TRAGAMONEDAS**",
                description="Máquina de slots clásica con múltiples combinaciones",
                color=0xff00ff
            )
            embed.add_field(
                name="🎯 **REGLAS**",
                value=(
                    "• Gira los 3 rodillos para hacer combinaciones\n"
                    "• Múltiples combinaciones ganadoras\n"
                    "• Símbolos especiales pagan más"
                ),
                inline=False
            )
            embed.add_field(
                name="💰 **COMANDOS**",
                value=(
                    "```\n"
                    "!slots <apuesta>\n"
                    "!traga <apuesta>\n"
                    "Apuesta mínima: 10 créditos\n"
                    "```"
                ),
                inline=False
            )
            
        elif juego in ["ruleta", "roulette"]:
            embed = discord.Embed(
                title="🎡 **AYUDA - RULETA**",
                description="La clásica ruleta europea (0-36)",
                color=0xff9900
            )
            embed.add_field(
                name="🎯 **TIPOS DE APUESTA**",
                value=(
                    "• **Color:** rojo/negro → **x2**\n"
                    "• **Par/Impar:** → **x2**\n"
                    "• **Docena:** 1/2/3 → **x3**\n"
                    "• **Número específico:** 0-36 → **x36**"
                ),
                inline=False
            )
            embed.add_field(
                name="💰 **EJEMPLOS**",
                value=(
                    "```\n"
                    "!ruleta 100 color rojo\n"
                    "!ruleta 50 par impar\n" 
                    "!ruleta 25 docena 2\n"
                    "!ruleta 10 numero 17\n"
                    "```"
                ),
                inline=False
            )
            
        elif juego in ["dados", "craps"]:
            embed = discord.Embed(
                title="🎲 **AYUDA - DADOS (CRAPS)**",
                description="Juego simple de tirar 2 dados",
                color=0x9933ff
            )
            embed.add_field(
                name="🎯 **REGLAS**",
                value=(
                    "• Tiras 2 dados\n"
                    "• **Ganas con:** 7 u 11\n"
                    "• **Pierdes con:** 2, 3 o 12\n"
                    "• **Otros números:** punto (juego continúa)"
                ),
                inline=False
            )
            embed.add_field(
                name="💰 **COMANDOS**",
                value=(
                    "```\n"
                    "!dados <apuesta>\n"
                    "!craps <apuesta>\n"
                    "Apuesta mínima: 10 créditos\n"
                    "Pago: 2x tu apuesta\n"
                    "```"
                ),
                inline=False
            )
            
        else:
            embed = discord.Embed(
                title="❌ JUEGO NO ENCONTRADO",
                description=f"El juego `{juego}` no existe.\nUsa `!helpgames` para ver la lista.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        embed.set_footer(text=f"¡Diviértete jugando {juego.upper()}! 🎮")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Games(bot))