import os
import random
import asyncio
import discord
from discord import app_commands

# Configuración global del bot y canales/roles
config_global = {
    "rol_comandos_id": None,  
    "rol_atencion_id": None,   
    "canal_logs_id": None,     # Canal donde se envían los resultados de postulaciones
    "contador_postulaciones": 0, 
    "embed_juegos_titulo": "🎮 Zona de Juegos e Interacción",
    "embed_juegos_desc": "¡Diviértete con los minijuegos multijugador y nuestra trivia masiva estilo Nekotrivia!",
    "embed_juegos_color": 0xF1C40F
}

# Base de datos en memoria para formularios
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

# 🧠 BANCO DE TRIVIA LIMPIO Y SIN NÚMEROS ESTILO NEKOTRIVIA
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
        "p": "¿Qué deporte juega apasionadamente el equipo Karasuno en Haikyuu?",
        "correcta": "Voleibol",
        "opciones": ["Baloncesto", "Fútbol", "Voleibol", "Béisbol"],
        "cat": "Anime",
        "img": "https://media.giphy.com/media/BEob5qwFkSJ7G/giphy.gif"
    },
    {
        "p": "¿Cómo se llama el espadachín de tres espadas en One Piece?",
        "correcta": "Zoro",
        "opciones": ["Sanji", "Zoro", "Luffy", "Shanks"],
        "cat": "Anime",
        "img": "https://media.giphy.com/media/13sL05U54IPEek/giphy.gif"
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
    },
    {
        "p": "¿Qué imperio antiguo construyó el famoso Coliseo Romano?",
        "correcta": "Imperio Romano",
        "opciones": ["Imperio Griego", "Imperio Persa", "Imperio Romano", "Imperio Otomano"],
        "cat": "Historia",
        "img": "https://media.giphy.com/media/xT5LMGvD9WivxcK9c4/giphy.gif"
    }
]

for i in range(290):
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
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("¡Slash commands sincronizados!")

client = Bot()

@client.event
async def on_ready():
    print(f'¡Bot conectado con éxito como {client.user}!')

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if client.user in message.mentions:
        embed = discord.Embed(
            title="✨ ¡Hola! Soy Nexus Bot — Tu Centro de Control",
            description="> *Sistema automatizado de gestión, postulaciones seguras y entretenimiento multijugador.*\n\nResumen de módulos activos:",
            color=0x5865F2
        )
        if client.user.avatar:
            embed.set_thumbnail(url=client.user.avatar.url)

        embed.add_field(name="🛠️ Configuración", value="• `/configuracion` ➜ Roles y diseño de embeds.", inline=False)
        embed.add_field(name="📋 Postulaciones Seguras", value="• `/postulacion_staff` | `/postulacion_casa-ally` | `/postulaicon_redes` | `/postulacion_nexus`\n*✨ Solo el postulante asignado puede responder.*", inline=False)
        embed.add_field(name="🎯 Zona de Juegos Multijugador", value="• `/juegos` • `/dado` • `/ppt` • `/trivia` • `/adivina_palabra` • `/colgado`", inline=False)
        embed.set_footer(text=f"Solicitado por {message.author.display_name}", icon_url=message.author.display_avatar.url)
        await message.channel.send(embed=embed)


