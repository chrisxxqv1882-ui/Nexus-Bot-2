import os
import json
import random
from typing import Optional
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
    g.setdefault("ev", {
        "roles": [],
        "activos": {},
        "style": {"titulo": "🎉 Nuevo evento", "color": "5865F2", "imagen": None, "miniatura": None, "footer": None},
    })
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
        self.add_view(EventoView())
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


# ───────────────────────────────── Eventos ───────────────────────────────────
ESTADOS = {"abierto": "🟢 Abierto", "iniciado": "▶️ En curso", "finalizado": "🏁 Finalizado"}


def puede_organizar(member: discord.Member) -> bool:
    c = cfg(member.guild.id)["ev"]
    return member.guild_permissions.administrator or any(r.id in c["roles"] for r in member.roles)


def build_event_embed(ev: dict) -> discord.Embed:
    st = ev["style"]
    try:
        color = int(st["color"].lstrip("#"), 16)
    except ValueError:
        color = 0x5865F2
    embed = discord.Embed(title=st["titulo"], description=ev["descripcion"], color=color)
    embed.add_field(name="👤 Organizador", value=f"<@{ev['organizador']}>", inline=True)
    # Campos opcionales: solo aparecen si se rellenaron
    if ev.get("tipo"):
        embed.add_field(name="🎯 Tipo de evento", value=ev["tipo"], inline=True)
    if ev.get("premio"):
        embed.add_field(name="🎁 Premio", value=ev["premio"], inline=True)
    if ev.get("tiempo"):
        embed.add_field(name="⏰ Tiempo", value=ev["tiempo"], inline=True)
    if ev.get("ganadores"):
        embed.add_field(name="🏆 Ganadores", value=ev["ganadores"], inline=True)
    embed.add_field(name="📌 Estado", value=ESTADOS[ev["estado"]], inline=True)
    embed.add_field(name="👥 Participantes", value=str(len(ev["participantes"])), inline=True)
    if ev.get("resultado"):
        embed.add_field(name="🥇 Resultado", value=ev["resultado"], inline=False)
    if st.get("imagen"):
        embed.set_image(url=st["imagen"])
    if st.get("miniatura"):
        embed.set_thumbnail(url=st["miniatura"])
    if st.get("footer"):
        embed.set_footer(text=st["footer"])
    return embed


class EventoView(discord.ui.View):
    def __init__(self, cerrado: bool = False):
        super().__init__(timeout=None)
        if cerrado:
            for c in self.children:
                c.disabled = True

    @discord.ui.button(label="Participar", emoji="✅", style=discord.ButtonStyle.success, custom_id="ev:join")
    async def participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ev = cfg(interaction.guild.id)["ev"]["activos"].get(str(interaction.message.id))
        if not ev:
            return await interaction.response.send_message("❌ Este evento ya no existe.", ephemeral=True)
        if ev["estado"] != "abierto":
            return await interaction.response.send_message("🔒 Las inscripciones de este evento ya cerraron.", ephemeral=True)
        uid = interaction.user.id
        if uid in ev["participantes"]:
            ev["participantes"].remove(uid)
            texto = "👋 Saliste del evento."
        else:
            ev["participantes"].append(uid)
            texto = "✅ ¡Ya estás participando!"
        save()
        await interaction.response.edit_message(embed=build_event_embed(ev))
        await interaction.followup.send(texto, ephemeral=True)


async def eventos_ac(interaction: discord.Interaction, current: str, estado: str):
    activos = cfg(interaction.guild.id)["ev"]["activos"]
    out = []
    for mid, ev in activos.items():
        if ev["estado"] != estado:
            continue
        etiqueta = f"{ev.get('tipo') or 'Evento'} · {ev['descripcion']}"[:95]
        if current.lower() in etiqueta.lower():
            out.append(app_commands.Choice(name=etiqueta, value=mid))
    return out[:25]


