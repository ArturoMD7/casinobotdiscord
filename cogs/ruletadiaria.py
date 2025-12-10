import discord
from discord.ext import commands
from discord.ui import Button, View
from db.database import Database
import random
import asyncio
import time

db = Database()

# Sistema de Ruleta Diaria ACTUALIZADO - Multiplicadores por usos
RULETA_DIARIA = {
    "cooldown": 86400,  # 24 horas en segundos
    "premios": [
        # Premios en créditos (15 premios)
        {"tipo": "creditos", "valor": 1000, "nombre": "🎯 Premio Básico", "emoji": "💰", "color": 0x808080},
        {"tipo": "creditos", "valor": 1500, "nombre": "🎪 Premio Estándar", "emoji": "💰", "color": 0x808080},
        {"tipo": "creditos", "valor": 2000, "nombre": "🔥 Premio Caliente", "emoji": "💰", "color": 0x808080},
        {"tipo": "creditos", "valor": 2500, "nombre": "⚡ Premio Rápido", "emoji": "💰", "color": 0x808080},
        {"tipo": "creditos", "valor": 3000, "nombre": "🎨 Premio Colorido", "emoji": "💰", "color": 0x808080},
        {"tipo": "creditos", "valor": 4000, "nombre": "🚀 Premio Espacial", "emoji": "💰", "color": 0x0099ff},
        {"tipo": "creditos", "valor": 5000, "nombre": "🌟 Premio Estrella", "emoji": "💰", "color": 0x0099ff},
        {"tipo": "creditos", "valor": 6000, "nombre": "💎 Premio Diamante", "emoji": "💎", "color": 0x9933ff},
        {"tipo": "creditos", "valor": 7500, "nombre": "👑 Premio Real", "emoji": "👑", "color": 0x9933ff},
        {"tipo": "creditos", "valor": 10000, "nombre": "🎊 Premio Fiesta", "emoji": "🎊", "color": 0xff9900},
        {"tipo": "creditos", "valor": 12500, "nombre": "🏆 Premio Campeón", "emoji": "🏆", "color": 0xff9900},
        {"tipo": "creditos", "valor": 15000, "nombre": "⭐ Premio Legendario", "emoji": "⭐", "color": 0xff9900},
        {"tipo": "creditos", "valor": 17500, "nombre": "💫 Premio Mítico", "emoji": "💫", "color": 0xff0000},
        {"tipo": "creditos", "valor": 20000, "nombre": "🎇 Premio Épico", "emoji": "🎇", "color": 0xff0000},
        {"tipo": "creditos", "valor": 50000, "nombre": "🎉 PREMIO MAYOR", "emoji": "🎉", "color": 0xff0000},
        
        # Multiplicadores (5 premios) - SISTEMA POR USOS
        {"tipo": "multiplicador", "valor": 1.25, "nombre": "✨ Multiplicador x1.25", "emoji": "✨", "color": 0x808080, "usos": 8},
        {"tipo": "multiplicador", "valor": 1.5, "nombre": "🌟 Multiplicador x1.5", "emoji": "🌟", "color": 0x0099ff, "usos": 12},
        {"tipo": "multiplicador", "valor": 2.0, "nombre": "💫 Multiplicador x2.0", "emoji": "💫", "color": 0x9933ff, "usos": 15},
        {"tipo": "multiplicador", "valor": 2.5, "nombre": "🎊 Multiplicador x2.5", "emoji": "🎊", "color": 0xff9900, "usos": 10},
        {"tipo": "multiplicador", "valor": 3.0, "nombre": "🔥 MULTIPLICADOR x3.0", "emoji": "🔥", "color": 0xff0000, "usos": 8}
    ]
}

# Diccionario solo para cooldowns de la ruleta
cooldowns_ruleta = {}

