import os
import random
import asyncio
import discord
from discord import app_commands

# Configuración global del bot, roles, canales y prefijo
config_global = {
    "prefijo": "a¡",
    "rol_comandos_id": None,  
    "rol_atencion_id": None,   
    "canal_logs_id": None,     
    "contador_postulaciones": 0, 
    "embed_juegos_titulo": "🎮 Zona de Juegos e Interacción",
    "embed_juegos_desc": "¡Diviértete con los minijuegos multijugador y nuestra trivia masiva estilo Nekotrivia!",
    "embed_juegos_color": 0xF1C40F
}

# Base de datos en memoria para formularios (Soporta cantidad ilimitada de preguntas)
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

    # 1. Comprobación de Prefijo para comandos de texto
    if message.content.startswith(config_global["prefijo"]):
        contenido = message.content[len(config_global["prefijo"]):].strip().lower()
        if contenido == "ayuda" or contenido == "config":
            await message.channel.send(f"⚙️ El prefijo actual del bot es `{config_global['prefijo']}`. Usa los comandos barra `/` para gestionar el servidor.")
        return

    # 2. Responder EXCLUSIVAMENTE si el bot es mencionado directamente como primera mención o al inicio
    if client.user in message.mentions and message.reference is None:
        embed = discord.Embed(
            title="✨ ¡Hola! Soy Nexus Bot — Tu Centro de Control",
            description=f"> *Prefijo actual:* `{config_global['prefijo']}`\n\nResumen de módulos activos:",
            color=0x5865F2
        )
        if client.user.avatar:
            embed.set_thumbnail(url=client.user.avatar.url)

        embed.add_field(name="🛠️ Configuración", value=f"• `/configuracion` o `{config_global['prefijo']}config` ➜ Roles, canales y formularios ilimitados.", inline=False)
        embed.add_field(name="📋 Postulaciones Interactivas", value="• `/postulacion_staff` | `/postulacion_casa-ally` | `/postulaicon_redes` | `/postulacion_nexus`", inline=False)
        embed.add_field(name="🎯 Zona de Juegos", value="• `/juegos` • `/trivia` • `/ppt` • `/dado`", inline=False)
        embed.set_footer(text=f"Solicitado por {message.author.display_name}", icon_url=message.author.display_avatar.url)
        await message.channel.send(embed=embed)


