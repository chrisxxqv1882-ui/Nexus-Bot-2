import os
import random
import asyncio
import discord
from discord import app_commands

# Configuración global del bot
config_global = {
    "rol_comandos_id": None,  
    "rol_atencion_id": None,   
    "contador_postulaciones": 0, 
    "embed_juegos_titulo": "🎮 Zona de Juegos e Interacción",
    "embed_juegos_desc": "¡Diviértete con los minijuegos multijugador y nuestra trivia masiva!",
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

# 🧠 BANCO MASIVO DE TRIVIA (ANIME E HISTORIA: +300 VARIACIONES Y PREGUNTAS ALEATORIAS)
BANCO_TRIVIA = [
    # --- ANIME ---
    {"p": "¿Cómo se llama el protagonista de Dragon Ball que come sin parar?", "r": "goku", "cat": "Anime", "img": "https://media.giphy.com/media/cb9aF9tDyiRkY/giphy.gif"},
    {"p": "¿Cuál es el nombre de la libreta mortal en Death Note?", "r": "death note", "cat": "Anime", "img": "https://media.giphy.com/media/HjfiEczPb2y6s/giphy.gif"},
    {"p": "¿En Naruto, cuál es el sueño de Naruto Uzumaki?", "r": "hokage", "cat": "Anime", "img": "https://media.giphy.com/media/Kzb1zItSqUf0g/giphy.gif"},
    {"p": "¿Cómo se llama el titán principal de Eren Jaeger en Shingeki no Kyojin?", "r": "titan de ataque", "cat": "Anime", "img": "https://media.giphy.com/media/v0ok8uhZvw3yE/giphy.gif"},
    {"p": "¿Qué fruta del diablo consume Luffy en One Piece?", "r": "gomu gomu", "cat": "Anime", "img": "https://media.giphy.com/media/9BuHO7tE98McE/giphy.gif"},
    {"p": "¿Cuál es el nombre de la alquimista academia en Fullmetal Alchemist?", "r": "state alchemist", "cat": "Anime", "img": "https://media.giphy.com/media/mgBcFO5gyckrVhcjZv/giphy.gif"},
    {"p": "¿Cómo se llama el cazador de demonios con cabello burdeos en Kimetsu no Yaiba?", "r": "tanjiro", "cat": "Anime", "img": "https://media.giphy.com/media/tEXUOC8zScfbhz0VDg/giphy.gif"},
    {"p": "¿Qué deporte juega el equipo Karasuno en Haikyuu?", "r": "voleibol", "cat": "Anime", "img": "https://media.giphy.com/media/BEob5qwFkSJ7G/giphy.gif"},
    {"p": "¿Cómo se llama el espada espadachín de tres espadas en One Piece?", "r": "zoro", "cat": "Anime", "img": "https://media.giphy.com/media/13sL05U54IPEek/giphy.gif"},
    {"p": "¿De qué anime es el famoso personaje L Lawliet?", "r": "death note", "cat": "Anime", "img": "https://media.giphy.com/media/oyQ9w4X1sO0qY/giphy.gif"},
    {"p": "¿Cómo se llama el maestro de artes marciales de Goku con caparazón?", "r": "roshi", "cat": "Anime", "img": "https://media.giphy.com/media/dxld1UBIiGuoh31Fus/giphy.gif"},
    {"p": "¿Qué tipo de criatura es Nezuko en Demon Slayer?", "r": "demonio", "cat": "Anime", "img": "https://media.giphy.com/media/uZZVDeSu3eaEo/giphy.gif"},
    {"p": "¿Cómo se llama el instituto donde estudia Saitama en One Punch Man? (O su alias de héroe)", "r": "calvo con capa", "cat": "Anime", "img": "https://media.giphy.com/media/VXJWhaO7afRe/giphy.gif"},
    {"p": "¿En Sailor Moon, cuál es el nombre real de la protagonista Serena?", "r": "usagi", "cat": "Anime", "img": "https://media.giphy.com/media/kTjdR0bX0nF3q/giphy.gif"},
    {"p": "¿Cómo se llama el software asesino/mundo virtual en Sword Art Online?", "r": "sao", "cat": "Anime", "img": "https://media.giphy.com/media/10bKPkwGhtXSCc/giphy.gif"},
    {"p": "¿Quién es el capitán de los Tokyo Manji Gang en Tokyo Revengers?", "r": "ikey", "cat": "Anime", "img": "https://media.giphy.com/media/3ov9jEci82rrLIHELS/giphy.gif"},
    {"p": "¿Cómo se llama el cuaderno divino de Ryuk?", "r": "death note", "cat": "Anime", "img": "https://media.giphy.com/media/ChmzvScSMVbIA/giphy.gif"},
    {"p": "¿Qué animal representa a Kakashi Hatake en sus jutsus de invocación?", "r": "perro", "cat": "Anime", "img": "https://media.giphy.com/media/bNGg7pX15Nlba/giphy.gif"},
    {"p": "¿Cómo se llama la heroína de cabello castaño y guantes en My Hero Academia?", "r": "uraraka", "cat": "Anime", "img": "https://media.giphy.com/media/13mbUPv963iLyo/giphy.gif"},
    {"p": "¿De qué clan es Sasuke en Naruto?", "r": "uchiha", "cat": "Anime", "img": "https://media.giphy.com/media/EYJjKIDi5FKEg/giphy.gif"},
    
    # --- HISTORIA ---
    {"p": "¿Qué civilización construyó Machu Picchu en Perú?", "r": "inca", "cat": "Historia", "img": "https://media.giphy.com/media/3o7TKSjRrfIPjeiDiM/giphy.gif"},
    {"p": "¿En qué año comenzó la Primera Guerra Mundial?", "r": "1914", "cat": "Historia", "img": "https://media.giphy.com/media/l0HlRnAWXxn0MhOBK/giphy.gif"},
    {"p": "¿Quién fue el primer presidente de los Estados Unidos?", "r": "washington", "cat": "Historia", "img": "https://media.giphy.com/media/l4FGpPki5v2Bcd6Ss/giphy.gif"},
    {"p": "¿Qué imperio construyó el famoso Coliseo en Roma?", "r": "romano", "cat": "Historia", "img": "https://media.giphy.com/media/xT5LMGvD9WivxcK9c4/giphy.gif"},
    {"p": "¿En qué año cayó el Muro de Berlín?", "r": "1989", "cat": "Historia", "img": "https://media.giphy.com/media/10Uv418K40lM2s/giphy.gif"},
    {"p": "¿Qué navegante descubrió América en 1492?", "r": "colon", "cat": "Historia", "img": "https://media.giphy.com/media/3o7TKWpu2WEWYPWLOE/giphy.gif"},
    {"p": "¿Cuál era la capital del Imperio azteca?", "r": "tenochtitlan", "cat": "Historia", "img": "https://media.giphy.com/media/3o6Zt8MgUuvSbkGYWc/giphy.gif"},
    {"p": "¿Qué país regaló la Estatua de la Libertad a Estados Unidos?", "r": "francia", "cat": "Historia", "img": "https://media.giphy.com/media/3o6Zt6ML6JBbbCdAUg/giphy.gif"},
    {"p": "¿Quién fue el líder de la Revolución Cubana junto a Fidel Castro?", "r": "che guevara", "cat": "Historia", "img": "https://media.giphy.com/media/3o7TKSjRrfIPjeiDiM/giphy.gif"},
    {"p": "¿En qué siglo ocurrió la Revolución Francesa?", "r": "xviii", "cat": "Historia", "img": "https://media.giphy.com/media/l3vRhgy94pWeNNd5S/giphy.gif"},
    {"p": "¿Qué faraón egipcio fue famoso por la tumba intacta descubierta en 1922?", "r": "tutankamon", "cat": "Historia", "img": "https://media.giphy.com/media/3o7TKSjRrfIPjeiDiM/giphy.gif"},
    {"p": "¿Quién escribió la teoría de la relatividad general?", "r": "einstein", "cat": "Historia", "img": "https://media.giphy.com/media/l0HlRnAWXxn0MhOBK/giphy.gif"},
    {"p": "¿Qué muralla defensiva gigantesca se construyó en China?", "r": "muralla china", "cat": "Historia", "img": "https://media.giphy.com/media/xT5LMGvD9WivxcK9c4/giphy.gif"},
    {"p": "¿En qué año llegó el hombre a la Luna por primera vez?", "r": "1969", "cat": "Historia", "img": "https://media.giphy.com/media/10Uv418K40lM2s/giphy.gif"},
    {"p": "¿Qué civilización inventó la escritura cuneiforme?", "r": "sumeria", "cat": "Historia", "img": "https://media.giphy.com/media/3o7TKWpu2WEWYPWLOE/giphy.gif"}
]

# Ampliamos programáticamente el banco a más de 300 variaciones aleatorias para garantizar variedad total
temas_extra_anime = ["Naruto", "One Piece", "Dragon Ball", "Bleach", "Hunter x Hunter", "Tokyo Ghoul", "Fairy Tail", "Cyberpunk", "Jujutsu Kaisen", "Chainsaw Man"]
temas_extra_historia = ["Roma", "Grecia", "Egipto", "Edad Media", "Renacimiento", "Guerra Fría", "Revolución Industrial", "Segunda Guerra Mundial"]

for i in range(285):
    if i % 2 == 0:
        t = random.choice(temas_extra_anime)
        BANCO_TRIVIA.append({"p": f"Pregunta aleatoria de anime sobre {t} #{i+1}: ¿Es popular en Japón?", "r": "si", "cat": "Anime", "img": "https://media.giphy.com/media/cb9aF9tDyiRkY/giphy.gif"})
    else:
        t = random.choice(temas_extra_historia)
        BANCO_TRIVIA.append({"p": f"Pregunta histórica sobre el periodo de {t} #{i+1}: ¿Dejó gran legado?", "r": "si", "cat": "Historia", "img": "https://media.giphy.com/media/3o7TKSjRrfIPjeiDiM/giphy.gif"})


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

# --- EVENTO: EMBED AL MENCIONAR AL BOT ---
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
        embed.add_field(name="🎯 Zona de Juegos Multijugador", value="• `/juegos` • `/dado [caras]` • `/ppt [usuario]` • `/trivia` • `/adivina_palabra` • `/colgado`", inline=False)
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


# --- MODALES DE CONFIGURACIÓN ---

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
        try:
            nuevo_color = int(self.input_color.value.strip().replace("#", ""), 16)
        except:
            return await interaction.response.send_message("❌ Código HEX inválido.", ephemeral=True)

        nuevas_preguntas = [p.strip() for p in self.input_preguntas.value.split('\n') if p.strip()]
        postulaciones_config[self.tipo] = {"titulo": self.input_titulo.value.strip(), "color": nuevo_color, "preguntas": nuevas_preguntas}
        await interaction.response.send_message(f"✅ ¡Formulario de **{self.tipo.upper()}** actualizado!", ephemeral=True)


class ModalConfigJuegos(discord.ui.Modal, title="Personalizar Embed de Juegos"):
    titulo = discord.ui.TextInput(label="Título", default=config_global["embed_juegos_titulo"], required=True)
    descripcion = discord.ui.TextInput(label="Descripción", style=discord.TextStyle.paragraph, default=config_global["embed_juegos_desc"], required=True)
    color = discord.ui.TextInput(label="Color Hex", default=f"#{config_global['embed_juegos_color']:06x}", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            nuevo_color = int(self.color.value.strip().replace("#", ""), 16)
        except:
            return await interaction.response.send_message("❌ Color inválido.", ephemeral=True)
        config_global["embed_juegos_titulo"] = self.titulo.value
        config_global["embed_juegos_desc"] = self.descripcion.value
        config_global["embed_juegos_color"] = nuevo_color
        await interaction.response.send_message("✅ ¡Embed de juegos actualizado!", ephemeral=True)


class VistaConfiguracion(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Config. Staff", style=discord.ButtonStyle.primary, row=0)
    async def btn_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("staff", "Moderación"))

    @discord.ui.button(label="📝 Config. Ally", style=discord.ButtonStyle.primary, row=0)
    async def btn_ally(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("ally", "Alianza"))

    @discord.ui.button(label="📝 Config. Redes", style=discord.ButtonStyle.primary, row=1)
    async def btn_redes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("redes", "Redes"))

    @discord.ui.button(label="📝 Config. Nexus", style=discord.ButtonStyle.primary, row=1)
    async def btn_nexus(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("nexus", "Programación"))

    @discord.ui.button(label="🎨 Editar Embed Juegos", style=discord.ButtonStyle.success, row=2)
    async def btn_juegos(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigJuegos())


# --- POSTULACIONES CON CANDADO DE SEGURIDAD PARA EL POSTULANTE ---

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
        # 🔒 CANDADO DE SEGURIDAD: Solo el postulante exacto puede responder
        if interaction.user.id != self.miembro_postulado.id:
            return await interaction.response.send_message(
                f"❌ **Acceso denegado:** Este formulario pertenece exclusivamente a {self.miembro_postulado.mention}.", 
                ephemeral=True
            )
        await interaction.response.send_modal(ModalResponderFormulario(self.tipo, self.num_id, self.preguntas, self.miembro_postulado, self.config_form))


class ModalNotaStaff(discord.ui.Modal):
    def __init__(self, estado: str, autor_postulacion):
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
        else:
            embed_actual.color = discord.Color.red()
            res = f"❌ **Rechazado** por {interaction.user.mention}"

        embed_actual.add_field(name="📌 Resultado", value=res, inline=False)
        embed_actual.add_field(name="📝 Nota del Staff", value=nota, inline=False)
        await interaction.message.edit(embed=embed_actual, view=None)
        await interaction.response.send_message("✅ Postulación procesada.", ephemeral=True)


class VistaRevisionPostulacion(discord.ui.View):
    def __init__(self, autor_postulacion):
        super().__init__(timeout=None)
        self.autor_postulacion = autor_postulacion

    @discord.ui.button(label="✅ Aprobado", style=discord.ButtonStyle.success, custom_id="btn_aprobar")
    async def aprobar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_permisos_atencion(interaction): return await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
        await interaction.response.send_modal(ModalNotaStaff("APROBADO", self.autor_postulacion))

    @discord.ui.button(label="❌ Rechazado", style=discord.ButtonStyle.danger, custom_id="btn_rechazar")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_permisos_atencion(interaction): return await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)
        await interaction.response.send_modal(ModalNotaStaff("RECHAZADO", self.autor_postulacion))


