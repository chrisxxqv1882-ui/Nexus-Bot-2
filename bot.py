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
    "rol_atencion_id": None,   
    "rol_organizar_eventos_id": None, 
    "rol_aprobar_sugerencias_id": None, 
    "canal_logs_id": None,     
    "canal_sanciones_id": None, 
    "canal_tickets_id": None,  
    "canal_sugerencias_id": None, 
    "contador_postulaciones": 0, 
    "antispam_activo": True,
    "antispam_limite_mensajes": 5,
    "antispam_ventana_segundos": 5,
    "antispam_timeout_segundos": 60,
    "antibots_activo": True,
    # Configuración del panel de tickets principal
    "ticket_titulo": "🎟️ Sistema de Soporte y Tickets",
    "ticket_desc": "Haz clic en el botón inferior para abrir un ticket privado con el staff.",
    "ticket_color": 0x5865F2,
    "ticket_boton_texto": "🎫 Abrir Ticket",
    "ticket_imagen": "", 
    # Configuración del embed de bienvenida dentro del ticket
    "ticket_bienvenida_titulo": "🎫 Ticket de Soporte Abierto",
    "ticket_bienvenida_desc": "Hola $(user.mention), el staff te atenderá pronto.\nExplica tu duda detalladamente.",
    "ticket_bienvenida_color": 0x2ECC71,
    "ticket_bienvenida_imagen": "", 
    "embed_juegos_titulo": "🎮 Zona de Juegos e Interacción",
    "embed_juegos_desc": "¡Diviértete con los minijuegos multijugador y nuestra trivia masiva estilo Nekotrivia!",
    "embed_juegos_color": 0xF1C40F
}

registro_antispam = defaultdict(list)
base_datos_sanciones = defaultdict(list)
eventos_activos = {} 

