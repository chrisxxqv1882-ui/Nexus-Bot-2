import os
import random
import asyncio
import discord
from discord import app_commands

# Configuración global del bot y de los embeds de formularios
config_global = {
    "rol_comandos_id": None,  # Rol que puede usar los comandos de postulación
    "rol_atencion_id": None,   # Rol que puede aprobar/rechazar
    "contador_postulaciones": 0 # Número consecutivo de postulaciones
}

# Base de datos en memoria para las preguntas y el diseño de los formularios
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

class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("¡Slash commands sincronizados!")

client = Bot()

@client.event
async def on_ready():
    print(f'¡Bot conectado con éxito como {client.user}!')

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

# --- MODAL PARA EDITAR DISEÑO Y PREGUNTAS DEL FORMULARIO ---

class ModalConfigFormulario(discord.ui.Modal):
    def __init__(self, tipo: str, nombre_bonito: str):
        super().__init__(title=f"Configurar {nombre_bonito}")
        self.tipo = tipo
        
        cfg_actual = postulaciones_config.get(tipo, {})
        preguntas_actuales = "\n".join(cfg_actual.get("preguntas", []))
        color_actual_hex = f"#{cfg_actual.get('color', 3498335):06x}"

        self.input_titulo = discord.ui.TextInput(
            label="Título del Embed",
            style=discord.TextStyle.short,
            default=cfg_actual.get("titulo", ""),
            required=True,
            max_length=100
        )
        self.input_color = discord.ui.TextInput(
            label="Color Hex (ej: #3498db)",
            style=discord.TextStyle.short,
            default=color_actual_hex,
            required=True,
            max_length=7
        )
        self.input_preguntas = discord.ui.TextInput(
            label="Preguntas (una por línea)",
            style=discord.TextStyle.paragraph,
            default=preguntas_actuales,
            required=True,
            max_length=1000
        )

        self.add_item(self.input_titulo)
        self.add_item(self.input_color)
        self.add_item(self.input_preguntas)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            nuevo_color = int(self.input_color.value.strip().replace("#", ""), 16)
        except:
            return await interaction.response.send_message("❌ Código HEX de color inválido.", ephemeral=True)

        nuevas_preguntas = [p.strip() for p in self.input_preguntas.value.split('\n') if p.strip()]
        
        postulaciones_config[self.tipo] = {
            "titulo": self.input_titulo.value.strip(),
            "color": nuevo_color,
            "preguntas": nuevas_preguntas
        }

        await interaction.response.send_message(f"✅ ¡Formulario de **{self.tipo.upper()}** actualizado con éxito!", ephemeral=True)


# --- VISTA DE CONFIGURACIÓN (BOTONES) ---

