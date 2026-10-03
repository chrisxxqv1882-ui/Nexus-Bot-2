import os
import random
import asyncio
import time
from collections import defaultdict
import discord
from discord import app_commands

# Configuración global avanzada del bot
config_global = {
    "prefijo": "a¡",
    "rol_organizar_eventos_id": None, 
    "rol_aprobar_sugerencias_id": None, 
    "canal_sanciones_id": None, 
    "canal_sugerencias_id": None, 
    "canal_postulaciones_id": None, # Canal global para recibir postulaciones
    "contador_postulaciones": 0, 
    # Anti-Spam
    "antispam_activo": True,
    "antispam_limite_mensajes": 5,
    "antispam_ventana_segundos": 5,
    "antispam_timeout_segundos": 60,
    # Anti-Bot y Anti-Raid Avanzado
    "antibots_activo": True,
    "antiraid_activo": True,
    "antiraid_limite_ingresos": 5,
    "antiraid_ventana_segundos": 10,
    # Juegos
    "embed_juegos_titulo": "🎮 Zona de Juegos e Interacción",
    "embed_juegos_desc": "¡Diviértete con los minijuegos multijugador y nuestra trivia masiva estilo Nekotrivia!",
    "embed_juegos_color": 0xF1C40F
}

registro_antispam = defaultdict(list)
registro_antiraid = defaultdict(list)
base_datos_sanciones = defaultdict(list)
eventos_activos = {} 

# CONFIGURACIÓN DE POSTULACIONES (TOTALMENTE EDITABLES)
postulaciones_config = {
    "staff": {
        "titulo": "📝 Postulación: Cuerpo de Moderación",
        "color": 0x3498DB,
        "preguntas": ["¿Cuál es tu edad?", "¿Por qué quieres ser Moderador?", "¿Tienes experiencia previa moderando servidores?"]
    },
    "ally": {
        "titulo": "📝 Postulación: Casa Alianza",
        "color": 0x2ECC71,
        "preguntas": ["¿Cuál es el nombre y temática de tu servidor?", "¿Cuántos miembros activos tienes?", "¿Cuál es el link de invitación permanente?"]
    },
    "redes": {
        "titulo": "📝 Postulación: Cuerpo de Redes",
        "color": 0x9B59B6,
        "preguntas": ["¿Qué plataformas manejas (TikTok, Instagram, Twitter)?", "¿Tienes ejemplos de ediciones, videos o publicaciones previas?"]
    },
    "nexus": {
        "titulo": "📝 Postulación: Cuerpo de Programación",
        "color": 0xE74C3C,
        "preguntas": ["¿Qué lenguajes de programación conoces (Python, JavaScript, etc.)?", "¿Cuánto tiempo llevas programando bots o sistemas?"]
    }
}

BANCO_TRIVIA = [
    {
        "p": "¿Cómo se llama el protagonista de Dragon Ball que come sin parar?",
        "correcta": "Goku",
        "opciones": ["Vegeta", "Goku", "Piccolo", "Krillin"],
        "cat": "Anime",
        "img": "https://media.giphy.com/media/cb9aF9tDyiRkY/giphy.gif"
    }
]


class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("¡Slash commands sincronizados!")

client = Bot()

@client.event
async def on_ready():
    print(f'¡Bot conectado con éxito como {client.user}!')


async def registrar_log_sancion(guild: discord.Guild, embed: discord.Embed):
    canal_id = config_global["canal_sanciones_id"]
    if canal_id:
        canal = guild.get_channel(canal_id)
        if canal:
            try: await canal.send(embed=embed)
            except: pass


# ==========================================
# 🛡️️ SISTEMA AVANZADO ANTI-BOT Y ANTI-RAID
# ==========================================

@client.event
async def on_member_join(member):
    guild = member.guild
    ahora = time.time()

    if config_global["antiraid_activo"]:
        registro_antiraid[guild.id] = [t for t in registro_antiraid[guild.id] if ahora - t < config_global["antiraid_ventana_segundos"]]
        registro_antiraid[guild.id].append(ahora)

        if len(registro_antiraid[guild.id]) > config_global["antiraid_limite_ingresos"]:
            try:
                embed_raid = discord.Embed(
                    title="🚨 ¡ALERTA ANTI-RAID ACTIVADA!",
                    description=f"Se detectó un ingreso masivo de cuentas en **{guild.name}**.",
                    color=discord.Color.red()
                )
                await registrar_log_sancion(guild, embed_raid)
            except: pass

    if member.bot and config_global["antibots_activo"]:
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    invitador = entry.user
                    await guild.ban(member, reason="Anti-Bots: Bot no autorizado")
                    
                    if invitador and not invitador.guild_permissions.administrator:
                        await guild.ban(invitador, reason="Anti-Bots: Invitó un bot no autorizado sin permisos")
                    
                    embed_log = discord.Embed(
                        title="🤖 Anti-Bots Activado", 
                        description=f"Bot no autorizado {member.mention} baneado.\nInvitador: {invitador.mention if invitador else 'Desconocido'}", 
                        color=discord.Color.red()
                    )
                    await registrar_log_sancion(guild, embed_log)
                    break
        except Exception as e:
            print(f"Error en anti-bots: {e}")