postulaciones_config = {
    "staff": {
        "titulo": "📝 Postulación: Cuerpo de Moderación",
        "color": 0x3498DB,
        "preguntas": ["¿Cuál es tu edad?", "¿Por qué quieres ser Moderador?", "¿Tienes experiencia previa?"]
    },
    "ally": {
        "titulo": "📝 Postulación: Casa Alianza",
        "color": 0x2ECC71,
        "preguntas": ["¿Cuál es tu servidor?", "¿Cuántos miembros activos tienes?", "¿Cuál es la invitación?"]
    },
    "redes": {
        "titulo": "📝 Postulación: Cuerpo de Redes",
        "color": 0x9B59B6,
        "preguntas": ["¿Qué plataformas manejas?", "¿Tienes ejemplos de ediciones o publicaciones?"]
    },
    "nexus": {
        "titulo": "📝 Postulación: Cuerpo de Programación",
        "color": 0xE74C3C,
        "preguntas": ["¿Qué lenguajes de programación conoces?", "¿Cuánto tiempo llevas programando?"]
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
# ⚙️ /CONFI-GENERAL EN EMBED INTERACTIVO (SIN FORMULARIOS MOLESTOS)
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


@client.tree.command(name="confi-general", description="Panel visual en Embed para configurar roles y canales")
async def confi_general(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)

    embed = discord.Embed(
        title="⚙️ Panel de Configuración General",
        description="Haz clic en los botones inferiores para editar cada parámetro individualmente de forma visual:",
        color=0x3498DB
    )
    embed.add_field(name="📌 Prefijo actual", value=f"`{config_global['prefijo']}`", inline=True)
    embed.add_field(name="👑 Rol Organizar Eventos", value=f"<@&{config_global['rol_organizar_eventos_id']}>" if config_global['rol_organizar_eventos_id'] else "No configurado", inline=True)
    embed.add_field(name="💡 Rol Aprobar Sugerencias", value=f"<@&{config_global['rol_aprobar_sugerencias_id']}>" if config_global['rol_aprobar_sugerencias_id'] else "No configurado", inline=True)
    embed.add_field(name="🛡️ Canal Sanciones", value=f"<#{config_global['canal_sanciones_id']}>" if config_global['canal_sanciones_id'] else "No configurado", inline=True)
    embed.add_field(name="📢 Canal Sugerencias", value=f"<#{config_global['canal_sugerencias_id']}>" if config_global['canal_sugerencias_id'] else "No configurado", inline=True)

    await interaction.response.send_message(embed=embed, view=VistaBotonConfigGeneral(), ephemeral=True)


# ==========================================
# 🎫 /CONFIGURACION (EMBED PRINCIPAL DE TICKETS EDITABLE EN TIEMPO REAL)
# ==========================================

class VistaEditorEmbedTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="✏️️ Título", style=discord.ButtonStyle.secondary, row=0)
    async def ed_titulo(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Editar Título del Ticket"):
            v = discord.ui.TextInput(label="Título", default=config_global["ticket_titulo"], max_length=100)
            async def on_submit(self, i: discord.Interaction):
                config_global["ticket_titulo"] = self.v.value.strip()
                await i.response.send_message("✅ Título actualizado.", ephemeral=True)
        await interaction.response.send_modal(M())

    @discord.ui.button(label="📄 Descripción", style=discord.ButtonStyle.secondary, row=0)
    async def ed_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Editar Descripción"):
            v = discord.ui.TextInput(label="Descripción", style=discord.TextStyle.paragraph, default=config_global["ticket_desc"], max_length=1000)
            async def on_submit(self, i: discord.Interaction):
                config_global["ticket_desc"] = self.v.value.strip()
                await i.response.send_message("✅ Descripción actualizada.", ephemeral=True)
        await interaction.response.send_modal(M())

    @discord.ui.button(label="🎨 Color Hex", style=discord.ButtonStyle.secondary, row=0)
    async def ed_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Editar Color Hex"):
            v = discord.ui.TextInput(label="Color (ej: #5865F2)", default=f"#{config_global['ticket_color']:06x}", max_length=7)
            async def on_submit(self, i: discord.Interaction):
                try: config_global["ticket_color"] = int(self.v.value.strip().replace("#", ""), 16)
                except: return await i.response.send_message("❌ Color inválido.", ephemeral=True)
                await i.response.send_message("✅ Color actualizado.", ephemeral=True)
        await interaction.response.send_modal(M())

    @discord.ui.button(label="🖼️ Imagen / Banner", style=discord.ButtonStyle.primary, row=1)
    async def ed_img(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Editar URL de Imagen"):
            v = discord.ui.TextInput(label="URL de la imagen", default=config_global["ticket_imagen"], required=False, max_length=500)
            async def on_submit(self, i: discord.Interaction):
                config_global["ticket_imagen"] = self.v.value.strip()
                await i.response.send_message("✅ Imagen actualizada.", ephemeral=True)
        await interaction.response.send_modal(M())

    @discord.ui.button(label="🔘 Texto Botón", style=discord.ButtonStyle.secondary, row=1)
    async def ed_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        class M(discord.ui.Modal, title="Editar Botón"):
            v = discord.ui.TextInput(label="Texto del botón", default=config_global["ticket_boton_texto"], max_length=80)
            async def on_submit(self, i: discord.Interaction):
                config_global["ticket_boton_texto"] = self.v.value.strip()
                await i.response.send_message("✅ Botón actualizado.", ephemeral=True)
        await interaction.response.send_modal(M())


@client.tree.command(name="configuracion", description="Visualiza y edita en vivo el Embed principal de Tickets")
async def configuracion(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)

    embed_preview = discord.Embed(
        title=config_global["ticket_titulo"],
        description=config_global["ticket_desc"],
        color=config_global["ticket_color"]
    )
    if config_global["ticket_imagen"]:
        embed_preview.set_image(url=config_global["ticket_imagen"])
    embed_preview.set_footer(text="Vista previa en tiempo real del Panel de Tickets")

    await interaction.response.send_message(embed=embed_preview, view=VistaEditorEmbedTicket(), ephemeral=True)


# ==========================================
# 🎫 SISTEMA DE TICKETS (CON RECLAMACIÓN)
# ==========================================

class VistaTicketActivo(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="🙋‍♂️ Reclamar Ticket", style=discord.ButtonStyle.primary, custom_id="btn_reclamar_ticket_rt")
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        rol_staff_id = config_global["rol_atencion_id"]
        es_staff = interaction.user.guild_permissions.administrator
        if not es_staff and rol_staff_id:
            rol = interaction.guild.get_role(rol_staff_id)
            if rol and rol in interaction.user.roles: es_staff = True

        if not es_staff: return await interaction.response.send_message("❌ No tienes permisos de staff.", ephemeral=True)
        
        button.disabled = True
        button.label = f"Reclamado por {interaction.user.display_name}"
        button.style = discord.ButtonStyle.secondary
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"🙋‍♂️ {interaction.user.mention} ha reclamado este ticket.")

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="btn_cerrar_ticket_rt")
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Cerrando canal en 5 segundos...", ephemeral=False)
        await asyncio.sleep(5)
        try: await interaction.channel.delete()
        except: pass


class VistaCrearTicket(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label=config_global["ticket_boton_texto"], style=discord.ButtonStyle.success, custom_id="btn_abrir_ticket_rt")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        cat = discord.utils.get(guild.categories, name="Tickets")
        if not cat: 
            try: cat = await guild.create_category("Tickets")
            except: cat = None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        if config_global["rol_atencion_id"]:
            r = guild.get_role(config_global["rol_atencion_id"])
            if r: overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        canal = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=cat, overwrites=overwrites)
        desc = config_global["ticket_bienvenida_desc"].replace("$(user.mention)", interaction.user.mention).replace("$(user.name)", interaction.user.name).replace("$(guild.name)", guild.name)
        embed = discord.Embed(title=config_global["ticket_bienvenida_titulo"], description=desc, color=config_global["ticket_bienvenida_color"])
        if config_global["ticket_bienvenida_imagen"]: embed.set_image(url=config_global["ticket_bienvenida_imagen"])
        
        await canal.send(embed=embed, view=VistaTicketActivo())
        await interaction.response.send_message(f"✅ ¡Ticket creado en {canal.mention}!", ephemeral=True)


