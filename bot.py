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
    "rol_atencion_id": None,   # Rol autorizado para atender tickets y postulaciones
    "canal_logs_id": None,     
    "canal_sanciones_id": None, 
    "canal_tickets_id": None,  
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
base_datos_sanciones = defaultdict(list) # usuario_id -> lista de sanciones
eventos_activos = {} # ID del mensaje del evento -> dict con datos y participantes

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
    },
    {
        "p": "¿Cuál es el nombre de la libreta mortal en Death Note?",
        "correcta": "Death Note",
        "opciones": ["Life Note", "Death Note", "Dark Book", "Shinigami Note"],
        "cat": "Anime",
        "img": "https://media.giphy.com/media/HjfiEczPb2y6s/giphy.gif"
    }
]

for i in range(30):
    BANCO_TRIVIA.append({
        "p": "Cultura General: ¿Este concepto es ampliamente reconocido a nivel mundial?",
        "correcta": "Sí",
        "opciones": ["Sí", "No", "Falso", "Dudoso"],
        "cat": "Historia",
        "img": "https://media.giphy.com/media/3o7TKSjRrfIPjeiDiM/giphy.gif"
    })


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


# --- FUNCIÓN AUXILIAR PARA LOGS DE SANCIONES ---
async def registrar_log_sancion(guild: discord.Guild, embed: discord.Embed):
    canal_id = config_global["canal_sanciones_id"]
    if canal_id:
        canal = guild.get_channel(canal_id)
        if canal:
            try: await canal.send(embed=embed)
            except: pass


# --- SISTEMA ANTI-BOTS AUTOMÁTICO ---
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


@client.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # --- FILTRO ANTI-SPAM CON TIMEOUT ---
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
                base_datos_sanciones[autor_id].append(f"🔇 **Timeout automático por Spam** ({duracion_timeout}s)")
                
                embed_log = discord.Embed(title="🔇 Timeout Automático (Anti-Spam)", description=f"**Usuario:** {message.author.mention}\n**Duración:** {duracion_timeout}s", color=discord.Color.orange())
                await registrar_log_sancion(message.guild, embed_log)

                warning = await message.channel.send(f"⚠️ {message.author.mention} ha recibido un **Timeout de {duracion_timeout} segundos** por spam.")
                await asyncio.sleep(5)
                await warning.delete()
            except Exception as e:
                print(f"Error al aplicar timeout: {e}")
            return


# ==========================================
# 🎨 EDITOR VISUAL CON SOPORTE DE IMAGEN
# ==========================================