async def mensaje_evento(guild: discord.Guild, ev: dict):
    canal = guild.get_channel(ev["canal"])
    if canal is None:
        return None, None
    try:
        return canal, await canal.fetch_message(ev["msg"])
    except discord.NotFound:
        return canal, None


@tree.command(name="organizar-evento", description="Publica un evento con botón para participar")
@app_commands.describe(
    canal="Canal donde se enviará el evento",
    organizador="Quién organiza el evento",
    descripcion="Descripción del evento",
    ping="Rol a mencionar (opcional)",
    premio="Premio (opcional)",
    tiempo="Duración o fecha (opcional)",
    tipo="Tipo de evento (opcional)",
    ganadores="Cantidad de ganadores (opcional)",
)
@app_commands.guild_only()
async def organizar_evento(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    organizador: discord.Member,
    descripcion: app_commands.Range[str, 1, 2000],
    ping: Optional[discord.Role] = None,
    premio: Optional[str] = None,
    tiempo: Optional[str] = None,
    tipo: Optional[str] = None,
    ganadores: Optional[str] = None,
):
    if not puede_organizar(interaction.user):
        return await interaction.response.send_message("❌ No tienes permiso para organizar eventos.", ephemeral=True)
    ev = {
        "canal": canal.id,
        "organizador": organizador.id,
        "descripcion": descripcion,
        "premio": premio,
        "tiempo": tiempo,
        "tipo": tipo,
        "ganadores": ganadores,
        "estado": "abierto",
        "participantes": [],
        "style": dict(cfg(interaction.guild.id)["ev"]["style"]),  # copia del diseño actual
        "creado_por": interaction.user.id,
    }
    try:
        msg = await canal.send(
            content=ping.mention if ping else None,
            embed=build_event_embed(ev),
            view=EventoView(),
            allowed_mentions=discord.AllowedMentions(roles=True, everyone=True),
        )
    except discord.Forbidden:
        return await interaction.response.send_message(f"❌ No puedo enviar mensajes en {canal.mention}.", ephemeral=True)
    ev["msg"] = msg.id
    cfg(interaction.guild.id)["ev"]["activos"][str(msg.id)] = ev
    save()
    await interaction.response.send_message(f"✅ Evento publicado: {msg.jump_url}", ephemeral=True)


