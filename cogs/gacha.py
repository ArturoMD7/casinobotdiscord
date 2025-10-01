import discord
from discord.ext import commands
from discord.ui import Button, View
from db.database import Database
import random
import asyncio
import time

db = Database()

# Sistema de Gacha completo
SISTEMA_GACHA = {
    "cajas": {
        "basica": {
            "nombre": "📦 Caja Básica",
            "costo": 100,
            "cooldown": 3600,  # 1 hora
            "probabilidades": [
                {"tipo": "creditos", "valor": 50, "prob": 0.40, "emoji": "💰", "nombre": "Créditos Pequeños", "rareza": "comun"},
                {"tipo": "creditos", "valor": 100, "prob": 0.25, "emoji": "💰", "nombre": "Créditos Medianos", "rareza": "comun"},
                {"tipo": "creditos", "valor": 200, "prob": 0.15, "emoji": "💰", "nombre": "Créditos Grandes", "rareza": "raro"},
                {"tipo": "multiplicador", "valor": 1.5, "prob": 0.10, "emoji": "✨", "nombre": "Multiplicador x1.5", "rareza": "raro", "duracion": 3600},
                {"tipo": "proteccion", "valor": "inmunidad", "prob": 0.08, "emoji": "🛡️", "nombre": "Escudo Anti-Pérdidas", "rareza": "epico", "duracion": 7200},
                {"tipo": "creditos", "valor": 500, "prob": 0.02, "emoji": "💎", "nombre": "BOLSA DE ORO", "rareza": "epico"}
            ]
        },
        "premium": {
            "nombre": "🎁 Caja Premium", 
            "costo": 500,
            "cooldown": 10800,  # 3 horas
            "probabilidades": [
                {"tipo": "creditos", "valor": 200, "prob": 0.30, "emoji": "💰", "nombre": "Créditos Decentes", "rareza": "comun"},
                {"tipo": "creditos", "valor": 500, "prob": 0.25, "emoji": "💰", "nombre": "Créditos Buenos", "rareza": "raro"},
                {"tipo": "multiplicador", "valor": 2.0, "prob": 0.15, "emoji": "✨", "nombre": "Multiplicador x2", "rareza": "raro", "duracion": 3600},
                {"tipo": "proteccion", "valor": "inmunidad", "prob": 0.12, "emoji": "🛡️", "nombre": "Escudo Dorado", "rareza": "epico", "duracion": 10800},
                {"tipo": "vip", "valor": "acceso_vip", "prob": 0.10, "emoji": "👑", "nombre": "Pase VIP", "rareza": "epico", "duracion": 86400},
                {"tipo": "creditos", "valor": 1000, "prob": 0.05, "emoji": "💎", "nombre": "COFRE DEL TESORO", "rareza": "legendario"},
                {"tipo": "jackpot", "valor": 5000, "prob": 0.03, "emoji": "🎊", "nombre": "JACKPOT ÉPICO", "rareza": "legendario"}
            ]
        },
        "legendaria": {
            "nombre": "🔥 Caja Legendaria",
            "costo": 2000,
            "cooldown": 86400,  # 24 horas
            "probabilidades": [
                {"tipo": "creditos", "valor": 1000, "prob": 0.25, "emoji": "💰", "nombre": "Fortuna Pequeña", "rareza": "raro"},
                {"tipo": "multiplicador", "valor": 3.0, "prob": 0.20, "emoji": "✨", "nombre": "Multiplicador x3", "rareza": "epico", "duracion": 7200},
                {"tipo": "proteccion", "valor": "inmunidad_total", "prob": 0.15, "emoji": "🛡️", "nombre": "Inmunidad Total", "rareza": "epico", "duracion": 14400},
                {"tipo": "vip", "valor": "acceso_vip", "prob": 0.15, "emoji": "👑", "nombre": "Pase VIP Plus", "rareza": "epico", "duracion": 172800},
                {"tipo": "revivir", "valor": "revivir", "prob": 0.10, "emoji": "💖", "nombre": "Poción de Revivir", "rareza": "legendario"},
                {"tipo": "creditos", "valor": 5000, "prob": 0.08, "emoji": "💎", "nombre": "TESORO ANCESTRAL", "rareza": "legendario"},
                {"tipo": "jackpot", "valor": 10000, "prob": 0.05, "emoji": "🎊", "nombre": "MEGA JACKPOT", "rareza": "mitico"},
                {"tipo": "legendario", "valor": "titulo_legendario", "prob": 0.02, "emoji": "🏆", "nombre": "TÍTULO LEGENDARIO", "rareza": "mitico"}
            ]
        }
    },
    "bonos_rareza": {
        "comun": {"color": 0x808080, "multiplicador": 1.0},
        "raro": {"color": 0x0099ff, "multiplicador": 1.5},
        "epico": {"color": 0x9933ff, "multiplicador": 2.0},
        "legendario": {"color": 0xff9900, "multiplicador": 3.0},
        "mitico": {"color": 0xff0000, "multiplicador": 5.0}
    }
}

