import os
import random
import asyncio
import discord
from discord import app_commands

# Configuración global editable (Tickets y Postulaciones)
config_global = {
    "admin_rol_id": None, 
    "rol_id": 1549479823200747521,
    "categoria_id": None,
    "titulo": "⚖️ Sistema de Apelaciones y Reclamaciones",
    "descripcion": "Si necesitas abrir un ticket, reclamar o apelar una sanción, haz clic en el botón de abajo.",
    "color": 0x3498db,
    "autor": "Hakkuze - Moderación",
    "thumbnail": None,
    "image": None,
    "footer": "Sistema seguro de tickets",
    "ticket_embed_titulo": "📥 ¡Nuevo Ticket Abierto!",
    "ticket_embed_descripcion": "El usuario {usuario} ha iniciado un caso.\n\n**Motivo / Razón:**\n{razon}",
    "ticket_embed_footer": "Atiende con respeto y profesionalismo."
}

# Base de datos temporal para formularios de postulaciones
# (Guarda las preguntas configuradas para cada tipo)
postulaciones_config = {
    "staff": ["¿Cuál es tu edad?", "¿Por qué quieres ser Moderador?", "¿Tienes experiencia previa?"],
    "ally": ["¿Cuál es tu servidor?", "¿Cuántos miembros activos tienes?", "¿Cuál es la invitación?"],
    "redes": ["¿Qué plataformas manejas?", "¿Tienes ejemplos de ediciones o publicaciones?"],
    "nexus": ["¿Qué lenguajes de programación conoces?", "¿Cuánto tiempo llevas programando?"]
}

apelaciones_db = []

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

# --- MODALES PARA EL EDITOR VISUAL ---

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


# --- EDITOR DE PREGUNTAS DE POSTULACIONES ---

class ModalEditarPreguntas(discord.ui.Modal):
    def __init__(self, tipo: str, nombre_bonito: str):
        super().__init__(title=f"Configurar {nombre_bonito}")
        self.tipo = tipo
        
        preguntas_actuales = "\n".join(postulaciones_config.get(tipo, []))
        self.preguntas_input = discord.ui.TextInput(
            label="Preguntas (una por línea)",
            style=discord.TextStyle.paragraph,
            placeholder="Pregunta 1\nPregunta 2\nPregunta 3",
            default=preguntas_actuales,
            required=True,
            max_length=1000
        )
        self.add_item(self.preguntas_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Separa las preguntas por saltos de línea
        nuevas_preguntas = [p.strip() for p in self.preguntas_input.value.split('\n') if p.strip()]
        postulaciones_config[self.tipo] = nuevas_preguntas
        await interaction.response.send_message(f"✅ ¡Formulario actualizado con {len(nuevas_preguntas)} preguntas!", ephemeral=True)


# --- VISTA DEL EDITOR VISUAL DE TICKETS Y POSTULACIONES ---

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

    @discord.ui.button(label="📝 Config. Staff", style=discord.ButtonStyle.secondary, row=1)
    async def btn_cfg_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarPreguntas("staff", "Cuerpo de Moderación"))

    @discord.ui.button(label="📝 Config. Ally", style=discord.ButtonStyle.secondary, row=1)
    async def btn_cfg_ally(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarPreguntas("ally", "Casa Alianza"))

    @discord.ui.button(label="📝 Config. Redes", style=discord.ButtonStyle.secondary, row=1)
    async def btn_cfg_redes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarPreguntas("redes", "Cuerpo de Redes"))

    @discord.ui.button(label="📝 Config. Nexus", style=discord.ButtonStyle.secondary, row=1)
    async def btn_cfg_nexus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarPreguntas("nexus", "Cuerpo de Programación"))

    @discord.ui.button(label="🖼️ Thumbnail", style=discord.ButtonStyle.success, row=2)
    async def btn_thumb(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarURLs("thumbnail"))

    @discord.ui.button(label="📸 Imagen", style=discord.ButtonStyle.success, row=2)
    async def btn_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarURLs("image"))

    @discord.ui.button(label="🚀 Publicar Panel Tickets", style=discord.ButtonStyle.danger, row=2)
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

        await interaction.channel.send(embed=embed, view=VistaApelacionBotonesPublico())
        await interaction.response.send_message("✅ ¡Panel de tickets publicado con éxito!", ephemeral=True)


class VistaApelacionBotonesPublico(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Abrir Ticket / Reclamación", style=discord.ButtonStyle.danger, custom_id="btn_abrir_ticket")
    async def boton_apelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApelacionModal())