@client.tree.command(name="ticket", description="Envía el panel de tickets")
async def ticket(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
    embed = discord.Embed(title=config_global["ticket_titulo"], description=config_global["ticket_desc"], color=config_global["ticket_color"])
    if config_global["ticket_imagen"]: embed.set_image(url=config_global["ticket_imagen"])
    
    destino = interaction.guild.get_channel(config_global["canal_tickets_id"]) if config_global["canal_tickets_id"] else interaction.channel
    await destino.send(embed=embed, view=VistaCrearTicket())
    await interaction.response.send_message(f"✅ Panel enviado a {destino.mention}.", ephemeral=True)


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
# 📋 POSTULACIONES Y MODERACIÓN (CON UNBAN)
# ==========================================

@client.tree.command(name="ban", description="Banea a un miembro")
async def ban(interaction: discord.Interaction, miembro: discord.Member, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.ban_members: return await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
    await miembro.ban(reason=razon)
    base_datos_sanciones[miembro.id].append(f"🔨 Ban - {razon}")
    await interaction.response.send_message(f"🔨 {miembro.mention} baneado.")


@client.tree.command(name="unban", description="Desbanea a un usuario")
async def unban(interaction: discord.Interaction, usuario_id: str, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.ban_members: return await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
    async for entry in interaction.guild.bans():
        if str(entry.user.id) == usuario_id.strip() or entry.user.name.lower() == usuario_id.strip().lower():
            await interaction.guild.unban(entry.user, reason=razon)
            return await interaction.response.send_message(f"🔓 Desbaneado **{entry.user}**.")
    await interaction.response.send_message("❌ No encontrado.", ephemeral=True)


@client.tree.command(name="kick", description="Expulsa a un miembro")
async def kick(interaction: discord.Interaction, miembro: discord.Member, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.kick_members: return await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
    await miembro.kick(reason=razon)
    base_datos_sanciones[miembro.id].append(f"👢 Kick - {razon}")
    await interaction.response.send_message(f"👢 {miembro.mention} expulsado.")


@client.tree.command(name="mute", description="Silencia a un miembro")
async def mute(interaction: discord.Interaction, miembro: discord.Member, segundos: int, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.moderate_members: return await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
    await miembro.timeout(discord.utils.utcnow() + discord.Timedelta(seconds=segundos), reason=razon)
    base_datos_sanciones[miembro.id].append(f"🔇 Mute ({segundos}s) - {razon}")
    await interaction.response.send_message(f"🔇 {miembro.mention} silenciado.")


@client.tree.command(name="unmute", description="Quita el mute")
async def unmute(interaction: discord.Interaction, miembro: discord.Member):
    if not interaction.user.guild_permissions.moderate_members: return await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
    await miembro.timeout(None)
    await interaction.response.send_message(f"🔊 {miembro.mention} desmuteado.")


@client.tree.command(name="warn", description="Advierte a un miembro")
async def warn(interaction: discord.Interaction, miembro: discord.Member, razon: str):
    if not interaction.user.guild_permissions.moderate_members: return await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
    base_datos_sanciones[miembro.id].append(f"⚠ Warn - {razon}")
    try: await miembro.send(embed=discord.Embed(title="⚠ Advertencia", description=razon, color=0xF1C40F))
    except: pass
    await interaction.response.send_message(f"⚠️ {miembro.mention} advertido.")


@client.tree.command(name="historial", description="Muestra sanciones")
async def historial(interaction: discord.Interaction, miembro: discord.Member):
    s = base_datos_sanciones.get(miembro.id, [])
    if not s: return await interaction.response.send_message(f"🛡 {miembro.mention} limpio.", ephemeral=True)
    await interaction.response.send_message(embed=discord.Embed(title=f"📜 Sanciones: {miembro.display_name}", description="\n".join([f"• {x}" for x in s]), color=0xE74C3C), ephemeral=True)


@client.tree.command(name="help", description="Centro de ayuda")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="✨ Centro de Ayuda", description=f"Prefijo: `{config_global['prefijo']}`", color=0x5865F2)
    embed.add_field(name="⚙ Módulos Completos", value="• `/configuracion` • `/confi-general` • `/variables` • `/antibots`\n• `/organizar-evento` • `/iniciar-evento` • `/lista-eventos`\n• `/ticket` • `/ban` • `/unban` • `/historial` • `/trivia`", inline=False)
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