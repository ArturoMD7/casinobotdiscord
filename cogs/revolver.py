import discord
from discord.ext import commands
import random
import asyncio
from db.database import Database

db = Database()

class RuletaRusa(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.juegos_activos = {}
        self.buscando_partida = {}

    @commands.command(name="ruletarusa", aliases=["rr", "rusa", "revolver"])
    async def ruletarusa(self, ctx, bet: int = None, oponente: discord.Member = None):
        """🎪 Ruleta Rusa Multijugador - Enfréntate a la máquina o a otros jugadores"""
        
        if bet is None:
            embed = discord.Embed(
                title="🎪 RULETA RUSA MULTIJUGADOR",
                description="**¿CONTRA QUIÉN TE ATREVES A JUGAR?**\n\n6 cámaras, 1 bala... ¡El superviviente se lleva todo!",
                color=0xff0000
            )
            embed.add_field(
                name="💀 REGLAS DEL JUEGO", 
                value="• 🔫 **6 cámaras, 1 bala** (posición fija)\n"
                      "• 🔄 **Tambor gira después de cada disparo**\n"
                      "• 👤 **Turnos alternados**\n"
                      "• 💰 **El ganador se lleva el bote completo**\n"
                      "• 🤖 **Puedes jugar contra la máquina o otros jugadores**", 
                inline=False
            )
            embed.add_field(
                name="🎯 MODOS DE JUEGO", 
                value="• `!ruletarusa 1000` → vs Máquina 🤖\n"
                      "• `!ruletarusa 1000 @usuario` → vs Jugador 👤", 
                inline=False
            )
            embed.set_footer(text="En un revólver real, la bala espera en una cámara... ¿en cuál?")
            await ctx.send(embed=embed)
            return

        if bet < 100:
            await ctx.send("❌ **Apuesta mínima: 100 créditos** - ¡El riesgo merece la pena!")
            return

        user_id = ctx.author.id
        
        # Verificar si ya tiene un juego activo
        if user_id in self.juegos_activos:
            await ctx.send("❌ **Ya tienes un juego de ruleta rusa en progreso.**")
            return

        # Verificar créditos
        credits = db.get_saldo(ctx.author.id)
        if bet > credits:
            await ctx.send(f"❌ **No tienes suficientes créditos.**\nTu balance: {credits:,} créditos")
            return

        # Determinar tipo de juego
        if oponente is None:
            # Juego contra la máquina
            await self.iniciar_juego_maquina(ctx, bet)
        else:
            # Juego contra otro jugador
            if oponente.id == ctx.author.id:
                await ctx.send("❌ **No puedes jugar contra ti mismo.**")
                return
            if oponente.bot:
                await ctx.send("❌ **No puedes jugar contra bots.**")
                return
            
            await self.iniciar_juego_jugador(ctx, bet, oponente)

    async def iniciar_juego_maquina(self, ctx, bet):
        """Inicia un juego contra la máquina"""
        user_id = ctx.author.id
        
        # Inicializar juego vs máquina - Bala en posición fija
        bala_posicion = random.randint(1, 6)
        
        self.juegos_activos[user_id] = {
            'tipo': 'maquina',
            'jugador1': ctx.author,
            'apuesta': bet,
            'cámaras_totales': 6,
            'posición_actual': 1,  # Por dónde va el tambor
            'bala_posicion': bala_posicion,  # Posición FIJA de la bala
            'turno_actual': 'jugador',
            'ronda': 1,
            'mensaje_inicial': None
        }

        juego = self.juegos_activos[user_id]
        
        # Descontar apuesta del jugador
        db.update_saldo(user_id, -bet, "bet", "ruletarusa", "Apuesta vs máquina")
        
        # Mensaje de inicio
        embed = discord.Embed(
            title="🤖 RULETA RUSA vs MÁQUINA",
            description=f"**{ctx.author.mention} se enfrenta a la máquina**\n*La bala está cargada en una de las 6 cámaras...*",
            color=0xff9900
        )
        embed.add_field(name="💰 APUESTA TOTAL", value=f"**{bet*2:,}** créditos", inline=True)
        embed.add_field(name="🎯 CÁMARAS", value=f"**6** cámaras, **1** bala", inline=True)
        embed.add_field(name="🔫 PRIMER TURNO", value="**Jugador** 🎯", inline=True)
        embed.add_field(name="📊 PROBABILIDAD INICIAL", value=f"**{int(5/6*100)}%** de sobrevivir", inline=True)
        
        view = self.crear_vista_disparo(user_id)
        mensaje = await ctx.send(embed=embed, view=view)
        juego['mensaje_inicial'] = mensaje

    async def iniciar_juego_jugador(self, ctx, bet, oponente):
        """Inicia un juego contra otro jugador"""
        user_id = ctx.author.id
        oponente_id = oponente.id

        # Verificar si el oponente está disponible
        if oponente_id in self.juegos_activos:
            await ctx.send("❌ **El oponente seleccionado ya está en un juego.**")
            return

        # Verificar créditos del oponente
        credits_oponente = db.get_saldo(oponente_id)
        if bet > credits_oponente:
            await ctx.send(f"❌ **{oponente.mention} no tiene suficientes créditos para esta apuesta.**")
            return

        # Enviar invitación
        embed_invitacion = discord.Embed(
            title="🎯 INVITACIÓN A RULETA RUSA",
            description=f"**{ctx.author.mention} te reta a un duelo mortal**\n*6 cámaras, 1 bala... ¿quién sobrevivirá?*",
            color=0xffff00
        )
        embed_invitacion.add_field(name="💰 APUESTA", value=f"**{bet:,}** créditos cada uno", inline=True)
        embed_invitacion.add_field(name="🏆 BOTE TOTAL", value=f"**{bet*2:,}** créditos", inline=True)
        embed_invitacion.set_footer(text="Tienes 60 segundos para aceptar")

        class InvitacionView(discord.ui.View):
            def __init__(self, cog, retador, oponente, bet):
                super().__init__(timeout=60.0)
                self.cog = cog
                self.retador = retador
                self.oponente = oponente
                self.bet = bet

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return interaction.user.id == self.oponente.id

            @discord.ui.button(label="✅ ACEPTAR RETO", style=discord.ButtonStyle.success)
            async def aceptar(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Verificar que ambos todavía tienen créditos
                credits1 = db.get_saldo(self.retador.id)
                credits2 = db.get_saldo(self.oponente.id)
                
                if credits1 < self.bet or credits2 < self.bet:
                    await interaction.response.edit_message(
                        content="❌ **Uno de los jugadores ya no tiene créditos suficientes**",
                        embed=None,
                        view=None
                    )
                    return

                # Bala en posición fija
                bala_posicion = random.randint(1, 6)
                
                # Inicializar juego PvP
                self.cog.juegos_activos[self.retador.id] = {
                    'tipo': 'pvp',
                    'jugador1': self.retador,
                    'jugador2': self.oponente,
                    'apuesta': self.bet,
                    'cámaras_totales': 6,
                    'posición_actual': 1,
                    'bala_posicion': bala_posicion,
                    'turno_actual': 'jugador1',
                    'ronda': 1,
                    'mensaje_inicial': None
                }

                juego = self.cog.juegos_activos[self.retador.id]

                # Descontar apuestas
                db.update_saldo(self.retador.id, -self.bet, "bet", "ruletarusa", f"Apuesta vs {self.oponente}")
                db.update_saldo(self.oponente.id, -self.bet, "bet", "ruletarusa", f"Apuesta vs {self.retador}")

                # Mensaje de inicio del juego
                embed = discord.Embed(
                    title="⚔️ RULETA RUSA PvP",
                    description=f"**{self.retador.mention} vs {self.oponente.mention}**\n*La bala está cargada...*",
                    color=0xff0000
                )
                embed.add_field(name="💰 BOTE TOTAL", value=f"**{self.bet*2:,}** créditos", inline=True)
                embed.add_field(name="🎯 CÁMARAS", value="**6** cámaras, **1** bala", inline=True)
                
                # Decidir aleatoriamente quién empieza
                if random.choice([True, False]):
                    juego['turno_actual'] = 'jugador1'
                    embed.add_field(name="🔫 PRIMER TURNO", value=f"**{self.retador.display_name}** 🎯", inline=True)
                else:
                    juego['turno_actual'] = 'jugador2'
                    embed.add_field(name="🔫 PRIMER TURNO", value=f"**{self.oponente.display_name}** 🎯", inline=True)

                view = self.cog.crear_vista_disparo(self.retador.id)
                mensaje = await interaction.channel.send(embed=embed, view=view)
                juego['mensaje_inicial'] = mensaje

                await interaction.response.edit_message(
                    content=f"🎯 **Reto aceptado!** El juego ha comenzado.",
                    embed=None,
                    view=None
                )

            @discord.ui.button(label="❌ RECHAZAR", style=discord.ButtonStyle.danger)
            async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.edit_message(
                    content=f"❌ **{self.oponente.mention} rechazó el reto.**",
                    embed=None,
                    view=None
                )

            async def on_timeout(self):
                await self.message.edit(
                    content=f"⏰ **Invitación expirada.** {self.oponente.mention} no respondió a tiempo.",
                    embed=None,
                    view=None
                )

        view = InvitacionView(self, ctx.author, oponente, bet)
        view.message = await ctx.send(f"{oponente.mention}", embed=embed_invitacion, view=view)

    def crear_vista_disparo(self, game_id):
        """Crea la vista de botones para disparar"""
        class DisparoView(discord.ui.View):
            def __init__(self, cog, game_id):
                super().__init__(timeout=60.0)
                self.cog = cog
                self.game_id = game_id

            @discord.ui.button(label="🔫 DISPARAR", style=discord.ButtonStyle.danger)
            async def disparar(self, interaction: discord.Interaction, button: discord.ui.Button):
                juego = self.cog.juegos_activos.get(self.game_id)
                if not juego:
                    await interaction.response.send_message("❌ El juego ya no está activo.", ephemeral=True)
                    return

                # Verificar turno
                if juego['tipo'] == 'maquina':
                    if juego['turno_actual'] != 'jugador':
                        await interaction.response.send_message("❌ No es tu turno.", ephemeral=True)
                        return
                else:  # PvP
                    turno_actual = juego['turno_actual']
                    jugador_actual = juego[turno_actual]
                    if interaction.user.id != jugador_actual.id:
                        await interaction.response.send_message("❌ No es tu turno.", ephemeral=True)
                        return

                await self.cog.procesar_disparo_jugador(interaction, self.game_id)

        return DisparoView(self, game_id)

    async def procesar_disparo_jugador(self, interaction, game_id):
        """Procesa un disparo del jugador"""
        juego = self.juegos_activos[game_id]
        
        # Determinar jugador actual
        if juego['tipo'] == 'maquina':
            jugador_actual = juego['jugador1']
            nombre_turno = jugador_actual.display_name
        else:
            turno_actual = juego['turno_actual']
            jugador_actual = juego[turno_actual]
            nombre_turno = jugador_actual.display_name

        # Animación de disparo
        embed_disparo = discord.Embed(
            title=f"🔫 {nombre_turno.upper()} DISPARA...",
            description="*El tambor gira... el gatillo cede...* 💥",
            color=0xffff00
        )
        embed_disparo.add_field(name="🎯 POSICIÓN ACTUAL", value=f"**Cámara {juego['posición_actual']}**", inline=True)
        embed_disparo.add_field(name="💰 BOTE", value=f"**{juego['apuesta']*2:,}** créditos", inline=True)
        await interaction.response.edit_message(embed=embed_disparo, view=None)
        
        await asyncio.sleep(2)
        
        # VERIFICAR SI HAY BALA (posición fija vs posición actual)
        hay_bala = juego['posición_actual'] == juego['bala_posicion']
        
        if hay_bala:
            # 💀 JUGADOR MUERE - BALA ENCONTRADA
            await self.procesar_muerte(interaction, game_id, jugador_actual)
        else:
            # 🎉 JUGADOR SOBREVIVE - NO HABÍA BALA
            juego['ronda'] += 1
            
            # GIRAR TAMBOR para siguiente disparo (posición avanza)
            juego['posición_actual'] = (juego['posición_actual'] % 6) + 1
            
            embed_sobrevive = discord.Embed(
                title="🎉 ¡SALVASTE! - CLICK...",
                description=f"**{jugador_actual.mention} sobrevivió... esta vez.** ✅",
                color=0x00ff00
            )
            embed_sobrevive.add_field(name="🔫 PRÓXIMA POSICIÓN", value=f"**Cámara {juego['posición_actual']}**", inline=True)
            embed_sobrevive.add_field(name="💰 BOTE", value=f"**{juego['apuesta']*2:,}** créditos", inline=True)
            embed_sobrevive.add_field(name="📅 RONDA", value=f"**{juego['ronda']}**", inline=True)
            
            await interaction.edit_original_response(embed=embed_sobrevive)
            await asyncio.sleep(2)
            
            # Pasar al siguiente turno
            if juego['tipo'] == 'maquina':
                juego['turno_actual'] = 'maquina'
                await self.procesar_turno_maquina(interaction, game_id)
            else:
                # Cambiar turno en PvP
                if juego['turno_actual'] == 'jugador1':
                    juego['turno_actual'] = 'jugador2'
                    siguiente_jugador = juego['jugador2']
                else:
                    juego['turno_actual'] = 'jugador1'
                    siguiente_jugador = juego['jugador1']
                
                await self.mostrar_siguiente_turno_pvp(interaction, game_id, siguiente_jugador)

    async def procesar_turno_maquina(self, interaction, game_id):
        """Procesa el turno de la máquina"""
        juego = self.juegos_activos[game_id]
        
        embed = discord.Embed(
            title="🤖 LA MÁQUINA DISPARA...",
            description="*La máquina aprieta el gatillo...* 🤖",
            color=0x666666
        )
        embed.add_field(name="🎯 POSICIÓN ACTUAL", value=f"**Cámara {juego['posición_actual']}**", inline=True)
        embed.add_field(name="💰 BOTE", value=f"**{juego['apuesta']*2:,}** créditos", inline=True)
        await interaction.edit_original_response(embed=embed)
        await asyncio.sleep(2)
        
        # VERIFICAR SI HAY BALA (posición fija vs posición actual)
        hay_bala = juego['posición_actual'] == juego['bala_posicion']
        
        if hay_bala:
            # 💀 MÁQUINA MUERE - JUGADOR GANA
            bote = juego['apuesta'] * 2
            db.update_saldo(juego['jugador1'].id, bote, "win", "ruletarusa", "Ganó vs máquina")
            
            embed_victoria = discord.Embed(
                title="🎉 ¡BANG! ¡LA MÁQUINA MURIÓ!",
                description=f"## **{juego['jugador1'].mention} GANA EL BOTE!** 🏆\n*La máquina encontró la bala...*",
                color=0x00ff00
            )
            embed_victoria.add_field(name="💰 BOTE GANADO", value=f"**{bote:,}** créditos", inline=True)
            embed_victoria.add_field(name="💳 BALANCE NUEVO", value=f"**{db.get_saldo(juego['jugador1'].id):,}** créditos", inline=True)
            embed_victoria.add_field(name="🎯 BALA ENCONTRADA", value=f"**Cámara {juego['bala_posicion']}**", inline=True)
            embed_victoria.set_image(url="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExZjZjejQ2MHR5bGt4cmo2NDZyZXBnd3R3eGNrM3cwbjRvYW8xb2p3MSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/YBsd8wdchmxqg/giphy.gif")
            
            del self.juegos_activos[game_id]
            await interaction.edit_original_response(embed=embed_victoria)
        else:
            # 🎉 MÁQUINA SOBREVIVE
            juego['ronda'] += 1
            juego['posición_actual'] = (juego['posición_actual'] % 6) + 1
            
            embed_sobrevive = discord.Embed(
                title="🤖 MÁQUINA SOBREVIVE - CLICK...",
                description="**La máquina sobrevivió... esta vez.** ✅",
                color=0x666666
            )
            embed_sobrevive.add_field(name="🔫 PRÓXIMA POSICIÓN", value=f"**Cámara {juego['posición_actual']}**", inline=True)
            embed_sobrevive.add_field(name="💰 BOTE", value=f"**{juego['apuesta']*2:,}** créditos", inline=True)
            
            await interaction.edit_original_response(embed=embed_sobrevive)
            await asyncio.sleep(2)
            
            # Pasar al turno del jugador
            juego['turno_actual'] = 'jugador'
            embed_siguiente = discord.Embed(
                title=f"🎯 TU TURNO {juego['jugador1'].display_name.upper()}",
                description=f"**{juego['jugador1'].mention} es tu turno...** 🔫",
                color=0xff9900
            )
            embed_siguiente.add_field(name="💰 BOTE", value=f"**{juego['apuesta']*2:,}** créditos", inline=True)
            embed_siguiente.add_field(name="🎯 POSICIÓN ACTUAL", value=f"**Cámara {juego['posición_actual']}**", inline=True)
            embed_siguiente.add_field(name="📊 PROBABILIDAD", value=f"**1 de 6** cámaras tiene la bala", inline=True)
            
            view = self.crear_vista_disparo(game_id)
            await interaction.edit_original_response(embed=embed_siguiente, view=view)

    async def mostrar_siguiente_turno_pvp(self, interaction, game_id, siguiente_jugador):
        """Muestra el siguiente turno en PvP"""
        juego = self.juegos_activos[game_id]
        
        embed = discord.Embed(
            title=f"🎯 TURNO DE {siguiente_jugador.display_name.upper()}",
            description=f"**{siguiente_jugador.mention} es tu turno...** 🔫",
            color=0xff9900
        )
        embed.add_field(name="💰 BOTE", value=f"**{juego['apuesta']*2:,}** créditos", inline=True)
        embed.add_field(name="🎯 POSICIÓN ACTUAL", value=f"**Cámara {juego['posición_actual']}**", inline=True)
        embed.add_field(name="📊 PROBABILIDAD", value=f"**1 de 6** cámaras tiene la bala", inline=True)
        
        view = self.crear_vista_disparo(game_id)
        await interaction.edit_original_response(embed=embed, view=view)

    async def procesar_muerte(self, interaction, game_id, jugador_muerto):
        """Procesa cuando un jugador muere"""
        juego = self.juegos_activos[game_id]
        bote = juego['apuesta'] * 2
        
        # Determinar ganador
        if juego['tipo'] == 'maquina':
            # La máquina gana (jugador pierde su apuesta)
            embed_muerte = discord.Embed(
                title="💀 ¡BANG! ¡HAS MUERTO!",
                description=f"## **{jugador_muerto.mention} ENCONTRÓ LA BALA**\n*En la cámara {juego['bala_posicion']}...*\n\n**La máquina gana el bote** 🤖",
                color=0xff0000
            )
        else:
            # PvP - El otro jugador gana
            if jugador_muerto.id == juego['jugador1'].id:
                ganador = juego['jugador2']
                db.update_saldo(ganador.id, bote, "win", "ruletarusa", f"Ganó vs {jugador_muerto}")
            else:
                ganador = juego['jugador1']
                db.update_saldo(ganador.id, bote, "win", "ruletarusa", f"Ganó vs {jugador_muerto}")
            
            embed_muerte = discord.Embed(
                title="💀 ¡BANG! ¡JUGADOR ELIMINADO!",
                description=f"## **{jugador_muerto.mention} ENCONTRÓ LA BALA**\n*En la cámara {juego['bala_posicion']}...*\n\n**{ganador.mention} GANA {bote:,} CRÉDITOS!** 🎉",
                color=0xff0000
            )

        embed_muerte.add_field(name="💰 BOTE GANADO", value=f"**{bote:,}** créditos", inline=True)
        embed_muerte.add_field(name="🎯 BALA ENCONTRADA", value=f"**Cámara {juego['bala_posicion']}**", inline=True)
        
        if juego['tipo'] == 'pvp':
            embed_muerte.add_field(name="🏆 GANADOR", value=f"{ganador.mention}", inline=True)
        
        embed_muerte.set_image(url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExeTJzNTFucmZvZ2FoY3JzZ2k3Mm1kYjMxMnlneG1kNjJva2docm5peSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/OY9XK7PbFqkNO/giphy.gif")
        
        # Eliminar juego
        del self.juegos_activos[game_id]
        
        await interaction.edit_original_response(embed=embed_muerte)

    @commands.command(name="cancelar")
    async def cancelar_busqueda(self, ctx):
        """Cancela la búsqueda de partida"""
        if ctx.author.id in self.buscando_partida:
            del self.buscando_partida[ctx.author.id]
            await ctx.send("✅ **Búsqueda de partida cancelada.**")
        else:
            await ctx.send("❌ **No estás buscando partida.**")

    @ruletarusa.error
    async def ruletarusa_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("❌ **¡Usa un número válido!**\nEjemplo: `!ruletarusa 1000` o `!ruletarusa 1000 @usuario`")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ **¡Falta la apuesta!**\nEjemplo: `!ruletarusa 1000` o `!ruletarusa 1000 @usuario`")

async def setup(bot):
    await bot.add_cog(RuletaRusa(bot))