class RuletaDiariaView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60.0)
        self.user_id = user_id

    @discord.ui.button(label="🎡 GIRAR RULETA", style=discord.ButtonStyle.success, emoji="🎡")
    async def girar_button(self, interaction: discord.Interaction, button: Button):
        await self.girar_ruleta(interaction)

    async def girar_ruleta(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # Verificar cooldown
        if user_id in cooldowns_ruleta:
            tiempo_restante = cooldowns_ruleta[user_id] - time.time()
            if tiempo_restante > 0:
                horas = int(tiempo_restante // 3600)
                minutos = int((tiempo_restante % 3600) // 60)
                await interaction.response.send_message(
                    f"⏰ La ruleta diaria está en cooldown. Podrás girarla nuevamente en **{horas}h {minutos}m**", 
                    ephemeral=True
                )
                return
        
        # Animación de giro
        embed_giro = discord.Embed(
            title="🎡 GIRANDO RULETA DIARIA...",
            description="*La ruleta está girando...* 🎰",
            color=0xffff00
        )
        embed_giro.add_field(name="⏰ Próximo giro", value="Disponible en 24 horas", inline=True)
        embed_giro.add_field(name="🎯 Premios", value="20 premios diferentes", inline=True)
        embed_giro.set_footer(text="¡Buena suerte!")
        
        await interaction.response.edit_message(embed=embed_giro, view=None)
        await asyncio.sleep(3)
        
        # Obtener premio aleatorio
        premio = random.choice(RULETA_DIARIA["premios"])
        
        # Entregar premio
        success = await self.entregar_premio(interaction, premio, user_id)
        
        if success:
            # Solo aplicar cooldown si el premio se entregó correctamente
            cooldowns_ruleta[user_id] = time.time() + RULETA_DIARIA["cooldown"]

    async def entregar_premio(self, interaction: discord.Interaction, premio: dict, user_id: int) -> bool:
        try:
            mensaje_resultado = ""
            
            # Procesar premio según tipo
            if premio["tipo"] == "creditos":
                ganancia_final = premio["valor"]
                
                db.update_saldo(user_id, ganancia_final, "bonus", "ruleta_diaria", f"Ruleta: {premio['nombre']}")
                mensaje_resultado = f"**+{ganancia_final:,} créditos**"
                
            elif premio["tipo"] == "multiplicador":
                # Activar multiplicador por USOS usando el sistema del GACHA
                gacha_cog = interaction.client.get_cog('Gacha')
                if gacha_cog and hasattr(gacha_cog, 'bonos_activos'):
                    # Guardar el multiplicador en el sistema del Gacha (SISTEMA POR USOS)
                    usos = premio.get("usos", 5)
                    
                    if user_id not in gacha_cog.bonos_activos:
                        gacha_cog.bonos_activos[user_id] = {}
                    
                    gacha_cog.bonos_activos[user_id]["multiplicador"] = {
                        "valor": premio["valor"],
                        "usos_restantes": usos,
                        "usos_totales": usos,
                        "nombre": premio["nombre"],
                        "origen": "ruleta"  # Identificar que viene de la ruleta
                    }
                
                mensaje_resultado = f"**{premio['nombre']}** con {premio['usos']} usos"
            else:
                # Tipo de premio no reconocido
                return False

            # Crear embed de resultado
            embed_resultado = discord.Embed(
                title=f"{premio['emoji']} **{premio['nombre']}** {premio['emoji']}",
                description=f"¡Has ganado: {mensaje_resultado}!",
                color=premio["color"]
            )
            
            embed_resultado.add_field(name="🎁 Tipo de premio", value=premio["nombre"], inline=True)
            embed_resultado.add_field(name="🎰 Ruleta diaria", value="Giro gratuito", inline=True)
            
            # Mostrar información adicional según el premio
            if premio["tipo"] == "multiplicador":
                embed_resultado.add_field(
                    name="🔢 Usos disponibles", 
                    value=f"{premio['usos']} usos", 
                    inline=True
                )
                embed_resultado.add_field(
                    name="💡 ¿Cómo funciona?", 
                    value="Se aplicará automáticamente a tus ganancias en TODOS los juegos", 
                    inline=False
                )
            
            # Información sobre el próximo giro
            proximo_giro_timestamp = time.time() + RULETA_DIARIA["cooldown"]
            proximo_giro = time.strftime("%d/%m/%Y a las %H:%M", time.localtime(proximo_giro_timestamp))
            embed_resultado.add_field(
                name="⏰ Próximo giro disponible", 
                value=f"{proximo_giro}", 
                inline=False
            )
            
            # Efectos especiales para premios grandes
            if premio["valor"] in [50000, 20000] or premio["tipo"] == "multiplicador" and premio["valor"] == 3.0:
                embed_resultado.set_image(url="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExdzlvaTNsYTUxdmZvODA1YnJzbG5iYXRzdDhpZmk5a2lzZ2ZhbXQ2MiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Y3qaJQjDcbJPyK7kGk/giphy.gif")
            
            await interaction.message.edit(embed=embed_resultado, view=None)
            return True
            
        except Exception as e:
            print(f"Error entregando premio de ruleta: {e}")
            embed_error = discord.Embed(
                title="❌ Error en la Ruleta",
                description="Ha ocurrido un error al procesar tu premio. Por favor, intenta nuevamente.",
                color=0xff0000
            )
            await interaction.message.edit(embed=embed_error, view=None)
            return False

class RuletaDiaria(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="megaruleta", aliases=["mega", "ruletadiaria"])
    async def mega_ruleta(self, ctx):
        """🎡 Gira la ruleta diaria para ganar premios increíbles"""
        user_id = ctx.author.id
        
        # Verificar cooldown
        cooldown_info = ""
        if user_id in cooldowns_ruleta:
            tiempo_restante = cooldowns_ruleta[user_id] - time.time()
            if tiempo_restante > 0:
                horas = int(tiempo_restante // 3600)
                minutos = int((tiempo_restante % 3600) // 60)
                cooldown_info = f"\n\n⏰ **Podrás girar nuevamente en: {horas}h {minutos}m**"
            else:
                # Cooldown expirado, limpiar
                del cooldowns_ruleta[user_id]
        
        embed = discord.Embed(
            title="🎡 **RULETA DIARIA** 🎡",
            description=f"**¡Gira la ruleta cada 24 horas y gana premios increíbles!**{cooldown_info}",
            color=0xff00ff
        )
        
        # Información de premios
        premios_creditos = [p for p in RULETA_DIARIA["premios"] if p["tipo"] == "creditos"]
        premios_multiplicadores = [p for p in RULETA_DIARIA["premios"] if p["tipo"] == "multiplicador"]
        
        embed.add_field(
            name="💰 Premios en Créditos",
            value="\n".join([f"• {p['emoji']} **{p['valor']:,}** - {p['nombre']}" for p in premios_creditos[:8]]),
            inline=True
        )
        
        embed.add_field(
            name="✨ Multiplicadores (POR USOS)", 
            value="\n".join([f"• {p['emoji']} **{p['nombre']}** ({p['usos']} usos)" for p in premios_multiplicadores]),
            inline=True
        )
        
        # Mostrar premios grandes restantes
        premios_grandes = [p for p in premios_creditos if p["valor"] >= 10000]
        if premios_grandes:
            embed.add_field(
                name="🎊 Premios Grandes",
                value="\n".join([f"• {p['emoji']} **{p['valor']:,}** - {p['nombre']}" for p in premios_grandes]),
                inline=False
            )
        
        # Mostrar multiplicador activo si existe (del Gacha)
        gacha_cog = self.bot.get_cog('Gacha')
        if gacha_cog and hasattr(gacha_cog, 'obtener_multiplicador_activo'):
            multiplicador_activo = gacha_cog.obtener_multiplicador_activo(user_id)
            if multiplicador_activo > 1.0:
                # Verificar si es de la ruleta
                if hasattr(gacha_cog, 'bonos_activos') and user_id in gacha_cog.bonos_activos and "multiplicador" in gacha_cog.bonos_activos[user_id]:
                    multiplicador_info = gacha_cog.bonos_activos[user_id]["multiplicador"]
                    usos_restantes = multiplicador_info["usos_restantes"]
                    origen = multiplicador_info.get("origen", "gacha")
                    
                    if origen == "ruleta":
                        embed.add_field(
                            name="🎰 Multiplicador de Ruleta Activo",
                            value=f"**{multiplicador_info['nombre']}** - {usos_restantes} usos restantes",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="🎰 Multiplicador de Gacha Activo", 
                            value=f"**x{multiplicador_activo}** - {usos_restantes} usos restantes",
                            inline=False
                        )
        
        embed.set_footer(text="¡20 premios diferentes con la misma probabilidad!")
        
        # Solo mostrar botón si no está en cooldown
        if user_id not in cooldowns_ruleta or cooldowns_ruleta[user_id] <= time.time():
            view = RuletaDiariaView(user_id)
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(embed=embed)

    @commands.command(name="misbonosruleta", aliases=["myroulettebuffs", "bonosruleta"])
    async def misbonosruleta(self, ctx):
        """Muestra tus bonos activos de la ruleta diaria"""
        user_id = ctx.author.id
        
        gacha_cog = self.bot.get_cog('Gacha')
        if not gacha_cog or not hasattr(gacha_cog, 'obtener_multiplicador_activo'):
            await ctx.send("❌ El sistema de bonos no está disponible en este momento.")
            return
        
        multiplicador_activo = gacha_cog.obtener_multiplicador_activo(user_id)
        
        if multiplicador_activo <= 1.0:
            await ctx.send("❌ No tienes multiplicadores activos de la ruleta en este momento.")
            return
        
        # Verificar si el multiplicador activo es de la ruleta
        if hasattr(gacha_cog, 'bonos_activos') and user_id in gacha_cog.bonos_activos and "multiplicador" in gacha_cog.bonos_activos[user_id]:
            multiplicador_info = gacha_cog.bonos_activos[user_id]["multiplicador"]
            origen = multiplicador_info.get("origen", "gacha")
            
            if origen != "ruleta":
                await ctx.send("❌ No tienes multiplicadores activos de la ruleta en este momento.")
                return
            
            usos_restantes = multiplicador_info["usos_restantes"]
            usos_totales = multiplicador_info["usos_totales"]
            
            embed = discord.Embed(
                title="🎪 Tu Multiplicador de Ruleta Activo",
                color=0x00ff00
            )
            
            embed.add_field(
                name="✨ Multiplicador",
                value=f"**{multiplicador_info['nombre']}**",
                inline=True
            )
            
            embed.add_field(
                name="🔢 Usos",
                value=f"**{usos_restantes}/{usos_totales}** usos restantes",
                inline=True
            )
            
            embed.add_field(
                name="💡 ¿Dónde se aplica?",
                value="Este multiplicador se aplica automáticamente a tus ganancias en TODOS los juegos del casino",
                inline=False
            )
            
            # Información del próximo giro
            if user_id in cooldowns_ruleta:
                tiempo_restante_giro = cooldowns_ruleta[user_id] - time.time()
                if tiempo_restante_giro > 0:
                    horas = int(tiempo_restante_giro // 3600)
                    minutos = int((tiempo_restante_giro % 3600) // 60)
                    embed.add_field(
                        name="⏰ Próximo giro",
                        value=f"Disponible en {horas}h {minutos}m",
                        inline=True
                    )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ No tienes multiplicadores activos de la ruleta en este momento.")

    @commands.command(name="ruletastats", aliases=["ruletaestadisticas"])
    async def ruletastats(self, ctx):
        """Estadísticas de la ruleta diaria"""
        total_usuarios = len(cooldowns_ruleta)
        usuarios_activos = sum(1 for t in cooldowns_ruleta.values() if t > time.time())
        
        # Contar usuarios con multiplicadores de ruleta
        gacha_cog = self.bot.get_cog('Gacha')
        usuarios_con_multiplicador_ruleta = 0
        if gacha_cog and hasattr(gacha_cog, 'bonos_activos'):
            for user_id, bonos in gacha_cog.bonos_activos.items():
                if "multiplicador" in bonos and bonos["multiplicador"].get("origen") == "ruleta":
                    if bonos["multiplicador"]["usos_restantes"] > 0:
                        usuarios_con_multiplicador_ruleta += 1
        
        embed = discord.Embed(
            title="📊 ESTADÍSTICAS RULETA DIARIA",
            color=0xff00ff
        )
        
        embed.add_field(name="👥 Usuarios registrados", value=f"**{total_usuarios}**", inline=True)
        embed.add_field(name="🎡 Giros activos", value=f"**{usuarios_activos}**", inline=True)
        embed.add_field(name="✨ Con multiplicador", value=f"**{usuarios_con_multiplicador_ruleta}**", inline=True)
        
        # Distribución de premios
        premios_creditos = len([p for p in RULETA_DIARIA["premios"] if p["tipo"] == "creditos"])
        premios_multiplicadores = len([p for p in RULETA_DIARIA["premios"] if p["tipo"] == "multiplicador"])
        
        embed.add_field(
            name="🎰 Distribución de Premios",
            value=f"💰 Créditos: **{premios_creditos}**\n✨ Multiplicadores: **{premios_multiplicadores}**",
            inline=True
        )
        
        embed.add_field(name="⏰ Cooldown", value="**24 horas**", inline=True)
        embed.add_field(name="🎊 Premio mayor", value="**50,000 créditos**", inline=True)
        
        # Multiplicador más alto
        multiplicador_max = max([p["valor"] for p in RULETA_DIARIA["premios"] if p["tipo"] == "multiplicador"])
        embed.add_field(name="🚀 Multiplicador máximo", value=f"**x{multiplicador_max}**", inline=True)
        
        # Sistema de usos
        embed.add_field(
            name="🔄 Sistema de Multiplicadores",
            value="Los multiplicadores de la ruleta usan el mismo sistema por USOS que el Gacha",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RuletaDiaria(bot))