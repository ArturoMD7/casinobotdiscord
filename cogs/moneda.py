import discord
from discord.ext import commands
from discord.ui import Button, View
from db.database import Database
import random

db = Database()

# Diccionario para duelos pendientes
duelos_pendientes = {}

class MonedaView(View):
    def __init__(self, user_id, apuesta, es_duelo=False, oponente_id=None):
        super().__init__(timeout=30.0)
        self.user_id = user_id
        self.apuesta = apuesta
        self.es_duelo = es_duelo
        self.oponente_id = oponente_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.es_duelo:
            return interaction.user.id in [self.user_id, self.oponente_id]
        return interaction.user.id == self.user_id

    @discord.ui.button(label="🪙 Cara", style=discord.ButtonStyle.primary, emoji="😀")
    async def cara_button(self, interaction: discord.Interaction, button: Button):
        await self.procesar_apuesta(interaction, "cara")

    @discord.ui.button(label="🪙 Cruz", style=discord.ButtonStyle.primary, emoji="⭕")
    async def cruz_button(self, interaction: discord.Interaction, button: Button):
        await self.procesar_apuesta(interaction, "cruz")

    async def procesar_apuesta(self, interaction: discord.Interaction, eleccion: str):
        if self.es_duelo:
            await self.procesar_duelo(interaction, eleccion)
        else:
            await self.procesar_solitario(interaction, eleccion)

    async def procesar_solitario(self, interaction: discord.Interaction, eleccion: str):
        # Verificar créditos
        credits = db.get_saldo(self.user_id)
        if credits < self.apuesta:
            await interaction.response.send_message("❌ No tienes suficientes créditos.", ephemeral=True)
            return

        # Girar la moneda
        resultado = random.choice(["cara", "cruz"])
        emoji_resultado = "😀" if resultado == "cara" else "⭕"
        
        # Determinar ganancia base
        if eleccion == resultado:
            ganancia_base = self.apuesta
            mensaje = f"🎉 **¡GANASTE!** La moneda cayó en **{resultado}** {emoji_resultado}"
            tipo_transaccion = "win"
            
            # APLICAR MULTIPLICADOR DEL GACHA (SISTEMA POR USOS)
            multiplicador_gacha = 1.0
            gacha_cog = interaction.client.get_cog('Gacha')

            if gacha_cog:
                multiplicador_gacha = gacha_cog.obtener_multiplicador_activo(self.user_id)
                if multiplicador_gacha > 1.0:
                    # Aplicar multiplicador del Gacha a la ganancia (esto consume usos automáticamente)
                    ganancia_final = gacha_cog.aplicar_multiplicador_ganancias(self.user_id, ganancia_base)
                    mensaje += f"\n✨ **BONO GACHA:** {ganancia_base:,} → **{ganancia_final:,}** créditos (x{multiplicador_gacha})"
                    ganancia_neto = ganancia_final
                    
                    # Mostrar usos restantes si hay multiplicador activo
                    if self.user_id in gacha_cog.bonos_activos and "multiplicador" in gacha_cog.bonos_activos[self.user_id]:
                        usos_restantes = gacha_cog.bonos_activos[self.user_id]["multiplicador"]["usos_restantes"]
                        mensaje += f" | Usos restantes: {usos_restantes}"
                else:
                    ganancia_neto = ganancia_base
            else:
                ganancia_neto = ganancia_base
                
        else:
            ganancia_neto = -self.apuesta
            ganancia_base = 0
            mensaje = f"❌ **¡Perdiste!** La moneda cayó en **{resultado}** {emoji_resultado}"
            tipo_transaccion = "loss"

        # Actualizar créditos
        db.update_saldo(self.user_id, ganancia_neto, tipo_transaccion, "moneda", 
                         f"Moneda: {eleccion} vs {resultado}")

        embed = discord.Embed(
            title="🪙 **RESULTADO - CARA O CRUZ**",
            color=0x00ff00 if ganancia_neto > 0 else 0xff0000
        )
        embed.add_field(name="🎯 Tu elección", value=f"**{eleccion.upper()}**", inline=True)
        embed.add_field(name="🪙 Resultado", value=f"**{resultado.upper()}** {emoji_resultado}", inline=True)
        embed.add_field(name="💰 Apuesta", value=f"**{self.apuesta:,}** créditos", inline=True)
        
        # Mostrar información de ganancia con multiplicador si aplica
        if ganancia_neto > 0 and multiplicador_gacha > 1.0:
            embed.add_field(name="💸 Ganancia base", value=f"**+{ganancia_base:,}** créditos", inline=True)
            embed.add_field(name="✨ Ganancia final", value=f"**+{ganancia_neto:,}** créditos (x{multiplicador_gacha})", inline=True)
            
            # Mostrar usos restantes
            if gacha_cog and self.user_id in gacha_cog.bonos_activos and "multiplicador" in gacha_cog.bonos_activos[self.user_id]:
                usos_restantes = gacha_cog.bonos_activos[self.user_id]["multiplicador"]["usos_restantes"]
                embed.add_field(name="🔢 Usos restantes", value=f"**{usos_restantes}** usos", inline=True)
        else:
            embed.add_field(name="💸 Resultado", value=f"**{'+' if ganancia_neto > 0 else ''}{ganancia_neto:,}** créditos", inline=True)
        
        embed.add_field(name="💳 Balance nuevo", value=f"**{db.get_saldo(self.user_id):,}** créditos", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)

    async def procesar_duelo(self, interaction: discord.Interaction, eleccion: str):
        duelo_id = f"{self.user_id}_{self.oponente_id}"
        
        if duelo_id not in duelos_pendientes:
            await interaction.response.send_message("❌ Este duelo ya no está disponible.", ephemeral=True)
            return

        duelo = duelos_pendientes[duelo_id]
        
        # Registrar la elección del jugador
        if interaction.user.id == self.user_id:
            duelo['eleccion_creador'] = eleccion
            await interaction.response.send_message(f"✅ Elegiste **{eleccion}**. Esperando a {duelo['oponente_nombre']}...", ephemeral=True)
        else:
            duelo['eleccion_oponente'] = eleccion
            await interaction.response.send_message(f"✅ Elegiste **{eleccion}**. Esperando a {duelo['creador_nombre']}...", ephemeral=True)

        # Verificar si ambos han elegido
        if duelo['eleccion_creador'] and duelo['eleccion_oponente']:
            await self.resolver_duelo(interaction, duelo_id, duelo)

    async def resolver_duelo(self, interaction: discord.Interaction, duelo_id: str, duelo: dict):
        # Girar la moneda
        resultado = random.choice(["cara", "cruz"])
        emoji_resultado = "😀" if resultado == "cara" else "⭕"

        # Determinar ganadores
        ganador_creador = duelo['eleccion_creador'] == resultado
        ganador_oponente = duelo['eleccion_oponente'] == resultado

        # APLICAR MULTIPLICADORES DEL GACHA A AMBOS JUGADORES (SISTEMA POR USOS)
        gacha_cog = interaction.client.get_cog('Gacha')
        multiplicador_creador = 1.0
        multiplicador_oponente = 1.0
        
        if gacha_cog:
            multiplicador_creador = gacha_cog.obtener_multiplicador_activo(duelo['creador_id'])
            multiplicador_oponente = gacha_cog.obtener_multiplicador_activo(duelo['oponente_id'])

        # Calcular resultados
        if ganador_creador and ganador_oponente:
            # Empate - ambos ganan (raro pero posible)
            resultado_texto = "🤝 **EMPATE** - Ambos ganan!"
            
            # Aplicar multiplicadores a las ganancias (esto consume usos automáticamente)
            ganancia_creador_base = duelo['apuesta']
            ganancia_oponente_base = duelo['apuesta']
            
            if multiplicador_creador > 1.0:
                ganancia_creador_final = gacha_cog.aplicar_multiplicador_ganancias(duelo['creador_id'], ganancia_creador_base)
            else:
                ganancia_creador_final = ganancia_creador_base
                
            if multiplicador_oponente > 1.0:
                ganancia_oponente_final = gacha_cog.aplicar_multiplicador_ganancias(duelo['oponente_id'], ganancia_oponente_base)
            else:
                ganancia_oponente_final = ganancia_oponente_base
            
            db.update_saldo(duelo['creador_id'], ganancia_creador_final, "win", "moneda_duelo", f"Empate vs {duelo['oponente_nombre']}")
            db.update_saldo(duelo['oponente_id'], ganancia_oponente_final, "win", "moneda_duelo", f"Empate vs {duelo['creador_nombre']}")
            
        elif ganador_creador:
            # Creador gana
            resultado_texto = f"🎉 **{duelo['creador_nombre']} GANA!**"
            ganancia_base = duelo['apuesta']
            
            if multiplicador_creador > 1.0:
                ganancia_final = gacha_cog.aplicar_multiplicador_ganancias(duelo['creador_id'], ganancia_base)
            else:
                ganancia_final = ganancia_base
                
            db.update_saldo(duelo['creador_id'], ganancia_final, "win", "moneda_duelo", f"Ganó vs {duelo['oponente_nombre']}")
            db.update_saldo(duelo['oponente_id'], -duelo['apuesta'], "loss", "moneda_duelo", f"Perdió vs {duelo['creador_nombre']}")
            
        elif ganador_oponente:
            # Oponente gana
            resultado_texto = f"🎉 **{duelo['oponente_nombre']} GANA!**"
            ganancia_base = duelo['apuesta']
            
            if multiplicador_oponente > 1.0:
                ganancia_final = gacha_cog.aplicar_multiplicador_ganancias(duelo['oponente_id'], ganancia_base)
            else:
                ganancia_final = ganancia_base
                
            db.update_saldo(duelo['oponente_id'], ganancia_final, "win", "moneda_duelo", f"Ganó vs {duelo['creador_nombre']}")
            db.update_saldo(duelo['creador_id'], -duelo['apuesta'], "loss", "moneda_duelo", f"Perdió vs {duelo['oponente_nombre']}")
        else:
            # Nadie gana (ambos pierden)
            resultado_texto = "💥 **AMBOS PIERDEN!**"
            db.update_saldo(duelo['creador_id'], -duelo['apuesta'], "loss", "moneda_duelo", f"Ambos perdieron vs {duelo['oponente_nombre']}")
            db.update_saldo(duelo['oponente_id'], -duelo['apuesta'], "loss", "moneda_duelo", f"Ambos perdieron vs {duelo['creador_nombre']}")

        # Crear embed de resultado
        embed = discord.Embed(
            title="⚔️ **DUELO DE MONEDAS - RESULTADO** ⚔️",
            description=resultado_texto,
            color=0xff9900
        )
        
        embed.add_field(name="🪙 Resultado de la moneda", value=f"**{resultado.upper()}** {emoji_resultado}", inline=False)
        embed.add_field(name=f"🎯 {duelo['creador_nombre']}", value=f"Eligió: **{duelo['eleccion_creador'].upper()}**", inline=True)
        embed.add_field(name=f"🎯 {duelo['oponente_nombre']}", value=f"Eligió: **{duelo['eleccion_oponente'].upper()}**", inline=True)
        embed.add_field(name="💰 Apuesta", value=f"**{duelo['apuesta']:,}** créditos c/u", inline=True)
        embed.add_field(name="🏆 Ganador", value=resultado_texto, inline=False)
        
        # Mostrar multiplicadores aplicados si los hay
        info_multiplicadores = []
        if multiplicador_creador > 1.0 and ganador_creador:
            usos_restantes_creador = gacha_cog.bonos_activos.get(duelo['creador_id'], {}).get('multiplicador', {}).get('usos_restantes', 0)
            info_multiplicadores.append(f"**{duelo['creador_nombre']}**: x{multiplicador_creador} (usos restantes: {usos_restantes_creador})")
        if multiplicador_oponente > 1.0 and ganador_oponente:
            usos_restantes_oponente = gacha_cog.bonos_activos.get(duelo['oponente_id'], {}).get('multiplicador', {}).get('usos_restantes', 0)
            info_multiplicadores.append(f"**{duelo['oponente_nombre']}**: x{multiplicador_oponente} (usos restantes: {usos_restantes_oponente})")
            
        if info_multiplicadores:
            embed.add_field(
                name="✨ Multiplicadores Aplicados", 
                value="\n".join(info_multiplicadores), 
                inline=False
            )

        # Eliminar duelo pendiente
        del duelos_pendientes[duelo_id]

        # Editar mensaje original
        original_message = await interaction.channel.fetch_message(duelo['mensaje_id'])
        await original_message.edit(embed=embed, view=None)