class VistaConfiguracion(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Config. Staff", style=discord.ButtonStyle.primary, row=0)
    async def btn_cfg_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo un administrador puede configurar esto.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("staff", "Cuerpo de Moderación"))

    @discord.ui.button(label="📝 Config. Ally", style=discord.ButtonStyle.primary, row=0)
    async def btn_cfg_ally(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo un administrador puede configurar esto.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("ally", "Casa Alianza"))

    @discord.ui.button(label="📝 Config. Redes", style=discord.ButtonStyle.primary, row=1)
    async def btn_cfg_redes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo un administrador puede configurar esto.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("redes", "Cuerpo de Redes"))

    @discord.ui.button(label="📝 Config. Nexus", style=discord.ButtonStyle.primary, row=1)
    async def btn_cfg_nexus(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo un administrador puede configurar esto.", ephemeral=True)
        await interaction.response.send_modal(ModalConfigFormulario("nexus", "Cuerpo de Programación"))


# --- MODAL DE RESPUESTAS DEL USUARIO ---

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
            text_input = discord.ui.TextInput(
                label=pregunta[:45],
                style=discord.TextStyle.paragraph,
                placeholder="Escribe tu respuesta aquí...",
                required=True,
                max_length=300
            )
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
        # Mostrar el avatar del postulante en la imagen chica (thumbnail)
        embed.set_thumbnail(url=self.miembro_postulado.display_avatar.url)
        embed.set_footer(text=f"Enviado por {interaction.user} | Esperando revisión del Staff.")

        await interaction.message.edit(embed=embed, view=VistaRevisionPostulacion(self.miembro_postulado))
        await interaction.response.send_message("✅ ¡Tus respuestas han sido enviadas correctamente!", ephemeral=True)


# --- VISTA INICIAL PARA EL USUARIO ---

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
        await interaction.response.send_modal(ModalResponderFormulario(self.tipo, self.num_id, self.preguntas, self.miembro_postulado, self.config_form))


# --- MODAL PARA ESCRIBIR LA NOTA DEL STAFF ---

class ModalNotaStaff(discord.ui.Modal):
    def __init__(self, estado: str, autor_postulacion):
        super().__init__(title=f"Nota de Postulación ({estado})")
        self.estado = estado
        self.autor_postulacion = autor_postulacion

        self.nota_input = discord.ui.TextInput(
            label="Escribe una nota o razón",
            style=discord.TextStyle.paragraph,
            placeholder="Ej: Excelente actitud, bienvenido / Faltó experiencia...",
            required=True,
            max_length=500
        )
        self.add_item(self.nota_input)

    async def on_submit(self, interaction: discord.Interaction):
        nota = self.nota_input.value
        
        for child in interaction.message.components:
            for row_child in child.children:
                row_child.disabled = True

        embed_actual = interaction.message.embeds[0]
        
        if self.estado == "APROBADO":
            embed_actual.color = discord.Color.green()
            resultado_txt = f"✅ **Aprobado** por {interaction.user.mention}"
        else:
            embed_actual.color = discord.Color.red()
            resultado_txt = f"❌ **No Clasificado / Rechazado** por {interaction.user.mention}"

        embed_actual.add_field(name="📌 Resultado", value=resultado_txt, inline=False)
        embed_actual.add_field(name="📝 Nota del Staff", value=nota, inline=False)

        await interaction.message.edit(embed=embed_actual, view=None)
        await interaction.response.send_message(f"✅ Postulación procesada correctamente con nota añadida.", ephemeral=True)


# --- VISTA DE REVISIÓN PARA EL STAFF ---

class VistaRevisionPostulacion(discord.ui.View):
    def __init__(self, autor_postulacion):
        super().__init__(timeout=None)
        self.autor_postulacion = autor_postulacion

    @discord.ui.button(label="✅ Aprobado", style=discord.ButtonStyle.success, custom_id="btn_aprobar")
    async def aprobar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_permisos_atencion(interaction):
            return await interaction.response.send_message("❌ No tienes el rol autorizado para atender postulaciones.", ephemeral=True)
        
        await interaction.response.send_modal(ModalNotaStaff("APROBADO", self.autor_postulacion))

    @discord.ui.button(label="❌ Rechazado", style=discord.ButtonStyle.danger, custom_id="btn_rechazar")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_permisos_atencion(interaction):
            return await interaction.response.send_message("❌ No tienes el rol autorizado para atender postulaciones.", ephemeral=True)
        
        await interaction.response.send_modal(ModalNotaStaff("RECHAZADO", self.autor_postulacion))


# --- COMANDOS DE CONFIGURACIÓN Y POSTULACIÓN ---

@client.tree.command(name="configuracion", description="Panel para configurar los formularios y roles autorizados")
@app_commands.describe(
    rol_comandos="Rol que tendrá permiso para ejecutar los comandos de postulación",
    rol_atencion="Rol que tendrá permisos para aprobar/rechazar postulaciones"
)
async def configuracion(interaction: discord.Interaction, rol_comandos: discord.Role = None, rol_atencion: discord.Role = None):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo un administrador puede usar este comando.", ephemeral=True)

    texto_roles = ""
    if rol_comandos:
        config_global["rol_comandos_id"] = rol_comandos.id
        texto_roles += f"\n- Rol para comandos de postulación: {rol_comandos.mention}"
    if rol_atencion:
        config_global["rol_atencion_id"] = rol_atencion.id
        texto_roles += f"\n- Rol para atender/revisar: {rol_atencion.mention}"

    embed = discord.Embed(
        title="⚙️ Configuración del Bot",
        description=f"Usa los botones de abajo para editar el diseño y preguntas de cada formulario.{texto_roles}",
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed, view=VistaConfiguracion(), ephemeral=True)

async def enviar_anuncio_postulacion(interaction: discord.Interaction, tipo: str, miembro: discord.Member):
    if not verificar_permisos_comandos(interaction):
        return await interaction.response.send_message("❌ No tienes el rol autorizado para ejecutar comandos de postulación.", ephemeral=True)

    config_form = postulaciones_config.get(tipo, {})
    preguntas = config_form.get("preguntas", [])
    if not preguntas:
        return await interaction.response.send_message(
            f"❌ Este formulario aún no ha sido configurado. Un administrador debe usar el comando `/configuracion`.",
            ephemeral=True
        )

    # Incrementar el número consecutivo de la postulación
    config_global["contador_postulaciones"] += 1
    num_id = config_global["contador_postulaciones"]

    embed = discord.Embed(
        title=f"{config_form['titulo']} (#{num_id})",
        description=f"Candidato: {miembro.mention}\nIniciado por: {interaction.user.mention}\nHaz clic en el botón de abajo para rellenar tus respuestas.",
        color=config_form['color']
    )
    # Mostrar el avatar del candidato como thumbnail
    embed.set_thumbnail(url=miembro.display_avatar.url)

    await interaction.channel.send(embed=embed, view=VistaBotonResponder(tipo, num_id, preguntas, miembro, config_form))
    await interaction.response.send_message(f"✅ ¡Formulario `#{num_id}` enviado al chat público!", ephemeral=True)

@client.tree.command(name="postulacion_staff", description="Inicia el formulario para el Cuerpo de Moderación")
@app_commands.describe(miembro="¿Qué usuario va a aplicar el formulario?")
async def postulacion_staff(interaction: discord.Interaction, miembro: discord.Member):
    await enviar_anuncio_postulacion(interaction, "staff", miembro)

@client.tree.command(name="postulacion_casa-ally", description="Inicia el formulario para Casa Alianza")
@app_commands.describe(miembro="¿Qué usuario va a aplicar el formulario?")
async def postulacion_casa_ally(interaction: discord.Interaction, miembro: discord.Member):
    await enviar_anuncio_postulacion(interaction, "ally", miembro)

@client.tree.command(name="postulaicon_redes", description="Inicia el formulario para el Cuerpo de Redes")
@app_commands.describe(miembro="¿Qué usuario va a aplicar el formulario?")
async def postulaicon_redes(interaction: discord.Interaction, miembro: discord.Member):
    await enviar_anuncio_postulacion(interaction, "redes", miembro)

@client.tree.command(name="postulacion_nexus", description="Inicia el formulario para el Cuerpo de Programación")
@app_commands.describe(miembro="¿Qué usuario va a aplicar el formulario?")
async def postulacion_nexus(interaction: discord.Interaction, miembro: discord.Member):
    await enviar_anuncio_postulacion(interaction, "nexus", miembro)


# --- JUEGOS INTERACTIVOS (LIBRES PARA TODOS) ---

@client.tree.command(name="dado", description="Lanza un dado de N caras (Libre para todos)")
@app_commands.describe(caras="Número de caras (por defecto 6)")
async def dado(interaction: discord.Interaction, caras: int = 6):
    if caras < 2:
        return await interaction.response.send_message("❌ El dado debe tener al menos 2 caras.", ephemeral=True)
    resultado = random.randint(1, caras)
    await interaction.response.send_message(f"🎲 {interaction.user.mention} lanzó un dado de {caras} caras y salió: **{resultado}**")

@client.tree.command(name="adivina_palabra", description="Juega a adivinar una palabra secreta por letras (Libre para todos)")
async def adivina_palabra(interaction: discord.Interaction):
    palabras = ["discord", "python", "railway", "programacion", "moderacion", "desarrollo", "servidor"]
    palabra_secreta = random.choice(palabras)
    letras_ocultas = ["_"] * len(palabra_secreta)
    intentos = 6
    letras_usadas = set()

    await interaction.response.send_message(
        f"🎮 **¡Adivina la Palabra!**\nPalabra: `{' '.join(letras_ocultas)}`\nTienes {intentos} intentos fallidos permitidos.\nEscribe una letra en el chat para empezar."
    )

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and len(m.content) == 1 and m.content.isalpha()

    while intentos > 0 and "_" in letras_ocultas:
        try:
            msg = await client.wait_for('message', timeout=30.0, check=check)
            letra = msg.content.lower()
            try:
                await msg.delete()
            except:
                pass

            if letra in letras_usadas:
                continue
            letras_usadas.add(letra)

            if letra in palabra_secreta:
                for idx, l in enumerate(palabra_secreta):
                    if l == letra:
                        letras_ocultas[idx] = letra
            else:
                intentos -= 1

            estado_actual = f"🎮 **¡Adivina la Palabra!**\nPalabra: `{' '.join(letras_ocultas)}`\nLetras usadas: {', '.join(letras_usadas)}\nIntentos restantes: {intentos}"
            await interaction.edit_original_response(content=estado_actual)

        except asyncio.TimeoutError:
            return await interaction.edit_original_response(content=f"⏰ ¡Tiempo agotado! La palabra era **{palabra_secreta}**.")

    if "_" not in letras_ocultas:
        await interaction.edit_original_response(content=f"🎉 ¡Felicidades {interaction.user.mention}! Has adivinado la palabra secreta: **{palabra_secreta}**.")
    else:
        await interaction.edit_original_response(content=f"❌ ¡Te has quedado sin intentos! La palabra era **{palabra_secreta}**.")


@client.tree.command(name="colgado", description="El clásico juego del ahorcado (Libre para todos)")
async def colgado(interaction: discord.Interaction):
    palabras_ahorcado = ["discord", "bot", "python", "desarrollo", "videojuego", "computadora"]
    secreta = random.choice(palabras_ahorcado)
    adivinadas = set()
    fallos = 0
    max_fallos = 6

    def obtener_estado():
        return "".join([c if c in adivinadas else "_" for c in secreta])

    await interaction.response.send_message(
        f"🕹️ **Juego del Colgado**\nProgreso: `{' '.join(obtener_estado())}`\nErrores: {fallos}/{max_fallos}\nEscribe una letra en el canal."
    )

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and len(m.content) == 1 and m.content.isalpha()

    while fallos < max_fallos and "_" in obtener_estado():
        try:
            msg = await client.wait_for('message', timeout=25.0, check=check)
            letra = msg.content.lower()
            try:
                await msg.delete()
            except:
                pass

            if letra in adivinadas:
                continue
            adivinadas.add(letra)

            if letra not in secreta:
                fallos += 1

            estado_txt = f"🕹️ **Juego del Colgado**\nProgreso: `{' '.join(obtener_estado())}`\nErrores: {fallos}/{max_fallos}\nLetras probadas: {', '.join(adivinadas)}"
            await interaction.edit_original_response(content=estado_txt)
        except asyncio.TimeoutError:
            return await interaction.edit_original_response(content=f"⏰ ¡Se acabó el tiempo! La palabra era **{secreta}**.")

    if "_" not in obtener_estado():
        await interaction.edit_original_response(content=f"🏆 ¡Victoria! Has completado la palabra **{secreta}**.")
    else:
        await interaction.edit_original_response(content=f"💀 ¡Has perdido en el colgado! La palabra era **{secreta}**.")


client.run(os.environ['DISCORD_TOKEN'])