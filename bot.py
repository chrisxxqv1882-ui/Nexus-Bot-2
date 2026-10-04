import os
import json
import random
import discord
from discord import app_commands

# ──────────────────────────── Base de datos (JSON) ────────────────────────────
DB_FILE = "data.json"
try:
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    data = {}


def save():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def cfg(guild_id):
    g = data.setdefault(str(guild_id), {})
    g.setdefault("sug", {"canal": None, "roles": [], "items": {}})
    return g


# ──────────────────────────────── Cliente ────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class Nexus(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(SugerenciaView())  # botones persistentes tras reiniciar
        await self.tree.sync()


client = Nexus()
tree = client.tree


@client.event
async def on_ready():
    print(f"✅ {client.user} listo")


# ─────────────────────────────── /dado ───────────────────────────────────────
@tree.command(name="dado", description="Lanza un dado de hasta 16 caras")
@app_commands.describe(caras="Número de caras (2-16, por defecto 6)")
async def dado(interaction: discord.Interaction, caras: app_commands.Range[int, 2, 16] = 6):
    r = random.randint(1, caras)
    embed = discord.Embed(
        title=f"🎲 Dado de {caras} caras",
        description=f"{interaction.user.mention} lanzó el dado y salió **{r}**",
        color=0xE67E22,
    )
    await interaction.response.send_message(embed=embed)


# ─────────────────────────────── /ppt ────────────────────────────────────────
OPC = {"piedra": "🪨 Piedra", "papel": "📄 Papel", "tijera": "✂️ Tijera"}
GANA = {"piedra": "tijera", "papel": "piedra", "tijera": "papel"}


