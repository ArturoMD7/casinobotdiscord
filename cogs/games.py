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
        
        # Sección de Carrera de Buses
        embed.add_field(
            name="🚌 **CARRERA DE BUSES**",
            value=(
                "```\n"
                "🏁 CARRERA MULTIJUGADOR\n"
                "   !carrera\n"
                "   ¡Hasta 5 jugadores!\n"
                "   El ganador se lleva el pozo\n"
                "\n"
                "📊 CONTROL DE CARRERAS\n"
                "   !carreras       - Ver carreras activas\n"
                "   !micarrera      - Ver tu carrera\n"
                "```"
            ),
            inline=False
        )
        
        # Sección de Sistema Gacha
        embed.add_field(
            name="🎁 **SISTEMA GACHA**",
            value=(
                "```\n"
                "📦 CAJAS MISTERIOSAS\n"
                "   !gacha          - Abrir caja misteriosa\n"
                "   !gachastats     - Estadísticas del sistema\n"
                "\n"
                "🖼️ COLECCIÓN\n"
                "   !micoleccion    - Ver tus items\n"
                "   !misbonos       - Ver bonos activos\n"
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
                "\n"
                "🪙 CARA O CRUZ\n"
                "   !moneda <apuesta> <cara/cruz>\n"
                "   Apuesta: 10+ créditos\n"
                "   Pago: 2x\n"
                "\n"
                "⚔️ DUELO DE MONEDA\n"
                "   !duelomoneda @usuario <apuesta>\n"
                "   ¡Duelo contra otro jugador!\n"
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
                "   !blackjackstats\n"
                "   !monedastats\n"
                "   !ruletainfo\n"
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
                "\n"
                "⭐ RANGOS Y BONOS\n"
                "   !rangos          - Ver rangos disponibles\n"
                "   !rango           - Tu rango actual\n"
                "\n"
                "⚙️ ADMIN\n"
                "   !reload          - Recargar módulos (Owner)\n"
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
                "• 🆘 **Usa** `!help <comando>` **para más info**\n"
                "• 🆘 **Usa** `!helpgames <juego>` **para ayuda específica**"
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
                description="Usa `!helpgames <juego>` para ayuda específica\n\n**Juegos disponibles:** `blackjack`, `ruletarusa`, `carrera`, `gacha`, `slots`, `ruleta`, `dados`, `moneda`",
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
                    "!blackjackstats      - Ver estadísticas\n"
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
                    "4. !retirarse - Retirarte con ganancias\n"
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
            
        elif juego in ["carrera", "carreras", "bus"]:
            embed = discord.Embed(
                title="🚌 **AYUDA - CARRERA DE BUSES**",
                description="Carrera multijugador con hasta 5 participantes",
                color=0xff6600
            )
            embed.add_field(
                name="🎯 **REGLAS**",
                value=(
                    "• **Máximo 5 jugadores** por carrera\n"
                    "• Todos apuestan la misma cantidad\n"
                    "• **El ganador se lleva todo el pozo**\n"
                    "• Sistema de boost y eventos aleatorios\n"
                    "• El último bus en llegar pierde su apuesta"
                ),
                inline=False
            )
            embed.add_field(
                name="💰 **COMANDOS**",
                value=(
                    "```\n"
                    "!carrera        - Iniciar/Unirse a carrera\n"
                    "!carreras       - Ver carreras activas\n"
                    "!micarrera      - Ver tu carrera actual\n"
                    "```"
                ),
                inline=False
            )
            embed.add_field(
                name="🏆 **PREMIOS**",
                value=(
                    "• **1er lugar:** Todo el pozo\n"
                    "• **Eventos:** Bonos aleatorios\n"
                    "• **Boost:** Ventajas temporales"
                ),
                inline=True
            )
            
        elif juego in ["gacha", "caja", "misteriosa"]:
            embed = discord.Embed(
                title="🎁 **AYUDA - SISTEMA GACHA**",
                description="Sistema de cajas misteriosas con items épicos",
                color=0xff00ff
            )
            embed.add_field(
                name="🎯 **REGLAS**",
                value=(
                    "• **Diferentes rarezas:** Común, Raro, Épico, Legendario\n"
                    "• **Items coleccionables** únicos\n"
                    "• **Bonos temporales** de beneficios\n"
                    "• **Sistema de pity** para items raros\n"
                    "• **Colección completa** da recompensas especiales"
                ),
                inline=False
            )
            embed.add_field(
                name="💰 **COMANDOS**",
                value=(
                    "```\n"
                    "!gacha          - Abrir caja misteriosa\n"
                    "!gachastats     - Stats del sistema\n"
                    "!micoleccion    - Tu colección de items\n"
                    "!misbonos       - Tus bonos activos\n"
                    "```"
                ),
                inline=False
            )
            embed.add_field(
                name="📊 **RAREZAS**",
                value=(
                    "• **Común:** 60% probabilidad\n"
                    "• **Raro:** 25% probabilidad\n"
                    "• **Épico:** 10% probabilidad\n"
                    "• **Legendario:** 5% probabilidad"
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
                    "• Símbolos especiales pagan más\n"
                    "• **Jackpot progresivo** disponible"
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
            embed.add_field(
                name="🎯 **COMBINACIONES**",
                value=(
                    "• **3 iguales:** x5 a x100\n"
                    "• **2 iguales:** x2\n"
                    "• **Secuencias:** x10 a x50\n"
                    "• **Jackpot:** x1000"
                ),
                inline=True
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
                    "• **Columna:** → **x3**\n"
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
            embed.add_field(
                name="📊 **INFORMACIÓN**",
                value=(
                    "• **Ruleta Europea:** 0-36\n"
                    "• **Usa** `!ruletainfo` para stats\n"
                    "• **Probabilidad número:** 2.7%\n"
                    "• **Probabilidad color:** 48.6%"
                ),
                inline=True
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
                    "• Tiras 2 dados de 6 caras\n"
                    "• **Ganas con:** 7 u 11\n"
                    "• **Pierdes con:** 2, 3 o 12\n"
                    "• **Otros números:** punto (juego continúa)\n"
                    "• **Pago:** 2x tu apuesta"
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
                    "```"
                ),
                inline=False
            )
            embed.add_field(
                name="🎯 **PROBABILIDADES**",
                value=(
                    "• **Ganar en 1ra:** 22.2%\n"
                    "• **Perder en 1ra:** 11.1%\n"
                    "• **Punto:** 66.7%\n"
                    "• **Ventaja casa:** 1.41%"
                ),
                inline=True
            )
            
        elif juego in ["moneda", "caraocruz", "coin"]:
            embed = discord.Embed(
                title="🪙 **AYUDA - CARA O CRUZ**",
                description="Juego simple de azar contra la casa o otros jugadores",
                color=0xffcc00
            )
            embed.add_field(
                name="🎯 **MODOS DE JUEGO**",
                value=(
                    "• **Contra la casa:** !moneda <apuesta> <cara/cruz>\n"
                    "• **Duelo:** !duelomoneda @usuario <apuesta>\n"
                    "• **Pago normal:** 2x tu apuesta\n"
                    "• **50% de probabilidad** de ganar\n"
                    "• **Estadísticas:** !monedastats"
                ),
                inline=False
            )
            embed.add_field(
                name="💰 **EJEMPLOS**",
                value=(
                    "```\n"
                    "!moneda 100 cara\n"
                    "!moneda 50 cruz\n"
                    "!duelomoneda @amigo 200\n"
                    "```"
                ),
                inline=False
            )
            embed.add_field(
                name="📊 **ESTADÍSTICAS**",
                value=(
                    "• **Probabilidad:** 50%\n"
                    "• **Pago:** 2:1\n"
                    "• **Mínimo:** 10 créditos\n"
                    "• **Máximo:** Sin límite"
                ),
                inline=True
            )
            
        else:
            embed = discord.Embed(
                title="❌ JUEGO NO ENCONTRADO",
                description=f"El juego `{juego}` no existe.\nUsa `!helpgames` para ver la lista completa.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        embed.set_footer(text=f"¡Diviértete jugando {juego.upper()}! 🎮")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Games(bot))