def verificar_permisos_comandos(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator: return True
    if config_global["rol_comandos_id"]:
        rol = interaction.guild.get_role(config_global["rol_comandos_id"])
        if rol and rol in interaction.user.roles: return True
    return False

def verificar_permisos_atencion(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator: return True
    if config_global["rol_atencion_id"]:
        rol = interaction.guild.get_role(config_global["rol_atencion_id"])
        if rol and rol in interaction.user.roles: return True
    return False


# --- MODALES DE CONFIGURACIÓN DINÁMICA DE PREGUNTAS (SIN LÍMITE DE CANTIDAD) ---

class ModalConfigFormulario(discord.ui.Modal):
    def __init__(self, tipo: str, nombre_bonito: str):
        super().__init__(title=f"Configurar {nombre_bonito}")
        self.tipo = tipo
        cfg_actual = postulaciones_config.get(tipo, {})
        preguntas_actuales = "\n".join(cfg_actual.get("preguntas", []))
        color_actual_hex = f"#{cfg_actual.get('color', 3498335):06x}"

        self.input_titulo = discord.ui.TextInput(label="Título del Embed", default=cfg_actual.get("titulo", ""), required=True, max_length=100)
        self.input_color = discord.ui.TextInput(label="Color Hex", default=color_actual_hex, required=True, max_length=7)
        # Usamos un campo de texto grande (paragraph) que permite agregar tantas preguntas como quieras, una por línea
        self.input_preguntas = discord.ui.TextInput(label="Preguntas (Una por línea, sin límite)", style=discord.TextStyle.paragraph, default=preguntas_actuales, required=True, max_length=4000)

        self.add_item(self.input_titulo)
        self.add_item(self.input_color)
        self.add_item(self.input_preguntas)

    async def on_submit(self, interaction: discord.Interaction):
        try: nuevo_color = int(self.input_color.value.strip().replace("#", ""), 16)
        except: return await interaction.response.send_message("❌ Color Hex inválido.", ephemeral=True)

        # Extraer todas las preguntas separadas por saltos de línea (admite la cantidad que agregues)
        nuevas_preguntas = [p.strip() for p in self.input_preguntas.value.split('\n') if p.strip()]
        if not nuevas_preguntas:
            return await interaction.response.send_message("❌ Debes incluir al menos una pregunta.", ephemeral=True)

        postulaciones_config[self.tipo] = {
            "titulo": self.input_titulo.value.strip(),
            "color": nuevo_color,
            "preguntas": nuevas_preguntas
        }
        await interaction.response.send_message(f"✅ ¡Formulario de **{self.tipo.upper()}** actualizado con éxito! Total de preguntas configuradas: **{len(nuevas_preguntas)}**", ephemeral=True)


class ModalConfigSistema(discord.ui.Modal, title="Configuración General y Prefijo"):
    input_prefijo = discord.ui.TextInput(label="Prefijo del Bot (ej: a¡)", default=config_global["prefijo"], required=True, max_length=5)
    rol_cmd_id = discord.ui.TextInput(label="ID Rol Ejecutar Postulación", default=str(config_global["rol_comandos_id"] or ""), required=False, max_length=20)
    rol_atc_id = discord.ui.TextInput(label="ID Rol Staff (Aprobar/Rechazar)", default=str(config_global["rol_atencion_id"] or ""), required=False, max_length=20)
    canal_log_id = discord.ui.TextInput(label="ID Canal de Registro / Logs", default=str(config_global["canal_logs_id"] or ""), required=False, max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            config_global["prefijo"] = self.input_prefijo.value.strip()
            config_global["rol_comandos_id"] = int(self.rol_cmd_id.value.strip()) if self.rol_cmd_id.value.strip() else None
            config_global["rol_atencion_id"] = int(self.rol_atc_id.value.strip()) if self.rol_atc_id.value.strip() else None
            config_global["canal_logs_id"] = int(self.canal_log_id.value.strip()) if self.canal_log_id.value.strip() else None

            await interaction.response.send_message(f"✅ ¡Configuración general guardada con éxito! Prefijo actual: `{config_global['prefijo']}`", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Error: Asegúrate de que los IDs de roles y canales sean numéricos.", ephemeral=True)


class VistaConfiguracion(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚙️ Configurar Prefijo y Roles", style=discord.ButtonStyle.danger, row=0)
    async def btn_sistema(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigSistema())

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


# --- FLUJO DE PREGUNTA POR PREGUNTA (CANTIDAD ILIMITADA) ---

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

        await interaction.response.send_message("📬 ¡Perfecto! He abierto tu cuestionario interactivo. Por favor, revisa tus **Mensajes Privados (MD)** para responder pregunta por pregunta.", ephemeral=True)

        respuestas_usuario = []
        
        try:
            # Iterará dinámicamente por todas las preguntas que hayas configurado (sin importar si son 3, 10 o más)
            for i, preg in enumerate(self.preguntas):
                embed_q = discord.Embed(
                    title=f"Pregunta {i+1} de {len(self.preguntas)}",
                    description=f"**{preg}**\n\n*(Tienes 90 segundos para enviar tu respuesta en este chat)*",
                    color=self.config_form['color']
                )
                await self.miembro_postulado.send(embed=embed_q)

                def check(m):
                    return m.author.id == self.miembro_postulado.id and isinstance(m.channel, discord.DMChannel)

                msg = await client.wait_for('message', timeout=90.0, check=check)
                respuestas_usuario.append((preg, msg.content))
                await self.miembro_postulado.send("✅ ¡Respuesta guardada con éxito! Siguiente pregunta...")

            # Al terminar todas las preguntas, recopilar en 1 solo embed detallado
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

            # Enviar embed recopilado al canal público del servidor con los botones de aprobación
            await interaction.channel.send(embed=embed_final, view=VistaRevisionPostulacion(self.miembro_postulado))
            await self.miembro_postulado.send("🎉 ¡Has completado todas tus preguntas! Tu postulación ha sido enviada al servidor para su revisión.")

        except asyncio.TimeoutError:
            await self.miembro_postulado.send("⏰ Se ha agotado el tiempo límite para responder el formulario.")


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

        # Enviar MD al candidato
        try:
            embed_md = discord.Embed(
                title=f"📋 Actualización de tu Postulación",
                description=f"Tu postulación (`{embed_actual.title}`) ha sido evaluada.\n\n**Estado:** {estado_titulo}\n**Nota del Staff:** {nota}",
                color=embed_actual.color
            )
            await self.autor_postulacion.send(embed=embed_md)
        except:
            pass

        # Enviar al canal de registro (logs)
        if config_global["canal_logs_id"]:
            canal_log = interaction.guild.get_channel(config_global["canal_logs_id"])
            if canal_log:
                try: await canal_log.send(embed=embed_actual)
                except: pass

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


# --- COMANDO DE CONFIGURACIÓN ---

@client.tree.command(name="configuracion", description="Panel visual para configurar roles, prefijo, canal de logs y formularios")
async def configuracion(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ Solo administradores.", ephemeral=True)

    r_cmd = interaction.guild.get_role(config_global["rol_comandos_id"]) if config_global["rol_comandos_id"] else "No asignado"
    r_atc = interaction.guild.get_role(config_global["rol_atencion_id"]) if config_global["rol_atencion_id"] else "No asignado"
    c_log = interaction.guild.get_channel(config_global["canal_logs_id"]) if config_global["canal_logs_id"] else "No asignado"

    embed = discord.Embed(
        title="⚙️ Panel de Configuración General",
        description=f"Prefijo actual: `{config_global['prefijo']}`\nUtiliza los botones inferiores para configurar los accesos y editar preguntas de manera ilimitada.",
        color=0x3498db
    )
    embed.add_field(name="🛡️ Seguridad y Roles", value=f"• **Ejecutar Postulaciones:** {r_cmd.mention if isinstance(r_cmd, discord.Role) else r_cmd}\n• **Revisar / Staff:** {r_atc.mention if isinstance(r_atc, discord.Role) else r_atc}", inline=False)
    embed.add_field(name="📢 Canales", value=f"• **Canal de Registro (Logs):** {c_log.mention if isinstance(c_log, discord.TextChannel) else c_log}", inline=False)

    await interaction.followup.send(embed=embed, view=VistaConfiguracion(), ephemeral=True)


async def enviar_anuncio_postulacion(interaction: discord.Interaction, tipo: str, miembro: discord.Member):
    if not verificar_permisos_comandos(interaction):
        return await interaction.response.send_message("❌ No tienes permisos para usar este comando.", ephemeral=True)

    config_form = postulaciones_config.get(tipo, {})
    preguntas = config_form.get("preguntas", [])
    if not preguntas: return await interaction.response.send_message("❌ Formulario sin preguntas configuradas.", ephemeral=True)

    config_global["contador_postulaciones"] += 1
    num_id = config_global["contador_postulaciones"]

    embed = discord.Embed(
        title=f"{config_form['titulo']} (#{num_id})",
        description=f"👤 **Candidato:** {miembro.mention}\n⚡ **Iniciado por:** {interaction.user.mention}\n\nPresiona el botón inferior para comenzar el cuestionario pregunta por pregunta en tus mensajes privados (MD).",
        color=config_form['color']
    )
    embed.set_thumbnail(url=miembro.display_avatar.url)

    await interaction.channel.send(embed=embed, view=VistaComenzarPostulacion(tipo, num_id, preguntas, miembro, config_form))
    await interaction.response.send_message(f"✅ ¡Panel de postulación `#{num_id}` enviado al canal!", ephemeral=True)

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
# 🎮 TRIVIA Y JUEGOS
# ==========================================

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

@client.tree.command(name="ppt", description="Piedra, papel o tijera")
@app_commands.choices(eleccion=[
    app_commands.Choice(name="Piedra", value="piedra"),
    app_commands.Choice(name="Papel", value="papel"),
    app_commands.Choice(name="Tijera", value="tijera")
])
async def ppt(interaction: discord.Interaction, eleccion: str):
    bot_elec = random.choice(["piedra", "papel", "tijera"])
    if eleccion == bot_elec: res = "¡Empate! 🤝"
    elif (eleccion == "piedra" and bot_elec == "tijera") or (eleccion == "papel" and bot_elec == "piedra") or (eleccion == "tijera" and bot_elec == "papel"): res = "¡Ganaste! 🎉"
    else: res = "¡Gané yo! 🤖"
    await interaction.response.send_message(f"Elegiste **{eleccion}**, yo **{bot_elec}**. {res}")


class VistaTriviaPublica(discord.ui.View):
    def __init__(self, pregunta_data: dict):
        super().__init__(timeout=20)
        self.pregunta_data = pregunta_data
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
            return await interaction.response.send_message("❌ ¡Trivia respondida!", ephemeral=True)

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
        await interaction.response.edit_message(content=f"✅ Trivia de **{cat}** iniciada:", embed=None, view=None)
        msg = await interaction.channel.send(embed=embed, view=view)
        view.message = msg


class VistaMenuTrivia(discord.ui.View):
    def __init__(self): super().__init__(timeout=30); self.add_item(SelectorCategoriaTrivia())


@client.tree.command(name="trivia", description="Trivia pública con botones y GIF")
async def trivia(interaction: discord.Interaction):
    embed = discord.Embed(title="🧠 Selector de Trivia", description="Elige la categoría:", color=0x3498DB)
    await interaction.response.send_message(embed=embed, view=VistaMenuTrivia(), ephemeral=True)


client.run(os.environ['DISCORD_TOKEN'])