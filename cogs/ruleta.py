import discord
from discord.ext import commands
import random
from db.database import Database

db = Database()

class Ruleta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.numbers = list(range(0, 37))  # 0-36
        self.colors = {
            **{i: "rojo" for i in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]},
            **{i: "negro" for i in [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]},
            0: "verde"
        }

    @commands.command(name="ruleta", aliases=["roulette"])
    async def ruleta(self, ctx, bet: int, tipo: str, *, apuesta: str = None):
        # Tipos de apuesta expandidos
        tipos_validos = ["color", "par", "docena", "fila", "columna", "cuadro", "calle", "pleno", "mitad", "tercio"]
        
        if tipo not in tipos_validos:
            embed = discord.Embed(
                title="🎡 Tipos de Apuesta Disponibles",
                description="```"
                          "color rojo/negro     - 2x\n"
                          "par impar           - 2x\n"
                          "docena 1/2/3        - 3x\n"
                          "fila 1/2/3          - 3x\n"
                          "columna 1/2/3       - 3x\n"
                          "mitad 1-18/19-36    - 2x\n"
                          "tercio bajo/medio/alto - 3x\n"
                          "calle 1-34          - 11x\n"
                          "cuadro 1-33         - 8x\n"
                          "pleno 0-36          - 36x\n"
                          "```",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        if bet < 10:
            await ctx.send("❌ Apuesta mínima: 10 créditos")
            return

        credits = db.get_credits(ctx.author.id)
        if bet > credits:
            await ctx.send(f"❌ No tienes suficientes créditos. Balance: {credits:,}")
            return

        # Girar ruleta
        numero_ganador = random.choice(self.numbers)
        color_ganador = self.colors[numero_ganador]

        # Verificar ganancia
        gano = False
        multiplicador_base = 1
        descripcion_apuesta = ""

        if tipo == "color":
            gano = apuesta.lower() == color_ganador
            multiplicador_base = 2
            descripcion_apuesta = f"Color: {apuesta.title()}"
            
        elif tipo == "par":
            es_par = numero_ganador % 2 == 0 and numero_ganador != 0
            gano = apuesta.lower() == "par" and es_par or apuesta.lower() == "impar" and not es_par
            multiplicador_base = 2
            descripcion_apuesta = f"Par/Impar: {apuesta.title()}"
            
        elif tipo == "docena":
            if numero_ganador == 0:
                gano = False
            else:
                docena = (numero_ganador - 1) // 12 + 1
                gano = int(apuesta) == docena
            multiplicador_base = 3
            descripcion_apuesta = f"Docena: {apuesta}"
            
        elif tipo == "fila":
            if numero_ganador == 0:
                gano = False
            else:
                fila = (numero_ganador - 1) % 3 + 1
                gano = int(apuesta) == fila
            multiplicador_base = 3
            descripcion_apuesta = f"Fila: {apuesta}"
            
        elif tipo == "columna":
            if numero_ganador == 0:
                gano = False
            else:
                columna = ((numero_ganador - 1) // 3) % 3 + 1
                gano = int(apuesta) == columna
            multiplicador_base = 3
            descripcion_apuesta = f"Columna: {apuesta}"
            
        elif tipo == "mitad":
            if numero_ganador == 0:
                gano = False
            else:
                if apuesta.lower() in ["1-18", "bajo"]:
                    gano = 1 <= numero_ganador <= 18
                elif apuesta.lower() in ["19-36", "alto"]:
                    gano = 19 <= numero_ganador <= 36
            multiplicador_base = 2
            descripcion_apuesta = f"Mitad: {apuesta}"
            
        elif tipo == "tercio":
            if numero_ganador == 0:
                gano = False
            else:
                if apuesta.lower() in ["bajo", "1-12"]:
                    gano = 1 <= numero_ganador <= 12
                elif apuesta.lower() in ["medio", "13-24"]:
                    gano = 13 <= numero_ganador <= 24
                elif apuesta.lower() in ["alto", "25-36"]:
                    gano = 25 <= numero_ganador <= 36
            multiplicador_base = 3
            descripcion_apuesta = f"Tercio: {apuesta}"
            
        elif tipo == "calle":
            if numero_ganador == 0:
                gano = False
            else:
                try:
                    calle_num = int(apuesta)
                    # Las calles son grupos de 3 números: 1-3, 4-6, ..., 34-36
                    gano = (calle_num - 1) * 3 + 1 <= numero_ganador <= calle_num * 3
                    multiplicador_base = 11
                    descripcion_apuesta = f"Calle: {apuesta} ({(calle_num-1)*3+1}-{calle_num*3})"
                except:
                    gano = False
                    
        elif tipo == "cuadro":
            if numero_ganador == 0:
                gano = False
            else:
                try:
                    cuadro_num = int(apuesta)
                    
                    if cuadro_num <= 8:
                        gano = (cuadro_num - 1) * 4 + 1 <= numero_ganador <= cuadro_num * 4
                        descripcion_apuesta = f"Cuadro: {apuesta} ({(cuadro_num-1)*4+1}-{cuadro_num*4})"
                    elif cuadro_num == 9:
                        gano = 33 <= numero_ganador <= 36
                        descripcion_apuesta = f"Cuadro: {apuesta} (33-36)"
                    else:
                        gano = False
                    multiplicador_base = 8
                except:
                    gano = False
                    
        elif tipo == "pleno":
            gano = int(apuesta) == numero_ganador
            multiplicador_base = 36
            descripcion_apuesta = f"Pleno: {apuesta}"

        # Calcular pago base
        if gano:
            ganancia_base = bet * multiplicador_base
            
            # APLICAR MULTIPLICADOR DEL GACHA (SISTEMA POR USOS)
            multiplicador_gacha = 1.0
            gacha_cog = self.bot.get_cog('Gacha')
            
            if gacha_cog:
                multiplicador_gacha = gacha_cog.obtener_multiplicador_activo(ctx.author.id)
                if multiplicador_gacha > 1.0:
                    # Aplicar multiplicador del Gacha a la ganancia (esto consume usos automáticamente)
                    ganancia_final = gacha_cog.aplicar_multiplicador_ganancias(ctx.author.id, ganancia_base)
                    
                    # Obtener usos restantes
                    usos_restantes = 0
                    if ctx.author.id in gacha_cog.bonos_activos and "multiplicador" in gacha_cog.bonos_activos[ctx.author.id]:
                        usos_restantes = gacha_cog.bonos_activos[ctx.author.id]["multiplicador"]["usos_restantes"]
                else:
                    ganancia_final = ganancia_base
                    usos_restantes = 0
            else:
                ganancia_final = ganancia_base
                usos_restantes = 0
                
            resultado_texto = f"🎉 **GANASTE** {ganancia_final:,} créditos!"
            
            # Añadir información del multiplicador si aplica
            if multiplicador_gacha > 1.0:
                resultado_texto += f"\n✨ **BONO GACHA:** {ganancia_base:,} → **{ganancia_final:,}** créditos (x{multiplicador_gacha})"
                if usos_restantes > 0:
                    resultado_texto += f" | Usos restantes: {usos_restantes}"
            
            # CORRECCIÓN: La ganancia neta es la ganancia final MENOS la apuesta inicial
            # porque ya se descontó la apuesta al principio
            ganancia_neto = ganancia_final - bet  # ¡ESTA ES LA LÍNEA CLAVE!
        
        else:
            ganancia_neto = -bet
            ganancia_final = 0
            resultado_texto = f"❌ **Perdiste** {bet:,} créditos"
            usos_restantes = 0

        # Actualizar créditos en la base de datos
        db.update_credits(ctx.author.id, ganancia_neto, "win" if gano else "loss", "ruleta", 
                         f"Ruleta: {tipo} {apuesta} -> {numero_ganador}")

        # Crear embed
        embed = discord.Embed(
            title="🎡 Ruleta",
            color=discord.Color.green() if gano else discord.Color.red()
        )
        
        embed.add_field(name="🎯 Número ganador", value=f"**{numero_ganador}** {color_ganador.title()}", inline=True)
        embed.add_field(name="💰 Tu apuesta", value=f"{bet:,}cr | {descripcion_apuesta}", inline=True)
        embed.add_field(name="📈 Multiplicador", value=f"{multiplicador_base}x", inline=True)
        
        # Mostrar información del multiplicador Gacha si aplica
        if gano and multiplicador_gacha > 1.0:
            embed.add_field(
                name="✨ Multiplicador Gacha Activo", 
                value=f"**x{multiplicador_gacha}** aplicado a tu ganancia | Usos restantes: **{usos_restantes}**", 
                inline=False
            )
        
        embed.add_field(name="🎰 Resultado", value=resultado_texto, inline=False)
        embed.add_field(name="💳 Balance nuevo", value=f"{db.get_credits(ctx.author.id):,} créditos", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="ruletainfo")
    async def ruleta_info(self, ctx):
        embed = discord.Embed(
            title="🎡 Información de Ruleta - Sistema Europeo (0-36)",
            color=discord.Color.blue()
        )
        
        # Tabla de apuestas
        apuestas_texto = (
            "```"
            "TIPO APUESTA        EJEMPLO              PAGO  PROBABILIDAD\n"
            "──────────────────────────────────────────────────────────\n"
            "Pleno               !ruleta 10 pleno 17   36x   2.7%\n"
            "Color               !ruleta 100 color rojo 2x   48.6%\n"
            "Par/Impar           !ruleta 50 par impar   2x   48.6%\n"
            "Mitad (1-18/19-36)  !ruleta 25 mitad bajo  2x   48.6%\n"
            "Docena (1-12/etc)   !ruleta 25 docena 1    3x   32.4%\n"
            "Columna             !ruleta 25 columna 1   3x   32.4%\n"
            "Fila                !ruleta 25 fila 1      3x   32.4%\n"
            "Tercio (bajo/medio/alto) 3x   32.4%\n"
            "Calle (1-3/etc)     !ruleta 10 calle 1    11x   8.1%\n"
            "Cuadro (1-4/etc)    !ruleta 10 cuadro 1    8x   10.8%\n"
            "```"
        )
        
        embed.add_field(
            name="🎯 Tipos de Apuesta",
            value=apuestas_texto,
            inline=False
        )
        
        # Distribución de números
        numeros_rojos = "1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36"
        numeros_negros = "2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35"
        
        embed.add_field(
            name="🎨 Distribución de Colores",
            value=f"**Rojo:** {numeros_rojos}\n**Negro:** {numeros_negros}\n**Verde:** 0",
            inline=False
        )
        
        # Información sobre multiplicadores Gacha
        embed.add_field(
            name="✨ Sistema de Multiplicadores Gacha",
            value="Los multiplicadores obtenidos en el Gacha se aplican automáticamente a tus ganancias\n"
                  "**Sistema por usos:** Cada multiplicador tiene usos limitados que se consumen al ganar",
            inline=False
        )
        
        # Ejemplos expandidos
        ejemplos_texto = (
            "```"
            "!ruleta 100 color rojo\n"
            "!ruleta 50 par impar\n"
            "!ruleta 25 docena 2\n"
            "!ruleta 25 fila 1\n"
            "!ruleta 25 columna 3\n"
            "!ruleta 25 mitad bajo\n"
            "!ruleta 25 tercio medio\n"
            "!ruleta 10 calle 5\n"
            "!ruleta 10 cuadro 3\n"
            "!ruleta 10 pleno 17\n"
            "```"
        )
        
        embed.add_field(
            name="💡 Ejemplos de Uso",
            value=ejemplos_texto,
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="ruletamulti")
    async def ruleta_multi(self, ctx):
        """Muestra tu multiplicador activo de Gacha para la ruleta"""
        gacha_cog = self.bot.get_cog('Gacha')
        
        if not gacha_cog:
            await ctx.send("❌ El sistema de Gacha no está disponible.")
            return
            
        multiplicador = gacha_cog.obtener_multiplicador_activo(ctx.author.id)
        
        embed = discord.Embed(
            title="✨ Tu Multiplicador Activo - Ruleta",
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
                value="Se aplica cuando ganas en cualquier tipo de apuesta",
                inline=True
            )
        else:
            embed.add_field(
                name="❌ Sin Multiplicador Activo",
                value="No tienes multiplicadores activos del Gacha\n¡Abre cajas del Gacha para obtener multiplicadores!",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Ruleta(bot))