# ... (el resto del código de MonedaDueloView y Moneda cog se mantiene igual)

class MonedaDueloView(View):
    def __init__(self, creador_id, creador_nombre, oponente_id, oponente_nombre, apuesta, mensaje_id):
        super().__init__(timeout=60.0)
        self.creador_id = creador_id
        self.creador_nombre = creador_nombre
        self.oponente_id = oponente_id
        self.oponente_nombre = oponente_nombre
        self.apuesta = apuesta
        self.mensaje_id = mensaje_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.oponente_id

    @discord.ui.button(label="✅ Aceptar Duelo", style=discord.ButtonStyle.success, emoji="⚔️")
    async def aceptar_button(self, interaction: discord.Interaction, button: Button):
        # Verificar créditos del oponente
        credits = db.get_saldo(self.oponente_id)
        if credits < self.apuesta:
            await interaction.response.send_message("❌ No tienes suficientes créditos para aceptar este duelo.", ephemeral=True)
            return

        # Crear duelo pendiente
        duelo_id = f"{self.creador_id}_{self.oponente_id}"
        duelos_pendientes[duelo_id] = {
            'creador_id': self.creador_id,
            'creador_nombre': self.creador_nombre,
            'oponente_id': self.oponente_id,
            'oponente_nombre': self.oponente_nombre,
            'apuesta': self.apuesta,
            'mensaje_id': self.mensaje_id,
            'eleccion_creador': None,
            'eleccion_oponente': None
        }

        # Crear embed de duelo aceptado
        embed = discord.Embed(
            title="⚔️ **DUELO DE MONEDAS ACEPTADO!** ⚔️",
            description=f"**{self.creador_nombre}** vs **{self.oponente_nombre}**\nCada uno elija Cara o Cruz:",
            color=0x00ff00
        )
        
        embed.add_field(name="💰 Apuesta", value=f"**{self.apuesta:,}** créditos c/u", inline=True)
        embed.add_field(name="🏆 Premio", value=f"**{self.apuesta:,}** créditos", inline=True)
        embed.add_field(name="✨ Multiplicadores", value="Los multiplicadores del Gacha se aplican automáticamente", inline=False)
        embed.add_field(name="🎯 Instrucciones", value="Ambos elijan Cara 😀 o Cruz ⭕", inline=False)

        # Cambiar a la vista de elección de moneda
        view = MonedaView(self.creador_id, self.apuesta, es_duelo=True, oponente_id=self.oponente_id)
        
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="❌ Rechazar Duelo", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def rechazar_button(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="❌ Duelo Rechazado",
            description=f"**{self.oponente_nombre}** rechazó el duelo de **{self.creador_nombre}**",
            color=0xff0000
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class Moneda(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="moneda", aliases=["coin", "caraocruz"])
    async def moneda(self, ctx, apuesta: int = None):
        """Juega Cara o Cruz contra la casa"""
        
        if apuesta is None:
            embed = discord.Embed(
                title="🪙 CARA O CRUZ",
                description="**¡Adivina si caerá Cara o Cruz!**\n\nPaga 1:1 - Ganas lo mismo que apuestas",
                color=0xffd700
            )
            embed.add_field(name="🎯 Cómo jugar", value="Elige Cara 😀 o Cruz ⭕", inline=False)
            embed.add_field(name="💰 Ejemplo", value="`!moneda 100` - Apuesta 100 créditos", inline=False)
            embed.add_field(name="📊 Probabilidades", value="50% de ganar\nPago: 1:1", inline=True)
            embed.add_field(name="✨ Multiplicadores", value="Los multiplicadores del Gacha se aplican a tus ganancias", inline=True)
            await ctx.send(embed=embed)
            return

        if apuesta < 10:
            await ctx.send("❌ Apuesta mínima: 10 créditos")
            return

        # Verificar créditos
        credits = db.get_saldo(ctx.author.id)
        if credits < apuesta:
            await ctx.send(f"❌ No tienes suficientes créditos. Tu balance: {credits:,}")
            return

        embed = discord.Embed(
            title="🪙 CARA O CRUZ",
            description=f"**{ctx.author.display_name}** apuesta **{apuesta:,}** créditos\n\n**Elige Cara o Cruz:**",
            color=0xffd700
        )
        embed.add_field(name="💰 Apuesta", value=f"**{apuesta:,}** créditos", inline=True)
        embed.add_field(name="🏆 Premio potencial", value=f"**{apuesta:,}** créditos", inline=True)
        
        # Verificar si tiene multiplicador activo
        gacha_cog = self.bot.get_cog('Gacha')
        if gacha_cog:
            multiplicador = gacha_cog.obtener_multiplicador_activo(ctx.author.id)
            if multiplicador > 1.0:
                premio_con_multiplicador = int(apuesta * multiplicador)
                embed.add_field(
                    name="✨ Multiplicador Activo", 
                    value=f"**x{multiplicador}** → Ganarías **{premio_con_multiplicador:,}** créditos", 
                    inline=False
                )
        
        view = MonedaView(ctx.author.id, apuesta)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="duelomoneda", aliases=["coinduel", "duelocoin"])
    async def duelomoneda(self, ctx, oponente: discord.Member, apuesta: int):
        """Desafia a otro usuario a un duelo de Cara o Cruz"""
        
        if oponente.id == ctx.author.id:
            await ctx.send("❌ No puedes desafiarte a ti mismo.")
            return

        if apuesta < 10:
            await ctx.send("❌ Apuesta mínima: 10 créditos")
            return

        # Verificar créditos del creador
        credits_creador = db.get_saldo(ctx.author.id)
        if credits_creador < apuesta:
            await ctx.send(f"❌ No tienes suficientes créditos. Tu balance: {credits_creador:,}")
            return

        # Verificar créditos del oponente
        credits_oponente = db.get_saldo(oponente.id)
        if credits_oponente < apuesta:
            await ctx.send(f"❌ {oponente.mention} no tiene suficientes créditos. Su balance: {credits_oponente:,}")
            return

        embed = discord.Embed(
            title="⚔️ **DUELO DE MONEDAS** ⚔️",
            description=f"**{ctx.author.display_name}** desafía a **{oponente.display_name}**\n\n**Apuesta:** {apuesta:,} créditos c/u",
            color=0xff0000
        )
        embed.add_field(name="🎯 Reglas", value="• Ambos eligen Cara o Cruz\n• Gana quien acierte el resultado\n• Empate si ambos aciertan\n• Ambos pierden si nadie acierta", inline=False)
        embed.add_field(name="💰 Premio", value=f"**{apuesta:,}** créditos", inline=True)
        embed.add_field(name="✨ Multiplicadores", value="Los multiplicadores del Gacha se aplican automáticamente", inline=True)
        embed.add_field(name="⏰ Tiempo", value="60 segundos para aceptar", inline=True)
        
        message = await ctx.send(f"{oponente.mention} ¡Te han desafiado a un duelo!", embed=embed)
        
        view = MonedaDueloView(
            ctx.author.id, 
            ctx.author.display_name,
            oponente.id,
            oponente.display_name,
            apuesta,
            message.id
        )
        
        await message.edit(view=view)

    @commands.command(name="monedastats", aliases=["coinstats"])
    async def monedastats(self, ctx):
        """Muestra estadísticas de moneda"""
        embed = discord.Embed(
            title="📊 ESTADÍSTICAS CARA O CRUZ",
            color=0xffd700
        )
        embed.add_field(name="🎯 Probabilidad", value="50% de ganar", inline=True)
        embed.add_field(name="💰 Pago", value="1:1", inline=True)
        embed.add_field(name="📈 Esperanza matemática", value="0% (juego justo)", inline=True)
        embed.add_field(name="🎮 Modos", value="• Solitario vs Casa\n• Duelo vs Jugador", inline=False)
        embed.add_field(name="✨ Sistema Gacha", value="Los multiplicadores se aplican automáticamente a las ganancias", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moneda(bot))