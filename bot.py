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
    # Configuración del embed de bienvenida dentro del ticket
    "ticket_bienvenida_titulo": "🎫 Ticket de Soporte Abierto",
    "ticket_bienvenida_desc": "Hola $(user.mention), el staff te atenderá pronto.\nExplica tu duda detalladamente.",
    "ticket_bienvenida_color": 0x2ECC71,
    "embed_juegos_titulo": "🎮 Zona de Juegos e Interacción",
    "embed_juegos_desc": "¡Diviértete con los minijuegos multijugador y nuestra trivia masiva estilo Nekotrivia!",
    "embed_juegos_color": 0xF1C40F
}

registro_antispam = defaultdict(list)
base_datos_sanciones = defaultdict(list)

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
    },
    {
        "p": "¿En Naruto, cuál es el gran sueño de Naruto Uzumaki?",
        "correcta": "Hokage",
        "opciones": ["Kazekage", "Hokage", "Hokage Oscuro", "Sannin"],
        "cat": "Anime",
        "img": "https://media.giphy.com/media/Kzb1zItSqUf0g/giphy.gif"
    },
    {
        "p": "¿Cómo se llama el titán principal de Eren Jaeger en Shingeki no Kyojin?",
        "correcta": "Titán de Ataque",
        "opciones": ["Titán Colosal", "Titán Blindado", "Titán de Ataque", "Titán Bestia"],
        "cat": "Media",
        "img": "https://media.giphy.com/media/v0ok8uhZvw3yE/giphy.gif"
    }
]

for i in range(50):
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
                    
                    canal_id = config_global["canal_sanciones_id"]
                    if canal_id:
                        c = member.guild.get_channel(canal_id)
                        if c:
                            embed_log = discord.Embed(title="🤖 Anti-Bots Activado", description=f"Bot no autorizado {member.mention} fue baneado.\nInvitador: {invitador.mention if invitador else 'Desconocido'}", color=discord.Color.red())
                            await c.send(embed=embed_log)
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
                
                canal_id = config_global["canal_sanciones_id"]
                if canal_id:
                    c = message.guild.get_channel(canal_id)
                    if c:
                        await c.send(embed=discord.Embed(title="🔇 Timeout Automático", description=f"**Usuario:** {message.author.mention}\n**Duración:** {duracion_timeout}s", color=discord.Color.orange()))

                warning = await message.channel.send(f"⚠️ {message.author.mention} ha recibido un **Timeout de {duracion_timeout} segundos** por spam.")
                await asyncio.sleep(5)
                await warning.delete()
            except Exception as e:
                print(f"Error al aplicar timeout: {e}")
            return


# ==========================================
# 🎨 EDITOR VISUAL ESTILO LUMINOUS (TICKETS Y BIENVENIDA)
# ==========================================

