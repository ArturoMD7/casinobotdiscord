import discord
from discord.ext import commands
from discord.ui import Button, View
from db.database import Database
import random
import asyncio
import time

db = Database()

# Sistema de Gacha modificado - Multiplicadores por usos en lugar de tiempo
SISTEMA_GACHA = {
    "cajas": {
        "basica": {
            "nombre": "📦 Caja Básica",
            "costo": 100,
            "cooldown": 3600,  # 1 hora
            "probabilidades": [
                {"tipo": "creditos", "valor": 50, "prob": 0.50, "emoji": "💰", "nombre": "Créditos Pequeños", "rareza": "comun"},
                {"tipo": "creditos", "valor": 100, "prob": 0.30, "emoji": "💰", "nombre": "Créditos Medianos", "rareza": "comun"},
                {"tipo": "creditos", "valor": 200, "prob": 0.15, "emoji": "💰", "nombre": "Créditos Grandes", "rareza": "raro"},
                {"tipo": "multiplicador", "valor": 1.25, "prob": 0.05, "emoji": "✨", "nombre": "Multiplicador x1.25", "rareza": "raro", "usos": 5}
            ]
        },
        "premium": {
            "nombre": "🎁 Caja Premium", 
            "costo": 500,
            "cooldown": 10800,  # 3 horas
            "probabilidades": [
                {"tipo": "creditos", "valor": 200, "prob": 0.35, "emoji": "💰", "nombre": "Créditos Decentes", "rareza": "comun"},
                {"tipo": "creditos", "valor": 500, "prob": 0.25, "emoji": "💰", "nombre": "Créditos Buenos", "rareza": "raro"},
                {"tipo": "multiplicador", "valor": 1.5, "prob": 0.20, "emoji": "✨", "nombre": "Multiplicador x1.5", "rareza": "raro", "usos": 8},
                {"tipo": "multiplicador", "valor": 1.75, "prob": 0.15, "emoji": "✨", "nombre": "Multiplicador x1.75", "rareza": "epico", "usos": 12},
                {"tipo": "creditos", "valor": 1000, "prob": 0.05, "emoji": "💎", "nombre": "BOLSA PREMIUM", "rareza": "epico"}
            ]
        },
        "legendaria": {
            "nombre": "🔥 Caja Legendaria",
            "costo": 2000,
            "cooldown": 86400,  # 24 horas
            "probabilidades": [
                {"tipo": "creditos", "valor": 1000, "prob": 0.30, "emoji": "💰", "nombre": "Fortuna Pequeña", "rareza": "raro"},
                {"tipo": "multiplicador", "valor": 2.0, "prob": 0.25, "emoji": "✨", "nombre": "Multiplicador x2.0", "rareza": "epico", "usos": 10},
                {"tipo": "multiplicador", "valor": 2.5, "prob": 0.20, "emoji": "✨", "nombre": "Multiplicador x2.5", "rareza": "legendario", "usos": 10},
                {"tipo": "creditos", "valor": 5000, "prob": 0.15, "emoji": "💎", "nombre": "TESORO ÉPICO", "rareza": "legendario"},
                {"tipo": "multiplicador", "valor": 3.0, "prob": 0.10, "emoji": "🎊", "nombre": "MULTIPLICADOR LEGENDARIO x3.0", "rareza": "mitico", "usos": 10}
            ]
        }
    },
    "bonos_rareza": {
        "comun": {"color": 0x808080, "multiplicador": 1.0},
        "raro": {"color": 0x0099ff, "multiplicador": 1.2},
        "epico": {"color": 0x9933ff, "multiplicador": 1.5},
        "legendario": {"color": 0xff9900, "multiplicador": 2.0},
        "mitico": {"color": 0xff0000, "multiplicador": 3.0}
    }
}


