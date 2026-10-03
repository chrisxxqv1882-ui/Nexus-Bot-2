import os
import random
import asyncio
import time
from collections import defaultdict
import discord
from discord import app_commands

# Configuración global del bot y base de datos en memoria para sanciones y tickets
config_global = {
    "prefijo": "a¡",
    "rol_comandos_id": None,  
    "rol_atencion_id": None,   
    "canal_logs_id": None,     
    "canal_tickets_id": None,  
    "contador_postulaciones": 0, 
    "antispam_activo": True,
    "antispam_limite_mensajes": 5,
    "antispam_ventana_segundos": 5,
    "antispam_timeout_segundos": 60,
    "antibots_activo": True,
    # Configuración de Tickets estilo Luminous
    "ticket_titulo": "🎟️ Sistema de Soporte y Tickets",
    "ticket_desc": "Haz clic en el botón inferior o selecciona una opción para abrir un ticket privado con el staff.",
    "ticket_color": 0x5865F2,
    "ticket_boton_texto": "🎫 Abrir Ticket",
    "ticket_bienvenida": "🎫 **Ticket de Soporte**\nHola {usuario}, el staff te atenderá pronto. Explica tu duda detalladamente.",
    "ticket_tipo_menu": "botones", # "botones" o "menu"
    "embed_juegos_titulo": "🎮 Zona de Juegos e Interacción",
    "embed_juegos_desc": "¡Diviértete con los minijuegos multijugador y nuestra trivia masiva estilo Nekotrivia!",
    "embed_juegos_color": 0xF1C40F
}

registro_antispam = defaultdict(list)
base_datos_sanciones = defaultdict(list) # usuario_id -> lista de sanciones

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
        "cat": "Anime",
        "img": "https://media.giphy.com/media/v0ok8uhZvw3yE/giphy.gif"
    },
    {
        "p": "¿Qué fruta del diablo consume Monkey D. Luffy en One Piece?",
        "correcta": "Gomu Gomu",
        "opciones": ["Mera Mera", "Gomu Gomu", "Ope Ope", "Hito Hito"],
        "cat": "Anime",
        "img": "https://media.giphy.com/media/9BuHO7tE98McE/giphy.gif"
    },
    {
        "p": "¿Cómo se llama el cazador de demonios con cabello burdeos en Kimetsu no Yaiba?",
        "correcta": "Tanjiro",
        "opciones": ["Inosuke", "Zenitsu", "Tanjiro", "Muzan"],
        "cat": "Anime",
        "img": "https://media.giphy.com/media/tEXUOC8zScfbhz0VDg/giphy.gif"
    },
    {
        "p": "¿Qué civilización construyó la majestuosa ciudad de Machu Picchu?",
        "correcta": "Inca",
        "opciones": ["Maya", "Azteca", "Inca", "Romana"],
        "cat": "Historia",
        "img": "https://media.giphy.com/media/3o7TKSjRrfIPjeiDiM/giphy.gif"
    },
    {
        "p": "¿En qué año dio inicio oficialmente la Primera Guerra Mundial?",
        "correcta": "1914",
        "opciones": ["1914", "1939", "1812", "1905"],
        "cat": "Historia",
        "img": "https://media.giphy.com/media/l0HlRnAWXxn0MhOBK/giphy.gif"
    },
    {
        "p": "¿Quién fue el primer presidente en la historia de los Estados Unidos?",
        "correcta": "George Washington",
        "opciones": ["Abraham Lincoln", "George Washington", "Thomas Jefferson", "John Adams"],
        "cat": "Historia",
        "img": "https://media.giphy.com/media/l4FGpPki5v2Bcd6Ss/giphy.gif"
    }
]