class ModalEditarPanelTicket(discord.ui.Modal, title="Editar Panel Principal de Tickets"):
    titulo = discord.ui.TextInput(label="Título del Embed", default=config_global["ticket_titulo"], required=True, max_length=100)
    color = discord.ui.TextInput(label="Color Hex (ej: #5865F2)", default=f"#{config_global['ticket_color']:06x}", required=True, max_length=7)
    boton = discord.ui.TextInput(label="Texto del Botón", default=config_global["ticket_boton_texto"], required=True, max_length=80)
    descripcion = discord.ui.TextInput(label="Descripción del Embed", style=discord.TextStyle.paragraph, default=config_global["ticket_desc"], required=True, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        try: nuevo_color = int(self.color.value.strip().replace("#", ""), 16)
        except: return await interaction.response.send_message("❌ Color Hex inválido.", ephemeral=True)

        config_global["ticket_titulo"] = self.titulo.value.strip()
        config_global["ticket_color"] = nuevo_color
        config_global["ticket_boton_texto"] = self.boton.value.strip()
        config_global["ticket_desc"] = self.descripcion.value.strip()

        embed_preview = discord.Embed(
            title=config_global["ticket_titulo"],
            description=config_global["ticket_desc"],
            color=config_global["ticket_color"]
        )
        await interaction.response.send_message("✅ ¡Panel de tickets actualizado con éxito! Vista previa:", embed=embed_preview, ephemeral=True)


class ModalEditarBienvenidaTicket(discord.ui.Modal, title="Editar Embed de Bienvenida (Ticket)"):
    titulo = discord.ui.TextInput(label="Título del Embed", default=config_global["ticket_bienvenida_titulo"], required=True, max_length=100)
    color = discord.ui.TextInput(label="Color Hex (ej: #2ECC71)", default=f"#{config_global['ticket_bienvenida_color']:06x}", required=True, max_length=7)
    descripcion = discord.ui.TextInput(label="Descripción (Usa variables como $(user.mention))", style=discord.TextStyle.paragraph, default=config_global["ticket_bienvenida_desc"], required=True, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        try: nuevo_color = int(self.color.value.strip().replace("#", ""), 16)
        except: return await interaction.response.send_message("❌ Color Hex inválido.", ephemeral=True)

        config_global["ticket_bienvenida_titulo"] = self.titulo.value.strip()
        config_global["ticket_bienvenida_color"] = nuevo_color
        config_global["ticket_bienvenida_desc"] = self.descripcion.value.strip()

        await interaction.response.send_message("✅ ¡Mensaje de bienvenida dentro de los tickets actualizado correctamente!", ephemeral=True)


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

    @discord.ui.button(label="💬 Editar Mensaje de Bienvenida", style=discord.ButtonStyle.success, row=0)
    async def btn_bienvenida(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarBienvenidaTicket())


class SelectorConfiguracion(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Editor Visual de Tickets (Estilo Luminous)", description="Modifica en tiempo real el panel y la bienvenida", emoji="🎨", value="editor_tickets"),
            discord.SelectOption(label="Configurar Canales de Envío de Panel", description="Define el ID del canal donde se publicará el ticket", emoji="📢", value="canal_panel")
        ]
        super().__init__(placeholder="Elige una opción de configuración...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)

        if val == "editor_tickets":
            embed_editor = discord.Embed(
                title="✨ Editor Visual de Tickets",
                description="Usa los botones inferiores para personalizar el panel de apertura y el mensaje interno de bienvenida:",
                color=0x5865F2
            )
            await interaction.response.send_message(embed=embed_editor, view=VistaEditorVisualTickets(), ephemeral=True)
        elif val == "canal_panel":
            class ModalCanalPanel(discord.ui.Modal, title="Canal del Panel de Tickets"):
                c_id = discord.ui.TextInput(label="ID del Canal", default=str(config_global["canal_tickets_id"] or ""), required=True, max_length=20)
                async def on_submit(self, interaction2: discord.Interaction):
                    config_global["canal_tickets_id"] = int(self.c_id.value.strip())
                    await interaction2.response.send_message(f"✅ Canal de panel configurado a <#{config_global['canal_tickets_id']}>", ephemeral=True)
            await interaction.response.send_modal(ModalCanalPanel())


class VistaMenuConfiguracion(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(SelectorConfiguracion())


@client.tree.command(name="configuracion", description="Panel visual interactivo para tickets y editor Luminous")
async def configuracion(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)

    embed = discord.Embed(
        title="⚙️ Panel de Configuración de Tickets",
        description="Selecciona una opción en el menú desplegable para configurar el sistema de tickets estilo Luminous:",
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed, view=VistaMenuConfiguracion(), ephemeral=True)


@client.tree.command(name="confi-general", description="Configura prefijo, roles, canales de logs/sanciones y anti-spam")
async def confi_general(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
    
    await interaction.response.send_modal(ModalConfigGeneral())


@client.tree.command(name="variables", description="Muestra la lista de variables disponibles para los embeds")
async def variables(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Variables Disponibles para Tickets",
        description="Puedes utilizar las siguientes variables en tus mensajes de bienvenida y títulos:",
        color=0xF1C40F
    )
    embed.add_field(name="Usuarios y Servidor", value="• `$(user.mention)` ➜ Menciona al usuario que abrió el ticket\n• `$(user.name)` ➜ Nombre de usuario\n• `$(guild.name)` ➜ Nombre del servidor", inline=False)
    embed.add_field(name="Información", value="• `$(ticket.id)` ➜ Identificador numérico del ticket", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.tree.command(name="antibots", description="Activa o desactiva el sistema Anti-Bots automático")
@app_commands.choices(estado=[
    app_commands.Choice(name="Activado", value="on"),
    app_commands.Choice(name="Desactivado", value="off")
])
async def antibots(interaction: discord.Interaction, estado: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
    
    config_global["antibots_activo"] = (estado == "on")
    await interaction.response.send_message(f"🛡️ El sistema Anti-Bots ha sido **{'activado' if config_global['antibots_activo'] else 'desactivado'}** correctamente.", ephemeral=True)


# ==========================================
# 🎫 SISTEMA DE TICKETS (CON RECLAMACIÓN Y TOPICS)
# ==========================================

class VistaTicketActivo(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🙋‍♂️ Reclamar Ticket", style=discord.ButtonStyle.primary, custom_id="btn_reclamar_ticket")
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        rol_staff_id = config_global["rol_atencion_id"]
        es_staff = False
        if interaction.user.guild_permissions.administrator:
            es_staff = True
        elif rol_staff_id:
            rol = interaction.guild.get_role(rol_staff_id)
            if rol and rol in interaction.user.roles:
                es_staff = True

        if not es_staff:
            return await interaction.response.send_message("❌ No tienes el rol de staff autorizado para reclamar tickets.", ephemeral=True)
        
        button.disabled = True
        button.label = f"Reclamado por {interaction.user.display_name}"
        button.style = discord.ButtonStyle.secondary
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"🙋‍♂️ {interaction.user.mention} ha tomado y reclamado este ticket.")

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="btn_cerrar_ticket")
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Cerrando canal de ticket en 5 segundos...", ephemeral=False)
        await asyncio.sleep(5)
        try: await interaction.channel.delete()
        except: pass


class VistaCrearTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label=config_global["ticket_boton_texto"], style=discord.ButtonStyle.success, custom_id="btn_abrir_ticket")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        categoria = discord.utils.get(guild.categories, name="Tickets")
        if not categoria:
            try: categoria = await guild.create_category("Tickets")
            except: categoria = None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        
        if config_global["rol_atencion_id"]:
            rol_staff = guild.get_role(config_global["rol_atencion_id"])
            if rol_staff: overwrites[rol_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        canal_ticket = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=categoria, overwrites=overwrites)

        # Reemplazar variables en el mensaje de bienvenida
        desc = config_global["ticket_bienvenida_desc"]
        desc = desc.replace("$(user.mention)", interaction.user.mention)
        desc = desc.replace("$(user.name)", interaction.user.name)
        desc = desc.replace("$(guild.name)", guild.name)

        embed_bienvenida = discord.Embed(
            title=config_global["ticket_bienvenida_titulo"],
            description=desc,
            color=config_global["ticket_bienvenida_color"]
        )
        
        await canal_ticket.send(embed=embed_bienvenida, view=VistaTicketActivo())
        await interaction.response.send_message(f"✅ ¡Tu ticket ha sido creado en {canal_ticket.mention}!", ephemeral=True)


@client.tree.command(name="ticket", description="Envía el panel de tickets configurado al canal actual o configurado")
async def ticket(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)

    embed = discord.Embed(
        title=config_global["ticket_titulo"],
        description=config_global["ticket_desc"],
        color=config_global["ticket_color"]
    )
    
    canal_destino = interaction.guild.get_channel(config_global["canal_tickets_id"]) if config_global["canal_tickets_id"] else interaction.channel
    await canal_destino.send(embed=embed, view=VistaCrearTicket())
    await interaction.response.send_message(f"✅ Panel de tickets enviado correctamente a {canal_destino.mention}.", ephemeral=True)


# ==========================================
# 📋 POSTULACIONES PÚBLICAS
# ==========================================

class VistaComenzarPostulacion(discord.ui.View):
    def __init__(self, tipo: str, num_id: int, preguntas: list, miembro_postulado: discord.Member, config_form: dict):
        super().__init__(timeout=None)
        self.tipo = tipo
        self.num_id = num_id
        self.preguntas = preguntas
        self.miembro_postulado = miembro_postulado
        self.config_form = config_form

    @discord.ui.button(label="🚀 Comenzar Postulación", style=discord.ButtonStyle.success, custom_id="btn_comenzar_postulacion")
    async def comenzar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.miembro_postulado.id:
            return await interaction.response.send_message(f"❌ **Acceso denegado:** Este formulario pertenece exclusivamente a {self.miembro_postulado.mention}.", ephemeral=True)

        await interaction.response.send_message("📬 ¡Cuestionario abierto en tus **Mensajes Privados (MD)**!", ephemeral=True)

        respuestas_usuario = []
        try:
            for i, preg in enumerate(self.preguntas):
                embed_q = discord.Embed(
                    title=f"Pregunta {i+1} de {len(self.preguntas)}",
                    description=f"**{preg}**\n\n*(Tienes 90 segundos para enviar tu respuesta)*",
                    color=self.config_form['color']
                )
                await self.miembro_postulado.send(embed=embed_q)

                def check(m):
                    return m.author.id == self.miembro_postulado.id and isinstance(m.channel, discord.DMChannel)

                msg = await client.wait_for('message', timeout=90.0, check=check)
                respuestas_usuario.append((preg, msg.content))
                await self.miembro_postulado.send("✅ ¡Respuesta guardada!")

            respuestas_texto = ""
            for idx, (p, r) in enumerate(respuestas_usuario):
                respuestas_texto += f"**P{idx+1}: {p}**\n↳ {r}\n\n"

            embed_final = discord.Embed(
                title=f"{self.config_form['titulo']} (#{self.num_id})",
                description=f"👤 **Postulante:** {self.miembro_postulado.mention} (`{self.miembro_postulado}`)\n\n{respuestas_texto}",
                color=self.config_form['color']
            )
            embed_final.set_thumbnail(url=self.miembro_postulado.display_avatar.url)
            embed_final.set_footer(text="Esperando revisión del Staff.")

            destino_canal = interaction.guild.get_channel(config_global["canal_logs_id"]) if config_global["canal_logs_id"] else interaction.channel
            if destino_canal:
                await destino_canal.send(embed=embed_final, view=VistaRevisionPostulacion(self.miembro_postulado))

            await self.miembro_postulado.send("🎉 ¡Postulación completada y publicada en el servidor para revisión!")

        except asyncio.TimeoutError:
            await self.miembro_postulado.send("⏰ Tiempo agotado para responder el formulario.")


class ModalNotaStaff(discord.ui.Modal):
    def __init__(self, estado: str, autor_postulacion: discord.Member):
        super().__init__(title=f"Nota de Postulación ({estado})")
        self.estado = estado
        self.autor_postulacion = autor_postulacion
        self.nota_input = discord.ui.TextInput(label="Razón o nota", style=discord.TextStyle.paragraph, placeholder="Escribe tu comentario...", required=True, max_length=500)
        self.add_item(self.nota_input)

    async def on_submit(self, interaction: discord.Interaction):
        nota = self.nota_input.value
        for child in interaction.message.components:
            for row_child in child.children: row_child.disabled = True

        embed_actual = interaction.message.embeds[0]
        if self.estado == "APROBADO":
            embed_actual.color = discord.Color.green()
            res = f"✅ **Aprobado** por {interaction.user.mention}"
            estado_titulo = "¡APROBADO! 🎉"
        else:
            embed_actual.color = discord.Color.red()
            res = f"❌ **Rechazado** por {interaction.user.mention}"
            estado_titulo = "NO CLASIFICADO / RECHAZADO ❌"

        embed_actual.add_field(name="📌 Resultado", value=res, inline=False)
        embed_actual.add_field(name="📝 Nota del Staff", value=nota, inline=False)
        
        await interaction.message.edit(embed=embed_actual, view=None)

        try:
            embed_md = discord.Embed(title=f"📋 Actualización de tu Postulación", description=f"Tu postulación (`{embed_actual.title}`) ha sido evaluada.\n\n**Estado:** {estado_titulo}\n**Nota del Staff:** {nota}", color=embed_actual.color)
            await self.autor_postulacion.send(embed=embed_md)
        except:
            pass

        await interaction.response.send_message("✅ Postulación procesada correctamente.", ephemeral=True)


class VistaRevisionPostulacion(discord.ui.View):
    def __init__(self, autor_postulacion: discord.Member):
        super().__init__(timeout=None)
        self.autor_postulacion = autor_postulacion

    @discord.ui.button(label="✅ Aprobado", style=discord.ButtonStyle.success, custom_id="btn_aprobar")
    async def aprobar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalNotaStaff("APROBADO", self.autor_postulacion))

    @discord.ui.button(label="❌ Rechazado", style=discord.ButtonStyle.danger, custom_id="btn_rechazar")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalNotaStaff("RECHAZADO", self.autor_postulacion))


class SelectorPostulaciones(discord.ui.Select):
    def __init__(self, miembro: discord.Member):
        self.miembro = miembro
        options = [
            discord.SelectOption(label="Cuerpo de Moderación (Staff)", description="Inicia el formulario de moderación", emoji="🛡️", value="staff"),
            discord.SelectOption(label="Casa Alianza (Ally)", description="Inicia el formulario para alianzas", emoji="🤝", value="ally"),
            discord.SelectOption(label="Cuerpo de Redes", description="Inicia el formulario de redes sociales", emoji="🎨", value="redes"),
            discord.SelectOption(label="Cuerpo de Programación (Nexus)", description="Inicia el formulario de programación", emoji="💻", value="nexus")
        ]
        super().__init__(placeholder="Selecciona el tipo de postulación...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        tipo = self.values[0]
        config_form = postulaciones_config.get(tipo, {})
        preguntas = config_form.get("preguntas", [])
        if not preguntas: return await interaction.response.send_message("❌ Este formulario no tiene preguntas configuradas.", ephemeral=True)

        config_global["contador_postulaciones"] += 1
        num_id = config_global["contador_postulaciones"]

        embed = discord.Embed(
            title=f"{config_form['titulo']} (#{num_id})",
            description=f"👤 **Candidato:** {self.miembro.mention}\n⚡ **Iniciado por:** {interaction.user.mention}\n\nPresiona el botón inferior para comenzar el cuestionario en tus mensajes privados (MD).",
            color=config_form['color']
        )
        embed.set_thumbnail(url=self.miembro.display_avatar.url)

        await interaction.channel.send(content=f"📋 Panel de postulación creado para {self.miembro.mention}:", embed=embed, view=VistaComenzarPostulacion(tipo, num_id, preguntas, self.miembro, config_form))
        await interaction.response.edit_message(content="✅ ¡Panel de postulación generado con éxito en el canal!", embed=None, view=None)


class VistaMenuPostulacion(discord.ui.View):
    def __init__(self, miembro: discord.Member):
        super().__init__(timeout=30)
        self.add_item(SelectorPostulaciones(miembro))


@client.tree.command(name="postulacion", description="Inicia un panel de postulación interactivo eligiendo el tipo")
@app_commands.describe(miembro="Usuario al que se le asignará la postulación")
async def postulacion(interaction: discord.Interaction, miembro: discord.Member):
    embed = discord.Embed(title="📋 Menú de Postulaciones", description=f"Selecciona en el menú desplegable de abajo el tipo de formulario que deseas abrir para **{miembro.display_name}**:", color=0x3498DB)
    await interaction.response.send_message(embed=embed, view=VistaMenuPostulacion(miembro), ephemeral=True)


# ==========================================
# 🛡️ SISTEMA DE SANCIONES Y MODERACIÓN
# ==========================================

@client.tree.command(name="ban", description="Banea a un miembro del servidor")
@app_commands.describe(miembro="Miembro a banear", razon="Motivo del baneo")
async def ban(interaction: discord.Interaction, miembro: discord.Member, razon: str = "Sin motivo especificado"):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    try:
        await miembro.ban(reason=razon)
        base_datos_sanciones[miembro.id].append(f"🔨 **Ban** por {interaction.user} - Razón: {razon}")
        await interaction.response.send_message(f"🔨 {miembro.mention} ha sido baneado. Razón: *{razon}*")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


@client.tree.command(name="unban", description="Desbanea a un usuario mediante su ID o Nombre")
@app_commands.describe(usuario_id="ID de Discord del usuario baneado", razon="Motivo")
async def unban(interaction: discord.Interaction, usuario_id: str, razon: str = "Sin motivo especificado"):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    try:
        ban_entry = None
        async for entry in interaction.guild.bans():
            if str(entry.user.id) == usuario_id.strip() or entry.user.name.lower() == usuario_id.strip().lower():
                ban_entry = entry
                break
        if not ban_entry: return await interaction.response.send_message("❌ No se encontró ese baneo.", ephemeral=True)
        await interaction.guild.unban(ban_entry.user, reason=razon)
        await interaction.response.send_message(f"🔓 Se ha desbaneado a **{ban_entry.user}**.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


@client.tree.command(name="kick", description="Expulsa a un miembro del servidor")
@app_commands.describe(miembro="Miembro a expulsar", razon="Motivo")
async def kick(interaction: discord.Interaction, miembro: discord.Member, razon: str = "Sin motivo especificado"):
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    try:
        await miembro.kick(reason=razon)
        base_datos_sanciones[miembro.id].append(f"👢 **Kick** por {interaction.user} - Razón: {razon}")
        await interaction.response.send_message(f"👢 {miembro.mention} expulsado.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


@client.tree.command(name="mute", description="Silencia temporalmente a un miembro")
@app_commands.describe(miembro="Miembro", segundos="Duración en segundos", razon="Motivo")
async def mute(interaction: discord.Interaction, miembro: discord.Member, segundos: int, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    try:
        await miembro.timeout(discord.utils.utcnow() + discord.Timedelta(seconds=segundos), reason=razon)
        base_datos_sanciones[miembro.id].append(f"🔇 **Mute** ({segundos}s) - Razón: {razon}")
        await interaction.response.send_message(f"🔇 {miembro.mention} silenciado por {segundos}s.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


@client.tree.command(name="unmute", description="Quita el timeout a un miembro")
@app_commands.describe(miembro="Miembro")
async def unmute(interaction: discord.Interaction, miembro: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    try:
        await miembro.timeout(None, reason="Desmuteado")
        await interaction.response.send_message(f"🔊 {miembro.mention} desmuteado.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


@client.tree.command(name="warn", description="Advierte a un miembro")
@app_commands.describe(miembro="Miembro", razon="Motivo")
async def warn(interaction: discord.Interaction, miembro: discord.Member, razon: str):
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    try:
        base_datos_sanciones[miembro.id].append(f"⚠️ **Warn** - Razón: {razon}")
        await miembro.send(embed=discord.Embed(title="⚠️ Advertencia", description=f"Razón: {razon}", color=0xF1C40F))
        await interaction.response.send_message(f"⚠️ {miembro.mention} advertido.")
    except:
        await interaction.response.send_message(f"⚠️ {miembro.mention} advertido (MD cerrados).")


@client.tree.command(name="historial", description="Muestra el historial de sanciones de un usuario")
@app_commands.describe(miembro="Miembro a consultar")
async def historial(interaction: discord.Interaction, miembro: discord.Member):
    sanciones = base_datos_sanciones.get(miembro.id, [])
    if not sanciones: return await interaction.response.send_message(f"🛡️ {miembro.mention} no tiene sanciones registradas.", ephemeral=True)
    await interaction.response.send_message(embed=discord.Embed(title=f"📜 Historial: {miembro.display_name}", description="\n".join([f"• {s}" for s in sanciones]), color=0xE74C3C), ephemeral=True)


# ==========================================
# 🎮 JUEGOS Y TRIVIA
# ==========================================

@client.tree.command(name="help", description="Centro de ayuda y comandos")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="✨ Centro de Ayuda — Nexus Bot", description=f"Prefijo: `{config_global['prefijo']}`", color=0x5865F2)
    embed.add_field(name="⚙️️ Configuración", value="• `/configuracion` (Editor Luminous)\n• `/confi-general` (Prefijo, roles y canales)\n• `/variables` (Variables de ticket)\n• `/antibots` (Activar/Desactivar)", inline=False)
    embed.add_field(name="📋 Módulos", value="• `/postulacion` • `/ticket` • `/ban` • `/unban` • `/historial` • `/trivia` • `/ppt`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.tree.command(name="juegos", description="Menú principal de juegos")
async def juegos(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(title=config_global["embed_juegos_titulo"], description=config_global["embed_juegos_desc"], color=config_global["embed_juegos_color"]))


@client.tree.command(name="dado", description="Lanza un dado")
@app_commands.describe(caras="Caras del dado")
async def dado(interaction: discord.Interaction, caras: int = 6):
    await interaction.response.send_message(f"🎲 Lanzaste un dado de {caras} y sacaste: **{random.randint(1, caras)}**")


# --- PPT 2 JUGADORES ---
class VistaEleccionPPT(discord.ui.View):
    def __init__(self, retador, retado, jugada_retador):
        super().__init__(timeout=30)
        self.retador, self.retado, self.jugada_retador = retador, retado, jugada_retador

    @discord.ui.button(label="🪨 Piedra", style=discord.ButtonStyle.secondary)
    async def piedra(self, i, b): await self.proc(i, "piedra")
    @discord.ui.button(label="📄 Papel", style=discord.ButtonStyle.secondary)
    async def papel(self, i, b): await self.proc(i, "papel")
    @discord.ui.button(label="✂️ Tijera", style=discord.ButtonStyle.secondary)
    async def tijera(self, i, b): await self.proc(i, "tijera")

    async def proc(self, interaction, jugada):
        if interaction.user.id != self.retado.id: return await interaction.response.send_message("❌ No es tu duelo.", ephemeral=True)
        r1, r2 = self.jugada_retador, jugada
        if r1 == r2: res = "¡Empate! 🤝"
        elif (r1 == "piedra" and r2 == "tijera") or (r1 == "papel" and r2 == "piedra") or (r1 == "tijera" and r2 == "papel"): res = f"🎉 ¡{self.retador.mention} gana con **{r1}**!"
        else: res = f"🎉 ¡{self.retado.mention} gana con **{r2}**!"
        for c in self.children: c.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"⚔️ {self.retador.mention} (`{r1}`) vs {self.retado.mention} (`{r2}`)\n{res}")


class SelectorPPTInicial(discord.ui.Select):
    def __init__(self, retador, retado):
        self.retador, self.retado = retador, retado
        super().__init__(placeholder="Elige tu jugada...", options=[discord.SelectOption(label="Piedra", value="piedra"), discord.SelectOption(label="Papel", value="papel"), discord.SelectOption(label="Tijera", value="tijera")])

    async def callback(self, interaction):
        if interaction.user.id != self.retador.id: return await interaction.response.send_message("❌ No.", ephemeral=True)
        await interaction.response.edit_message(content=f"⚔️ {self.retado.mention}, tu turno de elegir:", embed=None, view=VistaEleccionPPT(self.retador, self.retado, self.values[0]))


@client.tree.command(name="ppt", description="Reta a Piedra, Papel o Tijera")
async def ppt(interaction: discord.Interaction, adversario: discord.Member):
    if adversario.id == interaction.user.id or adversario.bot: return await interaction.response.send_message("❌ Inválido.", ephemeral=True)
    v = discord.ui.View(timeout=30)
    v.add_item(SelectorPPTInicial(interaction.user, adversario))
    await interaction.response.send_message(embed=discord.Embed(title="⚔️ Duelo PPT", description=f"{interaction.user.mention} reta a {adversario.mention}!"), view=v, ephemeral=True)


# --- TRIVIA ---
class VistaTriviaPublica(discord.ui.View):
    def __init__(self, pd):
        super().__init__(timeout=20)
        for op in pd["opciones"]: self.add_item(discord.ui.Button(label=op, style=discord.ButtonStyle.primary))

@client.tree.command(name="trivia", description="Trivia pública")
async def trivia(interaction: discord.Interaction):
    t = random.choice(BANCO_TRIVIA)
    embed = discord.Embed(title=f"🧠 Trivia: {t['cat']}", description=f"**{t['p']}**", color=0x3498DB)
    embed.set_image(url=t["img"])
    await interaction.response.send_message(embed=embed, view=VistaTriviaPublica(t), ephemeral=True)


client.run(os.environ['DISCORD_TOKEN'])