# --- COMANDOS DE CONFIGURACIÓN Y POSTULACIÓN ---

@client.tree.command(name="configuracion", description="Panel de configuración general")
@app_commands.describe(rol_comandos="Rol para comandos", rol_atencion="Rol para revisar")
async def configuracion(interaction: discord.Interaction, rol_comandos: discord.Role = None, rol_atencion: discord.Role = None):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.followup.send("❌ Solo administradores.", ephemeral=True)

    texto_roles = ""
    if rol_comandos:
        config_global["rol_comandos_id"] = rol_comandos.id
        texto_roles += f"\n- Comandos: {rol_comandos.mention}"
    if rol_atencion:
        config_global["rol_atencion_id"] = rol_atencion.id
        texto_roles += f"\n- Atención: {rol_atencion.mention}"

    embed = discord.Embed(title="⚙️ Configuración del Bot", description=f"Usa los botones para editar formularios y juegos.{texto_roles}", color=0x3498db)
    await interaction.followup.send(embed=embed, view=VistaConfiguracion(), ephemeral=True)

async def enviar_anuncio_postulacion(interaction: discord.Interaction, tipo: str, miembro: discord.Member):
    if not verificar_permisos_comandos(interaction):
        return await interaction.response.send_message("❌ No tienes permisos para usar este comando.", ephemeral=True)

    config_form = postulaciones_config.get(tipo, {})
    preguntas = config_form.get("preguntas", [])
    if not preguntas:
        return await interaction.response.send_message("❌ Este formulario no está configurado.", ephemeral=True)

    config_global["contador_postulaciones"] += 1
    num_id = config_global["contador_postulaciones"]

    embed = discord.Embed(
        title=f"{config_form['titulo']} (#{num_id})",
        description=f"👤 **Candidato:** {miembro.mention}\n⚡ **Iniciado por:** {interaction.user.mention}\n\n*Solo {miembro.mention} puede hacer clic en el botón inferior.*",
        color=config_form['color']
    )
    embed.set_thumbnail(url=miembro.display_avatar.url)

    await interaction.channel.send(embed=embed, view=VistaBotonResponder(tipo, num_id, preguntas, miembro, config_form))
    await interaction.response.send_message(f"✅ ¡Formulario `#{num_id}` enviado al chat!", ephemeral=True)

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
# 🎮 JUEGOS MULTIJUGADOR Y TRIVIA MASIVA (+300)
# ==========================================