for i in range(80):
    if i % 2 == 0:
        BANCO_TRIVIA.append({
            "p": "Cultura Otaku: ¿Este personaje o serie es sumamente popular globalmente?",
            "correcta": "Sí",
            "opciones": ["Sí", "No", "Tal vez", "Falso"],
            "cat": "Anime",
            "img": "https://media.giphy.com/media/cb9aF9tDyiRkY/giphy.gif"
        })
    else:
        BANCO_TRIVIA.append({
            "p": "Acontecimiento Histórico: ¿Este evento cambió radicalmente el mundo?",
            "correcta": "Sí",
            "opciones": ["Sí", "No", "Fue menor", "Ficción"],
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
                warning = await message.channel.send(f"⚠️ {message.author.mention} ha recibido un **Timeout de {duracion_timeout} segundos** por spam.")
                await asyncio.sleep(5)
                await warning.delete()
            except Exception as e:
                print(f"Error al aplicar timeout: {e}")
            return

    if message.content.startswith(config_global["prefijo"]):
        contenido = message.content[len(config_global["prefijo"]):].strip().lower()
        if contenido == "ayuda" or contenido == "help":
            await message.channel.send(f"⚙️️ El prefijo actual es `{config_global['prefijo']}`. Usa `/help` para ver los comandos.")
        return


# ==========================================
# ⚙️ MODALES DE CONFIGURACIÓN Y TICKET
# ==========================================

class ModalConfigFormulario(discord.ui.Modal):
    def __init__(self, tipo: str, nombre_bonito: str):
        super().__init__(title=f"Configurar {nombre_bonito}")
        self.tipo = tipo
        cfg_actual = postulaciones_config.get(tipo, {})
        preguntas_actuales = "\n".join(cfg_actual.get("preguntas", []))
        color_actual_hex = f"#{cfg_actual.get('color', 3498335):06x}"

        self.input_titulo = discord.ui.TextInput(label="Título del Embed", default=cfg_actual.get("titulo", ""), required=True, max_length=100)
        self.input_color = discord.ui.TextInput(label="Color Hex", default=color_actual_hex, required=True, max_length=7)
        self.input_preguntas = discord.ui.TextInput(label="Preguntas (Una por línea)", style=discord.TextStyle.paragraph, default=preguntas_actuales, required=True, max_length=4000)

        self.add_item(self.input_titulo)
        self.add_item(self.input_color)
        self.add_item(self.input_preguntas)

    async def on_submit(self, interaction: discord.Interaction):
        try: nuevo_color = int(self.input_color.value.strip().replace("#", ""), 16)
        except: return await interaction.response.send_message("❌ Color Hex inválido.", ephemeral=True)

        nuevas_preguntas = [p.strip() for p in self.input_preguntas.value.split('\n') if p.strip()]
        if not nuevas_preguntas:
            return await interaction.response.send_message("❌ Debes incluir al menos una pregunta.", ephemeral=True)

        postulaciones_config[self.tipo] = {
            "titulo": self.input_titulo.value.strip(),
            "color": nuevo_color,
            "preguntas": nuevas_preguntas
        }
        await interaction.response.send_message(f"✅ ¡Formulario de **{self.tipo.upper()}** actualizado!", ephemeral=True)


class ModalConfigGeneral(discord.ui.Modal, title="Configuración General y Seguridad"):
    input_prefijo = discord.ui.TextInput(label="Prefijo del Bot", default=config_global["prefijo"], required=True, max_length=5)
    rol_cmd_id = discord.ui.TextInput(label="ID Rol Ejecutar Postulación", default=str(config_global["rol_comandos_id"] or ""), required=False, max_length=20)
    rol_atc_id = discord.ui.TextInput(label="ID Rol Staff", default=str(config_global["rol_atencion_id"] or ""), required=False, max_length=20)
    canal_log_id = discord.ui.TextInput(label="ID Canal Respuestas Postulaciones", default=str(config_global["canal_logs_id"] or ""), required=False, max_length=20)
    antispam_time = discord.ui.TextInput(label="Timeout por Spam (Segundos)", default=str(config_global["antispam_timeout_segundos"]), required=True, max_length=5)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            config_global["prefijo"] = self.input_prefijo.value.strip()
            config_global["rol_comandos_id"] = int(self.rol_cmd_id.value.strip()) if self.rol_cmd_id.value.strip() else None
            config_global["rol_atencion_id"] = int(self.rol_atc_id.value.strip()) if self.rol_atc_id.value.strip() else None
            config_global["canal_logs_id"] = int(self.canal_log_id.value.strip()) if self.canal_log_id.value.strip() else None
            config_global["antispam_timeout_segundos"] = int(self.antispam_time.value.strip())

            await interaction.response.send_message("✅ ¡Configuración general guardada con éxito!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Error: Asegúrate de ingresar IDs numéricos válidos.", ephemeral=True)


class ModalConfigTicket(discord.ui.Modal, title="Configurar Panel de Tickets (Luminous)"):
    titulo = discord.ui.TextInput(label="Título del Embed", default=config_global["ticket_titulo"], required=True, max_length=100)
    color = discord.ui.TextInput(label="Color Hex (ej: #5865F2)", default=f"#{config_global['ticket_color']:06x}", required=True, max_length=7)
    boton = discord.ui.TextInput(label="Texto del Botón / Opción", default=config_global["ticket_boton_texto"], required=True, max_length=80)
    canal_id = discord.ui.TextInput(label="ID Canal para enviar el Panel", default=str(config_global["canal_tickets_id"] or ""), required=False, max_length=20)
    bienvenida = discord.ui.TextInput(label="Mensaje de bienvenida en el Ticket", style=discord.TextStyle.paragraph, default=config_global["ticket_bienvenida"], required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        try: nuevo_color = int(self.color.value.strip().replace("#", ""), 16)
        except: return await interaction.response.send_message("❌ Color Hex inválido.", ephemeral=True)

        config_global["ticket_titulo"] = self.titulo.value.strip()
        config_global["ticket_color"] = nuevo_color
        config_global["ticket_boton_texto"] = self.boton.value.strip()
        config_global["ticket_bienvenida"] = self.bienvenida.value.strip()
        
        if self.canal_id.value.strip():
            config_global["canal_tickets_id"] = int(self.canal_id.value.strip())

        await interaction.response.send_message("✅ ¡Configuración y bienvenida de tickets actualizada!", ephemeral=True)


class VistaBotonesFormularios(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="📝 Staff", style=discord.ButtonStyle.primary, row=0)
    async def btn_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalConfigFormulario("staff", "Moderación"))

    @discord.ui.button(label="🤝 Casa Alianza", style=discord.ButtonStyle.primary, row=0)
    async def btn_ally(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalConfigFormulario("ally", "Casa Alianza"))

    @discord.ui.button(label="🎨 Redes", style=discord.ButtonStyle.primary, row=1)
    async def btn_redes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalConfigFormulario("redes", "Cuerpo de Redes"))

    @discord.ui.button(label="💻 Programación (Nexus)", style=discord.ButtonStyle.primary, row=1)
    async def btn_nexus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalConfigFormulario("nexus", "Programación (Nexus)"))


