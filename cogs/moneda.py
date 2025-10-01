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
        credits = db.get_credits(self.user_id)
        if credits < self.apuesta:
            await interaction.response.send_message("❌ No tienes suficientes créditos.", ephemeral=True)
            return

        # Girar la moneda
        resultado = random.choice(["cara", "cruz"])
        emoji_resultado = "😀" if resultado == "cara" else "⭕"
        
        # Determinar ganancia
        if eleccion == resultado:
            ganancia = self.apuesta
            mensaje = f"🎉 **¡GANASTE!** La moneda cayó en **{resultado}** {emoji_resultado}"
            tipo_transaccion = "win"
        else:
            ganancia = -self.apuesta
            mensaje = f"❌ **¡Perdiste!** La moneda cayó en **{resultado}** {emoji_resultado}"
            tipo_transaccion = "loss"

        # Actualizar créditos
        db.update_credits(self.user_id, ganancia, tipo_transaccion, "moneda", 
                         f"Moneda: {eleccion} vs {resultado}")

        embed = discord.Embed(
            title="🪙 **RESULTADO - CARA O CRUZ**",
            color=0x00ff00 if ganancia > 0 else 0xff0000
        )
        embed.add_field(name="🎯 Tu elección", value=f"**{eleccion.upper()}**", inline=True)
        embed.add_field(name="🪙 Resultado", value=f"**{resultado.upper()}** {emoji_resultado}", inline=True)
        embed.add_field(name="💰 Apuesta", value=f"**{self.apuesta:,}** créditos", inline=True)
        embed.add_field(name="💸 Resultado", value=f"**{'+' if ganancia > 0 else ''}{ganancia:,}** créditos", inline=True)
        embed.add_field(name="💳 Balance nuevo", value=f"**{db.get_credits(self.user_id):,}** créditos", inline=True)
        
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

        # Calcular resultados
        if ganador_creador and ganador_oponente:
            # Empate - ambos ganan (raro pero posible)
            resultado_texto = "🤝 **EMPATE** - Ambos ganan!"
            db.update_credits(duelo['creador_id'], duelo['apuesta'], "win", "moneda_duelo", f"Empate vs {duelo['oponente_nombre']}")
            db.update_credits(duelo['oponente_id'], duelo['apuesta'], "win", "moneda_duelo", f"Empate vs {duelo['creador_nombre']}")
        elif ganador_creador:
            # Creador gana
            resultado_texto = f"🎉 **{duelo['creador_nombre']} GANA!**"
            db.update_credits(duelo['creador_id'], duelo['apuesta'], "win", "moneda_duelo", f"Ganó vs {duelo['oponente_nombre']}")
            db.update_credits(duelo['oponente_id'], -duelo['apuesta'], "loss", "moneda_duelo", f"Perdió vs {duelo['creador_nombre']}")
        elif ganador_oponente:
            # Oponente gana
            resultado_texto = f"🎉 **{duelo['oponente_nombre']} GANA!**"
            db.update_credits(duelo['oponente_id'], duelo['apuesta'], "win", "moneda_duelo", f"Ganó vs {duelo['creador_nombre']}")
            db.update_credits(duelo['creador_id'], -duelo['apuesta'], "loss", "moneda_duelo", f"Perdió vs {duelo['oponente_nombre']}")
        else:
            # Nadie gana (ambos pierden)
            resultado_texto = "💥 **AMBOS PIERDEN!**"
            db.update_credits(duelo['creador_id'], -duelo['apuesta'], "loss", "moneda_duelo", f"Ambos perdieron vs {duelo['oponente_nombre']}")
            db.update_credits(duelo['oponente_id'], -duelo['apuesta'], "loss", "moneda_duelo", f"Ambos perdieron vs {duelo['creador_nombre']}")

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

        # Eliminar duelo pendiente
        del duelos_pendientes[duelo_id]

        # Editar mensaje original
        original_message = await interaction.channel.fetch_message(duelo['mensaje_id'])
        await original_message.edit(embed=embed, view=None)

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
        credits = db.get_credits(self.oponente_id)
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
            await ctx.send(embed=embed)
            return

        if apuesta < 10:
            await ctx.send("❌ Apuesta mínima: 10 créditos")
            return

        # Verificar créditos
        credits = db.get_credits(ctx.author.id)
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
        credits_creador = db.get_credits(ctx.author.id)
        if credits_creador < apuesta:
            await ctx.send(f"❌ No tienes suficientes créditos. Tu balance: {credits_creador:,}")
            return

        # Verificar créditos del oponente
        credits_oponente = db.get_credits(oponente.id)
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
        # Aquí podrías agregar estadísticas específicas del juego de moneda
        embed = discord.Embed(
            title="📊 ESTADÍSTICAS CARA O CRUZ",
            color=0xffd700
        )
        embed.add_field(name="🎯 Probabilidad", value="50% de ganar", inline=True)
        embed.add_field(name="💰 Pago", value="1:1", inline=True)
        embed.add_field(name="📈 Esperanza matemática", value="0% (juego justo)", inline=True)
        embed.add_field(name="🎮 Modos", value="• Solitario vs Casa\n• Duelo vs Jugador", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moneda(bot))