@tree.command(name="iniciar-evento", description="Inicia un evento que está abierto")
@app_commands.describe(evento="Evento a iniciar")
@app_commands.guild_only()
async def iniciar_evento(interaction: discord.Interaction, evento: str):
    if not puede_organizar(interaction.user):
        return await interaction.response.send_message("❌ No tienes permiso para esto.", ephemeral=True)
    ev = cfg(interaction.guild.id)["ev"]["activos"].get(evento)
    if not ev or ev["estado"] != "abierto":
        return await interaction.response.send_message("⚠️ Ese evento no existe o ya fue iniciado.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    ev["estado"] = "iniciado"
    save()
    canal, msg = await mensaje_evento(interaction.guild, ev)
    if msg:
        await msg.edit(embed=build_event_embed(ev), view=EventoView(cerrado=True))
    if canal:
        await canal.send(
            f"▶️ **¡El evento ha comenzado!** Organiza <@{ev['organizador']}> · "
            f"{len(ev['participantes'])} participante(s).",
            allowed_mentions=discord.AllowedMentions.none(),
        )
    await interaction.followup.send("✅ Evento iniciado.", ephemeral=True)


@iniciar_evento.autocomplete("evento")
async def ac_iniciar(interaction: discord.Interaction, current: str):
    return await eventos_ac(interaction, current, "abierto")


@tree.command(name="finalizar-evento", description="Finaliza un evento iniciado y anuncia ganadores")
@app_commands.describe(
    evento="Evento a finalizar",
    ganador="Ganador (o 1.º lugar)",
    segundo="2.º lugar (opcional, para top 3)",
    tercero="3.º lugar (opcional, para top 3)",
    foto="Foto del premio entregado (opcional)",
)
@app_commands.guild_only()
async def finalizar_evento(
    interaction: discord.Interaction,
    evento: str,
    ganador: Optional[discord.Member] = None,
    segundo: Optional[discord.Member] = None,
    tercero: Optional[discord.Member] = None,
    foto: Optional[discord.Attachment] = None,
):
    if not puede_organizar(interaction.user):
        return await interaction.response.send_message("❌ No tienes permiso para esto.", ephemeral=True)
    ev = cfg(interaction.guild.id)["ev"]["activos"].get(evento)
    if not ev or ev["estado"] != "iniciado":
        return await interaction.response.send_message("⚠️ Ese evento no existe o aún no fue iniciado.", ephemeral=True)
    if foto and not (foto.content_type or "").startswith("image/"):
        return await interaction.response.send_message("❌ El archivo adjunto debe ser una imagen.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    lineas = [f"{medalla} {m.mention}" for medalla, m in (("🥇", ganador), ("🥈", segundo), ("🥉", tercero)) if m]
    ev["estado"] = "finalizado"
    ev["resultado"] = "\n".join(lineas) or None
    save()

    canal, msg = await mensaje_evento(interaction.guild, ev)
    if msg:
        await msg.edit(embed=build_event_embed(ev), view=None)
    if canal:
        resultado = discord.Embed(
            title="🏁 ¡Evento finalizado!",
            description=ev["descripcion"],
            color=0xF1C40F,
        )
        resultado.add_field(name="🏆 Ganador(es)", value=ev["resultado"] or "Sin ganadores registrados", inline=False)
        if ev.get("premio"):
            resultado.add_field(name="🎁 Premio", value=ev["premio"], inline=False)
        resultado.add_field(name="👤 Organizador", value=f"<@{ev['organizador']}>", inline=True)
        resultado.add_field(name="👥 Participantes", value=str(len(ev["participantes"])), inline=True)
        kwargs = {}
        if foto:
            archivo = await foto.to_file()
            resultado.set_image(url=f"attachment://{archivo.filename}")
            kwargs["file"] = archivo
        await canal.send(embed=resultado, allowed_mentions=discord.AllowedMentions(users=True), **kwargs)
    await interaction.followup.send("✅ Evento finalizado.", ephemeral=True)


@finalizar_evento.autocomplete("evento")
async def ac_finalizar(interaction: discord.Interaction, current: str):
    return await eventos_ac(interaction, current, "iniciado")




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
        if k == "eventos":
            return await interaction.response.edit_message(
                embeds=ev_panel(interaction.guild.id, interaction.user.id), view=EvConfigView()
            )
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


def ev_panel(guild_id: int, user_id: int):
    c = cfg(guild_id)["ev"]
    info = discord.Embed(title="🎉 Configurar eventos", color=0x5865F2)
    info.add_field(
        name="Roles que pueden organizar / iniciar / finalizar",
        value=" ".join(f"<@&{r}>" for r in c["roles"]) or "Solo administradores",
        inline=False,
    )
    info.set_footer(text="Abajo está la vista previa del embed. Se actualiza al editarlo.")
    ejemplo = {
        "style": c["style"],
        "descripcion": "Así se verá la descripción del evento.",
        "organizador": user_id,
        "tipo": "Ejemplo",
        "premio": "Premio de ejemplo",
        "tiempo": "30 minutos",
        "estado": "abierto",
        "participantes": [],
    }
    return [info, build_event_embed(ejemplo)]


class EvTextoModal(discord.ui.Modal, title="Editar texto y color"):
    def __init__(self, guild_id: int):
        super().__init__()
        st = cfg(guild_id)["ev"]["style"]
        self.titulo = discord.ui.TextInput(label="Título", default=st["titulo"], max_length=100)
        self.color = discord.ui.TextInput(label="Color (hex, ej: 5865F2)", default=st["color"], min_length=6, max_length=7)
        self.footer = discord.ui.TextInput(
            label="Pie de página (vacío = ninguno)", default=st["footer"] or "", required=False, max_length=100
        )
        for i in (self.titulo, self.color, self.footer):
            self.add_item(i)

    async def on_submit(self, interaction: discord.Interaction):
        hexa = self.color.value.lstrip("#")
        try:
            if len(hexa) != 6:
                raise ValueError
            int(hexa, 16)
        except ValueError:
            return await interaction.response.send_message("❌ Color inválido. Usa 6 dígitos hex, ej: 5865F2.", ephemeral=True)
        st = cfg(interaction.guild.id)["ev"]["style"]
        st["titulo"] = self.titulo.value
        st["color"] = hexa
        st["footer"] = self.footer.value or None
        save()
        await interaction.response.edit_message(embeds=ev_panel(interaction.guild.id, interaction.user.id), view=EvConfigView())


class EvImagenModal(discord.ui.Modal, title="Editar imágenes"):
    def __init__(self, guild_id: int):
        super().__init__()
        st = cfg(guild_id)["ev"]["style"]
        self.imagen = discord.ui.TextInput(
            label="URL de la imagen grande (vacío = ninguna)", default=st["imagen"] or "", required=False
        )
        self.miniatura = discord.ui.TextInput(
            label="URL de la miniatura (vacío = ninguna)", default=st["miniatura"] or "", required=False
        )
        self.add_item(self.imagen)
        self.add_item(self.miniatura)

    async def on_submit(self, interaction: discord.Interaction):
        for url in (self.imagen.value, self.miniatura.value):
            if url and not url.startswith(("http://", "https://")):
                return await interaction.response.send_message("❌ Las URLs deben empezar con http:// o https://", ephemeral=True)
        st = cfg(interaction.guild.id)["ev"]["style"]
        st["imagen"] = self.imagen.value or None
        st["miniatura"] = self.miniatura.value or None
        save()
        await interaction.response.edit_message(embeds=ev_panel(interaction.guild.id, interaction.user.id), view=EvConfigView())


class EvConfigView(AdminView):
    @discord.ui.select(
        cls=discord.ui.RoleSelect, min_values=1, max_values=10,
        placeholder="➕ Agregar roles que pueden organizar eventos", row=0,
    )
    async def agregar(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        roles = cfg(interaction.guild.id)["ev"]["roles"]
        for r in select.values:
            if r.id not in roles:
                roles.append(r.id)
        save()
        await interaction.response.edit_message(embeds=ev_panel(interaction.guild.id, interaction.user.id), view=EvConfigView())

    @discord.ui.select(
        cls=discord.ui.RoleSelect, min_values=1, max_values=10,
        placeholder="➖ Quitar roles", row=1,
    )
    async def quitar(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        c = cfg(interaction.guild.id)["ev"]
        quitar = {r.id for r in select.values}
        c["roles"] = [r for r in c["roles"] if r not in quitar]
        save()
        await interaction.response.edit_message(embeds=ev_panel(interaction.guild.id, interaction.user.id), view=EvConfigView())

    @discord.ui.button(label="✏️ Texto y color", style=discord.ButtonStyle.primary, row=2)
    async def texto(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EvTextoModal(interaction.guild.id))

    @discord.ui.button(label="🖼️ Imágenes", style=discord.ButtonStyle.primary, row=2)
    async def imagenes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EvImagenModal(interaction.guild.id))

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=2)
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
    embed.add_field(
        name="🎉 Eventos",
        value="`/organizar-evento` publica el evento con botón **Participar**\n"
        "`/iniciar-evento` lo inicia · `/finalizar-evento` lo cierra y anuncia ganadores/top 3\n"
        "Roles y diseño del embed: `/configuracion → Eventos`",
        inline=False,
    )
    embed.add_field(name="🚧 Próximamente", value="Postulaciones, seguridad, moderación y adivina la palabra.", inline=False)
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