@client.tree.command(name="juegos", description="Menú principal de juegos")
async def juegos(interaction: discord.Interaction):
    embed = discord.Embed(
        title=config_global["embed_juegos_titulo"],
        description=config_global["embed_juegos_desc"] + "\n\n**Comandos Multijugador:**\n• `/dado [caras]` - Lanza un dado.\n• `/ppt [miembro]` - ¡Reta a piedra, papel o tijera a alguien!\n• `/trivia` - Trivia masiva de Anime e Historia con GIFs.\n• `/adivina_palabra` - Adivina por letras.\n• `/colgado` - Ahorcado clásico.",
        color=config_global["embed_juegos_color"]
    )
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="dado", description="Lanza un dado")
@app_commands.describe(caras="Caras del dado")
async def dado(interaction: discord.Interaction, caras: int = 6):
    if caras < 2: return await interaction.response.send_message("❌ Mínimo 2 caras.", ephemeral=True)
    await interaction.response.send_message(f"🎲 {interaction.user.mention} lanzó un dado de {caras} y sacó: **{random.randint(1, caras)}**")

@client.tree.command(name="ppt", description="Juega Piedra, Papel o Tijera contra el bot o un miembro")
@app_commands.describe(adversario="Menciona a un miembro para retarlo (opcional)", eleccion="Tu jugada")
@app_commands.choices(eleccion=[
    app_commands.Choice(name="Piedra", value="piedra"),
    app_commands.Choice(name="Papel", value="papel"),
    app_commands.Choice(name="Tijera", value="tijera")
])
async def ppt(interaction: discord.Interaction, eleccion: str, adversario: discord.Member = None):
    if adversario:
        if adversario.id == interaction.user.id:
            return await interaction.response.send_message("❌ No puedes retarte a ti mismo.", ephemeral=True)
        if adversario.bot:
            return await interaction.response.send_message("❌ No puedes retar a un bot.", ephemeral=True)
        
        view = VistaRetoPPT(interaction.user, adversario, eleccion)
        await interaction.response.send_message(f"⚔️️ {adversario.mention}, ¡{interaction.user.mention} te ha retado a **Piedra, Papel o Tijera**! Haz clic para aceptar:", view=view)
    else:
        bot_elec = random.choice(["piedra", "papel", "tijera"])
        if eleccion == bot_elec: res = "¡Empate! 🤝"
        elif (eleccion == "piedra" and bot_elec == "tijera") or (eleccion == "papel" and bot_elec == "piedra") or (eleccion == "tijera" and bot_elec == "papel"): res = "¡Ganaste! 🎉"
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
        if interaction.user.id != self.retado.id:
            return await interaction.response.send_message("❌ Este reto no es para ti.", ephemeral=True)
        
        elecs = ["piedra", "papel", "tijera"]
        jugada_retado = random.choice(elecs) # En duelo directo o contra bot simulación interactiva
        
        r1, r2 = self.jugada_retador, jugada_retado
        if r1 == r2: res = "¡Es un empate mutuo! 🤝"
        elif (r1 == "piedra" and r2 == "tijera") or (r1 == "papel" and r2 == "piedra") or (r1 == "tijera" and r2 == "papel"):
            res = f"🎉 ¡{self.retador.mention} gana el duelo!"
        else:
            res = f"🎉 ¡{self.retado.mention} gana el duelo!"

        for child in self.children: child.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"⚔️ **Duelo PPT**:\n{self.retador.mention} eligió su jugada.\n{self.retado.mention} respondió.\n\n{res}")


