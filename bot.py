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
    "rol_comandos_id": None,  
    "rol_organizar_eventos_id": None, 
    "rol_aprobar_sugerencias_id": None, 
    "canal_logs_id": None,     
    "canal_sanciones_id": None, 
    "canal_sugerencias_id": None, 
    "contador_postulaciones": 0, 
    "antispam_activo": True,
    "antispam_limite_mensajes": 5,
    "antispam_ventana_segundos": 5,
    "antispam_timeout_segundos": 60,
    "antibots_activo": True,
    "embed_juegos_titulo": "🎮 Zona de Juegos e Interacción",
    "embed_juegos_desc": "¡Diviértete con los minijuegos multijugador y nuestra trivia masiva estilo Nekotrivia!",
    "embed_juegos_color": 0xF1C40F
}

registro_antispam = defaultdict(list)
base_datos_sanciones = defaultdict(list)
eventos_activos = {} 

# CONFIGURACIÓN DE POSTULACIONES (CON PREGUNTAS EDITABLES)
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


@client.event
async def on_member_join(member):
    if member.bot and config_global["antibots_activo"]:
        try:
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    invitador = entry.user
                    await member.guild.ban(member, reason="Anti-Bots: Bot no autorizado")
                    if invitador and not invitador.guild_permissions.administrator:
                        await member.guild.ban(invitador, reason="Anti-Bots: Invitó un bot no autorizado")
                    
                    embed_log = discord.Embed(title="🤖 Anti-Bots Activado", description=f"Bot no autorizado {member.mention} baneado.\nInvitador: {invitador.mention if invitador else 'Desconocido'}", color=discord.Color.red())
                    await registrar_log_sancion(member.guild, embed_log)
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
# ⚙️️ /CONFI-GENERAL EN EMBED INTERACTIVO
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

    @discord.ui.button(label="🛡️️ Canal Sanciones", style=discord.ButtonStyle.primary, row=1)
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

    @discord.ui.button(label="📋 Canal Postulaciones (Logs)", style=discord.ButtonStyle.success, row=1)
    async def set_canallogs(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Configurar Canal Logs Postulaciones"):
            v = discord.ui.TextInput(label="ID del Canal", default=str(config_global["canal_logs_id"] or ""), max_length=20)
            async def on_submit(self, i: discord.Interaction):
                config_global["canal_logs_id"] = int(self.v.value.strip()) if self.v.value.strip() else None
                await i.response.send_message(f"✅ Canal de postulaciones actualizado.", ephemeral=True)
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
    embed.add_field(name="📋 Canal Postulaciones", value=f"<#{config_global['canal_logs_id']}>" if config_global['canal_logs_id'] else "No configurado", inline=True)

    await interaction.response.send_message(embed=embed, view=VistaBotonConfigGeneral(), ephemeral=True)


# ==========================================
# 📋 SISTEMA DE POSTULACIONES CON PREGUNTAS EDITABLES Y MD
# ==========================================

class ModalEditarPreguntasPostulacion(discord.ui.Modal):
    def __init__(self, post_key, cfg):
        super().__init__(title=f"Editar Preguntas: {cfg['titulo']}")
        self.post_key = post_key
        self.cfg = cfg

        self.preguntas_input = discord.ui.TextInput(
            label="Preguntas (Una por línea)",
            style=discord.TextStyle.paragraph,
            default="\n".join(cfg["preguntas"]),
            max_length=2000
        )
        self.add_item(self.preguntas_input)

    async def on_submit(self, interaction: discord.Interaction):
        nuevas_preguntas = [p.strip() for p in self.preguntas_input.value.split("\n") if p.strip()]
        if nuevas_preguntas:
            postulaciones_config[self.post_key]["preguntas"] = nuevas_preguntas
            await interaction.response.send_message(f"✅ ¡Preguntas de **{self.cfg['titulo']}** actualizadas correctamente!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Debes incluir al menos una pregunta válida.", ephemeral=True)


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
            
            destino = interaction.guild.get_channel(config_global["canal_logs_id"]) if config_global["canal_logs_id"] else interaction.channel
            if destino: 
                await destino.send(embed=embed_final)
            
            await self.miembro_postulado.send("🎉 ¡Postulación completada y enviada al staff con éxito!")
        except Exception as e:
            try:
                await self.miembro_postulado.send("❌ La postulación ha expirado o ha ocurrido un error.")
            except: pass


@client.tree.command(name="postulacion", description="Envía un panel de postulación y permite editar sus preguntas")
async def postulacion(interaction: discord.Interaction, miembro: discord.Member):
    if not interaction.user.guild_permissions.administrator and not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ No tienes permisos para gestionar postulaciones.", ephemeral=True)

    v = discord.ui.View(timeout=60)
    s = discord.ui.Select(
        placeholder="Selecciona el formulario de postulación...", 
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
        
        class VistaMenuPostulacionOpciones(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)

            @discord.ui.button(label="🚀 Enviar Formulario al Usuario", style=discord.ButtonStyle.success)
            async def btn_enviar(self, i2: discord.Interaction, btn: discord.ui.Button):
                config_global["contador_postulaciones"] += 1
                num_id = config_global["contador_postulaciones"]
                embed_panel = discord.Embed(
                    title=cfg['titulo'],
                    description=f"Candidato: {miembro.mention}\nHaz clic en el botón inferior para responder las preguntas en tus **Mensajes Privados (MD)**.",
                    color=cfg['color']
                )
                await i2.channel.send(embed=embed_panel, view=VistaComenzarPostulacion(tipo_sel, num_id, cfg["preguntas"], miembro, cfg))
                await i2.response.edit_message(content=f"✅ Formulario enviado a {miembro.mention}.", embed=None, view=None)

            @discord.ui.button(label="✏️ Editar Preguntas del Formulario", style=discord.ButtonStyle.primary)
            async def btn_editar(self, i2: discord.Interaction, btn: discord.ui.Button):
                await i2.response.send_modal(ModalEditarPreguntasPostulacion(tipo_sel, cfg))

        preguntas_actuales = "\n".join([f"• {p}" for p in cfg["preguntas"]])
        embed_config = discord.Embed(
            title=f"⚙️ Gestión: {cfg['titulo']}",
            description=f"**Preguntas configuradas actualmente:**\n{preguntas_actuales}\n\nElige una opción:",
            color=cfg['color']
        )
        await i.response.edit_message(content=None, embed=embed_config, view=VistaMenuPostulacionOpciones())

    s.callback = cb
    v.add_item(s)
    await interaction.response.send_message(embed=discord.Embed(title="📋 Menú de Postulaciones", description=f"Selecciona el formulario para {miembro.mention}:"), view=v, ephemeral=True)


# ==========================================
# 📅 SISTEMA DE EVENTOS Y /INICIAR-EVENTO
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
            description=embed_viejo.description.split("\n\n👑")[0],
            color=embed_viejo.color
        )
        embed_nuevo.add_field(name="👑 Organizadores", value=datos["organizadores"], inline=False)
        embed_nuevo.add_field(name="⏰ Inicio", value=datos["tiempo"], inline=True)
        embed_nuevo.add_field(name="🏆 Ganadores", value=datos["ganadores"], inline=True)
        embed_nuevo.add_field(name=f"👥 Participantes ({len(participantes)})", value=lista_nombres_str, inline=False)
        
        if embed_viejo.image.url:
            embed_nuevo.set_image(url=embed_viejo.image.url)

        await interaction.message.edit(embed=embed_nuevo)
        await interaction.response.send_message(estado_msj, ephemeral=True)


@client.tree.command(name="organizar-evento", description="Organiza un evento con múltiples organizadores y tiempo real")
@app_commands.describe(
    nombre="Nombre del evento", 
    canal="Canal donde se publicará", 
    texto="Descripción del evento", 
    organizadores="Nombres de los organizadores (ej: @Mod1, @Mod2)",
    tiempo="¿Cuándo empieza? (ej: Mañana a las 5 PM)",
    ganadores="Número de ganadores (ej: 3 ganadores)",
    mencion="Rol a pingo avisar (ej: @everyone)"
)
async def organizar_evento(interaction: discord.Interaction, nombre: str, canal: discord.TextChannel, texto: str, organizadores: str, tiempo: str, ganadores: str, mencion: str = ""):
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
    embed.add_field(name="⚙ Módulos Activos", value="• `/confi-general` • `/postulacion`\n• `/organizar-evento` • `/iniciar-evento` • `/lista-eventos`\n• `/juegos` • `/dado` • `/trivia`", inline=False)
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