# Diccionarios para guardar estados temporales
bonos_activos = {}
cooldowns_gacha = {}
colecciones_usuarios = {}

class GachaView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60.0)
        self.user_id = user_id

    @discord.ui.button(label="📦 Caja Básica (100cr)", style=discord.ButtonStyle.secondary, emoji="📦")
    async def basica_button(self, interaction: discord.Interaction, button: Button):
        await self.abrir_caja(interaction, "basica")

    @discord.ui.button(label="🎁 Caja Premium (500cr)", style=discord.ButtonStyle.primary, emoji="🎁")
    async def premium_button(self, interaction: discord.Interaction, button: Button):
        await self.abrir_caja(interaction, "premium")

    @discord.ui.button(label="🔥 Caja Legendaria (2000cr)", style=discord.ButtonStyle.danger, emoji="🔥")
    async def legendaria_button(self, interaction: discord.Interaction, button: Button):
        await self.abrir_caja(interaction, "legendaria")

    async def abrir_caja(self, interaction: discord.Interaction, tipo_caja: str):
        caja = SISTEMA_GACHA["cajas"][tipo_caja]
        user_id = interaction.user.id
        
        # Verificar cooldown
        cooldown_key = f"{user_id}_{tipo_caja}"
        if cooldown_key in cooldowns_gacha:
            tiempo_restante = cooldowns_gacha[cooldown_key] - time.time()
            if tiempo_restante > 0:
                horas = int(tiempo_restante // 3600)
                minutos = int((tiempo_restante % 3600) // 60)
                await interaction.response.send_message(
                    f"⏰ Esta caja está en cooldown. Tiempo restante: {horas}h {minutos}m", 
                    ephemeral=True
                )
                return
        
        # Verificar créditos
        credits = db.get_credits(user_id)
        if credits < caja["costo"]:
            await interaction.response.send_message(
                f"❌ No tienes suficientes créditos. Necesitas: {caja['costo']:,}", 
                ephemeral=True
            )
            return
        
        # Cobrar costo
        db.update_credits(user_id, -caja["costo"], "gacha", "compra_caja", f"Compra {caja['nombre']}")
        
        # Animación de apertura
        embed_animacion = discord.Embed(
            title=f"🎰 Abriendo {caja['nombre']}...",
            description="*La caja está brillando...* ✨",
            color=0xffff00
        )
        await interaction.response.edit_message(embed=embed_animacion, view=None)
        await asyncio.sleep(2)
        
        # Obtener premio
        premio = self.obtener_premio(caja["probabilidades"])
        await self.entregar_premio(interaction, premio, caja, user_id)
        
        # Aplicar cooldown
        cooldowns_gacha[cooldown_key] = time.time() + caja["cooldown"]

    def obtener_premio(self, probabilidades):
        rand = random.random()
        acumulado = 0
        for premio in probabilidades:
            acumulado += premio["prob"]
            if rand <= acumulado:
                return premio
        return probabilidades[0]  # Fallback

    async def entregar_premio(self, interaction: discord.Interaction, premio: dict, caja: dict, user_id: int):
        # Aplicar bono de rareza
        bono_rareza = SISTEMA_GACHA["bonos_rareza"][premio["rareza"]]
        
        # Procesar premio según tipo
        mensaje_resultado = ""
        if premio["tipo"] == "creditos":
            valor_final = int(premio["valor"] * bono_rareza["multiplicador"])
            db.update_credits(user_id, valor_final, "bonus", "gacha_premio", f"{premio['nombre']} de {caja['nombre']}")
            mensaje_resultado = f"**+{valor_final:,} créditos**"
            
        elif premio["tipo"] == "multiplicador":
            # Activar bono temporal
            if user_id not in bonos_activos:
                bonos_activos[user_id] = {}
            bonos_activos[user_id]["multiplicador"] = {
                "valor": premio["valor"],
                "expiracion": time.time() + premio.get("duracion", 3600)
            }
            mensaje_resultado = f"**Multiplicador x{premio['valor']}** por {premio.get('duracion', 3600)//3600}h"
            
        elif premio["tipo"] == "proteccion":
            if user_id not in bonos_activos:
                bonos_activos[user_id] = {}
            bonos_activos[user_id]["proteccion"] = {
                "tipo": premio["valor"],
                "expiracion": time.time() + premio.get("duracion", 7200)
            }
            mensaje_resultado = f"**{premio['nombre']}** por {premio.get('duracion', 7200)//3600}h"
            
        elif premio["tipo"] == "vip":
            if user_id not in bonos_activos:
                bonos_activos[user_id] = {}
            bonos_activos[user_id]["vip"] = {
                "expiracion": time.time() + premio.get("duracion", 86400)
            }
            mensaje_resultado = f"**{premio['nombre']}** por {premio.get('duracion', 86400)//86400}días"
            
        elif premio["tipo"] == "revivir":
            if user_id not in bonos_activos:
                bonos_activos[user_id] = {}
            bonos_activos[user_id]["revivir"] = True
            mensaje_resultado = f"**{premio['nombre']}** - Recupera tu última apuesta perdida"
            
        elif premio["tipo"] == "jackpot":
            valor_final = int(premio["valor"] * bono_rareza["multiplicador"])
            db.update_credits(user_id, valor_final, "bonus", "gacha_jackpot", f"JACKPOT {premio['nombre']}")
            mensaje_resultado = f"**🎊 JACKPOT! +{valor_final:,} créditos 🎊**"
            
        elif premio["tipo"] == "legendario":
            # Título especial en el perfil
            mensaje_resultado = f"**{premio['nombre']}** - ¡Eres una leyenda!"
        
        # Registrar en colección
        if user_id not in colecciones_usuarios:
            colecciones_usuarios[user_id] = []
        
        item_id = f"{premio['nombre']}_{premio['rareza']}"
        if item_id not in colecciones_usuarios[user_id]:
            colecciones_usuarios[user_id].append(item_id)
        
        # Crear embed de resultado
        embed_resultado = discord.Embed(
            title=f"{premio['emoji']} **{premio['nombre']}** {premio['emoji']}",
            description=f"¡Has obtenido: {mensaje_resultado}!",
            color=bono_rareza["color"]
        )
        
        embed_resultado.add_field(name="🎁 Tipo de premio", value=premio["nombre"], inline=True)
        embed_resultado.add_field(name="📊 Rareza", value=premio["rareza"].upper(), inline=True)
        embed_resultado.add_field(name="📦 Caja", value=caja["nombre"], inline=True)
        embed_resultado.add_field(name="🎰 Probabilidad", value=f"{premio['prob']*100:.1f}%", inline=True)
        
        if premio["rareza"] in ["epico", "legendario", "mitico"]:
            embed_resultado.set_image(url="https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif")
        
        await interaction.edit_original_response(embed=embed_resultado)

class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gacha", aliases=["cajas", "misterio"])
    async def gacha(self, ctx):
        """Sistema de cajas misteriosas con premios épicos"""
        embed = discord.Embed(
            title="🎰 **SISTEMA GACHA - CAJAS MISTERIOSAS** 🎰",
            description="**¡Abre cajas y descubre premios increíbles!**\nCada caja tiene diferentes rarezas y cooldowns.",
            color=0xff00ff
        )
        
        # Información de cajas
        for caja_id, caja in SISTEMA_GACHA["cajas"].items():
            # Calcular cooldown restante
            cooldown_key = f"{ctx.author.id}_{caja_id}"
            cooldown_info = ""
            if cooldown_key in cooldowns_gacha:
                tiempo_restante = cooldowns_gacha[cooldown_key] - time.time()
                if tiempo_restante > 0:
                    horas = int(tiempo_restante // 3600)
                    minutos = int((tiempo_restante % 3600) // 60)
                    cooldown_info = f" - ⏰ {horas}h {minutos}m"
            
            embed.add_field(
                name=f"{caja['nombre']} - {caja['costo']:,}cr{cooldown_info}",
                value=f"Cooldown: {caja['cooldown']//3600}h | Mejores premios: {self.obtener_mejores_premios(caja_id)}",
                inline=False
            )
        
        # Información de rarezas
        rarezas_text = ""
        for rareza, info in SISTEMA_GACHA["bonos_rareza"].items():
            rarezas_text += f"{info['color']} **{rareza.upper()}** (x{info['multiplicador']})\n"
        
        embed.add_field(name="🎨 SISTEMA DE RAREZAS", value=rarezas_text, inline=False)
        embed.add_field(name="🎯 Tipos de Premios", value="💰 Créditos\n✨ Multiplicadores\n🛡️ Protecciones\n👑 Pases VIP\n💖 Revivir\n🎊 JACKPOTS", inline=True)
        
        embed.set_footer(text="¡Cada caja puede cambiar tu suerte!")
        
        view = GachaView(ctx.author.id)
        await ctx.send(embed=embed, view=view)

    def obtener_mejores_premios(self, caja_id: str) -> str:
        caja = SISTEMA_GACHA["cajas"][caja_id]
        premios_epicos = [p for p in caja["probabilidades"] if p["rareza"] in ["epico", "legendario", "mitico"]]
        return ", ".join([p["nombre"] for p in premios_epicos[:2]])

    @commands.command(name="micoleccion", aliases=["mycollection", "coleccion"])
    async def micoleccion(self, ctx):
        """Muestra tu colección de items del Gacha"""
        user_id = ctx.author.id
        
        if user_id not in colecciones_usuarios or not colecciones_usuarios[user_id]:
            await ctx.send("❌ Aún no tienes items en tu colección. ¡Abre algunas cajas!")
            return
        
        # Agrupar items por rareza
        items_por_rareza = {}
        for item_id in colecciones_usuarios[user_id]:
            rareza = item_id.split("_")[-1]
            if rareza not in items_por_rareza:
                items_por_rareza[rareza] = []
            items_por_rareza[rareza].append(item_id)
        
        embed = discord.Embed(
            title=f"📚 Colección de {ctx.author.display_name}",
            description=f"**{len(colecciones_usuarios[user_id])}** items coleccionados",
            color=0x9933ff
        )
        
        for rareza, items in items_por_rareza.items():
            color_rareza = SISTEMA_GACHA["bonos_rareza"][rareza]["color"]
            items_text = "\n".join([f"• {item.replace('_' + rareza, '')}" for item in items[:5]])
            if len(items) > 5:
                items_text += f"\n• ... y {len(items) - 5} más"
                
            embed.add_field(
                name=f"{rareza.upper()} ({len(items)})",
                value=items_text,
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="misbonos", aliases=["mybuffs", "bonos"])
    async def misbonos(self, ctx):
        """Muestra tus bonos activos del Gacha"""
        user_id = ctx.author.id
        
        if user_id not in bonos_activos or not bonos_activos[user_id]:
            await ctx.send("❌ No tienes bonos activos en este momento.")
            return
        
        embed = discord.Embed(
            title=f"✨ Bonos Activos de {ctx.author.display_name}",
            color=0x00ff00
        )
        
        for bono_tipo, bono_info in bonos_activos[user_id].items():
            if bono_tipo == "multiplicador":
                tiempo_restante = bono_info["expiracion"] - time.time()
                if tiempo_restante > 0:
                    minutos = int(tiempo_restante // 60)
                    embed.add_field(
                        name="✨ Multiplicador", 
                        value=f"x{bono_info['valor']} - {minutos}m restantes", 
                        inline=True
                    )
                    
            elif bono_tipo == "proteccion":
                tiempo_restante = bono_info["expiracion"] - time.time()
                if tiempo_restante > 0:
                    minutos = int(tiempo_restante // 60)
                    embed.add_field(
                        name="🛡️ Protección", 
                        value=f"{bono_info['tipo']} - {minutos}m restantes", 
                        inline=True
                    )
                    
            elif bono_tipo == "vip":
                tiempo_restante = bono_info["expiracion"] - time.time()
                if tiempo_restante > 0:
                    horas = int(tiempo_restante // 3600)
                    embed.add_field(
                        name="👑 VIP", 
                        value=f"Activo - {horas}h restantes", 
                        inline=True
                    )
                    
            elif bono_tipo == "revivir":
                embed.add_field(
                    name="💖 Revivir", 
                    value="Disponible - Recupera última apuesta", 
                    inline=True
                )
        
        await ctx.send(embed=embed)

    @commands.command(name="gachastats", aliases=["gachaestadisticas"])
    async def gachastats(self, ctx):
        """Estadísticas del sistema Gacha"""
        total_cajas = sum(len(coleccion) for coleccion in colecciones_usuarios.values())
        total_usuarios = len(colecciones_usuarios)
        
        embed = discord.Embed(
            title="📊 ESTADÍSTICAS DEL SISTEMA GACHA",
            color=0xff00ff
        )
        
        embed.add_field(name="👥 Usuarios con colección", value=f"**{total_usuarios}**", inline=True)
        embed.add_field(name="📦 Items totales obtenidos", value=f"**{total_cajas}**", inline=True)
        embed.add_field(name="🎰 Cajas disponibles", value=f"**{len(SISTEMA_GACHA['cajas'])}** tipos", inline=True)
        
        # Estadísticas de rarezas
        todas_rarezas = {}
        for usuario_items in colecciones_usuarios.values():
            for item in usuario_items:
                rareza = item.split("_")[-1]
                todas_rarezas[rareza] = todas_rarezas.get(rareza, 0) + 1
        
        if todas_rarezas:
            rarezas_text = ""
            for rareza, cantidad in sorted(todas_rarezas.items(), key=lambda x: x[1], reverse=True):
                rarezas_text += f"**{rareza.upper()}**: {cantidad}\n"
            embed.add_field(name="🎨 Distribución de Rarezas", value=rarezas_text, inline=True)
        
        embed.add_field(name="💎 Mejor premio posible", value="**TÍTULO LEGENDARIO** (0.02%)", inline=True)
        embed.add_field(name="⏰ Cooldowns", value="Básica: 1h\nPremium: 3h\nLegendaria: 24h", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Gacha(bot))