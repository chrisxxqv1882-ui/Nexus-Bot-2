import os
import random
import asyncio
import discord
from discord import app_commands

# Configuración global editable para los formularios y su publicación
config_global = {
    "admin_rol_id": None, 
    "titulo": "📝 Panel de Postulaciones y Formularios",
    "descripcion": "Haz clic en el botón correspondiente abajo para ver el formulario y postularte.",
    "color": 0x3498db,
    "autor": "Hakkuze - Reclutamiento",
    "thumbnail": None,
    "image": None,
    "footer": "Sistema de postulaciones oficiales"
}

# Base de datos temporal para guardar las preguntas personalizadas de cada formulario
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
    if config_global["admin_rol_id"]:
        rol = interaction.guild.get_role(config_global["admin_rol_id"])
        if rol and rol in interaction.user.roles:
            return True
    return False

# --- MODALES PARA EL EDITOR VISUAL DE CONFIGURACIÓN ---

class ModalEditarTexto(discord.ui.Modal):
    def __init__(self, campo: str):
        super().__init__(title=f"Editar {campo.replace('_', ' ').capitalize()}")
        self.campo = campo
        
        self.valor = discord.ui.TextInput(
            label="Nuevo valor",
            style=discord.TextStyle.paragraph if "descripcion" in campo else discord.TextStyle.short,
            placeholder="Escribe aquí...",
            required=True,
            max_length=1000
        )
        self.add_item(self.valor)

    async def on_submit(self, interaction: discord.Interaction):
        config_global[self.campo] = self.valor.value
        await interaction.response.send_message(f"✅ ¡{self.campo.replace('_', ' ').capitalize()} actualizado con éxito!", ephemeral=True)

class ModalEditarURLs(discord.ui.Modal):
    def __init__(self, campo: str):
        super().__init__(title=f"Editar {campo.capitalize()}")
        self.campo = campo
        
        self.valor = discord.ui.TextInput(
            label="Enlace URL (o escribe 'none' para quitar)",
            style=discord.TextStyle.short,
            placeholder="https://...",
            required=True
        )
        self.add_item(self.valor)

    async def on_submit(self, interaction: discord.Interaction):
        val = self.valor.value.strip()
        config_global[self.campo] = None if val.lower() == "none" else val
        await interaction.response.send_message(f"✅ ¡{self.campo.capitalize()} actualizado!", ephemeral=True)

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
        await interaction.response.send_message(f"✅ ¡Formulario de **{self.tipo.upper()}** actualizado con {len(nuevas_preguntas)} preguntas!", ephemeral=True)


# --- VISTA DEL EDITOR VISUAL DE CONFIGURACIÓN Y PUBLICACIÓN ---

class VistaEditorVisual(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✏ Título Panel", style=discord.ButtonStyle.primary, row=0)
    async def btn_titulo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarTexto("titulo"))

    @discord.ui.button(label="📄 Desc. Panel", style=discord.ButtonStyle.primary, row=0)
    async def btn_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarTexto("descripcion"))

    @discord.ui.button(label="🎨 Color (Hex)", style=discord.ButtonStyle.primary, row=0)
    async def btn_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        class ModalColor(discord.ui.Modal, title="Editar Color"):
            hex_val = discord.ui.TextInput(label="Código Hex (ej: #3498db)", placeholder="#3498db", required=True)
            async def on_submit(self, inter: discord.Interaction):
                try:
                    config_global["color"] = int(hex_val.value.replace("#", ""), 16)
                    await inter.response.send_message("✅ ¡Color actualizado!", ephemeral=True)
                except:
                    await inter.response.send_message("❌ Código HEX inválido.", ephemeral=True)
        await interaction.response.send_modal(ModalColor())

    @discord.ui.button(label="📝 Staff", style=discord.ButtonStyle.secondary, row=1)
    async def btn_cfg_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarPreguntas("staff", "Cuerpo de Moderación"))

    @discord.ui.button(label="📝 Ally", style=discord.ButtonStyle.secondary, row=1)
    async def btn_cfg_ally(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarPreguntas("ally", "Casa Alianza"))

    @discord.ui.button(label="📝 Redes", style=discord.ButtonStyle.secondary, row=1)
    async def btn_cfg_redes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarPreguntas("redes", "Cuerpo de Redes"))

    @discord.ui.button(label="📝 Nexus", style=discord.ButtonStyle.secondary, row=1)
    async def btn_cfg_nexus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarPreguntas("nexus", "Cuerpo de Programación"))

    @discord.ui.button(label="🖼️ Thumbnail", style=discord.ButtonStyle.success, row=2)
    async def btn_thumb(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarURLs("thumbnail"))

    @discord.ui.button(label="📸 Imagen", style=discord.ButtonStyle.success, row=2)
    async def btn_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarURLs("image"))

    @discord.ui.button(label="🚀 Publicar Panel", style=discord.ButtonStyle.danger, row=2)
    async def btn_publicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=config_global["titulo"],
            description=config_global["descripcion"],
            color=config_global["color"]
        )
        if config_global["autor"]: embed.set_author(name=config_global["autor"])
        if config_global["thumbnail"]: embed.set_thumbnail(url=config_global["thumbnail"])
        if config_global["image"]: embed.set_image(url=config_global["image"])
        if config_global["footer"]: embed.set_footer(text=config_global["footer"])

        # Vista pública con botones para cada postulación
        await interaction.channel.send(embed=embed, view=VistaBotonesPostulacionesPublicas())
        await interaction.response.send_message("✅ ¡Panel de postulaciones publicado con éxito!", ephemeral=True)