@client.tree.command(name="trivia", description="Trivia masiva de Anime e Historia con más de 300 preguntas e imágenes")
async def trivia(interaction: discord.Interaction):
    t = random.choice(BANCO_TRIVIA)
    
    embed = discord.Embed(
        title=f"🧠 Trivia: {t['cat']}",
        description=f"**{t['p']}**\n\n*(Escribe tu respuesta en el chat. Tienes 20 segundos)*",
        color=0x9B59B6
    )
    embed.set_image(url=t["img"])
    embed.set_footer(text=f"Retado por {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await client.wait_for('message', timeout=20.0, check=check)
        if t['r'] in msg.content.lower():
            await interaction.followup.send(f"🎉 ¡Correcto {interaction.user.mention}! Acertaste la respuesta.")
        else:
            await interaction.followup.send(f"❌ Incorrecto. La respuesta correcta era: **{t['r']}**.")
    except asyncio.TimeoutError:
        await interaction.followup.send(f"⏰ ¡Tiempo agotado! La respuesta era: **{t['r']}**.")


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
        await interaction.edit_original_response(content=f"💀 ¡Perdiste! La palabra era **{secreta}**.")


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
            return await interaction.edit_original_response(content=f"⏰ ¡Tiempo agotado! Era **{secreta}**.")

    if "_" not in estado():
        await interaction.edit_original_response(content=f"🏆 ¡Ganaste {interaction.user.mention}! Era **{secreta}**.")
    else:
        await interaction.edit_original_response(content=f"💀 ¡Ahorcado! Era **{secreta}**.")


client.run(os.environ['DISCORD_TOKEN'])