# ==========================================
# 💡 SISTEMA DE SUGERENCIAS AUTOMÁTICO
# ==========================================

class VistaSugerenciaStaff(discord.ui.View):
    def __init__(self, autor_id: int):
        super().__init__(timeout=None)
        self.autor_id = autor_id

    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.success, custom_id="btn_aprobar_sugerencia")
    async def aprobar(self, interaction: discord.Interaction, button: discord.ui.Button):
        rol_req_id = config_global["rol_aprobar_sugerencias_id"]
        tiene_permiso = interaction.user.guild_permissions.administrator
        if not tiene_permiso and rol_req_id:
            rol = interaction.guild.get_role(rol_req_id)
            if rol and rol in interaction.user.roles: tiene_permiso = True

        if not tiene_permiso:
            return await interaction.response.send_message("❌ No tienes permisos para aprobar sugerencias.", ephemeral=True)

        for child in self.children: child.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="📌 Estado", value=f"✅ **Aprobada** por {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=self)

        try:
            usuario = interaction.guild.get_member(self.autor_id)
            if usuario:
                embed_md = discord.Embed(
                    title="💡 Sugerencia Aprobada",
                    description=f"¡Tu sugerencia en **{interaction.guild.name}** ha sido **APROBADA**!\n\n**Sugerencia:**\n{embed.description}",
                    color=discord.Color.green()
                )
                await usuario.send(embed=embed_md)
        except: pass

        await interaction.response.send_message("✅ Sugerencia aprobada.", ephemeral=True)

    @discord.ui.button(label="❌ Rechazar", style=discord.ButtonStyle.danger, custom_id="btn_rechazar_sugerencia")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        rol_req_id = config_global["rol_aprobar_sugerencias_id"]
        tiene_permiso = interaction.user.guild_permissions.administrator
        if not tiene_permiso and rol_req_id:
            rol = interaction.guild.get_role(rol_req_id)
            if rol and rol in interaction.user.roles: tiene_permiso = True

        if not tiene_permiso:
            return await interaction.response.send_message("❌ No tienes permisos para rechazar sugerencias.", ephemeral=True)

        for child in self.children: child.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="📌 Estado", value=f"❌ **Rechazada** por {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=self)

        try:
            usuario = interaction.guild.get_member(self.autor_id)
            if usuario:
                embed_md = discord.Embed(
                    title="💡 Sugerencia Rechazada",
                    description=f"Tu sugerencia en **{interaction.guild.name}** ha sido **rechazada**.\n\n**Sugerencia:**\n{embed.description}",
                    color=discord.Color.red()
                )
                await usuario.send(embed=embed_md)
        except: pass

        await interaction.response.send_message("❌ Sugerencia rechazada.", ephemeral=True)


@client.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    canal_sugerencias_id = config_global["canal_sugerencias_id"]
    if canal_sugerencias_id and message.channel.id == canal_sugerencias_id:
        try:
            await message.delete()
            embed = discord.Embed(title="💡 Nueva Sugerencia", description=message.content, color=0x3498DB)
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            embed.set_footer(text=f"ID: {message.author.id}")

            nuevo_msg = await message.channel.send(embed=embed, view=VistaSugerenciaStaff(message.author.id))
            await nuevo_msg.add_reaction("👍")
            await nuevo_msg.add_reaction("👎")
        except Exception as e:
            print(f"Error en sugerencias: {e}")
        return

    if config_global["antispam_activo"] and not message.author.guild_permissions.administrator:
        ahora = time.time()
        autor_id = message.author.id
        ventana = config_global["antispam_ventana_segundos"]
        registro_antispam[autor_id] = [t for t in registro_antispam[autor_id] if ahora - t < ventana]
        registro_antispam[autor_id].append(ahora)

        if len(registro_antispam[autor_id]) > config_global["antispam_limite_mensajes"]:
            try:
                await message.delete()
                duracion_timeout = config_global["antispam_timeout_segundos"]
                await message.author.timeout(discord.utils.utcnow() + discord.Timedelta(seconds=duracion_timeout), reason="Anti-spam automático")
                base_datos_sanciones[autor_id].append(f"🔇 **Timeout automático** ({duracion_timeout}s)")
                
                embed_log = discord.Embed(title="🔇 Timeout Automático (Anti-Spam)", description=f"**Usuario:** {message.author.mention}", color=discord.Color.orange())
                await registrar_log_sancion(message.guild, embed_log)

                warning = await message.channel.send(f"⚠️ {message.author.mention} Timeout de {duracion_timeout}s por spam.")
                await asyncio.sleep(5)
                await warning.delete()
            except: pass
            return