class VistaBotonesPostulacionesPublicas(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def mostrar_formulario(self, interaction: discord.Interaction, tipo: str, nombre: str):
        preguntas = postulaciones_config.get(tipo, [])
        if not preguntas:
            return await interaction.response.send_message(
                f"❌ El formulario de **{nombre}** aún no ha sido configurado. Un administrador debe usar el comando `/configuracion`.",
                ephemeral=True
            )
        texto_preguntas = "\n".join([f"**{i+1}.** {p}" for i, p in enumerate(preguntas)])
        embed = discord.Embed(
            title=f"📝 Postulación: {nombre}",
            description=f"Preguntas configuradas:\n\n{texto_preguntas}",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Staff", style=discord.ButtonStyle.primary, custom_id="pub_staff")
    async def p_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.mostrar_formulario(interaction, "staff", "Cuerpo de Moderación")

    @discord.ui.button(label="Casa Alianza", style=discord.ButtonStyle.primary, custom_id="pub_ally")
    async def p_ally(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.mostrar_formulario(interaction, "ally", "Casa Alianza")

    @discord.ui.button(label="Cuerpo Redes", style=discord.ButtonStyle.primary, custom_id="pub_redes")
    async def p_redes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.mostrar_formulario(interaction, "redes", "Cuerpo de Redes")

    @discord.ui.button(label="Nexus", style=discord.ButtonStyle.primary, custom_id="pub_nexus")
    async def p_nexus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.mostrar_formulario(interaction, "nexus", "Cuerpo de Programación (Nexus)")


# --- COMANDOS DE CONFIGURACIÓN Y POSTULACIÓN ---

@client.tree.command(name="configuracion", description="Abre el panel de configuración y personalización de formularios")
async def configuracion(interaction: discord.Interaction):
    if not verificar_permisos(interaction):
        await interaction.response.send_message("❌ No tienes permisos para usar este comando.", ephemeral=True)
        return

    embed_preview = discord.Embed(
        title=config_global["titulo"],
        description=config_global["descripcion"],
        color=config_global["color"]
    )
    if config_global["autor"]: embed_preview.set_author(name=config_global["autor"])
    if config_global["thumbnail"]: embed_preview.set_thumbnail(url=config_global["thumbnail"])
    if config_global["image"]: embed_preview.set_image(url=config_global["image"])
    if config_global["footer"]: embed_preview.set_footer(text=config_global["footer"])

    await interaction.response.send_message(
        content="⚙️ **Panel de Configuración**\nPersonaliza el aspecto del panel y edita las preguntas de tus formularios:",
        embed=embed_preview,
        view=VistaEditorVisual(),
        ephemeral=True
    )

async def manejar_postulacion_cmd(interaction: discord.Interaction, tipo: str, nombre: str):
    preguntas = postulaciones_config.get(tipo, [])
    if not preguntas:
        return await interaction.response.send_message(
            f"❌ El formulario de **{nombre}** no está configurado. Ejecuta el comando `/configuracion` para añadirlo.",
            ephemeral=True
        )
    texto_preguntas = "\n".join([f"**{i+1}.** {p}" for i, p in enumerate(preguntas)])
    embed = discord.Embed(
        title=f"📝 Formulario: {nombre}",
        description=f"Preguntas:\n\n{texto_preguntas}",
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@client.tree.command(name="postulacion_staff", description="Postúlate al Cuerpo de Moderación")
async def postulacion_staff(interaction: discord.Interaction):
    await manejar_postulacion_cmd(interaction, "staff", "Cuerpo de Moderación")

@client.tree.command(name="postulacion_casa-ally", description="Postúlate a Casa Alianza")
async def postulacion_casa_ally(interaction: discord.Interaction):
    await manejar_postulacion_cmd(interaction, "ally", "Casa Alianza")

@client.tree.command(name="postulaicon_redes", description="Postúlate al Cuerpo de Redes")
async def postulaicon_redes(interaction: discord.Interaction):
    await manejar_postulacion_cmd(interaction, "redes", "Cuerpo de Redes")

@client.tree.command(name="postulacion_nexus", description="Postúlate al Cuerpo de Programación (Nexus)")
async def postulacion_nexus(interaction: discord.Interaction):
    await manejar_postulacion_cmd(interaction, "nexus", "Cuerpo de Programación (Nexus)")


# --- NUEVOS JUEGOS INTERACTIVOS ---

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

            # Actualizar mensaje con el estado del juego
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
        display = "".join([c if c in adivinadas else "_" for c in secreta])
        return display

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