class SelectorConfiguracion(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Configurar Formularios (Staff, Ally, Redes, Nexus)", description="Edita preguntas y colores", emoji="📝", value="formularios"),
            discord.SelectOption(label="Configurar Bot de Tickets y Bienvenida", description="Edita panel, botones y mensaje de bienvenida", emoji="🎫", value="tickets")
        ]
        super().__init__(placeholder="Elige una sección de configuración...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)

        if val == "formularios":
            embed_forms = discord.Embed(
                title="📝 Panel de Configuración de Formularios",
                description="Haz clic en los botones inferiores para editar los títulos, colores y preguntas:",
                color=0x2ECC71
            )
            await interaction.response.send_message(embed=embed_forms, view=VistaBotonesFormularios(), ephemeral=True)
        elif val == "tickets":
            await interaction.response.send_modal(ModalConfigTicket())


class VistaMenuConfiguracion(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(SelectorConfiguracion())


@client.tree.command(name="configuracion", description="Panel de configuración de formularios y tickets")
async def configuracion(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)

    embed = discord.Embed(
        title="⚙️ Panel de Configuración",
        description="Usa el menú desplegable de abajo para configurar los formularios o el sistema de tickets.",
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed, view=VistaMenuConfiguracion(), ephemeral=True)


@client.tree.command(name="confi-general", description="Configura prefijo, roles, canal de respuestas y anti-spam")
async def confi_general(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
    
    await interaction.response.send_modal(ModalConfigGeneral())


# ==========================================
# 🎫 SISTEMA DE TICKETS (CON RECLAMACIÓN)
# ==========================================

class VistaTicketActivo(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🙋‍♂️ Reclamar Ticket", style=discord.ButtonStyle.primary, custom_id="btn_reclamar_ticket")
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo el staff puede reclamar tickets.", ephemeral=True)
        
        button.disabled = True
        button.label = f"Reclamado por {interaction.user.display_name}"
        button.style = discord.ButtonStyle.secondary
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"🙋‍♂️ {interaction.user.mention} ha tomado y reclamado este ticket.")

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="btn_cerrar_ticket")
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Cerrando canal de ticket en 5 segundos...", ephemeral=False)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except:
            pass


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

        texto_bienvenida = config_global["ticket_bienvenida"].replace("{usuario}", interaction.user.mention)
        embed_bienvenida = discord.Embed(title="🎫 Soporte Técnico", description=texto_bienvenida, color=0x5865F2)
        
        await canal_ticket.send(embed=embed_bienvenida, view=VistaTicketActivo())
        await interaction.response.send_message(f"✅ ¡Tu ticket ha sido creado en {canal_ticket.mention}!", ephemeral=True)


@client.tree.command(name="ticket", description="Envía el panel de tickets configurado al canal actual")
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
    await interaction.response.send_message(f"✅ Panel de tickets enviado a {canal_destino.mention}.", ephemeral=True)


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
            embed_md = discord.Embed(
                title=f"📋 Actualización de tu Postulación",
                description=f"Tu postulación (`{embed_actual.title}`) ha sido evaluada.\n\n**Estado:** {estado_titulo}\n**Nota del Staff:** {nota}",
                color=embed_actual.color
            )
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
        if not verificar_permisos_atencion(interaction): return await interaction.response.send_message("❌ Sin permisos de staff.", ephemeral=True)
        await interaction.response.send_modal(ModalNotaStaff("APROBADO", self.autor_postulacion))

    @discord.ui.button(label="❌ Rechazado", style=discord.ButtonStyle.danger, custom_id="btn_rechazar")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_permisos_atencion(interaction): return await interaction.response.send_message("❌ Sin permisos de staff.", ephemeral=True)
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
    if not verificar_permisos_comandos(interaction):
        return await interaction.response.send_message("❌ No tienes permisos para ejecutar este comando.", ephemeral=True)

    embed = discord.Embed(
        title="📋 Menú de Postulaciones",
        description=f"Selecciona en el menú desplegable de abajo el tipo de formulario que deseas abrir para **{miembro.display_name}**:",
        color=0x3498DB
    )
    await interaction.response.send_message(embed=embed, view=VistaMenuPostulacion(miembro), ephemeral=True)


# ==========================================
# 🛡️ SISTEMA DE SANCIONES Y HISTORIAL
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

@client.tree.command(name="kick", description="Expulsa a un miembro del servidor")
@app_commands.describe(miembro="Miembro a expulsar", razon="Motivo")
async def kick(interaction: discord.Interaction, miembro: discord.Member, razon: str = "Sin motivo especificado"):
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    try:
        await miembro.kick(reason=razon)
        base_datos_sanciones[miembro.id].append(f"👢 **Kick** por {interaction.user} - Razón: {razon}")
        await interaction.response.send_message(f"👢 {miembro.mention} expulsado. Razón: *{razon}*")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@client.tree.command(name="mute", description="Silencia temporalmente a un miembro")
@app_commands.describe(miembro="Miembro", segundos="Duración en segundos", razon="Motivo")
async def mute(interaction: discord.Interaction, miembro: discord.Member, segundos: int, razon: str = "Sin motivo"):
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    try:
        await miembro.timeout(discord.utils.utcnow() + discord.Timedelta(seconds=segundos), reason=razon)
        base_datos_sanciones[miembro.id].append(f"🔇 **Mute** ({segundos}s) por {interaction.user} - Razón: {razon}")
        await interaction.response.send_message(f"🔇 {miembro.mention} silenciado por {segundos}s. Razón: *{razon}*")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@client.tree.command(name="unmute", description="Quita el timeout a un miembro")
@app_commands.describe(miembro="Miembro")
async def unmute(interaction: discord.Interaction, miembro: discord.Member):
    if not interaction.user.moderate_members if hasattr(interaction.user, 'moderate_members') else interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    try:
        await miembro.timeout(None, reason="Desmuteado por staff")
        await interaction.response.send_message(f"🔊 {miembro.mention} desmuteado.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@client.tree.command(name="warn", description="Advierte a un miembro")
@app_commands.describe(miembro="Miembro", razon="Motivo de la advertencia")
async def warn(interaction: discord.Interaction, miembro: discord.Member, razon: str):
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
    try:
        base_datos_sanciones[miembro.id].append(f"⚠️ **Warn** por {interaction.user} - Razón: {razon}")
        embed_warn = discord.Embed(title="⚠️ Advertencia", description=f"Has recibido una advertencia en **{interaction.guild.name}**.\n**Razón:** {razon}", color=0xF1C40F)
        await miembro.send(embed=embed_warn)
        await interaction.response.send_message(f"⚠️ {miembro.mention} advertido correctamente.")
    except:
        await interaction.response.send_message(f"⚠️ {miembro.mention} advertido (tenía los MD cerrados).")

@client.tree.command(name="historial", description="Muestra el historial de sanciones de un usuario")
@app_commands.describe(miembro="Miembro a consultar")
async def historial(interaction: discord.Interaction, miembro: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ No tienes permisos para ver el historial.", ephemeral=True)
    
    sanciones = base_datos_sanciones.get(miembro.id, [])
    if not sanciones:
        return await interaction.response.send_message(f"🛡️ {miembro.mention} no tiene ninguna sanción registrada en el sistema.", ephemeral=True)

    texto_sanciones = "\n".join([f"• {s}" for s in sanciones])
    embed = discord.Embed(
        title=f"📜 Historial de Sanciones: {miembro.display_name}",
        description=texto_sanciones,
        color=0xE74C3C
    )
    embed.set_thumbnail(url=miembro.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 🎮 JUEGOS Y TRIVIA
# ==========================================

@client.tree.command(name="help", description="Muestra la lista de comandos y módulos")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✨ Centro de Ayuda — Nexus Bot",
        description=f"Prefijo de texto actual: `{config_global['prefijo']}`\nExplora los módulos disponibles:",
        color=0x5865F2
    )
    embed.add_field(name="⚙️ Configuración", value="• `/configuracion` ➜ Formularios y tickets (Luminous).\n• `/confi-general` ➜ Prefijo, roles, canales y timeout por spam.", inline=False)
    embed.add_field(name="📋 Postulaciones y Soporte", value="• `/postulacion [miembro]`\n• `/ticket`", inline=False)
    embed.add_field(name="🛡️ Moderación y Sanciones", value="• `/ban` • `/kick` • `/mute` • `/unmute` • `/warn` • `/historial [miembro]`", inline=False)
    embed.add_field(name="🎮 Entretenimiento", value="• `/juegos` • `/dado` • `/ppt [miembro]` • `/trivia`", inline=False)
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.tree.command(name="juegos", description="Menú principal de juegos")
async def juegos(interaction: discord.Interaction):
    embed = discord.Embed(
        title=config_global["embed_juegos_titulo"],
        description=config_global["embed_juegos_desc"] + "\n\n**Comandos:**\n• `/dado` • `/ppt` • `/trivia`",
        color=config_global["embed_juegos_color"]
    )
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="dado", description="Lanza un dado")
@app_commands.describe(caras="Caras del dado")
async def dado(interaction: discord.Interaction, caras: int = 6):
    if caras < 2: return await interaction.response.send_message("❌ Mínimo 2 caras.", ephemeral=True)
    await interaction.response.send_message(f"🎲 {interaction.user.mention} lanzó un dado de {caras} y sacó: **{random.randint(1, caras)}**")


# --- PPT 2 JUGADORES INTERACTIVO ---
class VistaEleccionPPT(discord.ui.View):
    def __init__(self, retador: discord.Member, retado: discord.Member, jugada_retador: str):
        super().__init__(timeout=30)
        self.retador = retador
        self.retado = retado
        self.jugada_retador = jugada_retador
        self.jugada_retado = None

    @discord.ui.button(label="🪨 Piedra", style=discord.ButtonStyle.secondary)
    async def piedra(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.procesar_jugada(interaction, "piedra")

    @discord.ui.button(label="📄 Papel", style=discord.ButtonStyle.secondary)
    async def papel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.procesar_jugada(interaction, "papel")

    @discord.ui.button(label="✂️ Tijera", style=discord.ButtonStyle.secondary)
    async def tijera(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.procesar_jugada(interaction, "tijera")

    async def procesar_jugada(self, interaction: discord.Interaction, jugada: str):
        if interaction.user.id != self.retado.id:
            return await interaction.response.send_message("❌ Este duelo no es para ti.", ephemeral=True)

        self.jugada_retado = jugada
        r1, r2 = self.jugada_retador, self.jugada_retado

        if r1 == r2: res = "¡Empate técnico! 🤝"
        elif (r1 == "piedra" and r2 == "tijera") or (r1 == "papel" and r2 == "piedra") or (r1 == "tijera" and r2 == "papel"):
            res = f"🎉 ¡{self.retador.mention} gana el duelo con **{r1}** frente a **{r2}**!"
        else:
            res = f"🎉 ¡{self.retado.mention} gana el duelo con **{r2}** frente a **{r1}**!"

        for child in self.children: child.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"⚔️ **Resultado Duelo PPT**:\n{self.retador.mention} (`{r1}`) vs {self.retado.mention} (`{r2}`)\n\n{res}")


class SelectorPPTInicial(discord.ui.Select):
    def __init__(self, retador: discord.Member, retado: discord.Member):
        self.retador = retador
        self.retado = retado
        options = [
            discord.SelectOption(label="Piedra", emoji="🪨", value="piedra"),
            discord.SelectOption(label="Papel", emoji="📄", value="papel"),
            discord.SelectOption(label="Tijera", emoji="✂️", value="tijera")
        ]
        super().__init__(placeholder="Elige tu jugada secreta...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.retador.id:
            return await interaction.response.send_message("❌ No puedes responder a este reto.", ephemeral=True)
        
        jugada = self.values[0]
        view_retado = VistaEleccionPPT(self.retador, self.retado, jugada)
        await interaction.response.edit_message(content=f"⚔️ {self.retado.mention}, **{self.retador.display_name}** hizo su elección. ¡Haz clic en tu botón de abajo!", embed=None, view=view_retado)


class VistaRetoPPT2P(discord.ui.View):
    def __init__(self, retador: discord.Member, retado: discord.Member):
        super().__init__(timeout=30)
        self.retador = retador
        self.retado = retado
        self.add_item(SelectorPPTInicial(retador, retado))


@client.tree.command(name="ppt", description="Reta a Piedra, Papel o Tijera a otro miembro")
@app_commands.describe(adversario="Miembro al que deseas retar")
async def ppt(interaction: discord.Interaction, adversario: discord.Member):
    if adversario.id == interaction.user.id:
        return await interaction.response.send_message("❌ No puedes retarte a ti mismo.", ephemeral=True)
    if adversario.bot:
        return await interaction.response.send_message("❌ No puedes retar a un bot.", ephemeral=True)

    embed = discord.Embed(title="⚔️ Duelo de Piedra, Papel o Tijera", description=f"{interaction.user.mention} ha retado a {adversario.mention}!\n\n*{interaction.user.display_name}, selecciona tu jugada secreta:*", color=0xE74C3C)
    await interaction.response.send_message(embed=embed, view=VistaRetoPPT2P(interaction.user, adversario), ephemeral=True)


# --- TRIVIA PÚBLICA ---
class VistaTriviaPublica(discord.ui.View):
    def __init__(self, pregunta_data: dict):
        super().__init__(timeout=20)
        self.pregunta_data = pregunta_data
        self.respondido = False
        opciones = pregunta_data["opciones"].copy()
        random.shuffle(opciones)
        for op in opciones: self.add_item(BotonAlternativa(op, pregunta_data["correcta"], self))

    async def on_timeout(self):
        if not self.respondido:
            for child in self.children: child.disabled = True
            try: await self.message.edit(view=self)
            except: pass


class BotonAlternativa(discord.ui.Button):
    def __init__(self, label: str, correcta: str, vista_padre: VistaTriviaPublica):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.correcta = correcta
        self.vista_padre = vista_padre

    async def callback(self, interaction: discord.Interaction):
        if self.vista_padre.respondido: return await interaction.response.send_message("❌ ¡Trivia respondida!", ephemeral=True)
        self.vista_padre.respondido = True
        for child in self.vista_padre.children:
            child.disabled = True
            if child.label == self.correcta: child.style = discord.ButtonStyle.success
            elif child.label == self.label and child.label != self.correcta: child.style = discord.ButtonStyle.danger

        embed_actual = interaction.message.embeds[0]
        if self.label == self.correcta:
            res_txt = f"🎉 ¡{interaction.user.mention} acertó: **{self.correcta}**!"
            embed_actual.color = discord.Color.green()
        else:
            res_txt = f"❌ {interaction.user.mention} falló. Era: **{self.correcta}**."
            embed_actual.color = discord.Color.red()

        embed_actual.add_field(name="🏆 Resultado", value=res_txt, inline=False)
        await interaction.message.edit(embed=embed_actual, view=self.vista_padre)
        await interaction.response.send_message(f"Elegiste **{self.label}**", ephemeral=True)


class SelectorCategoriaTrivia(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Anime", emoji="⛩️", value="Anime"),
            discord.SelectOption(label="Historia", emoji="🏛️", value="Historia")
        ]
        super().__init__(placeholder="Elige categoría...", options=options)

    async def callback(self, interaction: discord.Interaction):
        cat = self.values[0]
        t = random.choice([p for p in BANCO_TRIVIA if p["cat"] == cat])
        embed = discord.Embed(title=f"🧠 Trivia: {t['cat']}", description=f"**{t['p']}**\n\n*20 segundos para responder 🌸*", color=0x9B59B6)
        embed.set_image(url=t["img"])
        view = VistaTriviaPublica(t)
        await interaction.channel.send(content=f"✅ Trivia de **{cat}** iniciada por {interaction.user.mention}:", embed=embed, view=view)
        await interaction.response.edit_message(content="✅ ¡Trivia iniciada!", embed=None, view=None)


class VistaMenuTrivia(discord.ui.View):
    def __init__(self): super().__init__(timeout=30); self.add_item(SelectorCategoriaTrivia())


@client.tree.command(name="trivia", description="Trivia pública con botones y GIF")
async def trivia(interaction: discord.Interaction):
    embed = discord.Embed(title="🧠 Selector de Trivia", description="Elige la categoría:", color=0x3498DB)
    await interaction.response.send_message(embed=embed, view=VistaMenuTrivia(), ephemeral=True)


client.run(os.environ['DISCORD_TOKEN'])