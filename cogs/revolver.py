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

    @commands.command(name="ruletarusa", aliases=["rr", "rusa", "revolver"])
    async def ruletarusa(self, ctx, bet: int = None):
        """🎪 Ruleta Rusa Progresiva - Sigue jugando para multiplicar tus ganancias"""
        
        if bet is None:
            embed = discord.Embed(
                title="🎪 RULETA RUSA PROGRESIVA",
                description="**¿CUÁNTO RIESGO ESTÁS DISPUESTO A TOMAR?**\n\n6 cámaras, 1 bala... ¡Multiplica tus ganancias mientras sobrevivas!",
                color=0xff0000
            )
            embed.add_field(
                name="💀 REGLAS DEL JUEGO", 
                value="• 🔫 **Ronda 1:** 6 cámaras, 1 bala → **x2**\n"
                      "• 🔫 **Ronda 2:** 5 cámaras, 1 bala → **x3**\n"
                      "• 🔫 **Ronda 3:** 4 cámaras, 1 bala → **x4**\n"
                      "• 🔫 **Ronda 4:** 3 cámaras, 1 bala → **x5**\n"
                      "• 🔫 **Ronda 5:** 2 cámaras, 1 bala → **x6**\n"
                      "• 🔫 **Ronda 6:** 1 cámara, 1 bala → **x10**", 
                inline=False
            )
            embed.add_field(
                name="🎯 PROBABILIDADES INICIALES", 
                value="• 🟢 **Sobrevivir Ronda 1:** 83.3%\n• 🔴 **Morir Ronda 1:** 16.7%", 
                inline=True
            )
            embed.add_field(
                name="💰 USO", 
                value="`!ruletarusa <apuesta>`", 
                inline=True
            )
            embed.set_footer(text="Los valientes son recompensados... los temerarios mueren ricos")
            await ctx.send(embed=embed)
            return

        if bet < 100:
            await ctx.send("❌ **Apuesta mínima: 100 créditos** - ¡El riesgo merece la pena!")
            return

        user_id = ctx.author.id
        
        # Verificar si ya tiene un juego activo
        if user_id in self.juegos_activos:
            await ctx.send("❌ **Ya tienes un juego de ruleta rusa en progreso.**\nUsa `!continuar` para seguir o `!retirarse` para cobrar.")
            return

        credits = db.get_credits(ctx.author.id)
        if bet > credits:
            await ctx.send(f"❌ **No tienes suficientes créditos.**\nTu balance: {credits:,} créditos")
            return

        # Inicializar juego
        self.juegos_activos[user_id] = {
            'apuesta_base': bet,
            'ronda_actual': 1,
            'multiplicador': 2,
            'cámaras_restantes': 6,
            'bala_posicion': random.randint(1, 6),  # Bala en posición aleatoria
            'ganancia_acumulada': bet * 2
        }

        juego = self.juegos_activos[user_id]
        
        # Mensaje de inicio
        embed = discord.Embed(
            title="🔫 RULETA RUSA - RONDA 1",
            description=f"**{ctx.author.mention} está jugando con la muerte...**",
            color=0xff9900
        )
        embed.add_field(name="💰 APUESTA BASE", value=f"**{bet:,}** créditos", inline=True)
        embed.add_field(name="🎯 MULTIPLICADOR ACTUAL", value=f"**x{juego['multiplicador']}**", inline=True)
        embed.add_field(name="💀 CÁMARAS RESTANTES", value=f"**{juego['cámaras_restantes']}**", inline=True)
        embed.add_field(name="💰 GANANCIA ACTUAL", value=f"**{juego['ganancia_acumulada']:,}** créditos", inline=True)
        embed.add_field(name="🎰 PROBABILIDAD", value=f"**{int((juego['cámaras_restantes']-1)/juego['cámaras_restantes']*100)}%** de sobrevivir", inline=True)
        
        # Botones de acción
        class RondaView(discord.ui.View):
            def __init__(self, cog, user_id):
                super().__init__(timeout=60.0)
                self.cog = cog
                self.user_id = user_id
            
            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return interaction.user.id == self.user_id
            
            @discord.ui.button(label="🎲 DISPARAR", style=discord.ButtonStyle.danger, emoji="🔫")
            async def disparar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.cog.procesar_disparo(interaction)
            
            @discord.ui.button(label="💰 RETIRARSE", style=discord.ButtonStyle.success, emoji="🏃")
            async def retirarse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.cog.retirarse(interaction)
            
            async def on_timeout(self):
                # Si se acaba el tiempo, cobrar automáticamente
                if self.user_id in self.cog.juegos_activos:
                    juego = self.cog.juegos_activos[self.user_id]
                    ganancia = juego['ganancia_acumulada'] - juego['apuesta_base']
                    db.update_credits(self.user_id, ganancia, "win", "ruletarusa", f"Retiro automático ronda {juego['ronda_actual']}")
                    del self.cog.juegos_activos[self.user_id]
        
        view = RondaView(self, user_id)
        await ctx.send(embed=embed, view=view)

    async def procesar_disparo(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id not in self.juegos_activos:
            await interaction.response.send_message("❌ No tienes un juego activo.", ephemeral=True)
            return
        
        juego = self.juegos_activos[user_id]
        
        # Animación de disparo
        embed_disparo = discord.Embed(
            title=f"🔫 RONDA {juego['ronda_actual']} - DISPARANDO...",
            description="*El tambor gira... tu corazón late...*",
            color=0xffff00
        )
        embed_disparo.add_field(name="🎯 CÁMARAS RESTANTES", value=f"**{juego['cámaras_restantes']}**", inline=True)
        embed_disparo.add_field(name="💰 GANANCIA EN JUEGO", value=f"**{juego['ganancia_acumulada']:,}** créditos", inline=True)
        await interaction.response.edit_message(embed=embed_disparo, view=None)
        
        await asyncio.sleep(2)
        
        # Verificar si hay bala
        cámara_actual = random.randint(1, juego['cámaras_restantes'])
        hay_bala = cámara_actual == juego['bala_posicion']
        
        if hay_bala:
            # 💀 MUERTO
            db.update_credits(user_id, -juego['apuesta_base'], "loss", "ruletarusa", f"Muerto en ronda {juego['ronda_actual']}")
            del self.juegos_activos[user_id]
            
            embed_muerte = discord.Embed(
                title="💀 ¡BANG! ¡HAS MUERTO!",
                description=f"## **{interaction.user.mention} PROBÓ SU SUERTE... Y PERDIÓ**\n\n*En la ronda {juego['ronda_actual']} encontraste la bala...*",
                color=0xff0000
            )
            embed_muerte.add_field(name="🔫 RONDA", value=f"**{juego['ronda_actual']}**", inline=True)
            embed_muerte.add_field(name="💰 PÉRDIDA", value=f"**-{juego['apuesta_base']:,}** créditos", inline=True)
            embed_muerte.add_field(name="💳 BALANCE NUEVO", value=f"**{db.get_credits(user_id):,}** créditos", inline=False)
            embed_muerte.set_image(url="https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif")
            embed_muerte.set_footer(text="La muerte no tiene prisa... siempre te espera.")
            
            await interaction.edit_original_response(embed=embed_muerte)
            
        else:
            # 🎉 SOBREVIVIÓ - Pasar a siguiente ronda
            juego['ronda_actual'] += 1
            juego['cámaras_restantes'] -= 1
            
            # Actualizar multiplicador según la ronda
            if juego['ronda_actual'] == 2:
                juego['multiplicador'] = 3
            elif juego['ronda_actual'] == 3:
                juego['multiplicador'] = 4
            elif juego['ronda_actual'] == 4:
                juego['multiplicador'] = 5
            elif juego['ronda_actual'] == 5:
                juego['multiplicador'] = 6
            elif juego['ronda_actual'] == 6:
                juego['multiplicador'] = 10
            
            juego['ganancia_acumulada'] = juego['apuesta_base'] * juego['multiplicador']
            
            # Verificar si ganó el juego completo
            if juego['ronda_actual'] > 6:
                # 🏆 GANÓ TODO
                ganancia = juego['ganancia_acumulada'] - juego['apuesta_base']
                db.update_credits(user_id, ganancia, "win", "ruletarusa", "Ganó todas las rondas")
                del self.juegos_activos[user_id]
                
                embed_victoria_total = discord.Embed(
                    title="🏆 ¡LE GANASTE A LA MUERTE!",
                    description=f"## **{interaction.user.mention} ES UNA LEYENDA!**\n\n*¡Sobreviviste a todas las rondas!*",
                    color=0x00ff00
                )
                embed_victoria_total.add_field(name="💰 GANANCIA TOTAL", value=f"**+{ganancia:,}** créditos 🎊", inline=True)
                embed_victoria_total.add_field(name="🎯 MULTIPLICADOR FINAL", value=f"**x10**", inline=True)
                embed_victoria_total.add_field(name="💳 BALANCE NUEVO", value=f"**{db.get_credits(user_id):,}** créditos 💰", inline=False)
                embed_victoria_total.set_image(url="https://media.giphy.com/media/3o7aD2s2fSrLcMaZEs/giphy.gif")
                embed_victoria_total.set_footer(text="¡Eres inmortal!... por ahora.")
                
                await interaction.edit_original_response(embed=embed_victoria_total)
                
            else:
                # Continuar a siguiente ronda
                embed_siguiente = discord.Embed(
                    title=f"🎉 ¡SOBREVIVISTE! - RONDA {juego['ronda_actual']}",
                    description=f"**{interaction.user.mention} sigue con vida... ¿continuarás?**",
                    color=0x00ff00
                )
                embed_siguiente.add_field(name="💰 APUESTA BASE", value=f"**{juego['apuesta_base']:,}** créditos", inline=True)
                embed_siguiente.add_field(name="🎯 MULTIPLICADOR ACTUAL", value=f"**x{juego['multiplicador']}**", inline=True)
                embed_siguiente.add_field(name="💀 CÁMARAS RESTANTES", value=f"**{juego['cámaras_restantes']}**", inline=True)
                embed_siguiente.add_field(name="💰 GANANCIA ACTUAL", value=f"**{juego['ganancia_acumulada']:,}** créditos", inline=True)
                embed_siguiente.add_field(name="🎰 PROBABILIDAD", value=f"**{int((juego['cámaras_restantes']-1)/juego['cámaras_restantes']*100)}%** de sobrevivir", inline=True)
                embed_siguiente.add_field(name="🏆 GANANCIA MÁXIMA", value=f"**{juego['apuesta_base'] * 10:,}** créditos", inline=True)
                
                class SiguienteRondaView(discord.ui.View):
                    def __init__(self, cog, user_id):
                        super().__init__(timeout=60.0)
                        self.cog = cog
                        self.user_id = user_id
                    
                    async def interaction_check(self, interaction: discord.Interaction) -> bool:
                        return interaction.user.id == self.user_id
                    
                    @discord.ui.button(label="🎲 SIGUIENTE DISPARO", style=discord.ButtonStyle.danger, emoji="🔫")
                    async def siguiente_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        await self.cog.procesar_disparo(interaction)
                    
                    @discord.ui.button(label="💰 COBRAR Y RETIRARSE", style=discord.ButtonStyle.success, emoji="💰")
                    async def cobrar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        await self.cog.retirarse(interaction)
                
                view = SiguienteRondaView(self, user_id)
                await interaction.edit_original_response(embed=embed_siguiente, view=view)

    async def retirarse(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id not in self.juegos_activos:
            await interaction.response.send_message("❌ No tienes un juego activo.", ephemeral=True)
            return
        
        juego = self.juegos_activos[user_id]
        ganancia = juego['ganancia_acumulada'] - juego['apuesta_base']
        
        db.update_credits(user_id, ganancia, "win", "ruletarusa", f"Retiro en ronda {juego['ronda_actual']}")
        del self.juegos_activos[user_id]
        
        embed_retiro = discord.Embed(
            title="💰 RETIRO EXITOSO",
            description=f"**{interaction.user.mention} se retira sabiamente...**",
            color=0x00ff00
        )
        embed_retiro.add_field(name="🔫 RONDA ALCANZADA", value=f"**{juego['ronda_actual']}**", inline=True)
        embed_retiro.add_field(name="🎯 MULTIPLICADOR", value=f"**x{juego['multiplicador']}**", inline=True)
        embed_retiro.add_field(name="💰 GANANCIA", value=f"**+{ganancia:,}** créditos", inline=True)
        embed_retiro.add_field(name="💳 BALANCE NUEVO", value=f"**{db.get_credits(user_id):,}** créditos", inline=False)
        embed_retiro.set_footer(text="Más vale pájaro en mano que ciento volando...")
        
        await interaction.response.edit_message(embed=embed_retiro, view=None)

    @commands.command(name="retirarse")
    async def retirarse_comando(self, ctx):
        """Retirarse del juego actual de ruleta rusa"""
        await self.retirarse(ctx)

    @ruletarusa.error
    async def ruletarusa_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("❌ **¡Usa un número válido!**\nEjemplo: `!ruletarusa 1000`")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ **¡Falta la apuesta!**\nEjemplo: `!ruletarusa 1000`")

async def setup(bot):
    await bot.add_cog(RuletaRusa(bot))