class PPTView(discord.ui.View):
    def __init__(self, a: discord.User, b: discord.User):
        super().__init__(timeout=60)
        self.players = [a.id, b.id]
        self.picks = {}
        self.message = None

    def estado(self):
        lineas = [
            f"<@{p}> — {'✅ ya eligió' if p in self.picks else '⏳ eligiendo...'}"
            for p in self.players
        ]
        return discord.Embed(
            title="🪨📄✂️ Piedra, Papel o Tijera",
            description="\n".join(lineas) + "\n\nLas elecciones son secretas hasta que ambos elijan.",
            color=0x3498DB,
        )

    async def elegir(self, interaction: discord.Interaction, pick: str):
        uid = interaction.user.id
        if uid not in self.players:
            return await interaction.response.send_message("No participas en esta partida.", ephemeral=True)
        if uid in self.picks:
            return await interaction.response.send_message("Ya elegiste, espera al otro jugador.", ephemeral=True)

        self.picks[uid] = pick
        if len(self.picks) < 2:
            await interaction.response.send_message(
                f"Elegiste {OPC[pick]}. Esperando al otro jugador...", ephemeral=True
            )
            return await self.message.edit(embed=self.estado())

        a, b = self.players
        pa, pb = self.picks[a], self.picks[b]
        if pa == pb:
            res = "🤝 **¡Empate!**"
        elif GANA[pa] == pb:
            res = f"🏆 Gana <@{a}>"
        else:
            res = f"🏆 Gana <@{b}>"
        embed = discord.Embed(
            title="🪨📄✂️ Resultado",
            description=f"<@{a}>: {OPC[pa]}\n<@{b}>: {OPC[pb]}\n\n{res}",
            color=0x2ECC71,
        )
        for c in self.children:
            c.disabled = True
        self.stop()
        await interaction.response.edit_message(content=None, embed=embed, view=self)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            await self.message.edit(
                content=None,
                embed=discord.Embed(description="⌛ Partida cancelada por inactividad.", color=0x95A5A6),
                view=self,
            )

    @discord.ui.button(label="Piedra", emoji="🪨", style=discord.ButtonStyle.primary)
    async def piedra(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.elegir(interaction, "piedra")

    @discord.ui.button(label="Papel", emoji="📄", style=discord.ButtonStyle.primary)
    async def papel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.elegir(interaction, "papel")

    @discord.ui.button(label="Tijera", emoji="✂️", style=discord.ButtonStyle.primary)
    async def tijera(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.elegir(interaction, "tijera")


@tree.command(name="ppt", description="Juega piedra, papel o tijera contra otra persona")
@app_commands.describe(oponente="Con quién quieres jugar")
async def ppt(interaction: discord.Interaction, oponente: discord.User):
    if oponente.bot or oponente.id == interaction.user.id:
        return await interaction.response.send_message(
            "Elige a otra persona (ni un bot ni tú mismo).", ephemeral=True
        )
    view = PPTView(interaction.user, oponente)
    await interaction.response.send_message(
        content=f"{oponente.mention}, {interaction.user.mention} te retó.",
        embed=view.estado(),
        view=view,
    )
    view.message = await interaction.original_response()


# ───────────────────────────── Sugerencias ───────────────────────────────────
def puede_moderar_sug(member: discord.Member) -> bool:
    c = cfg(member.guild.id)["sug"]
    return member.guild_permissions.manage_guild or any(r.id in c["roles"] for r in member.roles)


async def crear_sugerencia(guild, user, texto, imagen=None) -> bool:
    c = cfg(guild.id)["sug"]
    canal = guild.get_channel(c["canal"]) if c["canal"] else None
    if canal is None:
        return False
    embed = discord.Embed(
        title="💡 Nueva sugerencia",
        description=texto or "*(sin texto)*",
        color=0xF1C40F,
        timestamp=discord.utils.utcnow(),
    )
    embed.set_author(name=user.name, icon_url=user.display_avatar.url)
    embed.add_field(name="Estado", value="⏳ Pendiente")
    if imagen:
        embed.set_image(url=imagen)
    msg = await canal.send(embed=embed, view=SugerenciaView())
    c["items"][str(msg.id)] = user.id
    save()
    return True


class NotaModal(discord.ui.Modal):
    nota = discord.ui.TextInput(
        label="Nota (opcional)", style=discord.TextStyle.paragraph, required=False, max_length=1000
    )

    def __init__(self, aprobado: bool, mensaje: discord.Message):
        super().__init__(title="Aprobar sugerencia" if aprobado else "Rechazar sugerencia")
        self.aprobado = aprobado
        self.mensaje = mensaje

    async def on_submit(self, interaction: discord.Interaction):
        nota = self.nota.value or "Sin nota."
        embed = self.mensaje.embeds[0].copy()
        embed.color = 0x2ECC71 if self.aprobado else 0xE74C3C
        embed.clear_fields()
        embed.add_field(name="Estado", value="✅ Aprobada" if self.aprobado else "❌ Rechazada", inline=False)
        embed.add_field(name="Revisada por", value=interaction.user.mention, inline=True)
        embed.add_field(name="Nota", value=nota, inline=False)
        await interaction.response.edit_message(embed=embed, view=None)

        autor_id = cfg(interaction.guild.id)["sug"]["items"].get(str(self.mensaje.id))
        if autor_id:
            try:
                user = await client.fetch_user(autor_id)
                dm = discord.Embed(
                    title=f"Tu sugerencia fue {'aprobada ✅' if self.aprobado else 'rechazada ❌'}",
                    description=embed.description,
                    color=embed.color,
                )
                dm.add_field(name="Staff", value=interaction.user.name, inline=True)
                dm.add_field(name="Nota", value=nota, inline=False)
                await user.send(embed=dm)
            except (discord.Forbidden, discord.HTTPException):
                pass


class SugerenciaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not puede_moderar_sug(interaction.user):
            await interaction.response.send_message("❌ No tienes permiso para esto.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.success, custom_id="sug:ok")
    async def aprobar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NotaModal(True, interaction.message))

    @discord.ui.button(label="Rechazar", style=discord.ButtonStyle.danger, custom_id="sug:no")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NotaModal(False, interaction.message))


@tree.command(name="sugerencias", description="Envía una sugerencia al servidor")
@app_commands.describe(texto="Tu sugerencia")
async def sugerencias(interaction: discord.Interaction, texto: app_commands.Range[str, 1, 2000]):
    ok = await crear_sugerencia(interaction.guild, interaction.user, texto)
    await interaction.response.send_message(
        "✅ Sugerencia enviada."
        if ok
        else "⚠️ Aún no hay canal de sugerencias. Un admin debe configurarlo en `/configuracion`.",
        ephemeral=True,
    )


# ───────────────────────────── /configuracion ────────────────────────────────
SECCIONES = {
    "sugerencias": ("💡", "Sugerencias", "Canal y roles que aprueban"),
    "postulaciones": ("📝", "Postulaciones", "Formularios, embeds y canal"),
    "eventos": ("🎉", "Eventos", "Roles y embed de eventos"),
    "seguridad": ("🛡️", "Seguridad", "Anti-Bot, Anti-Raid, Anti-Spam, Whitelist"),
    "moderacion": ("🔨", "Moderación", "Sanciones, casos y registros"),
    "juegos": ("🎮", "Juegos", "Editar embeds de los juegos"),
}


def home_embed():
    lista = "\n".join(f"{e} **{n}** — {d}" for e, n, d in SECCIONES.values())
    return discord.Embed(
        title="⚙️ Configuración de Nexus",
        description=f"¡Bienvenido al panel! Elige en el menú qué quieres configurar:\n\n{lista}",
        color=0x5865F2,
    )


def sug_embed(guild_id):
    c = cfg(guild_id)["sug"]
    embed = discord.Embed(title="💡 Configurar sugerencias", color=0xF1C40F)
    embed.add_field(name="Canal", value=f"<#{c['canal']}>" if c["canal"] else "No configurado", inline=True)
    embed.add_field(
        name="Roles que aprueban/rechazan",
        value=" ".join(f"<@&{r}>" for r in c["roles"]) or "Solo quienes tengan *Gestionar servidor*",
        inline=True,
    )
    return embed


class AdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
            return False
        return True


class HomeView(AdminView):
    def __init__(self):
        super().__init__()
        self.add_item(Menu())


class Menu(discord.ui.Select):
    def __init__(self):
        opciones = [
            discord.SelectOption(label=n, value=k, emoji=e, description=d)
            for k, (e, n, d) in SECCIONES.items()
        ]
        super().__init__(placeholder="¿Qué quieres configurar?", options=opciones)

    async def callback(self, interaction: discord.Interaction):
        k = self.values[0]
        if k == "sugerencias":
            return await interaction.response.edit_message(embed=sug_embed(interaction.guild.id), view=SugView())
        e, n, _ = SECCIONES[k]
        embed = discord.Embed(
            title=f"{e} {n}", description="🚧 Esta sección se agregará en la siguiente fase.", color=0x95A5A6
        )
        await interaction.response.edit_message(embed=embed, view=BackView())


class BackView(AdminView):
    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=home_embed(), view=HomeView())