# ==========================================
# ⚙️ /CONFI-GENERAL EN EMBED INTERACTIVO
# ==========================================

class VistaBotonConfigGeneral(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="✏️ Prefijo", style=discord.ButtonStyle.secondary, row=0)
    async def set_prefijo(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Editar Prefijo"):
            v = discord.ui.TextInput(label="Nuevo Prefijo", default=config_global["prefijo"], max_length=5)
            async def on_submit(self, i: discord.Interaction):
                config_global["prefijo"] = self.v.value.strip()
                await i.response.send_message(f"✅ Prefijo actualizado a: `{config_global['prefijo']}`", ephemeral=True)
        await interaction.response.send_modal(M())

    @discord.ui.button(label="👑 Rol Eventos", style=discord.ButtonStyle.secondary, row=0)
    async def set_rolevento(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Configurar Rol Eventos"):
            v = discord.ui.TextInput(label="ID del Rol", default=str(config_global["rol_organizar_eventos_id"] or ""), max_length=20)
            async def on_submit(self, i: discord.Interaction):
                config_global["rol_organizar_eventos_id"] = int(self.v.value.strip()) if self.v.value.strip() else None
                await i.response.send_message(f"✅ Rol de eventos actualizado.", ephemeral=True)
        await interaction.response.send_modal(M())

    @discord.ui.button(label="💡 Rol Sugerencias", style=discord.ButtonStyle.secondary, row=0)
    async def set_rolsug(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Configurar Rol Sugerencias"):
            v = discord.ui.TextInput(label="ID del Rol", default=str(config_global["rol_aprobar_sugerencias_id"] or ""), max_length=20)
            async def on_submit(self, i: discord.Interaction):
                config_global["rol_aprobar_sugerencias_id"] = int(self.v.value.strip()) if self.v.value.strip() else None
                await i.response.send_message(f"✅ Rol de sugerencias actualizado.", ephemeral=True)
        await interaction.response.send_modal(M())

    @discord.ui.button(label="🛡️ Canal Sanciones", style=discord.ButtonStyle.primary, row=1)
    async def set_canalsancion(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Configurar Canal Sanciones"):
            v = discord.ui.TextInput(label="ID del Canal", default=str(config_global["canal_sanciones_id"] or ""), max_length=20)
            async def on_submit(self, i: discord.Interaction):
                config_global["canal_sanciones_id"] = int(self.v.value.strip()) if self.v.value.strip() else None
                await i.response.send_message(f"✅ Canal de sanciones actualizado.", ephemeral=True)
        await interaction.response.send_modal(M())

    @discord.ui.button(label="📢 Canal Sugerencias", style=discord.ButtonStyle.primary, row=1)
    async def set_canalsug(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Configurar Canal Sugerencias"):
            v = discord.ui.TextInput(label="ID del Canal", default=str(config_global["canal_sugerencias_id"] or ""), max_length=20)
            async def on_submit(self, i: discord.Interaction):
                config_global["canal_sugerencias_id"] = int(self.v.value.strip()) if self.v.value.strip() else None
                await i.response.send_message(f"✅ Canal de sugerencias actualizado.", ephemeral=True)
        await interaction.response.send_modal(M())

    @discord.ui.button(label="📋 Canal Global Postulaciones", style=discord.ButtonStyle.success, row=1)
    async def set_canallogs(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Configurar Canal Global Postulaciones"):
            v = discord.ui.TextInput(label="ID del Canal", default=str(config_global["canal_postulaciones_id"] or ""), max_length=20)
            async def on_submit(self, i: discord.Interaction):
                config_global["canal_postulaciones_id"] = int(self.v.value.strip()) if self.v.value.strip() else None
                await i.response.send_message(f"✅ Canal global de postulaciones actualizado.", ephemeral=True)
        await interaction.response.send_modal(M())


@client.tree.command(name="confi-general", description="Panel visual en Embed para configurar roles y canales")
async def confi_general(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)

    embed = discord.Embed(
        title="⚙️ Panel de Configuración General",
        description="Haz clic en los botones inferiores para editar cada parámetro individualmente:",
        color=0x3498DB
    )
    embed.add_field(name="📌 Prefijo actual", value=f"`{config_global['prefijo']}`", inline=True)
    embed.add_field(name="👑 Rol Organizar Eventos", value=f"<@&{config_global['rol_organizar_eventos_id']}>" if config_global['rol_organizar_eventos_id'] else "No configurado", inline=True)
    embed.add_field(name="💡 Rol Aprobar Sugerencias", value=f"<@&{config_global['rol_aprobar_sugerencias_id']}>" if config_global['rol_aprobar_sugerencias_id'] else "No configurado", inline=True)
    embed.add_field(name="🛡️ Canal Sanciones", value=f"<#{config_global['canal_sanciones_id']}>" if config_global['canal_sanciones_id'] else "No configurado", inline=True)
    embed.add_field(name="📢 Canal Sugerencias", value=f"<#{config_global['canal_sugerencias_id']}>" if config_global['canal_sugerencias_id'] else "No configurado", inline=True)
    embed.add_field(name="📋 Canal Global Postulaciones", value=f"<#{config_global['canal_postulaciones_id']}>" if config_global['canal_postulaciones_id'] else "No configurado", inline=True)

    await interaction.response.send_message(embed=embed, view=VistaBotonConfigGeneral(), ephemeral=True)


# ==========================================
# 📋 SISTEMA DE POSTULACIONES Y /CONFIGURAR-POSTULACIONES (CON BOTONES)
# ==========================================

class ModalEditarFormulario(discord.ui.Modal):
    def __init__(self, post_key, cfg):
        super().__init__(title=f"Configurar: {cfg['titulo']}")
        self.post_key = post_key
        self.cfg = cfg

        self.titulo_input = discord.ui.TextInput(label="Título del Formulario", default=cfg["titulo"], max_length=100)
        self.color_input = discord.ui.TextInput(label="Color Hex (ej: #3498DB)", default=f"#{cfg['color']:06x}", max_length=7)
        self.preguntas_input = discord.ui.TextInput(
            label="Preguntas (Una por línea)",
            style=discord.TextStyle.paragraph,
            default="\n".join(cfg["preguntas"]),
            max_length=2000
        )

        self.add_item(self.titulo_input)
        self.add_item(self.color_input)
        self.add_item(self.preguntas_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            nuevo_color = int(self.color_input.value.strip().replace("#", ""), 16)
        except:
            return await interaction.response.send_message("❌ Color Hex inválido.", ephemeral=True)

        nuevas_preguntas = [p.strip() for p in self.preguntas_input.value.split("\n") if p.strip()]
        if not nuevas_preguntas:
            return await interaction.response.send_message("❌ Debes incluir al menos una pregunta válida.", ephemeral=True)

        postulaciones_config[self.post_key]["titulo"] = self.titulo_input.value.strip()
        postulaciones_config[self.post_key]["color"] = nuevo_color
        postulaciones_config[self.post_key]["preguntas"] = nuevas_preguntas

        await interaction.response.send_message(f"✅ ¡Formulario **{self.post_key}** actualizado con éxito!", ephemeral=True)


class VistaBotonesConfigurarPostulaciones(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="📝 Staff (Moderación)", style=discord.ButtonStyle.primary, row=0)
    async def btn_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarFormulario("staff", postulaciones_config["staff"]))

    @discord.ui.button(label="🤝 Casa Alianza", style=discord.ButtonStyle.success, row=0)
    async def btn_ally(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarFormulario("ally", postulaciones_config["ally"]))

    @discord.ui.button(label="🎨 Cuerpo de Redes", style=discord.ButtonStyle.secondary, row=1)
    async def btn_redes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarFormulario("redes", postulaciones_config["redes"]))

    @discord.ui.button(label="💻 Cuerpo de Programación", style=discord.ButtonStyle.danger, row=1)
    async def btn_nexus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarFormulario("nexus", postulaciones_config["nexus"]))


@client.tree.command(name="configurar-postulaciones", description="Edita títulos, colores y preguntas mediante botones directos")
async def configurar_postulaciones(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)

    embed = discord.Embed(
        title="⚙️ Configurar Formularios de Postulación",
        description="Haz clic en el botón correspondiente al formulario que deseas editar en tiempo real:",
        color=0x3498DB
    )
    await interaction.response.send_message(embed=embed, view=VistaBotonesConfigurarPostulaciones(), ephemeral=True)


class VistaComenzarPostulacion(discord.ui.View):
    def __init__(self, tipo, num_id, preguntas, miembro_postulado, config_form):
        super().__init__(timeout=None)
        self.tipo, self.num_id, self.preguntas, self.miembro_postulado, self.config_form = tipo, num_id, preguntas, miembro_postulado, config_form

    @discord.ui.button(label="🚀 Comenzar Postulación", style=discord.ButtonStyle.success)
    async def comenzar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.miembro_postulado.id:
            return await interaction.response.send_message("❌ Este formulario no es para ti.", ephemeral=True)
        
        await interaction.response.send_message("📬 ¡Cuestionario abierto en tus **Mensajes Privados (MD)**!", ephemeral=True)
        try:
            respuestas = []
            for i, preg in enumerate(self.preguntas):
                await self.miembro_postulado.send(embed=discord.Embed(title=f"Pregunta {i+1} de {len(self.preguntas)}", description=preg, color=self.config_form['color']))
                msg = await client.wait_for('message', timeout=120.0, check=lambda m: m.author.id == self.miembro_postulado.id and isinstance(m.channel, discord.DMChannel))
                respuestas.append((preg, msg.content))
            
            txt = "".join([f"**{p}**\n↳ {r}\n\n" for p, r in respuestas])
            embed_final = discord.Embed(
                title=f"{self.config_form['titulo']} (#{self.num_id})", 
                description=f"👤 **Candidato:** {self.miembro_postulado.mention}\n\n{txt}", 
                color=self.config_form['color']
            )
            
            canal_id = config_global["canal_postulaciones_id"]
            destino = interaction.guild.get_channel(canal_id) if canal_id else interaction.channel
            if destino: 
                await destino.send(embed=embed_final)
            
            await self.miembro_postulado.send("🎉 ¡Postulación completada y enviada al staff con éxito!")
        except Exception as e:
            try:
                await self.miembro_postulado.send("❌ La postulación ha expirado o ha ocurrido un error.")
            except: pass


@client.tree.command(name="postulacion", description="Envía el panel de postulación para un usuario")
async def postulacion(interaction: discord.Interaction, miembro: discord.Member):
    if not interaction.user.guild_permissions.administrator and not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ No tienes permisos para gestionar postulaciones.", ephemeral=True)

    v = discord.ui.View(timeout=60)
    s = discord.ui.Select(
        placeholder="Selecciona el formulario...", 
        options=[
            discord.SelectOption(label="Staff (Moderación)", value="staff", emoji="📝"),
            discord.SelectOption(label="Casa Alianza", value="ally", emoji="🤝"),
            discord.SelectOption(label="Cuerpo de Redes", value="redes", emoji="🎨"),
            discord.SelectOption(label="Cuerpo de Programación", value="nexus", emoji="💻")
        ]
    )
    
    async def cb(i):
        tipo_sel = s.values[0]
        cfg = postulaciones_config.get(tipo_sel, {})
        config_global["contador_postulaciones"] += 1
        num_id = config_global["contador_postulaciones"]
        
        embed_panel = discord.Embed(
            title=cfg['titulo'],
            description=f"Candidato: {miembro.mention}\nHaz clic en el botón inferior para responder las preguntas en tus **Mensajes Privados (MD)**.",
            color=cfg['color']
        )
        await i.response.edit_message(content=f"✅ Formulario listo para {miembro.mention}.", embed=embed_panel, view=VistaComenzarPostulacion(tipo_sel, num_id, cfg["preguntas"], miembro, cfg))

    s.callback = cb
    v.add_item(s)
    await interaction.response.send_message(embed=discord.Embed(title="📋 Menú de Postulaciones", description=f"Selecciona el formulario para {miembro.mention}:"), view=v, ephemeral=True)


# ==========================================
# 🛡️ SANCIONES Y MODERACIÓN (BAN, UNBAN, KICK, MUTE, WARN, HISTORIAL)
# ==========================================

@client.tree.command(name="ban", description="Banea a un miembro del servidor")
async def ban(interaction: discord.Interaction, miembro: discord.Member, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.ban_members: 
        return await interaction.response.send_message("❌ No tienes permisos para banear miembros.", ephemeral=True)
    await miembro.ban(reason=razon)
    base_datos_sanciones[miembro.id].append(f"🔨 Ban - {razon}")
    
    embed_log = discord.Embed(title="🔨 Sanción: Ban", description=f"**Usuario:** {miembro.mention}\n**Moderador:** {interaction.user.mention}\n**Razón:** {razon}", color=discord.Color.red())
    await registrar_log_sancion(interaction.guild, embed_log)
    await interaction.response.send_message(f"🔨 {miembro.mention} ha sido baneado.")


@client.tree.command(name="unban", description="Desbanea a un usuario por su ID o Nombre")
async def unban(interaction: discord.Interaction, usuario_id: str, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.ban_members: 
        return await interaction.response.send_message("❌ No tienes permisos para desbanear.", ephemeral=True)
    async for entry in interaction.guild.bans():
        if str(entry.user.id) == usuario_id.strip() or entry.user.name.lower() == usuario_id.strip().lower():
            await interaction.guild.unban(entry.user, reason=razon)
            return await interaction.response.send_message(f"🔓 Usuario **{entry.user}** desbaneado correctamente.")
    await interaction.response.send_message("❌ No se encontró ningún usuario baneado con ese ID o nombre.", ephemeral=True)


@client.tree.command(name="kick", description="Expulsa a un miembro del servidor")
async def kick(interaction: discord.Interaction, miembro: discord.Member, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.kick_members: 
        return await interaction.response.send_message("❌ No tienes permisos para expulsar miembros.", ephemeral=True)
    await miembro.kick(reason=razon)
    base_datos_sanciones[miembro.id].append(f"👢 Kick - {razon}")
    
    embed_log = discord.Embed(title="👢 Sanción: Kick", description=f"**Usuario:** {miembro.mention}\n**Moderador:** {interaction.user.mention}\n**Razón:** {razon}", color=discord.Color.orange())
    await registrar_log_sancion(interaction.guild, embed_log)
    await interaction.response.send_message(f"👢 {miembro.mention} ha sido expulsado.")


@client.tree.command(name="mute", description="Silencia temporalmente a un miembro (Timeout)")
async def mute(interaction: discord.Interaction, miembro: discord.Member, segundos: int, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.moderate_members: 
        return await interaction.response.send_message("❌ No tienes permisos para silenciar miembros.", ephemeral=True)
    await miembro.timeout(discord.utils.utcnow() + discord.Timedelta(seconds=segundos), reason=razon)
    base_datos_sanciones[miembro.id].append(f"🔇 Mute ({segundos}s) - {razon}")
    
    embed_log = discord.Embed(title="🔇 Sanción: Timeout (Mute)", description=f"**Usuario:** {miembro.mention}\n**Duración:** {segundos}s\n**Moderador:** {interaction.user.mention}\n**Razón:** {razon}", color=discord.Color.gold())
    await registrar_log_sancion(interaction.guild, embed_log)
    await interaction.response.send_message(f"🔇 {miembro.mention} ha sido silenciado por {segundos} segundos.")


@client.tree.command(name="unmute", description="Quita el silencio a un miembro")
async def unmute(interaction: discord.Interaction, miembro: discord.Member):
    if not interaction.user.guild_permissions.moderate_members: 
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    await miembro.timeout(None)
    await interaction.response.send_message(f"🔊 Se ha retirado el silencio a {miembro.mention}.")


@client.tree.command(name="warn", description="Advierte formalmente a un miembro")
async def warn(interaction: discord.Interaction, miembro: discord.Member, razon: str):
    if not interaction.user.guild_permissions.moderate_members: 
        return await interaction.response.send_message("❌ No tienes permisos para advertir miembros.", ephemeral=True)
    base_datos_sanciones[miembro.id].append(f"⚠️ Warn - {razon}")
    
    try: 
        await miembro.send(embed=discord.Embed(title="⚠️ Advertencia", description=f"Has recibido una advertencia en **{interaction.guild.name}**.\n**Razón:** {razon}", color=discord.Color.gold()))
    except: pass
    
    embed_log = discord.Embed(title="⚠️ Sanción: Warn", description=f"**Usuario:** {miembro.mention}\n**Moderador:** {interaction.user.mention}\n**Razón:** {razon}", color=discord.Color.gold())
    await registrar_log_sancion(interaction.guild, embed_log)
    await interaction.response.send_message(f"⚠️ {miembro.mention} ha sido advertido.")


@client.tree.command(name="historial", description="Muestra el historial de sanciones de un miembro")
async def historial(interaction: discord.Interaction, miembro: discord.Member):
    if not interaction.user.guild_permissions.moderate_members: 
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    s = base_datos_sanciones.get(miembro.id, [])
    if not s: 
        return await interaction.response.send_message(f"🛡️ El usuario {miembro.mention} tiene el historial limpio.", ephemeral=True)
    
    embed = discord.Embed(title=f"📜 Historial de Sanciones: {miembro.display_name}", description="\n".join([f"• {x}" for x in s]), color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 📅 SISTEMA DE EVENTOS (CON OPCIONES OPCIONALES)
# ==========================================

class VistaEventoParticipar(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎉 Participar", style=discord.ButtonStyle.success, custom_id="btn_participar_evento_rt")
    async def participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg_id = interaction.message.id
        if msg_id not in eventos_activos:
            return await interaction.response.send_message("❌ Este evento ya no está activo.", ephemeral=True)

        datos = eventos_activos[msg_id]
        participantes = datos["participantes"]

        if interaction.user.id in participantes:
            participantes.remove(interaction.user.id)
            estado_msj = "❌ Te has **retirado** del evento."
        else:
            participantes.add(interaction.user.id)
            estado_msj = "✅ ¡Te has **unido** exitosamente al evento!"

        guild = interaction.guild
        nombres = [guild.get_member(uid).display_name for uid in participantes if guild.get_member(uid)]
        lista_nombres_str = ", ".join(nombres) if nombres else "Nadie apuntado aún"

        embed_viejo = interaction.message.embeds[0]
        embed_nuevo = discord.Embed(
            title=embed_viejo.title,
            description=embed_viejo.description,
            color=embed_viejo.color
        )
        for field in embed_viejo.fields:
            if "Participantes" not in field.name:
                embed_nuevo.add_field(name=field.name, value=field.value, inline=field.inline)
        
        embed_nuevo.add_field(name=f"👥 Participantes ({len(participantes)})", value=lista_nombres_str, inline=False)
        if embed_viejo.image.url:
            embed_nuevo.set_image(url=embed_viejo.image.url)

        await interaction.message.edit(embed=embed_nuevo)
        await interaction.response.send_message(estado_msj, ephemeral=True)


@client.tree.command(name="organizar-evento", description="Organiza un evento interactivo con parámetros opcionales")
@app_commands.describe(
    nombre="Nombre del evento", 
    canal="Canal donde se publicará", 
    texto="Descripción del evento (Opcional)", 
    organizadores="Nombres de los organizadores (Opcional)",
    tiempo="¿Cuándo empieza? (Opcional)",
    ganadores="Número de ganadores (Opcional)",
    mencion="Rol o mención a avisar (Opcional)"
)
async def organizar_evento(
    interaction: discord.Interaction, 
    nombre: str, 
    canal: discord.TextChannel, 
    texto: str = "¡Participa en nuestro evento!", 
    organizadores: str = "Staff", 
    tiempo: str = "Pronto", 
    ganadores: str = "Por definir", 
    mencion: str = ""
):
    rol_req_id = config_global["rol_organizar_eventos_id"]
    tiene_permiso = interaction.user.guild_permissions.manage_events or interaction.user.guild_permissions.administrator
    if not tiene_permiso and rol_req_id:
        rol = interaction.guild.get_role(rol_req_id)
        if rol and rol in interaction.user.roles: tiene_permiso = True

    if not tiene_permiso:
        return await interaction.response.send_message("❌ No tienes permisos para organizar eventos.", ephemeral=True)

    embed = discord.Embed(title=f"📅 ¡Evento: {nombre}!", description=texto, color=0xE91E63)
    embed.add_field(name="👑 Organizadores", value=organizadores, inline=False)
    embed.add_field(name="⏰ Inicio", value=tiempo, inline=True)
    embed.add_field(name="🏆 Ganadores", value=ganadores, inline=True)
    embed.add_field(name="👥 Participantes (0)", value="Nadie apuntado aún", inline=False)
    embed.set_footer(text="Haz clic en el botón inferior para unirte en tiempo real.")

    mensaje = await canal.send(content=mencion if mencion else "", embed=embed, view=VistaEventoParticipar())

    eventos_activos[mensaje.id] = {
        "nombre": nombre,
        "organizadores": organizadores,
        "tiempo": tiempo,
        "ganadores": ganadores,
        "participantes": set(),
        "canal_id": canal.id
    }

    await interaction.response.send_message(f"✅ ¡Evento **{nombre}** publicado en {canal.mention}!", ephemeral=True)


class SelectorIniciarEvento(discord.ui.Select):
    def __init__(self, eventos: dict):
        options = []
        for msg_id, datos in eventos.items():
            options.append(discord.SelectOption(label=datos["nombre"][:100], description=f"Organizadores: {datos['organizadores'][:50]}", value=str(msg_id)))
        super().__init__(placeholder="Selecciona el evento que deseas iniciar...", options=options)

    async def callback(self, interaction: discord.Interaction):
        msg_id = int(self.values[0])
        if msg_id not in eventos_activos:
            return await interaction.response.send_message("❌ Este evento ya no está disponible.", ephemeral=True)
        
        datos = eventos_activos[msg_id]
        guild = interaction.guild
        canal = guild.get_channel(datos["canal_id"])

        class ModalInicioPing(discord.ui.Modal, title="Iniciar Evento - Mención"):
            mencion_input = discord.ui.TextInput(label="Rol o Mención (ej: @everyone)", default="@everyone", required=True, max_length=50)

            async def on_submit(self, i2: discord.Interaction):
                ping = self.mencion_input.value
                if canal:
                    embed_inicio = discord.Embed(
                        title=f"🚨 ¡EL EVENTO '{datos['nombre']}' VA A DAR INICIO!",
                        description=f"¡El evento organizado por **{datos['organizadores']}** comienza ahora mismo!",
                        color=discord.Color.gold()
                    )
                    await canal.send(content=ping, embed=embed_inicio)
                    await i2.response.send_message(f"✅ ¡Anuncio enviado a {canal.mention}!", ephemeral=True)

        await interaction.response.send_modal(ModalInicioPing())


class VistaSelectorEventos(discord.ui.View):
    def __init__(self, eventos: dict):
        super().__init__(timeout=30)
        self.add_item(SelectorIniciarEvento(eventos))


@client.tree.command(name="iniciar-evento", description="Selecciona un evento activo y envía el aviso de inicio")
async def iniciar_evento(interaction: discord.Interaction):
    rol_req_id = config_global["rol_organizar_eventos_id"]
    tiene_permiso = interaction.user.guild_permissions.manage_events or interaction.user.guild_permissions.administrator
    if not tiene_permiso and rol_req_id:
        rol = interaction.guild.get_role(rol_req_id)
        if rol and rol in interaction.user.roles: tiene_permiso = True

    if not tiene_permiso:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    if not eventos_activos:
        return await interaction.response.send_message("🛡️ No hay eventos activos.", ephemeral=True)

    await interaction.response.send_message(embed=discord.Embed(title="🚀 Iniciar Evento", description="Selecciona en el menú desplegable:", color=0x3498DB), view=VistaSelectorEventos(eventos_activos), ephemeral=True)


@client.tree.command(name="lista-eventos", description="Muestra todos los eventos activos")
async def lista_eventos(interaction: discord.Interaction):
    if not eventos_activos:
        return await interaction.response.send_message("🛡️ No hay eventos activos.", ephemeral=True)

    embed = discord.Embed(title="📊 Lista de Eventos Activos", color=0x9B59B6)
    guild = interaction.guild

    for msg_id, datos in eventos_activos.items():
        canal = guild.get_channel(datos["canal_id"])
        nombres = [guild.get_member(uid).display_name for uid in datos["participantes"] if guild.get_member(uid)]
        lista_str = ", ".join(nombres) if nombres else "Nadie apuntado"
        
        embed.add_field(
            name=f"📌 {datos['nombre']} ({canal.mention if canal else 'Canal'})",
            value=f"**Organizadores:** {datos['organizadores']}\n**Participantes ({len(datos['participantes'])}):** {lista_str}",
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 🎮 JUEGOS Y AYUDA
# ==========================================

@client.tree.command(name="help", description="Centro de ayuda")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="✨ Centro de Ayuda", description=f"Prefijo: `{config_global['prefijo']}`", color=0x5865F2)
    embed.add_field(name="⚙ Módulos Activos", value="• `/confi-general` • `/configurar-postulaciones` • `/postulacion`\n• `/organizar-evento` • `/iniciar-evento` • `/lista-eventos`\n• `/ban` • `/kick` • `/mute` • `/warn` • `/historial`\n• `/juegos` • `/dado` • `/trivia`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.tree.command(name="juegos", description="Menú de juegos")
async def juegos(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(title=config_global["embed_juegos_titulo"], description=config_global["embed_juegos_desc"], color=config_global["embed_juegos_color"]))


@client.tree.command(name="dado", description="Lanza un dado")
async def dado(interaction: discord.Interaction, caras: int = 6):
    await interaction.response.send_message(f"🎲 Sacaste: **{random.randint(1, caras)}**")


@client.tree.command(name="trivia", description="Trivia pública")
async def trivia(interaction: discord.Interaction):
    t = random.choice(BANCO_TRIVIA)
    embed = discord.Embed(title=f"🧠 Trivia: {t['cat']}", description=f"**{t['p']}**", color=0x3498DB)
    embed.set_image(url=t["img"])
    await interaction.response.send_message(embed=embed, ephemeral=True)


client.run(os.environ['DISCORD_TOKEN'])