class ModalEditarPanelTicket(discord.ui.Modal, title="Editar Panel Principal de Tickets"):
    titulo = discord.ui.TextInput(label="Título del Embed", default=config_global["ticket_titulo"], required=True, max_length=100)
    color = discord.ui.TextInput(label="Color Hex (ej: #5865F2)", default=f"#{config_global['ticket_color']:06x}", required=True, max_length=7)
    boton = discord.ui.TextInput(label="Texto del Botón", default=config_global["ticket_boton_texto"], required=True, max_length=80)
    imagen = discord.ui.TextInput(label="URL de la Imagen / Banner (Opcional)", default=config_global["ticket_imagen"], required=False, max_length=500)
    descripcion = discord.ui.TextInput(label="Descripción del Embed", style=discord.TextStyle.paragraph, default=config_global["ticket_desc"], required=True, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        try: nuevo_color = int(self.color.value.strip().replace("#", ""), 16)
        except: return await interaction.response.send_message("❌ Color Hex inválido.", ephemeral=True)

        config_global["ticket_titulo"] = self.titulo.value.strip()
        config_global["ticket_color"] = nuevo_color
        config_global["ticket_boton_texto"] = self.boton.value.strip()
        config_global["ticket_imagen"] = self.imagen.value.strip()
        config_global["ticket_desc"] = self.descripcion.value.strip()

        await interaction.response.send_message("✅ ¡Panel de tickets actualizado con éxito!", ephemeral=True)


class ModalEditarBienvenidaTicket(discord.ui.Modal, title="Editar Embed de Bienvenida (Ticket)"):
    titulo = discord.ui.TextInput(label="Título del Embed", default=config_global["ticket_bienvenida_titulo"], required=True, max_length=100)
    color = discord.ui.TextInput(label="Color Hex (ej: #2ECC71)", default=f"#{config_global['ticket_bienvenida_color']:06x}", required=True, max_length=7)
    imagen = discord.ui.TextInput(label="URL de la Imagen / Banner (Opcional)", default=config_global["ticket_bienvenida_imagen"], required=False, max_length=500)
    descripcion = discord.ui.TextInput(label="Descripción (Usa $(user.mention))", style=discord.TextStyle.paragraph, default=config_global["ticket_bienvenida_desc"], required=True, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        try: nuevo_color = int(self.color.value.strip().replace("#", ""), 16)
        except: return await interaction.response.send_message("❌ Color Hex inválido.", ephemeral=True)

        config_global["ticket_bienvenida_titulo"] = self.titulo.value.strip()
        config_global["ticket_bienvenida_color"] = nuevo_color
        config_global["ticket_bienvenida_imagen"] = self.imagen.value.strip()
        config_global["ticket_bienvenida_desc"] = self.descripcion.value.strip()

        await interaction.response.send_message("✅ ¡Mensaje de bienvenida actualizado correctamente!", ephemeral=True)


class ModalConfigGeneral(discord.ui.Modal, title="Configuración General y Roles"):
    input_prefijo = discord.ui.TextInput(label="Prefijo del Bot", default=config_global["prefijo"], required=True, max_length=5)
    rol_cmd_id = discord.ui.TextInput(label="ID Rol Ejecutar Postulación", default=str(config_global["rol_comandos_id"] or ""), required=False, max_length=20)
    rol_atc_id = discord.ui.TextInput(label="ID Rol Staff (Atender Tickets)", default=str(config_global["rol_atencion_id"] or ""), required=False, max_length=20)
    canal_log_id = discord.ui.TextInput(label="ID Canal Respuestas Postulaciones", default=str(config_global["canal_logs_id"] or ""), required=False, max_length=20)
    canal_sanciones_id = discord.ui.TextInput(label="ID Canal Logs de Sanciones", default=str(config_global["canal_sanciones_id"] or ""), required=False, max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            config_global["prefijo"] = self.input_prefijo.value.strip()
            config_global["rol_comandos_id"] = int(self.rol_cmd_id.value.strip()) if self.rol_cmd_id.value.strip() else None
            config_global["rol_atencion_id"] = int(self.rol_atc_id.value.strip()) if self.rol_atc_id.value.strip() else None
            config_global["canal_logs_id"] = int(self.canal_log_id.value.strip()) if self.canal_log_id.value.strip() else None
            config_global["canal_sanciones_id"] = int(self.canal_sanciones_id.value.strip()) if self.canal_sanciones_id.value.strip() else None

            await interaction.response.send_message("✅ ¡Configuración general guardada con éxito!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Error: Asegúrate de ingresar IDs numéricos válidos.", ephemeral=True)


class VistaEditorVisualTickets(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="✏️ Editar Panel Principal", style=discord.ButtonStyle.primary, row=0)
    async def btn_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarPanelTicket())

    @discord.ui.button(label="💬 Editar Bienvenida", style=discord.ButtonStyle.success, row=0)
    async def btn_bienvenida(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarBienvenidaTicket())


class SelectorConfiguracion(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Editor Visual de Tickets (Panel y Bienvenida)", description="Modifica títulos, colores e imágenes", emoji="🎨", value="editor_tickets"),
            discord.SelectOption(label="Configurar Canal del Panel", description="Define el ID del canal del panel de tickets", emoji="📢", value="canal_panel")
        ]
        super().__init__(placeholder="Elige una opción...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)

        if val == "editor_tickets":
            await interaction.response.send_message(embed=discord.Embed(title="✨ Editor Visual de Tickets", description="Usa los botones inferiores:", color=0x5865F2), view=VistaEditorVisualTickets(), ephemeral=True)
        elif val == "canal_panel":
            class ModalCanalPanel(discord.ui.Modal, title="Canal del Panel"):
                c_id = discord.ui.TextInput(label="ID del Canal", default=str(config_global["canal_tickets_id"] or ""), required=True, max_length=20)
                async def on_submit(self, i2: discord.Interaction):
                    config_global["canal_tickets_id"] = int(self.c_id.value.strip())
                    await i2.response.send_message(f"✅ Canal configurado a <#{config_global['canal_tickets_id']}>", ephemeral=True)
            await interaction.response.send_modal(ModalCanalPanel())


class VistaMenuConfiguracion(discord.ui.View):
    def __init__(self): super().__init__(timeout=60); self.add_item(SelectorConfiguracion())


@client.tree.command(name="configuracion", description="Panel visual interactivo para tickets")
async def configuracion(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
    await interaction.response.send_message(embed=discord.Embed(title="⚙️ Panel de Configuración", description="Selecciona:", color=0x3498db), view=VistaMenuConfiguracion(), ephemeral=True)


@client.tree.command(name="confi-general", description="Configura prefijo, roles y canales de logs")
async def confi_general(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
    await interaction.response.send_modal(ModalConfigGeneral())


@client.tree.command(name="variables", description="Muestra la lista de variables disponibles")
async def variables(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Variables Disponibles", description="• `$(user.mention)`\n• `$(user.name)`\n• `$(guild.name)`", color=0xF1C40F)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.tree.command(name="antibots", description="Activa o desactiva Anti-Bots")
@app_commands.choices(estado=[app_commands.Choice(name="Activado", value="on"), app_commands.Choice(name="Desactivado", value="off")])
async def antibots(interaction: discord.Interaction, estado: str):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
    config_global["antibots_activo"] = (estado == "on")
    await interaction.response.send_message(f"🛡️ Anti-Bots **{'activado' if config_global['antibots_activo'] else 'desactivado'}**.", ephemeral=True)


# ==========================================
# 📅 SISTEMA DE EVENTOS TIEMPO REAL (PÚBLICO)
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
    if not interaction.user.guild_permissions.manage_events and not interaction.user.guild_permissions.administrator:
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

    await interaction.response.send_message(f"✅ ¡Evento **{nombre}** creado y publicado correctamente en {canal.mention}!", ephemeral=True)


@client.tree.command(name="lista-eventos", description="Muestra todos los eventos activos y sus participantes")
async def lista_eventos(interaction: discord.Interaction):
    if not eventos_activos:
        return await interaction.response.send_message("🛡️ No hay eventos activos en este momento.", ephemeral=True)

    embed = discord.Embed(title="📊 Lista General de Eventos Activos", color=0x9B59B6)
    guild = interaction.guild

    for msg_id, datos in eventos_activos.items():
        canal = guild.get_channel(datos["canal_id"])
        nombres = [guild.get_member(uid).display_name for uid in datos["participantes"] if guild.get_member(uid)]
        lista_str = ", ".join(nombres) if nombres else "Nadie apuntado"
        
        embed.add_field(
            name=f"📌 {datos['nombre']} ({canal.mention if canal else 'Canal'})",
            value=f"**Organizadores:** {datos['organizadores']}\n**Inicio:** {datos['tiempo']} | **Ganadores:** {datos['ganadores']}\n**Participantes ({len(datos['participantes'])}):** {lista_str}",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)


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
# 📋 POSTULACIONES PÚBLICAS
# ==========================================

class VistaComenzarPostulacion(discord.ui.View):
    def __init__(self, tipo, num_id, preguntas, miembro_postulado, config_form):
        super().__init__(timeout=None)
        self.tipo, self.num_id, self.preguntas, self.miembro_postulado, self.config_form = tipo, num_id, preguntas, miembro_postulado, config_form

    @discord.ui.button(label="🚀 Comenzar Postulación", style=discord.ButtonStyle.success)
    async def comenzar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.miembro_postulado.id: return await interaction.response.send_message("❌ No es tu formulario.", ephemeral=True)
        await interaction.response.send_message("📬 ¡Cuestionario abierto en tus **Mensajes Privados (MD)**!", ephemeral=True)
        try:
            respuestas = []
            for i, preg in enumerate(self.preguntas):
                await self.miembro_postulado.send(embed=discord.Embed(title=f"Pregunta {i+1}", description=preg, color=self.config_form['color']))
                msg = await client.wait_for('message', timeout=90.0, check=lambda m: m.author.id == self.miembro_postulado.id and isinstance(m.channel, discord.DMChannel))
                respuestas.append((preg, msg.content))
            
            txt = "".join([f"**{p}**\n↳ {r}\n\n" for p, r in respuestas])
            embed_final = discord.Embed(title=f"{self.config_form['titulo']} (#{self.num_id})", description=f"👤 **Candidato:** {self.miembro_postulado.mention}\n\n{txt}", color=self.config_form['color'])
            
            destino = interaction.guild.get_channel(config_global["canal_logs_id"]) if config_global["canal_logs_id"] else interaction.channel
            if destino: await destino.send(embed=embed_final)
            await self.miembro_postulado.send("🎉 ¡Postulación completada!")
        except: pass


@client.tree.command(name="postulacion", description="Inicia un panel de postulación")
async def postulacion(interaction: discord.Interaction, miembro: discord.Member):
    v = discord.ui.View(timeout=30)
    s = discord.ui.Select(placeholder="Elige postulación...", options=[discord.SelectOption(label="Staff", value="staff"), discord.SelectOption(label="Casa Alianza", value="ally"), discord.SelectOption(label="Redes", value="redes"), discord.SelectOption(label="Nexus", value="nexus")])
    async def cb(i):
        cfg = postulaciones_config.get(s.values[0], {})
        config_global["contador_postulaciones"] += 1
        await i.channel.send(embed=discord.Embed(title=cfg['titulo'], description=f"Candidato: {miembro.mention}", color=cfg['color']), view=VistaComenzarPostulacion(s.values[0], config_global["contador_postulaciones"], cfg["preguntas"], miembro, cfg))
        await i.response.edit_message(content="✅ Creado.", embed=None, view=None)
    s.callback = cb
    v.add_item(s)
    await interaction.response.send_message(embed=discord.Embed(title="📋 Postulaciones", description=f"Para {miembro.display_name}:"), view=v, ephemeral=True)


# ==========================================
# 🛡️ SANCIONES Y MODERACIÓN (CON UNBAN)
# ==========================================

@client.tree.command(name="ban", description="Banea a un miembro")
async def ban(interaction: discord.Interaction, miembro: discord.Member, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.ban_members: return await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
    await miembro.ban(reason=razon)
    base_datos_sanciones[miembro.id].append(f"🔨 Ban - {razon}")
    await interaction.response.send_message(f"🔨 {miembro.mention} baneado.")


@client.tree.command(name="unban", description="Desbanea a un usuario por ID o Nombre")
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


@client.tree.command(name="historial", description="Muestra sanciones de un usuario")
async def historial(interaction: discord.Interaction, miembro: discord.Member):
    s = base_datos_sanciones.get(miembro.id, [])
    if not s: return await interaction.response.send_message(f"🛡 {miembro.mention} limpio.", ephemeral=True)
    await interaction.response.send_message(embed=discord.Embed(title=f"📜 Sanciones: {miembro.display_name}", description="\n".join([f"• {x}" for x in s]), color=0xE74C3C), ephemeral=True)


# ==========================================
# 🎮 JUEGOS Y AYUDA
# ==========================================

@client.tree.command(name="help", description="Centro de ayuda")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="✨ Centro de Ayuda", description=f"Prefijo: `{config_global['prefijo']}`", color=0x5865F2)
    embed.add_field(name="⚙ Módulos Completos", value="• `/configuracion` • `/confi-general` • `/variables` • `/antibots`\n• `/organizar-evento` • `/lista-eventos` • `/ticket` • `/postulacion`\n• `/ban` • `/unban` • `/historial` • `/trivia`", inline=False)
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