class SugView(AdminView):
    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Elige el canal de sugerencias",
    )
    async def canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        cfg(interaction.guild.id)["sug"]["canal"] = select.values[0].id
        save()
        await interaction.response.edit_message(embed=sug_embed(interaction.guild.id), view=self)

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        min_values=0,
        max_values=10,
        placeholder="Roles que aprueban/rechazan",
    )
    async def roles(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        cfg(interaction.guild.id)["sug"]["roles"] = [r.id for r in select.values]
        save()
        await interaction.response.edit_message(embed=sug_embed(interaction.guild.id), view=self)

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=home_embed(), view=HomeView())


@tree.command(name="configuracion", description="Panel de configuración de Nexus")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def configuracion(interaction: discord.Interaction):
    await interaction.response.send_message(embed=home_embed(), view=HomeView(), ephemeral=True)


# ─────────────────────────────────── /help ───────────────────────────────────
@tree.command(name="help", description="Cómo usar y configurar Nexus")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Ayuda de Nexus", description="Guía rápida para configurar el bot:", color=0x5865F2)
    embed.add_field(name="1️⃣ Empieza aquí", value="Un admin usa `/configuracion` y elige una sección del menú.", inline=False)
    embed.add_field(
        name="💡 Sugerencias",
        value="En `/configuracion → Sugerencias` elige el canal y los roles que aprueban. "
        "Cada mensaje en ese canal se vuelve un embed con botones Aprobar/Rechazar.",
        inline=False,
    )
    embed.add_field(
        name="🎮 Juegos",
        value="`/ppt @usuario` — piedra, papel o tijera (ambos eligen en secreto)\n`/dado [caras]` — dado de 2 a 16 caras",
        inline=False,
    )
    embed.add_field(name="🚧 Próximamente", value="Eventos, postulaciones, seguridad, moderación y adivina la palabra.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ───────────────────── Mensajes: sugerencias + presentación ──────────────────
@client.event
async def on_message(m: discord.Message):
    if m.author.bot or not m.guild:
        return

    # Canal de sugerencias: cada mensaje se convierte en embed
    c = cfg(m.guild.id)["sug"]
    if c["canal"] and m.channel.id == c["canal"]:
        img = next((a.url for a in m.attachments if a.content_type and a.content_type.startswith("image/")), None)
        if m.content or img:
            if await crear_sugerencia(m.guild, m.author, m.content, img):
                try:
                    await m.delete()
                except discord.HTTPException:
                    pass
        return

    # Presentación: SOLO con mención directa (no si es respuesta a un mensaje)
    if (
        m.reference is None
        and not m.mention_everyone
        and m.content.strip() in (f"<@{client.user.id}>", f"<@!{client.user.id}>")
    ):
        embed = discord.Embed(
            title="👋 ¡Hola, soy Nexus!",
            description="Soy un bot multifuncional: juegos, eventos, postulaciones, sugerencias, "
            "seguridad y moderación.\n\n• Usa `/help` para ver cómo configurarme\n"
            "• Los administradores usan `/configuracion`",
            color=0x5865F2,
        )
        embed.set_thumbnail(url=client.user.display_avatar.url)
        await m.reply(embed=embed, mention_author=False)


client.run(os.environ['DISCORD_TOKEN'])