class ApelacionModal(discord.ui.Modal, title="Formulario de Reclamación / Ticket"):
    razon = discord.ui.TextInput(
        label="Motivo de tu ticket o reclamación",
        style=discord.TextStyle.paragraph,
        placeholder="Explica detalladamente tu caso...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        apelaciones_db.append({"usuario": str(interaction.user), "id_usuario": interaction.user.id, "razon": self.razon.value})
        guild = interaction.guild
        rol_obj = guild.get_role(config_global["rol_id"])
        categoria = discord.utils.get(guild.categories, id=int(config_global["categoria_id"])) if config_global["categoria_id"] else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
        }
        if rol_obj: overwrites[rol_obj] = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)

        canal = await guild.create_text_channel(f"ticket-{interaction.user.name}".lower(), category=categoria, overwrites=overwrites)
        if canal:
            embed_ticket = discord.Embed(
                title=config_global["ticket_embed_titulo"],
                description=config_global["ticket_embed_descripcion"].format(usuario=interaction.user.mention, razon=self.razon.value),
                color=config_global["color"]
            )
            embed_ticket.set_footer(text=config_global["ticket_embed_footer"])
            
            class VistaCerrarTicket(discord.ui.View):
                @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.secondary, custom_id="cerrar_tk")
                async def cerrar(self, inter: discord.Interaction, btn: discord.ui.Button):
                    await inter.response.send_message("🔒 Cerrando canal en 3 segundos...")
                    await asyncio.sleep(3)
                    await inter.channel.delete()

            mencion = f"<@&{config_global['rol_id']}>" if rol_obj else ""
            await canal.send(content=f"{mencion} ¡Nuevo ticket abierto por {interaction.user.mention}!", embed=embed_ticket, view=VistaCerrarTicket())
            await interaction.response.send_message(f"✅ ¡Tu ticket ha sido creado correctamente en {canal.mention}!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Hubo un error al crear el canal.", ephemeral=True)


# --- COMANDOS DE CONFIGURACIÓN ---

@client.tree.command(name="configurar", description="Abre el editor visual avanzado del bot")
async def configurar(interaction: discord.Interaction):
    if not verificar_permisos(interaction):
        await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
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
        content="✨ **Editor Visual General**\nUsa los botones para configurar los tickets y las preguntas de los formularios de postulación:",
        embed=embed_preview,
        view=VistaEditorVisual(),
        ephemeral=True
    )


# --- COMANDOS DE POSTULACIÓN SOLICITADOS ---

async def enviar_postulacion(interaction: discord.Interaction, tipo: str, nombre_bonito: str):
    preguntas = postulaciones_config.get(tipo, [])
    if not preguntas:
        return await interaction.response.send_message(
            "❌ Aún no se ha añadido un formulario para este servidor. Ejecuta el comando **/configurar** y añade tus preguntas.",
            ephemeral=True
        )

    preguntas_formateadas = "\n".join([f"**{i+1}.** {p}" for i, p in enumerate(preguntas)])
    embed = discord.Embed(
        title=f"📝 Formulario de Postulación: {nombre_bonito}",
        description=f"Responde a las siguientes preguntas:\n\n{preguntas_formateadas}",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@client.tree.command(name="postulacion_staff", description="Postúlate al Cuerpo de Moderación.")
async def postulacion_staff(interaction: discord.Interaction):
    await enviar_postulacion(interaction, "staff", "Cuerpo de Moderación")

@client.tree.command(name="postulacion_casa-ally", description="Postúlate a Casa Alianza.")
async def postulacion_casa_ally(interaction: discord.Interaction):
    await enviar_postulacion(interaction, "ally", "Casa Alianza")

@client.tree.command(name="postulaicon_redes", description="Postúlate al Cuerpo de Redes.")
async def postulaicon_redes(interaction: discord.Interaction):
    await enviar_postulacion(interaction, "redes", "Cuerpo de Redes")

@client.tree.command(name="postulacion_nexus", description="Postúlate al Cuerpo de Programación.")
async def postulacion_nexus(interaction: discord.Interaction):
    await enviar_postulacion(interaction, "nexus", "Cuerpo de Programación (Nexus)")


# --- UTILIDADES Y JUEGOS ---

@client.tree.command(name="dado", description="Lanza un dado interactivo")
@app_commands.describe(caras="Número de caras del dado (por defecto 6)")
async def dado(interaction: discord.Interaction, caras: int = 6):
    if caras < 2:
        await interaction.response.send_message("❌ El dado debe tener al menos 2 caras.", ephemeral=True)
        return
    resultado = random.randint(1, caras)
    await interaction.response.send_message(f"🎲 {interaction.user.mention} lanzó un dado de {caras} caras y salió: **{resultado}**")

client.run(os.environ['DISCORD_TOKEN'])