def verificar_permisos_comandos(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator: 
        return True
    if config_global["rol_comandos_id"]:
        rol = interaction.guild.get_role(config_global["rol_comandos_id"])
        if rol and rol in interaction.user.roles: 
            return True
    return False

def verificar_permisos_atencion(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator: 
        return True
    if config_global["rol_atencion_id"]:
        rol = interaction.guild.get_role(config_global["rol_atencion_id"])
        if rol and rol in interaction.user.roles: 
            return True
    return False


# --- MODALES DE CONFIGURACIÓN DE FORMULARIOS Y ROLES ---

class ModalConfigFormulario(discord.ui.Modal):
    def __init__(self, tipo: str, nombre_bonito: str):
        super().__init__(title=f"Configurar {nombre_bonito}")
        self.tipo = tipo
        cfg_actual = postulaciones_config.get(tipo, {})
        preguntas_actuales = "\n".join(cfg_actual.get("preguntas", []))
        color_actual_hex = f"#{cfg_actual.get('color', 3498335):06x}"

        self.input_titulo = discord.ui.TextInput(label="Título del Embed", default=cfg_actual.get("titulo", ""), required=True, max_length=100)
        self.input_color = discord.ui.TextInput(label="Color Hex (ej: #3498db)", default=color_actual_hex, required=True, max_length=7)
        self.input_preguntas = discord.ui.TextInput(label="Preguntas (una por línea)", style=discord.TextStyle.paragraph, default=preguntas_actuales, required=True, max_length=1000)

        self.add_item(self.input_titulo)
        self.add_item(self.input_color)
        self.add_item(self.input_preguntas)

    async def on_submit(self, interaction: discord.Interaction):
        try: nuevo_color = int(self.input_color.value.strip().replace("#", ""), 16)
        except: return await interaction.response.send_message("❌ Código HEX inválido.", ephemeral=True)

        nuevas_preguntas = [p.strip() for p in self.input_preguntas.value.split('\n') if p.strip()]
        postulaciones_config[self.tipo] = {"titulo": self.input_titulo.value.strip(), "color": nuevo_color, "preguntas": nuevas_preguntas}
        await interaction.response.send_message(f"✅ ¡Formulario de **{self.tipo.upper()}** actualizado!", ephemeral=True)


class ModalConfigRolesCanal(discord.ui.Modal, title="Configurar Roles y Canal de Logs"):
    rol_cmd_id = discord.ui.TextInput(label="ID Rol Ejecutar Postulación", default=str(config_global["rol_comandos_id"] or ""), required=False, max_length=20)
    rol_atc_id = discord.ui.TextInput(label="ID Rol Staff (Aprobar/Rechazar)", default=str(config_global["rol_atencion_id"] or ""), required=False, max_length=20)
    canal_log_id = discord.ui.TextInput(label="ID Canal de Registro / Logs", default=str(config_global["canal_logs_id"] or ""), required=False, max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.rol_cmd_id.value.strip(): config_global["rol_comandos_id"] = int(self.rol_cmd_id.value.strip())
            else: config_global["rol_comandos_id"] = None

            if self.rol_atc_id.value.strip(): config_global["rol_atencion_id"] = int(self.rol_atc_id.value.strip())
            else: config_global["rol_atencion_id"] = None

            if self.canal_log_id.value.strip(): config_global["canal_logs_id"] = int(self.canal_log_id.value.strip())
            else: config_global["canal_logs_id"] = None

            await interaction.response.send_message("✅ ¡Roles y canales de registro actualizados correctamente!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Asegúrate de ingresar IDs numéricos válidos de Discord.", ephemeral=True)


class ModalConfigJuegos(discord.ui.Modal, title="Personalizar Embed de Juegos"):
    titulo = discord.ui.TextInput(label="Título", default=config_global["embed_juegos_titulo"], required=True)
    descripcion = discord.ui.TextInput(label="Descripción", style=discord.TextStyle.paragraph, default=config_global["embed_juegos_desc"], required=True)
    color = discord.ui.TextInput(label="Color Hex", default=f"#{config_global['embed_juegos_color']:06x}", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try: nuevo_color = int(self.color.value.strip().replace("#", ""), 16)
        except: return await interaction.response.send_message("❌ Color inválido.", ephemeral=True)
        config_global["embed_juegos_titulo"] = self.titulo.value
        config_global["embed_juegos_desc"] = self.descripcion.value
        config_global["embed_juegos_color"] = nuevo_color
        await interaction.response.send_message("✅ ¡Embed de juegos actualizado!", ephemeral=True)


class VistaConfiguracion(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛡️ Configurar Roles y Canal", style=discord.ButtonStyle.danger, row=0)
    async def btn_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigRolesCanal())

    @discord.ui.button(label="📝 Config. Staff", style=discord.ButtonStyle.primary, row=1)
    async def btn_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("staff", "Moderación"))

    @discord.ui.button(label="📝 Config. Ally", style=discord.ButtonStyle.primary, row=1)
    async def btn_ally(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("ally", "Alianza"))

    @discord.ui.button(label="📝 Config. Redes", style=discord.ButtonStyle.primary, row=2)
    async def btn_redes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("redes", "Redes"))

    @discord.ui.button(label="📝 Config. Nexus", style=discord.ButtonStyle.primary, row=2)
    async def btn_nexus(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("nexus", "Programación"))

    @discord.ui.button(label="🎨 Editar Embed Juegos", style=discord.ButtonStyle.success, row=3)
    async def btn_juegos(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigJuegos())


# --- POSTULACIONES CON CANDADO Y NOTIFICACIÓN MD / CANAL ---

class ModalResponderFormulario(discord.ui.Modal):
    def __init__(self, tipo: str, num_id: int, preguntas: list, miembro_postulado: discord.Member, config_form: dict):
        super().__init__(title=f"Postulación #{num_id}")
        self.tipo = tipo
        self.num_id = num_id
        self.preguntas = preguntas
        self.miembro_postulado = miembro_postulado
        self.config_form = config_form
        self.inputs = []

        for i, pregunta in enumerate(preguntas[:5]):
            text_input = discord.ui.TextInput(label=pregunta[:45], style=discord.TextStyle.paragraph, placeholder="Escribe aquí...", required=True, max_length=300)
            self.inputs.append(text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        respuestas_texto = ""
        for i, pregunta in enumerate(self.preguntas[:5]):
            respuestas_texto += f"**P{i+1}: {pregunta}**\n↳ {self.inputs[i].value}\n\n"

        embed = discord.Embed(
            title=f"{self.config_form['titulo']} (#{self.num_id})",
            description=f"👤 **Postulante:** {self.miembro_postulado.mention} (`{self.miembro_postulado}`)\n\n{respuestas_texto}",
            color=self.config_form['color']
        )
        embed.set_thumbnail(url=self.miembro_postulado.display_avatar.url)
        embed.set_footer(text=f"Enviado por {interaction.user} | Esperando revisión del Staff.")

        await interaction.message.edit(embed=embed, view=VistaRevisionPostulacion(self.miembro_postulado))
        await interaction.response.send_message("✅ ¡Tus respuestas han sido enviadas correctamente!", ephemeral=True)


class VistaBotonResponder(discord.ui.View):
    def __init__(self, tipo: str, num_id: int, preguntas: list, miembro_postulado: discord.Member, config_form: dict):
        super().__init__(timeout=None)
        self.tipo = tipo
        self.num_id = num_id
        self.preguntas = preguntas
        self.miembro_postulado = miembro_postulado
        self.config_form = config_form

    @discord.ui.button(label="✍️ Responder Formulario", style=discord.ButtonStyle.success, custom_id="btn_responder_form")
    async def responder(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.miembro_postulado.id:
            return await interaction.response.send_message(f"❌ **Acceso denegado:** Este formulario pertenece exclusivamente a {self.miembro_postulado.mention}.", ephemeral=True)
        await interaction.response.send_modal(ModalResponderFormulario(self.tipo, self.num_id, self.preguntas, self.miembro_postulado, self.config_form))


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
        
        # 1. Actualizar el mensaje público
        await interaction.message.edit(embed=embed_actual, view=None)

        # 2. Enviar MD (Mensaje Privado) al candidato
        try:
            embed_md = discord.Embed(
                title=f"📋 Actualización de tu Postulación",
                description=f"Tu postulación (`{embed_actual.title}`) ha sido evaluada.\n\n**Estado:** {estado_titulo}\n**Nota del Staff:** {nota}",
                color=embed_actual.color
            )
            embed_md.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            await self.autor_postulacion.send(embed=embed_md)
        except:
            pass # Si el usuario tiene los MDs cerrados

        # 3. Enviar copia al canal de registros/logs configurado
        if config_global["canal_logs_id"]:
            canal_log = interaction.guild.get_channel(config_global["canal_logs_id"])
            if canal_log:
                try:
                    await canal_log.send(embed=embed_actual)
                except:
                    pass

        await interaction.response.send_message("✅ Postulación procesada con éxito, notificada al candidato y registrada.", ephemeral=True)


class VistaRevisionPostulacion(discord.ui.View):
    def __init__(self, autor_postulacion: discord.Member):
        super().__init__(timeout=None)
        self.autor_postulacion = autor_postulacion

    @discord.ui.button(label="✅ Aprobado", style=discord.ButtonStyle.success, custom_id="btn_aprobar")
    async def aprobar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_permisos_atencion(interaction): return await interaction.response.send_message("❌ No tienes el rol de staff autorizado para revisar.", ephemeral=True)
        await interaction.response.send_modal(ModalNotaStaff("APROBADO", self.autor_postulacion))

    @discord.ui.button(label="❌ Rechazado", style=discord.ButtonStyle.danger, custom_id="btn_rechazar")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_permisos_atencion(interaction): return await interaction.response.send_message("❌ No tienes el rol de staff autorizado para revisar.", ephemeral=True)
        await interaction.response.send_modal(ModalNotaStaff("RECHAZADO", self.autor_postulacion))


# --- COMANDO DE CONFIGURACIÓN CON PANEL VISUAL ---

@client.tree.command(name="configuracion", description="Panel visual para configurar roles, formularios, canal de registro y juegos")
async def configuracion(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ Solo un administrador puede usar este comando.", ephemeral=True)

    r_cmd = interaction.guild.get_role(config_global["rol_comandos_id"]) if config_global["rol_comandos_id"] else "No asignado"
    r_atc = interaction.guild.get_role(config_global["rol_atencion_id"]) if config_global["rol_atencion_id"] else "No asignado"
    c_log = interaction.guild.get_channel(config_global["canal_logs_id"]) if config_global["canal_logs_id"] else "No asignado"

    embed = discord.Embed(
        title="⚙️ Panel de Configuración General",
        description="Utiliza los botones inferiores para configurar los accesos de roles, canales de registro, preguntas de formularios y la zona de juegos.",
        color=0x3498db
    )
    embed.add_field(name="🛡️ Seguridad y Roles", value=f"• **Ejecutar Postulaciones:** {r_cmd.mention if isinstance(r_cmd, discord.Role) else r_cmd}\n• **Revisar / Staff:** {r_atc.mention if isinstance(r_atc, discord.Role) else r_atc}", inline=False)
    embed.add_field(name="📢 Canales", value=f"• **Canal de Registro (Logs):** {c_log.mention if isinstance(c_log, discord.TextChannel) else c_log}", inline=False)

    await interaction.followup.send(embed=embed, view=VistaConfiguracion(), ephemeral=True)


async def enviar_anuncio_postulacion(interaction: discord.Interaction, tipo: str, miembro: discord.Member):
    if not verificar_permisos_comandos(interaction):
        return await interaction.response.send_message("❌ No tienes el rol autorizado para ejecutar comandos de postulación.", ephemeral=True)

    config_form = postulaciones_config.get(tipo, {})
    preguntas = config_form.get("preguntas", [])
    if not preguntas: return await interaction.response.send_message("❌ Este formulario no está configurado.", ephemeral=True)

    config_global["contador_postulaciones"] += 1
    num_id = config_global["contador_postulaciones"]

    embed = discord.Embed(
        title=f"{config_form['titulo']} (#{num_id})",
        description=f"👤 **Candidato:** {miembro.mention}\n⚡ **Iniciado por:** {interaction.user.mention}\n\n*Candado activo: Solo {miembro.mention} puede hacer clic en el botón inferior para responder.*",
        color=config_form['color']
    )
    embed.set_thumbnail(url=miembro.display_avatar.url)

    await interaction.channel.send(embed=embed, view=VistaBotonResponder(tipo, num_id, preguntas, miembro, config_form))
    await interaction.response.send_message(f"✅ ¡Formulario `#{num_id}` enviado al canal!", ephemeral=True)

@client.tree.command(name="postulacion_staff", description="Postulación a Moderación")
@app_commands.describe(miembro="Usuario a postular")
async def postulacion_staff(interaction: discord.Interaction, miembro: discord.Member): await enviar_anuncio_postulacion(interaction, "staff", miembro)

@client.tree.command(name="postulacion_casa-ally", description="Postulación a Casa Alianza")
@app_commands.describe(miembro="Usuario a postular")
async def postulacion_casa_ally(interaction: discord.Interaction, miembro: discord.Member): await enviar_anuncio_postulacion(interaction, "ally", miembro)

@client.tree.command(name="postulaicon_redes", description="Postulación a Redes")
@app_commands.describe(miembro="Usuario a postular")
async def postulaicon_redes(interaction: discord.Interaction, miembro: discord.Member): await enviar_anuncio_postulacion(interaction, "redes", miembro)

@client.tree.command(name="postulacion_nexus", description="Postulación a Programación")
@app_commands.describe(miembro="Usuario a postular")
async def postulacion_nexus(interaction: discord.Interaction, miembro: discord.Member): await enviar_anuncio_postulacion(interaction, "nexus", miembro)


# ==========================================
# 🎮 ZONA DE JUEGOS Y TRIVIA PÚBLICA
# ==========================================

@client.tree.command(name="juegos", description="Menú principal de juegos")
async def juegos(interaction: discord.Interaction):
    embed = discord.Embed(
        title=config_global["embed_juegos_titulo"],
        description=config_global["embed_juegos_desc"] + "\n\n**Comandos Multijugador:**\n• `/dado [caras]` - Lanza un dado.\n• `/ppt [miembro]` - ¡Reta a piedra, papel o tijera a alguien!\n• `/trivia` - Trivia pública interactiva con botones y GIF.\n• `/adivina_palabra` - Adivina por letras.\n• `/colgado` - Ahorcado clásico.",
        color=config_global["embed_juegos_color"]
    )
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="dado", description="Lanza un dado")
@app_commands.describe(caras="Caras del dado")
async def dado(interaction: discord.Interaction, caras: int = 6):
    if caras < 2: return await interaction.response.send_message("❌ Mínimo 2 caras.", ephemeral=True)
    await interaction.response.send_message(f"🎲 {interaction.user.mention} lanzó un dado de {caras} y sacó: **{random.randint(1, caras)}**")

@client.tree.command(name="ppt", description="Juega Piedra, Papel o Tijera contra un miembro o simulación")
@app_commands.describe(adversario="Menciona a un miembro para retarlo (opcional)", eleccion="Tu jugada")
@app_commands.choices(eleccion=[
    app_commands.Choice(name="Piedra", value="piedra"),
    app_commands.Choice(name="Papel", value="papel"),
    app_commands.Choice(name="Tijera", value="tijera")
])
async def ppt(interaction: discord.Interaction, eleccion: str, adversario: discord.Member = None):
    if adversario:
        if adversario.id == interaction.user.id: return await interaction.response.send_message("❌ No puedes retarte a ti mismo.", ephemeral=True)
        if adversario.bot: return await interaction.response.send_message("❌ No puedes retar a un bot.", ephemeral=True)
        view = VistaRetoPPT(interaction.user, adversario, eleccion)
        await interaction.response.send_message(f"⚔ {adversario.mention}, ¡{interaction.user.mention} te ha retado a **Piedra, Papel o Tijera**! Haz clic para aceptar:", view=view)
    else:
        bot_elec = random.choice(["piedra", "papel", "tijera"])
        if eleccion == bot_elec: res = "¡Empate! 🤝"
        elif (eleccion == "piedra" and bot_eleec == "tijera") or (eleccion == "papel" and bot_elec == "piedra") or (eleccion == "tijera" and bot_elec == "papel"): res = "¡Ganaste! 🎉"
        else: res = "¡Gané yo! 🤖"
        await interaction.response.send_message(f"Elegiste **{eleccion}**, yo **{bot_elec}**. {res}")

class VistaRetoPPT(discord.ui.View):
    def __init__(self, retador: discord.Member, retado: discord.Member, jugada_retador: str):
        super().__init__(timeout=30)
        self.retador = retador
        self.retado = retado
        self.jugada_retador = jugada_retador

    @discord.ui.button(label="Aceptar Reto", style=discord.ButtonStyle.success)
    async def aceptar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.retado.id: return await interaction.response.send_message("❌ Este reto no es para ti.", ephemeral=True)
        jugada_retado = random.choice(["piedra", "papel", "tijera"])
        r1, r2 = self.jugada_retador, jugada_retado
        if r1 == r2: res = "¡Empate mutuo! 🤝"
        elif (r1 == "piedra" and r2 == "tijera") or (r1 == "papel" and r2 == "piedra") or (r1 == "tijera" and r2 == "papel"): res = f"🎉 ¡{self.retador.mention} gana el duelo!"
        else: res = f"🎉 ¡{self.retado.mention} gana el duelo!"

        for child in self.children: child.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"⚔️ **Duelo PPT**:\n{self.retador.mention} vs {self.retado.mention}\n\n{res}")


class VistaTriviaPublica(discord.ui.View):
    def __init__(self, pregunta_data: dict, autor: discord.Member):
        super().__init__(timeout=20)
        self.pregunta_data = pregunta_data
        self.autor = autor
        self.respondido = False

        opciones = pregunta_data["opciones"].copy()
        random.shuffle(opciones)

        for op in opciones:
            self.add_item(BotonAlternativa(op, pregunta_data["correcta"], self))

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
        if self.vista_padre.respondido:
            return await interaction.response.send_message("❌ ¡Esta trivia ya ha sido respondida!", ephemeral=True)

        self.vista_padre.respondido = True
        
        for child in self.vista_padre.children:
            child.disabled = True
            if child.label == self.correcta: child.style = discord.ButtonStyle.success
            elif child.label == self.label and child.label != self.correcta: child.style = discord.ButtonStyle.danger

        embed_actual = interaction.message.embeds[0]
        
        if self.label == self.correcta:
            resultado_texto = f"🎉 ¡{interaction.user.mention} ha respondido correctamente: **{self.correcta}**!"
            embed_actual.color = discord.Color.green()
        else:
            resultado_texto = f"❌ {interaction.user.mention} falló. La respuesta correcta era: **{self.correcta}**."
            embed_actual.color = discord.Color.red()

        embed_actual.add_field(name="🏆 Resultado", value=resultado_texto, inline=False)
        await interaction.message.edit(embed=embed_actual, view=self.vista_padre)
        await interaction.response.send_message(f"¡Has seleccionado **{self.label}**!", ephemeral=True)


class SelectorCategoriaTrivia(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Anime", description="Preguntas sobre series, personajes y cultura otaku", emoji="⛩️", value="Anime"),
            discord.SelectOption(label="Historia", description="Acontecimientos mundiales, imperios y personajes célebres", emoji="🏛️", value="Historia")
        ]
        super().__init__(placeholder="Elige la categoría de la Trivia...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        categoria = self.values[0]
        preguntas_filtradas = [p for p in BANCO_TRIVIA if p["cat"] == categoria]
        t = random.choice(preguntas_filtradas)

        embed = discord.Embed(
            title=f"🧠 Trivia Pública: {t['cat']}",
            description=f"**{t['p']}**\n\n*Tienes 20 segundos para seleccionar la respuesta correcta 🌸*",
            color=0x9B59B6
        )
        embed.set_image(url=t["img"])
        embed.set_footer(text=f"Trivia solicitada por {interaction.user.display_name}")

        view = VistaTriviaPublica(t, interaction.user)
        await interaction.response.edit_message(content=f"✅ Trivia de **{categoria}** iniciada en el canal:", embed=None, view=None)
        
        mensaje_publico = await interaction.channel.send(embed=embed, view=view)
        view.message = mensaje_publico


class VistaMenuTrivia(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.add_item(SelectorCategoriaTrivia())


@client.tree.command(name="trivia", description="Inicia una trivia pública con botones interactivos y GIF")
async def trivia(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🧠 Selector de Trivia Masiva",
        description="Selecciona en el menú desplegable de abajo la categoría en la que deseas poner a prueba a todo el servidor:",
        color=0x3498DB
    )
    await interaction.response.send_message(embed=embed, view=VistaMenuTrivia(), ephemeral=True)


@client.tree.command(name="adivina_palabra", description="Juega a adivinar la palabra secreta")
async def adivina_palabra(interaction: discord.Interaction):
    palabras = ["discord", "python", "railway", "programacion", "anime", "historia", "otaku"]
    secreta = random.choice(palabras)
    ocultas = ["_"] * len(secreta)
    intentos = 6
    usadas = set()

    await interaction.response.send_message(f"🎮 **Adivina la Palabra**: `{' '.join(ocultas)}` (6 errores máx). Escribe una letra.")

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and len(m.content) == 1 and m.content.isalpha()

    while intentos > 0 and "_" in ocultas:
        try:
            msg = await client.wait_for('message', timeout=30.0, check=check)
            letra = msg.content.lower()
            try: await msg.delete()
            except: pass

            if letra in usadas: continue
            usadas.add(letra)

            if letra in secreta:
                for i, c in enumerate(secreta):
                    if c == letra: ocultas[i] = letra
            else:
                intentos -= 1

            await interaction.edit_original_response(content=f"🎮 **Palabra**: `{' '.join(ocultas)}` | Usadas: {', '.join(usadas)} | Errores: {intentos}/6")
        except asyncio.TimeoutError:
            return await interaction.edit_original_response(content=f"⏰ ¡Tiempo agotado! Era **{secreta}**.")

    if "_" not in ocultas:
        await interaction.edit_original_response(content=f"🎉 ¡Victoria {interaction.user.mention}! La palabra era **{secreta}**.")
    else:
        await interaction.edit_original_response(content=f"💀 ¡Perdiste! Era **{secreta}**.")


@client.tree.command(name="colgado", description="El clásico juego del ahorcado")
async def colgado(interaction: discord.Interaction):
    palabras = ["otaku", "samurai", "napoleon", "goku", "revolucion", "naruto", "imperio"]
    secreta = random.choice(palabras)
    adivinadas = set()
    fallos = 0
    max_fallos = 6

    def estado(): return "".join([c if c in adivinadas else "_" for c in secreta])

    await interaction.response.send_message(f"🕹️ **Ahorcado**: `{' '.join(estado())}` (Errores: {fallos}/{max_fallos}). Escribe una letra.")

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and len(m.content) == 1 and m.content.isalpha()

    while fallos < max_fallos and "_" in estado():
        try:
            msg = await client.wait_for('message', timeout=25.0, check=check)
            letra = msg.content.lower()
            try: await msg.delete()
            except: pass

            if letra in adivinadas: continue
            adivinadas.add(letra)
            if letra not in secreta: fallos += 1

            await interaction.edit_original_response(content=f"🕹️ **Ahorcado**: `{' '.join(estado())}` | Errores: {fallos}/{max_fallos}")
        except asyncio.TimeoutError:
            return await interaction.edit_original_response(content=f"⏰ ¡Se acabó el tiempo! Era **{secreta}**.")

    if "_" not in estado():
        await interaction.edit_original_response(content=f"🏆 ¡Ganaste {interaction.user.mention}! Era **{secreta}**.")
    else:
        await interaction.edit_original_response(content=f"💀 ¡Ahorcado! Era **{secreta}**.")


client.run(os.environ['DISCORD_TOKEN'])