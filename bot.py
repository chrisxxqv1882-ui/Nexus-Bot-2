import discord
from discord.ext import commands
from discord import app_commands
import os
import random

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Diccionarios en memoria para almacenar configuraciones, eventos activos y datos de juegos
CONFIGURACION_SERVER = {
    "roles_evento": [],
    "canal_sugerencias": None,
    "roles_sugerencias": [],
    "canal_postulaciones": None,
    "formularios": {},
    "embeds_config": {},
    "seguridad_antibot": False,
    "seguridad_antiraid": False,
    "seguridad_antispam": False,
    "whitelist": [],
    "canal_moderacion": None
}

EVENTOS_ACTIVOS = {}
POSTULACIONES_EN_CURSO = {}
CASOS_MODERACION = []

# --- VISTAS INTERACTIVAS Y BOTONES ---

class VistaParticiparEvento(discord.ui.View):
    def __init__(self, evento_id: str):
        super().__init__(timeout=None)
        self.evento_id = evento_id
        self.participantes = set()

    @discord.ui.button(label="Participar", style=discord.ButtonStyle.green, emoji="🎉", custom_id="btn_participar_evento")
    async def participar_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.participantes:
            self.participantes.remove(interaction.user.id)
            await interaction.response.send_message("Te has retirado del evento.", ephemeral=True)
        else:
            self.participantes.add(interaction.user.id)
            await interaction.response.send_message("¡Te has inscrito al evento exitosamente!", ephemeral=True)
        
        # Actualizar el embed con el contador de participantes
        try:
            embed = interaction.message.embeds[0]
            # Buscar o actualizar el campo de participantes
            actualizado = False
            for i, field in enumerate(embed.fields):
                if field.name == "Participantes":
                    embed.set_field_at(i, name="Participantes", value=f"👥 {len(self.participantes)} miembros participando", inline=False)
                    actualizado = True
                    break
            if not actualizado:
                embed.add_field(name="Participantes", value=f"👥 {len(self.participantes)} miembros participando", inline=False)
            await interaction.message.edit(embed=embed, view=self)
        except Exception:
            pass

class VistaPostulacionCanal(discord.ui.View):
    def __init__(self, nombre_formulario: str):
        super().__init__(timeout=None)
        self.nombre_formulario = nombre_formulario

    @discord.ui.button(label="Iniciar Formulario", style=discord.ButtonStyle.blurple, emoji="📝", custom_id="btn_iniciar_formulario")
    async def iniciar_formulario(self, interaction: discord.Interaction, button: discord.ui.Button):
        usuario = interaction.user
        if usuario.id in POSTULACIONES_EN_CURSO:
            await interaction.response.send_message("Ya tienes una postulación activa en curso. Revisa tus Mensajes Directos (MD).", ephemeral=True)
            return

        POSTULACIONES_EN_CURSO[usuario.id] = {"formulario": self.nombre_formulario, "paso": 0, "respuestas": []}
        
        try:
            dm_channel = await usuario.create_dm()
            embed_dm = discord.Embed(
                title=f"Postulación: {self.nombre_formulario}",
                description="Has iniciado el proceso de postulación. Responde a continuación a cada pregunta que te haré. Al terminar, el chat se limpiará y se enviará al staff.",
                color=discord.Color.blue()
            )
            await dm_channel.send(embed=embed_dm)
            await dm_channel.send("Pregunta 1/3: ¿Cuál es tu experiencia previa en este rol o puesto?")
            await interaction.response.send_message("¡Te he enviado un mensaje privado (MD) para comenzar el formulario!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("No pude enviarte un mensaje privado. Asegúrate de tener los MD abiertos para miembros del servidor.", ephemeral=True)
            del POSTULACIONES_EN_CURSO[usuario.id]

class VistaAprobarRechazarPostulacion(discord.ui.View):
    def __init__(self, postulante_id: int):
        super().__init__(timeout=None)
        self.postulante_id = postulante_id

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.green, emoji="✅")
    async def aprobar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Postulación aprobada. Notificando al usuario...", ephemeral=True)
        try:
            user = await interaction.client.fetch_user(self.postulante_id)
            await user.send("🎉 ¡Felicidades! Tu postulación ha sido **APROBADA** por el equipo de staff.")
        except Exception:
            pass
        self.disable_all_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Rechazar", style=discord.ButtonStyle.red, emoji="❌")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Postulación rechazada. Notificando al usuario...", ephemeral=True)
        try:
            user = await interaction.client.fetch_user(self.postulante_id)
            await user.send("❌ Lamentamos informarte que tu postulación ha sido **RECHAZADA** en esta ocasión.")
        except Exception:
            pass
        self.disable_all_items()
        await interaction.message.edit(view=self)

class ConfigSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Postulaciones", description="Configurar formularios, canales y roles de staff", emoji="📝"),
            discord.SelectOption(label="Eventos", description="Configurar roles organizadores y embeds de eventos", emoji="🎉"),
            discord.SelectOption(label="Sugerencias", description="Canal de sugerencias y roles con permisos", emoji="💡"),
            discord.SelectOption(label="Moderación", description="Registros de sanciones, baneos y casos", emoji="⚖️"),
            discord.SelectOption(label="Seguridad", description="Anti-Bot, Anti-Raid, Anti-Spam y White-List", emoji="🔒")
        ]
        super().__init__(placeholder="Selecciona el sistema que deseas configurar...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        opcion = self.values[0]
        embed = discord.Embed(
            title=f"Configuración de {opcion}",
            description=f"Panel exclusivo para ajustar los parámetros de **{opcion}**.",
            color=discord.Color.dark_theme()
        )
        if opcion == "Postulaciones":
            embed.add_field(name="Estado actual", value="Usa los comandos de configuración para agregar formularios y vincular canales.", inline=False)
        elif opcion == "Eventos":
            embed.add_field(name="Roles Organizadores", value=f"{len(CONFIGURACION_SERVER['roles_evento'])} roles configurados.", inline=False)
        elif opcion == "Seguridad":
            embed.add_field(name="Anti-Bot", value=str(CONFIGURACION_SERVER["seguridad_antibot"]), inline=True)
            embed.add_field(name="Anti-Raid", value=str(CONFIGURACION_SERVER["seguridad_antiraid"]), inline=True)
            embed.add_field(name="Anti-Spam", value=str(CONFIGURACION_SERVER["seguridad_antispam"]), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ConfigSelect())

# --- NUCLEO DEL BOT ---

class NexusBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="n!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.tree.sync()
        print("Comandos Slash de Nexus sincronizados globalmente.")

client = NexusBot()

@client.event
async def on_ready():
    print(f'¡Nexus está en línea como {client.user}!')
    await client.change_presence(activity=discord.Game(name="/help | /configuración"))

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # Mención directa (ignora si es una respuesta a otro mensaje)
    if client.user in message.mentions and message.reference is None:
        if str(client.user.id) in message.content:
            embed = discord.Embed(
                title="¡Hola! Soy Nexus 🌌",
                description="Soy tu bot multifuncional con sistemas avanzados de eventos, juegos, moderación y postulaciones.\n\nEscribe `/configuración` para ajustar mis sistemas o `/help` para ver la guía.",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=client.user.display_avatar.url)
            await message.channel.send(embed=embed)

    # Manejo de respuestas en MD para Postulaciones
    if isinstance(message.channel, discord.DMChannel) and message.author.id in POSTULACIONES_EN_CURSO:
        data = POSTULACIONES_EN_CURSO[message.author.id]
        data["respuestas"].append(message.content)
        data["paso"] += 1
        
        if data["paso"] == 1:
            await message.channel.send("Pregunta 2/3: ¿Por qué deberíamos escogerte a ti?")
        elif data["paso"] == 2:
            await message.channel.send("Pregunta 3/3: ¿Cuánto tiempo libre tienes disponible para aportar al servidor?")
        elif data["paso"] >= 3:
            await message.channel.send("¡Formulario completado con éxito! Tus respuestas han sido enviadas al equipo de staff.")
            
            # Enviar embed al canal de postulaciones configurado
            canal_id = CONFIGURACION_SERVER.get("canal_postulaciones")
            if canal_id:
                canal = client.get_channel(canal_id)
                if canal:
                    embed_post = discord.Embed(
                        title=f"Nueva Postulación: {data['formulario']}",
                        description=f"**Postulante:** {message.author.mention} (`{message.author.id}`)",
                        color=discord.Color.green()
                    )
                    embed_post.add_field(name="Experiencia", value=data["respuestas"][0], inline=False)
                    embed_post.add_field(name="Motivación", value=data["respuestas"][1], inline=False)
                    embed_post.add_field(name="Disponibilidad", value=data["respuestas"][2], inline=False)
                    
                    view_post = VistaAprobarRechazarPostulacion(message.author.id)
                    await canal.send(embed=embed_post, view=view_post)
            
            del POSTULACIONES_EN_CURSO[message.author.id]
        return

    # Sugerencias automáticas si el canal coincide
    if CONFIGURACION_SERVER.get("canal_sugerencias") and message.channel.id == CONFIGURACION_SERVER["canal_sugerencias"]:
        embed_sug = discord.Embed(
            title="💡 Nueva Sugerencia",
            description=message.content,
            color=discord.Color.gold()
        )
        embed_sug.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        try:
            await message.delete()
        except Exception:
            pass
        sug_msg = await message.channel.send(embed=embed_sug)
        await sug_msg.add_reaction("👍")
        await sug_msg.add_reaction("👎")
        return

    await client.process_commands(message)

# --- COMANDOS SLASH ---

@client.tree.command(name="dado", description="Lanza un dado de hasta 16 caras.")
async def dado(interaction: discord.Interaction):
    resultado = random.randint(1, 16)
    embed = discord.Embed(
        title="🎲 Lanzamiento de Dado",
        description=f"El dado de 16 caras ha girado y cayó en: **{resultado} / 16**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="ppt", description="Juega Piedra, Papel o Tijera con otro usuario a la vez.")
@app_commands.describe(adversario="El usuario con el que deseas jugar")
async def ppt(interaction: discord.Interaction, adversario: discord.Member):
    if adversario.bot or adversario == interaction.user:
        await interaction.response.send_message("No puedes jugar contigo mismo o contra un bot.", ephemeral=True)
        return
    await interaction.response.send_message(f"¡Reto de PPT entre {interaction.user.mention} y {adversario.mention}! Selección simultánea en proceso.", ephemeral=False)

@client.tree.command(name="trivia", description="Inicia una trivia de Anime, Videojuegos o Historia.")
@app_commands.choices(categoria=[
    app_commands.Choice(name="Anime", value="anime"),
    app_commands.Choice(name="Videojuegos", value="videojuegos"),
    app_commands.Choice(name="Historia", value="historia")
])
async def trivia(interaction: discord.Interaction, categoria: str):
    banco = {
        "anime": {"prega": "¿Cómo se llama el protagonista de Naruto?", "resp": "Naruto Uzumaki", "img": "https://i.imgur.com/example1.png"},
        "videojuegos": {"prega": "¿De qué franquicia es Master Chief?", "resp": "Halo", "img": "https://i.imgur.com/example2.png"},
        "historia": {"prega": "¿En qué año terminó la Segunda Guerra Mundial?", "resp": "1945", "img": "https://i.imgur.com/example3.png"}
    }
    item = banco.get(categoria)
    embed = discord.Embed(title=f"Trivia de {categoria.capitalize()}", description=item["prega"], color=discord.Color.gold())
    embed.set_image(url=item["img"])
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="adivina-la-palabra", description="Juego de adivinar la palabra según temática y jugadores.")
@app_commands.choices(
    jugadores=[app_commands.Choice(name="2 Jugadores", value=2), app_commands.Choice(name="3 Jugadores", value=3), app_commands.Choice(name="4 Jugadores", value=4)],
    tematica=[app_commands.Choice(name="Anime", value="anime"), app_commands.Choice(name="Historia", value="historia"), app_commands.Choice(name="Videojuegos", value="videojuegos")]
)
async def adivina_la_palabra(interaction: discord.Interaction, jugadores: int, tematica: str):
    palabras = {"anime": "GOKU", "historia": "NAPOLEON", "videojuegos": "ZELDA"}
    palabra_oculta = palabras.get(tematica, "DISCORD")
    embed = discord.Embed(
        title="🎮 Adivina la Palabra",
        description=f"Temática: **{tematica.capitalize()}** | Modo: **{jugadores} Jugadores**\n\nLa palabra oculta tiene `{len(palabra_oculta)}` letras: `_ ` * (longitud)",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="organizar-evento", description="Organiza un evento con opción de premios, tiempos y botón de participación.")
@app_commands.describe(titulo="Título del evento", descripcion="Descripción general", canal="Canal donde se enviará el evento", premio="Premio opcional", tiempo="Duración opcional")
async def organizar_evento(interaction: discord.Interaction, titulo: str, descripcion: str, canal: discord.TextChannel, premio: str = None, tiempo: str = None):
    evento_id = str(random.randint(1000, 9999))
    embed = discord.Embed(
        title=f"🎉 Evento: {titulo}",
        description=descripcion,
        color=discord.Color.orange()
    )
    if premio:
        embed.add_field(name="🎁 Premio", value=premio, inline=True)
    if tiempo:
        embed.add_field(name="⏰ Duración", value=tiempo, inline=True)
    
    embed.add_field(name="Participantes", value="👥 0 miembros participando", inline=False)
    
    view = VistaParticiparEvento(evento_id)
    msg = await canal.send(embed=embed, view=view)
    EVENTOS_ACTIVOS[evento_id] = {"msg_id": msg.id, "canal_id": canal.id, "titulo": titulo}
    
    await interaction.response.send_message(f"✅ Evento `{evento_id}` creado y enviado correctamente a {canal.mention}.", ephemeral=True)

@client.tree.command(name="iniciar-evento", description="Inicia un evento activo.")
@app_commands.describe(evento_id="ID del evento activo")
async def iniciar_evento(interaction: discord.Interaction, evento_id: str):
    if evento_id in EVENTOS_ACTIVOS:
        await interaction.response.send_message(f"🚀 El evento `{evento_id}` ha dado comienzo oficialmente.", ephemeral=False)
    else:
        await interaction.response.send_message("No se encontró ningún evento activo con ese ID.", ephemeral=True)

@client.tree.command(name="finalizar-evento", description="Finaliza un evento y anuncia ganadores.")
@app_commands.describe(evento_id="ID del evento", ganador="Mención del ganador o top 3")
async def finalizar_evento(interaction: discord.Interaction, evento_id: str, ganador: str):
    if evento_id in EVENTOS_ACTIVOS:
        evento = EVENTOS_ACTIVOS.pop(evento_id)
        embed = discord.Embed(
            title=f"🏁 Evento Finalizado: {evento['titulo']}",
            description=f"¡El evento ha concluido con éxito!\n\n🏆 **Ganador(es):** {ganador}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("ID de evento inválido o ya finalizado.", ephemeral=True)

@client.tree.command(name="configuración", description="Panel central de configuración de Nexus.")
async def configuracion(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Necesitas permisos de Administrador para usar este comando.", ephemeral=True)
        return

    embed = discord.Embed(
        title="⚙️ Panel de Configuración Principal - Nexus",
        description="Bienvenido al centro de control. Selecciona una categoría en el menú desplegable para configurar eventos, postulaciones, sugerencias, moderación y seguridad.",
        color=discord.Color.blurple()
    )
    view = ConfigView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@client.tree.command(name="help", description="Guía y explicación rápida de la configuración de Nexus.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Guía de Ayuda - Nexus",
        description="Bienvenido a Nexus, tu bot multifuncional completo.",
        color=discord.Color.blurple()
    )
    embed.add_field(name="⚙️ /configuración", value="Panel central para ajustar módulos.", inline=False)
    embed.add_field(name="🎮 Minijuegos", value="`/ppt`, `/trivia`, `/adivina-la-palabra`, `/dado`.", inline=False)
    embed.add_field(name="🎉 Eventos y Postulaciones", value="`/organizar-evento`, formularios por MD con aprobación.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

client.run(os.environ['DISCORD_TOKEN'])