class GachaView(View):
    def __init__(self, user_id, gacha_cog):
        super().__init__(timeout=60.0)
        self.user_id = user_id
        self.gacha_cog = gacha_cog

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
        cog = self.gacha_cog
        
        # Verificar cooldown
        cooldown_key = f"{user_id}_{tipo_caja}"
        if cooldown_key in cog.cooldowns_gacha:
            tiempo_restante = cog.cooldowns_gacha[cooldown_key] - time.time()
            if tiempo_restante > 0:
                horas = int(tiempo_restante // 3600)
                minutos = int((tiempo_restante % 3600) // 60)
                await interaction.response.send_message(
                    f"⏰ Esta caja está en cooldown. Tiempo restante: {horas}h {minutos}m", 
                    ephemeral=True
                )
                return
        
        # Verificar créditos
        credits = db.get_saldo(user_id)
        if credits < caja["costo"]:
            await interaction.response.send_message(
                f"❌ No tienes suficientes créditos. Necesitas: {caja['costo']:,}", 
                ephemeral=True
            )
            return
        
        # Cobrar costo
        db.update_saldo(user_id, -caja["costo"], "gacha", "compra_caja", f"Compra {caja['nombre']}")
        
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
        await self.entregar_premio(interaction, premio, caja, user_id, cog)
        
        # Aplicar cooldown
        cog.cooldowns_gacha[cooldown_key] = time.time() + caja["cooldown"]

    def obtener_premio(self, probabilidades):
        rand = random.random()
        acumulado = 0
        for premio in probabilidades:
            acumulado += premio["prob"]
            if rand <= acumulado:
                return premio
        return probabilidades[0]

    async def entregar_premio(self, interaction, premio, caja, user_id, cog):
        # Aplicar bono de rareza
        bono_rareza = SISTEMA_GACHA["bonos_rareza"][premio["rareza"]]
        
        mensaje_resultado = ""
        if premio["tipo"] == "creditos":
            valor_final = int(premio["valor"] * bono_rareza["multiplicador"])
            db.update_saldo(user_id, valor_final, "bonus", "gacha_premio", f"{premio['nombre']} de {caja['nombre']}")
            mensaje_resultado = f"**+{valor_final:,} créditos**"
        elif premio["tipo"] == "multiplicador":
            if user_id not in cog.bonos_activos:
                cog.bonos_activos[user_id] = {}
            usos = premio.get("usos", 5)
            cog.bonos_activos[user_id]["multiplicador"] = {
                "valor": premio["valor"],
                "usos_restantes": usos,
                "usos_totales": usos,
                "nombre": premio["nombre"]
            }
            mensaje_resultado = f"**{premio['nombre']}** con {usos} usos"
            if premio["valor"] >= 2.5:
                mensaje_resultado += " 🎊 **¡BONO ÉPICO!** 🎊"
        
        # Registrar en colección
        if user_id not in cog.colecciones_usuarios:
            cog.colecciones_usuarios[user_id] = []
        item_id = f"{premio['nombre']}_{premio['rareza']}"
        if item_id not in cog.colecciones_usuarios[user_id]:
            cog.colecciones_usuarios[user_id].append(item_id)
        
        embed_resultado = discord.Embed(
            title=f"{premio['emoji']} **{premio['nombre']}** {premio['emoji']}",
            description=f"¡Has obtenido: {mensaje_resultado}!",
            color=bono_rareza["color"]
        )
        
        embed_resultado.add_field(name="🎁 Tipo de premio", value=premio["nombre"], inline=True)
        embed_resultado.add_field(name="📊 Rareza", value=premio["rareza"].upper(), inline=True)
        embed_resultado.add_field(name="📦 Caja", value=caja["nombre"], inline=True)
        embed_resultado.add_field(name="🎰 Probabilidad", value=f"{premio['prob']*100:.1f}%", inline=True)
        
        if premio["tipo"] == "multiplicador":
            embed_resultado.add_field(
                name="💡 ¿Cómo funciona?", 
                value=f"Este multiplicador se aplicará a tus próximas {premio.get('usos', 5)} ganancias",
                inline=False
            )
        
        if premio["rareza"] in ["epico", "legendario", "mitico"]:
            embed_resultado.set_image(url="https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif")
        
        await interaction.edit_original_response(embed=embed_resultado)


class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bonos_activos = {}
        self.cooldowns_gacha = {}
        self.colecciones_usuarios = {}

    @commands.command(name="gacha", aliases=["cajas", "misterio"])
    async def gacha(self, ctx):
        """Sistema de cajas misteriosas con premios épicos"""
        embed = discord.Embed(
            title="🎰 **SISTEMA GACHA - CAJAS MISTERIOSAS** 🎰",
            description="**¡Abre cajas y descubre premios increíbles!**\nSolo créditos y multiplicadores disponibles.",
            color=0xff00ff
        )
        
        for caja_id, caja in SISTEMA_GACHA["cajas"].items():
            cooldown_key = f"{ctx.author.id}_{caja_id}"
            cooldown_info = ""
            if cooldown_key in self.cooldowns_gacha:
                tiempo_restante = self.cooldowns_gacha[cooldown_key] - time.time()
                if tiempo_restante > 0:
                    horas = int(tiempo_restante // 3600)
                    minutos = int((tiempo_restante % 3600) // 60)
                    cooldown_info = f" - ⏰ {horas}h {minutos}m"
            
            embed.add_field(
                name=f"{caja['nombre']} - {caja['costo']:,}cr{cooldown_info}",
                value=f"Cooldown: {caja['cooldown']//3600}h | Mejores premios: {self.obtener_mejores_premios(caja_id)}",
                inline=False
            )
        
        rarezas_text = ""
        for rareza, info in SISTEMA_GACHA["bonos_rareza"].items():
            rarezas_text += f"{info['color']} **{rareza.upper()}** (x{info['multiplicador']})\n"
        embed.add_field(name="🎨 SISTEMA DE RAREZAS", value=rarezas_text, inline=False)
        embed.add_field(name="🎯 Tipos de Premios", value="💰 Créditos directos\n✨ Multiplicadores (por usos)", inline=True)
        embed.set_footer(text="¡Los multiplicadores ahora tienen usos limitados en lugar de tiempo!")
        
        view = GachaView(ctx.author.id, self)
        await ctx.send(embed=embed, view=view)

    def obtener_mejores_premios(self, caja_id: str) -> str:
        caja = SISTEMA_GACHA["cajas"][caja_id]
        premios_epicos = [p for p in caja["probabilidades"] if p["rareza"] in ["epico", "legendario", "mitico"]]
        return ", ".join([p["nombre"] for p in premios_epicos[:2]])

    def limpiar_bonos_sin_usos(self, user_id: int):
        if user_id in self.bonos_activos:
            bonos_a_eliminar = [bt for bt, bi in self.bonos_activos[user_id].items() if bi.get("usos_restantes", 1) <= 0]
            for bono in bonos_a_eliminar:
                del self.bonos_activos[user_id][bono]
            if not self.bonos_activos[user_id]:
                del self.bonos_activos[user_id]

    def obtener_multiplicador_activo(self, user_id: int) -> float:
        self.limpiar_bonos_sin_usos(user_id)
        if user_id in self.bonos_activos and "multiplicador" in self.bonos_activos[user_id]:
            return self.bonos_activos[user_id]["multiplicador"]["valor"]
        return 1.0

    def aplicar_multiplicador_ganancias(self, user_id: int, ganancia_base: int) -> int:
        multiplicador = self.obtener_multiplicador_activo(user_id)
        ganancia_final = int(ganancia_base * multiplicador)
        if multiplicador > 1.0 and user_id in self.bonos_activos and "multiplicador" in self.bonos_activos[user_id]:
            self.bonos_activos[user_id]["multiplicador"]["usos_restantes"] -= 1
            if self.bonos_activos[user_id]["multiplicador"]["usos_restantes"] <= 0:
                self.limpiar_bonos_sin_usos(user_id)
        return ganancia_final

    @commands.command(name="micoleccion", aliases=["mycollection", "coleccion"])
    async def micoleccion(self, ctx):
        user_id = ctx.author.id
        if user_id not in self.colecciones_usuarios or not self.colecciones_usuarios[user_id]:
            await ctx.send("❌ Aún no tienes items en tu colección. ¡Abre algunas cajas!")
            return
        items_por_rareza = {}
        for item_id in self.colecciones_usuarios[user_id]:
            rareza = item_id.split("_")[-1]
            if rareza not in items_por_rareza:
                items_por_rareza[rareza] = []
            items_por_rareza[rareza].append(item_id)
        embed = discord.Embed(
            title=f"📚 Colección de {ctx.author.display_name}",
            description=f"**{len(self.colecciones_usuarios[user_id])}** items coleccionados",
            color=0x9933ff
        )
        for rareza, items in items_por_rareza.items():
            color_rareza = SISTEMA_GACHA["bonos_rareza"][rareza]["color"]
            items_text = "\n".join([f"• {item.replace('_' + rareza, '')}" for item in items[:5]])
            if len(items) > 5:
                items_text += f"\n• ... y {len(items) - 5} más"
            embed.add_field(name=f"{rareza.upper()} ({len(items)})", value=items_text, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="misbonos", aliases=["mybuffs", "bonos"])
    async def misbonos(self, ctx):
        user_id = ctx.author.id
        self.limpiar_bonos_sin_usos(user_id)
        if user_id not in self.bonos_activos or not self.bonos_activos[user_id]:
            await ctx.send("❌ No tienes bonos activos en este momento.")
            return
        embed = discord.Embed(title=f"✨ Bonos Activos de {ctx.author.display_name}", color=0x00ff00)
        for bono_tipo, bono_info in self.bonos_activos[user_id].items():
            if bono_tipo == "multiplicador":
                embed.add_field(
                    name="✨ Multiplicador Activo",
                    value=f"**{bono_info['nombre']}**\nUsos restantes: {bono_info['usos_restantes']}/{bono_info['usos_totales']}",
                    inline=True
                )
        await ctx.send(embed=embed)

    @commands.command(name="gachastats", aliases=["gachaestadisticas"])
    async def gachastats(self, ctx):
        total_cajas = sum(len(coleccion) for coleccion in self.colecciones_usuarios.values())
        total_usuarios = len(self.colecciones_usuarios)
        embed = discord.Embed(title="📊 ESTADÍSTICAS DEL SISTEMA GACHA", color=0xff00ff)
        embed.add_field(name="👥 Usuarios con colección", value=f"**{total_usuarios}**", inline=True)
        embed.add_field(name="📦 Items totales obtenidos", value=f"**{total_cajas}**", inline=True)
        embed.add_field(name="🎰 Cajas disponibles", value=f"**{len(SISTEMA_GACHA['cajas'])}** tipos", inline=True)
        todas_rarezas = {}
        for usuario_items in self.colecciones_usuarios.values():
            for item in usuario_items:
                rareza = item.split("_")[-1]
                todas_rarezas[rareza] = todas_rarezas.get(rareza, 0) + 1
        if todas_rarezas:
            rarezas_text = ""
            for rareza, cantidad in sorted(todas_rarezas.items(), key=lambda x: x[1], reverse=True):
                rarezas_text += f"**{rareza.upper()}**: {cantidad}\n"
            embed.add_field(name="🎨 Distribución de Rarezas", value=rarezas_text, inline=True)
        embed.add_field(name="💎 Mejor premio posible", value="**MULTIPLICADOR x3.0** (10 usos, 10%)", inline=True)
        embed.add_field(name="⏰ Cooldowns", value="Básica: 1h\nPremium: 3h\nLegendaria: 24h", inline=True)
        embed.add_field(name="🔄 Sistema de usos", value="Los multiplicadores ahora tienen usos limitados en lugar de tiempo", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Gacha(bot))
