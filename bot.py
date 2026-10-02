import os
import random
import asyncio
import discord
from discord import app_commands

# Configuración global del bot (Rol autorizado para atender postulaciones)
config_global = {
    "rol_atencion_id": None # ID del rol que puede aprobar/rechazar
}

# Base de datos en memoria para las preguntas de los formularios
postulaciones_config = {
    "staff": ["¿Cuál es tu edad?", "¿Por qué quieres ser Moderador?", "¿Tienes experiencia previa?"],
    "ally": ["¿Cuál es tu servidor?", "¿Cuántos miembros activos tienes?", "¿Cuál es la invitación?"],
    "redes": ["¿Qué plataformas manejas?", "¿Tienes ejemplos de ediciones o publicaciones?"],
    "nexus": ["¿Qué lenguajes de programación conoces?", "¿Cuánto tiempo llevas programando?"]
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

def verificar_permisos(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    if config_global["rol_atencion_id"]:
        rol = interaction.guild.get_role(config_global["rol_atencion_id"])
        if rol and rol in interaction.user.roles:
            return True
    return False

# --- MODAL PARA EDITAR LAS PREGUNTAS ---

class ModalEditarPreguntas(discord.ui.Modal):
    def __init__(self, tipo: str, nombre_bonito: str):
        super().__init__(title=f"Configurar {nombre_bonito}")
        self.tipo = tipo
        
        preguntas_actuales = "\n".join(postulaciones_config.get(tipo, []))
        self.preguntas_input = discord.ui.TextInput(
            label="Preguntas (escribe una por línea)",
            style=discord.TextStyle.paragraph,
            placeholder="Pregunta 1\nPregunta 2\nPregunta 3",
            default=preguntas_actuales,
            required=True,
            max_length=1000
        )
        self.add_item(self.preguntas_input)

    async def on_submit(self, interaction: discord.Interaction):
        nuevas_preguntas = [p.strip() for p in self.preguntas_input.value.split('\n') if p.strip()]
        postulaciones_config[self.tipo] = nuevas_preguntas
        await interaction.response.send_message(f"✅ ¡Formulario de **{self.tipo.upper()}** actualizado correctamente!", ephemeral=True)


# --- VISTA DE CONFIGURACIÓN (BOTONES) ---

class VistaConfiguracion(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Config. Staff", style=discord.ButtonStyle.primary, row=0)
    async def btn_cfg_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo un administrador puede configurar esto.", ephemeral=True)
        await interaction.response.send_modal(ModalEditarPreguntas("staff", "Cuerpo de Moderación"))

    @discord.ui.button(label="📝 Config. Ally", style=discord.ButtonStyle.primary, row=0)
    async def btn_cfg_ally(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo un administrador puede configurar esto.", ephemeral=True)
        await interaction.response.send_modal(ModalEditarPreguntas("ally", "Casa Alianza"))

    @discord.ui.button(label="📝 Config. Redes", style=discord.ButtonStyle.primary, row=1)
    async def btn_cfg_redes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo un administrador puede configurar esto.", ephemeral=True)
        await interaction.response.send_modal(ModalEditarPreguntas("redes", "Cuerpo de Redes"))

    @discord.ui.button(label="📝 Config. Nexus", style=discord.ButtonStyle.primary, row=1)
    async def btn_cfg_nexus(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo un administrador puede configurar esto.", ephemeral=True)
        await interaction.response.send_modal(ModalEditarPreguntas("nexus", "Cuerpo de Programación"))


# --- MODAL DE RESPUESTAS DEL USUARIO ---

class ModalResponderFormulario(discord.ui.Modal):
    def __init__(self, tipo: str, nombre_bonito: str, preguntas: list):
        super().__init__(title=f"Postulación: {nombre_bonito}")
        self.tipo = tipo
        self.nombre_bonito = nombre_bonito
        self.preguntas = preguntas
        self.inputs = []

        # Crear dinámicamente hasta 5 inputs según las preguntas configuradas
        for i, pregunta in enumerate(preguntas[:5]):
            text_input = discord.ui.TextInput(
                label=pregunta[:45], # Límite de caracteres de Discord para la etiqueta
                style=discord.TextStyle.paragraph,
                placeholder="Escribe tu respuesta aquí...",
                required=True,
                max_length=300
            )
            self.inputs.append(text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Recopilar las respuestas dadas
        respuestas_texto = ""
        for i, pregunta in enumerate(self.preguntas[:5]):
            respuestas_texto += f"**P{i+1}: {pregunta}**\n↳ {self.inputs[i].value}\n\n"

        embed = discord.Embed(
            title=f"📝 Postulación enviada: {self.nombre_bonito}",
            description=f"**Postulante:** {interaction.user.mention}\n\n{respuestas_texto}",
            color=0xF1C40F
        )
        embed.set_footer(text="Esperando revisión del Staff autorizado.")

        # Editar el mensaje público original para mostrar las respuestas y cambiar el botón a la vista de staff
        await interaction.message.edit(embed=embed, view=VistaRevisionPostulacion(interaction.user))
        await interaction.response.send_message("✅ ¡Tus respuestas han sido enviadas correctamente para su revisión!", ephemeral=True)


# --- VISTA INICIAL PARA EL USUARIO (BOTÓN RESPONDER) ---

class VistaBotonResponder(discord.ui.View):
    def __init__(self, tipo: str, nombre_bonito: str, preguntas: list):
        super().__init__(timeout=None)
        self.tipo = tipo
        self.nombre_bonito = nombre_bonito
        self.preguntas = preguntas

    @discord.ui.button(label="✍️ Responder Formulario", style=discord.ButtonStyle.success, custom_id="btn_responder_form")
    async def responder(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Asegurar que solo el creador del mensaje/comando pueda responder
        await interaction.response.send_modal(ModalResponderFormulario(self.tipo, self.nombre_bonito, self.preguntas))


# --- VISTA DE REVISIÓN PARA EL STAFF (APROBADO / RECHAZADO) ---

class VistaRevisionPostulacion(discord.ui.View):
    def __init__(self, autor_postulacion):
        super().__init__(timeout=None)
        self.autor_postulacion = autor_postulacion

    @discord.ui.button(label="✅ Aprobado", style=discord.ButtonStyle.success, custom_id="btn_aprobar")
    async def aprobar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_permisos(interaction):
            return await interaction.response.send_message("❌ No tienes el rol autorizado para atender postulaciones.", ephemeral=True)
        
        for child in self.children:
            child.disabled = True

        embed_actual = interaction.message.embeds[0]
        embed_actual.color = discord.Color.green()
        embed_actual.add_field(name="📌 Resultado", value=f"✅ **¡Aprobado!** por {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=embed_actual, view=self)
        await interaction.response.send_message(f"✅ Has aprobado la postulación de {self.autor_postulacion.mention}.", ephemeral=True)

    @discord.ui.button(label="❌ Rechazado", style=discord.ButtonStyle.danger, custom_id="btn_rechazar")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not verificar_permisos(interaction):
            return await interaction.response.send_message("❌ No tienes el rol autorizado para atender postulaciones.", ephemeral=True)
        
        for child in self.children:
            child.disabled = True

        embed_actual = interaction.message.embeds[0]
        embed_actual.color = discord.Color.red()
        embed_actual.add_field(name="📌 Resultado", value=f"❌ **No Clasificado / Rechazado** por {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=embed_actual, view=self)
        await interaction.response.send_message(f"❌ Postulación marcada como **no clasificada**.", ephemeral=True)


# --- COMANDOS DE CONFIGURACIÓN Y POSTULACIÓN ---

@client.tree.command(name="configuracion", description="Panel para configurar los formularios y el rol de atención")
@app_commands.describe(rol_atencion="Rol que tendrá permisos para atender y aprobar/rechazar postulaciones")
async def configuracion(interaction: discord.Interaction, rol_atencion: discord.Role = None):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo un administrador puede usar este comando.", ephemeral=True)

    texto_rol = ""
    if rol_atencion:
        config_global["rol_atencion_id"] = rol_atencion.id
        texto_rol = f"\n- Rol autorizado para atender: {rol_atencion.mention}"

    embed = discord.Embed(
        title="⚙️ Configuración de Formularios",
        description=f"Usa los botones de abajo para editar las preguntas de cada formulario.{texto_rol}",
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed, view=VistaConfiguracion(), ephemeral=True)

async def enviar_anuncio_postulacion(interaction: discord.Interaction, tipo: str, nombre: str):
    preguntas = postulaciones_config.get(tipo, [])
    if not preguntas:
        return await interaction.response.send_message(
            f"❌ El formulario de **{nombre}** aún no ha sido configurado. Un administrador debe usar el comando `/configuracion`.",
            ephemeral=True
        )

    embed = discord.Embed(
        title=f"📝 Postulación Abierta: {nombre}",
        description=f"Iniciado por: {interaction.user.mention}\nHaz clic en el botón de abajo para rellenar tus respuestas.",
        color=0x3498DB
    )

    # Envía el embed público con el botón "Responder"
    await interaction.channel.send(embed=embed, view=VistaBotonResponder(tipo, nombre, preguntas))
    await interaction.response.send_message("✅ ¡Formulario enviado al chat público!", ephemeral=True)

@client.tree.command(name="postulacion_staff", description="Inicia el formulario para el Cuerpo de Moderación")
async def postulacion_staff(interaction: discord.Interaction):
    await enviar_anuncio_postulacion(interaction, "staff", "Cuerpo de Moderación")

@client.tree.command(name="postulacion_casa-ally", description="Inicia el formulario para Casa Alianza")
async def postulacion_casa_ally(interaction: discord.Interaction):
    await enviar_anuncio_postulacion(interaction, "ally", "Casa Alianza")

@client.tree.command(name="postulaicon_redes", description="Inicia el formulario para el Cuerpo de Redes")
async def postulaicon_redes(interaction: discord.Interaction):
    await enviar_anuncio_postulacion(interaction, "redes", "Cuerpo de Redes")

@client.tree.command(name="postulacion_nexus", description="Inicia el formulario para el Cuerpo de Programación")
async def postulacion_nexus(interaction: discord.Interaction):
    await enviar_anuncio_postulacion(interaction, "nexus", "Cuerpo de Programación (Nexus)")


# --- JUEGOS INTERACTIVOS ---

@client.tree.command(name="dado", description="Lanza un dado de N caras")
@app_commands.describe(caras="Número de caras (por defecto 6)")
async def dado(interaction: discord.Interaction, caras: int = 6):
    if caras < 2:
        return await interaction.response.send_message("❌ El dado debe tener al menos 2 caras.", ephemeral=True)
    resultado = random.randint(1, caras)
    await interaction.response.send_message(f"🎲 {interaction.user.mention} lanzó un dado de {caras} caras y salió: **{resultado}**")

@client.tree.command(name="adivina_palabra", description="Juega a adivinar una palabra secreta por letras")
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


@client.tree.command(name="colgado", description="El clásico juego del ahorcado")
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
