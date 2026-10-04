import os
import json
import asyncio
import io
import random
from typing import Optional
from datetime import timedelta
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
    g.setdefault("mod", {
        "canal": None, "roles": [], "contador": 0, "casos": {}, "embeds": default_mod_embeds(),
    })
    g.setdefault("post", {
        "forms": {}, "roles_enviar": [], "roles_revisar": [], "canal": None,
        "contador": 0, "pend": {}, "rev": {}, "embeds": default_post_embeds(),
    })
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
        self.add_view(PostulaView())
        self.add_view(ReviewView())
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


# ─────────────────────────────── Postulaciones ───────────────────────────────
ACTIVAS = set()  # ids de mensajes públicos con un formulario en curso (en memoria)

VARIABLES = {
    "{candidato}": "Menciona a la persona que se postula",
    "{numero}": "Número de la postulación",
    "{ejecutor}": "Quien ejecutó el comando /postulacion",
    "{formulario}": "Nombre del formulario",
    "{servidor}": "Nombre del servidor",
    "{staff}": "Staff que aprobó/rechazó (solo en respuestas y MD)",
    "{estado}": "Estado de la postulación",
    "{nota}": "Nota del staff (solo en respuestas y MD)",
}


def default_post_embeds():
    return {
        "publica": {
            "titulo": "📝 Postulación #{numero}",
            "autor": "{servidor}",
            "descripcion": "{candidato} fue invitado a completar el formulario **{formulario}**.\n"
            "Solicitado por {ejecutor}.\n\nPulsa el botón para comenzar. Solo el candidato puede iniciarlo.",
            "color": "5865F2", "miniatura": None, "imagen": None, "footer": None,
        },
        "respuestas": {
            "titulo": "📋 Postulación #{numero} — {formulario}",
            "autor": None,
            "descripcion": "**Candidato:** {candidato}\n**Solicitada por:** {ejecutor}\n**Estado:** {estado}",
            "color": "F1C40F", "miniatura": None, "imagen": None, "footer": None,
        },
        "aprobada": {
            "titulo": "✅ Tu postulación fue aprobada",
            "autor": "{servidor}",
            "descripcion": "Hola {candidato}, tu postulación **#{numero}** ({formulario}) en **{servidor}** "
            "fue **aprobada** por {staff}.\n\n**Nota:** {nota}",
            "color": "2ECC71", "miniatura": None, "imagen": None, "footer": None,
        },
        "rechazada": {
            "titulo": "❌ Tu postulación fue rechazada",
            "autor": "{servidor}",
            "descripcion": "Hola {candidato}, tu postulación **#{numero}** ({formulario}) en **{servidor}** "
            "fue **rechazada** por {staff}.\n\n**Nota:** {nota}",
            "color": "E74C3C", "miniatura": None, "imagen": None, "footer": None,
        },
    }


def puede_enviar(member: discord.Member) -> bool:
    p = cfg(member.guild.id)["post"]
    return member.guild_permissions.administrator or any(r.id in p["roles_enviar"] for r in member.roles)


def puede_revisar(member: discord.Member) -> bool:
    p = cfg(member.guild.id)["post"]
    return member.guild_permissions.administrator or any(r.id in p["roles_revisar"] for r in member.roles)


def post_vars(guild, rec, estado="⏳ Pendiente", staff="—", nota="—"):
    return {
        "{candidato}": f"<@{rec['candidato']}>",
        "{numero}": str(rec["numero"]),
        "{ejecutor}": f"<@{rec['ejecutor']}>",
        "{formulario}": rec["formulario"],
        "{servidor}": guild.name,
        "{estado}": estado,
        "{staff}": staff,
        "{nota}": nota,
    }


def render(texto, vars):
    if not texto:
        return texto
    for k, v in vars.items():
        texto = texto.replace(k, v)
    return texto


def post_embed(st: dict, vars: dict) -> discord.Embed:
    try:
        color = int(st["color"].lstrip("#"), 16)
    except ValueError:
        color = 0x5865F2
    e = discord.Embed(
        title=(render(st.get("titulo"), vars) or None),
        description=(render(st.get("descripcion"), vars) or None),
        color=color,
    )
    if st.get("autor"):
        e.set_author(name=render(st["autor"], vars)[:256])
    if st.get("miniatura"):
        e.set_thumbnail(url=st["miniatura"])
    if st.get("imagen"):
        e.set_image(url=st["imagen"])
    if st.get("footer"):
        e.set_footer(text=render(st["footer"], vars)[:2048])
    return e


def build_resp_embed(guild, rec, vars=None) -> discord.Embed:
    vars = vars or post_vars(guild, rec)
    e = post_embed(cfg(guild.id)["post"]["embeds"]["respuestas"], vars)
    for q, a in rec["respuestas"]:
        e.add_field(name=q[:256], value=a[:1024] or "—", inline=False)
    return e


async def run_form(guild, pub_msg, rec, user, intro):
    """Hace las preguntas por MD una por una y envía todo al canal del staff."""
    p = cfg(guild.id)["post"]
    borrar = [intro]
    respuestas = []
    n = len(rec["preguntas"])

    async def limpiar():
        for m in borrar:
            try:
                await m.delete()
            except discord.HTTPException:
                pass

    async def abortar(texto):
        await limpiar()
        try:
            await user.send(texto)
        except discord.HTTPException:
            pass

    try:
        for i, q in enumerate(rec["preguntas"], 1):
            emb = discord.Embed(title=f"📝 Pregunta {i}/{n}", description=q, color=0x5865F2)
            emb.set_footer(text="Responde en un mensaje (máx. 400 caracteres) · Escribe 'cancelar' para salir")
            borrar.append(await user.send(embed=emb))
            while True:
                try:
                    resp = await client.wait_for(
                        "message",
                        check=lambda x: x.author.id == user.id and x.channel.id == intro.channel.id,
                        timeout=600,
                    )
                except asyncio.TimeoutError:
                    return await abortar("⌛ Se acabó el tiempo. Pulsa de nuevo **Iniciar formulario** para reintentar.")
                if resp.content.strip().lower() == "cancelar":
                    return await abortar("🚫 Formulario cancelado. Puedes volver a pulsar **Iniciar formulario**.")
                texto = resp.content.strip()
                if resp.attachments:
                    texto = (texto + "\n" + "\n".join(a.url for a in resp.attachments)).strip()
                if not texto:
                    borrar.append(await user.send("✏️ Escribe tu respuesta en texto."))
                    continue
                if len(texto) > 400:
                    borrar.append(await user.send(f"⚠️ Tu respuesta tiene {len(texto)} caracteres; el máximo es 400. Envíala más corta."))
                    continue
                break
            respuestas.append([q, texto])
    except discord.HTTPException:
        return
    finally:
        ACTIVAS.discard(pub_msg.id)

    canal = guild.get_channel(p["canal"]) if p["canal"] else None
    if canal is None:
        return await abortar("⚠️ El staff aún no configuró el canal de respuestas. Avísales e inténtalo de nuevo.")

    rec["respuestas"] = respuestas
    rec["estado"] = "completada"
    staff_msg = await canal.send(embed=build_resp_embed(guild, rec), view=ReviewView())
    p["rev"][str(staff_msg.id)] = dict(rec)
    save()

    try:
        e = pub_msg.embeds[0].copy()
        e.add_field(name="Estado", value="📨 Formulario enviado al staff", inline=False)
        await pub_msg.edit(embed=e, view=None)
    except discord.HTTPException:
        pass

    await limpiar()
    try:
        await user.send(f"✅ ¡Listo! Tu postulación **#{rec['numero']}** fue enviada al staff. Recibirás la respuesta por aquí.")
    except discord.HTTPException:
        pass


class PostulaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Iniciar formulario", emoji="📝", style=discord.ButtonStyle.success, custom_id="post:start")
    async def iniciar(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = cfg(interaction.guild.id)["post"]
        rec = p["pend"].get(str(interaction.message.id))
        if not rec:
            return await interaction.response.send_message("❌ Esta postulación ya no existe.", ephemeral=True)
        if interaction.user.id != rec["candidato"]:
            return await interaction.response.send_message(
                f"🔒 Solo <@{rec['candidato']}> puede iniciar este formulario.", ephemeral=True
            )
        if rec["estado"] == "completada":
            return await interaction.response.send_message("✅ Ya completaste este formulario.", ephemeral=True)
        if interaction.message.id in ACTIVAS:
            return await interaction.response.send_message("📬 Ya tienes el formulario abierto en tus MD.", ephemeral=True)
        try:
            intro = await interaction.user.send(
                embed=discord.Embed(
                    title=f"📝 Formulario: {rec['formulario']}",
                    description=f"Vas a responder **{len(rec['preguntas'])}** pregunta(s) para **{interaction.guild.name}**.\n"
                    "Te las haré una por una. Escribe `cancelar` en cualquier momento para salir.",
                    color=0x5865F2,
                )
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ No puedo escribirte por MD. Activa los mensajes directos del servidor y vuelve a intentarlo.",
                ephemeral=True,
            )
        ACTIVAS.add(interaction.message.id)
        await interaction.response.send_message("📬 ¡Te escribí por MD! Continúa ahí.", ephemeral=True)
        asyncio.create_task(run_form(interaction.guild, interaction.message, rec, interaction.user, intro))


class NotaPostModal(discord.ui.Modal):
    def __init__(self, aprobado: bool, mensaje: discord.Message):
        super().__init__(title="Aprobar postulación" if aprobado else "Rechazar postulación")
        self.aprobado = aprobado
        self.mensaje = mensaje
        self.nota = discord.ui.TextInput(
            label="Nota para el postulante (opcional)", style=discord.TextStyle.paragraph, required=False, max_length=800
        )
        self.add_item(self.nota)

    async def on_submit(self, interaction: discord.Interaction):
        p = cfg(interaction.guild.id)["post"]
        rec = p["rev"].get(str(self.mensaje.id))
        if not rec:
            return await interaction.response.send_message("❌ No encuentro los datos de esta postulación.", ephemeral=True)
        nota = self.nota.value or "Sin nota."
        estado = "✅ Aprobada" if self.aprobado else "❌ Rechazada"
        vars = post_vars(interaction.guild, rec, estado=estado, staff=interaction.user.mention, nota=nota)

        embed = build_resp_embed(interaction.guild, rec, vars)
        embed.color = 0x2ECC71 if self.aprobado else 0xE74C3C
        embed.add_field(name="Revisada por", value=interaction.user.mention, inline=True)
        embed.add_field(name="Nota", value=nota, inline=False)
        await interaction.response.edit_message(embed=embed, view=None)

        rec["estado"] = "aprobada" if self.aprobado else "rechazada"
        rec["revisor"] = interaction.user.id
        rec["nota"] = nota
        save()
        try:
            user = await client.fetch_user(rec["candidato"])
            dm = post_embed(p["embeds"]["aprobada" if self.aprobado else "rechazada"], vars)
            await user.send(embed=dm)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.followup.send("⚠️ No pude enviarle el MD al postulante (los tiene cerrados).", ephemeral=True)


class ReviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not puede_revisar(interaction.user):
            await interaction.response.send_message("❌ No tienes permiso para revisar postulaciones.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.success, custom_id="post:ok")
    async def aprobar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NotaPostModal(True, interaction.message))

    @discord.ui.button(label="Rechazar", style=discord.ButtonStyle.danger, custom_id="post:no")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NotaPostModal(False, interaction.message))


@tree.command(name="postulacion", description="Envía un formulario de postulación a un candidato")
@app_commands.describe(formulario="Formulario que debe responder", candidato="Quién se está postulando")
@app_commands.guild_only()
async def postulacion(interaction: discord.Interaction, formulario: str, candidato: discord.Member):
    p = cfg(interaction.guild.id)["post"]
    if not puede_enviar(interaction.user):
        return await interaction.response.send_message("❌ No tienes permiso para enviar postulaciones.", ephemeral=True)
    if candidato.bot:
        return await interaction.response.send_message("❌ Un bot no puede postularse.", ephemeral=True)
    preguntas = p["forms"].get(formulario)
    if not preguntas:
        return await interaction.response.send_message("⚠️ Ese formulario no existe.", ephemeral=True)
    if not p["canal"] or interaction.guild.get_channel(p["canal"]) is None:
        return await interaction.response.send_message(
            "⚠️ Falta configurar el canal de respuestas en `/configuracion → Postulaciones`.", ephemeral=True
        )
    p["contador"] += 1
    rec = {
        "numero": p["contador"],
        "formulario": formulario,
        "preguntas": list(preguntas),
        "candidato": candidato.id,
        "ejecutor": interaction.user.id,
        "canal_pub": interaction.channel_id,
        "estado": "esperando",
    }
    await interaction.response.send_message(
        content=candidato.mention,
        embed=post_embed(p["embeds"]["publica"], post_vars(interaction.guild, rec)),
        view=PostulaView(),
        allowed_mentions=discord.AllowedMentions(users=[candidato]),
    )
    msg = await interaction.original_response()
    p["pend"][str(msg.id)] = rec
    save()


@postulacion.autocomplete("formulario")
async def ac_formulario(interaction: discord.Interaction, current: str):
    forms = cfg(interaction.guild.id)["post"]["forms"]
    return [app_commands.Choice(name=n, value=n) for n in forms if current.lower() in n.lower()][:25]


@tree.command(name="variables", description="Variables que puedes usar en los embeds de postulación")
async def variables_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🧩 Variables de postulación",
        description="Escríbelas tal cual en el título, autor, descripción o pie de los embeds "
        "(`/configuracion → Postulaciones → Embeds`) y se reemplazarán solas.\n\n"
        + "\n".join(f"`{k}` — {v}" for k, v in VARIABLES.items()),
        color=0x5865F2,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────── Estado de postulaciones (para el staff) ──────────────────
@tree.command(name="postulacion-estado", description="Consulta el estado de una postulación por formulario y número")
@app_commands.describe(formulario="Nombre del formulario", numero="Número de la postulación")
@app_commands.guild_only()
async def postulacion_estado(interaction: discord.Interaction, formulario: str, numero: app_commands.Range[int, 1, 10_000_000]):
    if not (puede_enviar(interaction.user) or puede_revisar(interaction.user)):
        return await interaction.response.send_message("❌ Solo el staff puede consultar postulaciones.", ephemeral=True)
    g = interaction.guild
    p = cfg(g.id)["post"]
    rec = pub_id = rev_id = None
    for mid, r in p["pend"].items():
        if r["numero"] == numero:
            rec, pub_id = r, mid
            break
    for mid, r in p["rev"].items():  # la copia de revisión tiene el estado más reciente
        if r["numero"] == numero:
            rec, rev_id = r, mid
            break
    if not rec or rec["formulario"].lower() != formulario.lower():
        return await interaction.response.send_message(
            f"⚠️ No encontré la postulación **#{numero}** del formulario **{formulario}**.", ephemeral=True
        )

    est = rec["estado"]
    if est == "aprobada":
        texto, color = "✅ Aprobada", 0x2ECC71
    elif est == "rechazada":
        texto, color = "❌ Rechazada", 0xE74C3C
    elif est == "completada":
        texto, color = "📨 En revisión (esperando respuesta del staff)", 0xF1C40F
    elif pub_id and int(pub_id) in ACTIVAS:
        texto, color = "📝 El candidato está respondiendo el formulario", 0x3498DB
    else:
        texto, color = "⏳ Esperando a que el candidato inicie el formulario", 0x95A5A6

    e = discord.Embed(title=f"📋 Postulación #{numero} — {rec['formulario']}", color=color)
    e.add_field(name="Candidato", value=f"<@{rec['candidato']}>", inline=True)
    e.add_field(name="Solicitada por", value=f"<@{rec['ejecutor']}>", inline=True)
    e.add_field(name="Estado", value=texto, inline=False)
    if rec.get("revisor"):
        e.add_field(name="Revisada por", value=f"<@{rec['revisor']}>", inline=True)
        e.add_field(name="Nota", value=rec.get("nota") or "Sin nota.", inline=False)
    links = []
    if pub_id and rec.get("canal_pub"):
        links.append(f"[Mensaje del formulario](https://discord.com/channels/{g.id}/{rec['canal_pub']}/{pub_id})")
    if rev_id and p["canal"]:
        links.append(f"[Respuestas del candidato](https://discord.com/channels/{g.id}/{p['canal']}/{rev_id})")
    if links:
        e.add_field(name="Enlaces", value=" · ".join(links), inline=False)
    await interaction.response.send_message(embed=e, ephemeral=True)


@postulacion_estado.autocomplete("formulario")
async def ac_estado_form(interaction: discord.Interaction, current: str):
    p = cfg(interaction.guild.id)["post"]
    nombres = list(dict.fromkeys(list(p["forms"]) + [r["formulario"] for r in p["pend"].values()]))
    return [app_commands.Choice(name=n[:100], value=n[:100]) for n in nombres if current.lower() in n.lower()][:25]


# ─────────────────────────────── Moderación ──────────────────────────────────
TIPOS = {"Ban": "🔨", "Kick": "👢", "Warn": "⚠️", "Mute": "🔇", "Nota": "📝",
         "Unban": "✅", "Unwarn": "✅", "Unmute": "🔊"}

MOD_VARIABLES = {
    "{usuario}": "Menciona al usuario sancionado",
    "{usuario_id}": "ID del usuario",
    "{staff}": "Staff que aplicó la acción",
    "{razon}": "Razón indicada",
    "{caso}": "Número de caso",
    "{tipo}": "Tipo (Ban, Warn, Unban...)",
    "{duracion}": "Duración (solo mute)",
    "{fecha}": "Fecha y hora",
    "{servidor}": "Nombre del servidor",
}


def default_mod_embeds():
    return {
        "dm": {
            "titulo": "📢 Aviso de moderación: {tipo}",
            "autor": "{servidor}",
            "descripcion": "Hola {usuario}, en **{servidor}** se te aplicó **{tipo}** (Caso #{caso}).\n\n"
            "**Staff:** {staff}\n**Razón:** {razon}\n**Duración:** {duracion}\n**Fecha:** {fecha}",
            "color": "E74C3C", "miniatura": None, "imagen": None, "footer": None,
        },
        "registro": {
            "titulo": "#Caso {caso} ({tipo})",
            "autor": None,
            "descripcion": "**Usuario:** {usuario} (`{usuario_id}`)\n**Staff:** {staff}\n**Razón:** {razon}\n"
            "**Duración:** {duracion}\n**Fecha:** {fecha}",
            "color": "5865F2", "miniatura": None, "imagen": None, "footer": None,
        },
    }


def puede_moderar(member: discord.Member) -> bool:
    m = cfg(member.guild.id)["mod"]
    return member.guild_permissions.administrator or any(r.id in m["roles"] for r in member.roles)


def mod_vars(guild, caso):
    return {
        "{usuario}": f"<@{caso['usuario']}>",
        "{usuario_id}": str(caso["usuario"]),
        "{staff}": f"<@{caso['staff']}>",
        "{caso}": str(caso["n"]),
        "{tipo}": caso["tipo"],
        "{duracion}": caso.get("duracion") or "—",
        "{fecha}": f"<t:{caso['ts']}:f>",
        "{servidor}": guild.name,
        "{razon}": caso["razon"],  # al final para no re-sustituir variables escritas por el staff
    }


def caso_url(guild_id, caso):
    if caso.get("msg") and caso.get("canal"):
        return f"https://discord.com/channels/{guild_id}/{caso['canal']}/{caso['msg']}"
    return None


def anular_caso(m, usuario_id, tipo, nuevo, caso_id=None):
    for n, c in sorted(m["casos"].items(), key=lambda kv: int(kv[0]), reverse=True):
        if c["usuario"] == usuario_id and c["tipo"] == tipo and not c.get("anulado") and (caso_id is None or c["n"] == caso_id):
            c["anulado"] = nuevo
            return


async def precheck_mod(interaction: discord.Interaction, prueba=None) -> bool:
    if not puede_moderar(interaction.user):
        await interaction.response.send_message("❌ No tienes permiso para moderar.", ephemeral=True)
        return False
    m = cfg(interaction.guild.id)["mod"]
    if not m["canal"] or interaction.guild.get_channel(m["canal"]) is None:
        await interaction.response.send_message(
            "⚠️ Falta configurar el canal de registros en `/configuracion → Moderación`.", ephemeral=True
        )
        return False
    if prueba is not None and not (prueba.content_type or "").startswith("image/"):
        await interaction.response.send_message("❌ La prueba debe ser una imagen (foto).", ephemeral=True)
        return False
    return True


async def jerarquia(interaction: discord.Interaction, miembro: discord.Member) -> bool:
    g = interaction.guild
    msg = None
    if miembro.id == interaction.user.id:
        msg = "No puedes aplicarte una sanción a ti mismo."
    elif miembro.id == g.owner_id:
        msg = "No puedes sancionar al dueño del servidor."
    elif miembro.id == client.user.id:
        msg = "No puedo sancionarme a mí mismo."
    elif interaction.user.id != g.owner_id and miembro.top_role >= interaction.user.top_role:
        msg = "Su rol es igual o superior al tuyo."
    elif miembro.top_role >= g.me.top_role:
        msg = "Mi rol es igual o inferior al de esa persona; súbeme de rango."
    if msg:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
        return False
    return True


async def registrar_caso(interaction, tipo, usuario, razon, prueba=None, duracion=None,
                         accion=None, avisar=True, anula=None):
    """Avisa por MD, ejecuta la acción y deja el caso en el canal de registros."""
    guild = interaction.guild
    m = cfg(guild.id)["mod"]
    datos = await prueba.read() if prueba else None
    ext = "".join(ch for ch in prueba.filename.rsplit(".", 1)[-1] if ch.isalnum())[:5] if prueba and "." in prueba.filename else "png"
    nombre = f"prueba.{ext or 'png'}"

    m["contador"] += 1
    caso = {
        "n": m["contador"], "tipo": tipo, "usuario": usuario.id, "staff": interaction.user.id,
        "razon": razon, "duracion": duracion, "ts": int(discord.utils.utcnow().timestamp()),
        "prueba": bool(datos), "msg": None, "canal": None, "anulado": None,
    }
    vars = mod_vars(guild, caso)

    def adjuntar(emb):
        kw = {}
        if datos:
            emb.set_image(url=f"attachment://{nombre}")
            kw["file"] = discord.File(io.BytesIO(datos), filename=nombre)
        return kw

    # 1) MD al usuario (antes de ban/kick, después ya no podríamos escribirle)
    dm_ok = None
    if avisar:
        emb = post_embed(m["embeds"]["dm"], vars)
        kw = adjuntar(emb)
        try:
            await usuario.send(embed=emb, **kw)
            dm_ok = True
        except (discord.Forbidden, discord.HTTPException):
            dm_ok = False

    # 2) Acción real
    if accion:
        try:
            await accion()
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ No pude ejecutar la acción: {e.text or e}", ephemeral=True)
            return None

    # 3) Registro en el canal
    canal = guild.get_channel(m["canal"])
    emb = post_embed(m["embeds"]["registro"], vars)
    kw = adjuntar(emb)
    try:
        msg = await canal.send(embed=emb, **kw)
        base = emb.footer.text if emb.footer and emb.footer.text else None
        emb.set_footer(text=f"{base} · ID del mensaje: {msg.id}" if base else f"ID del mensaje: {msg.id}")
        await msg.edit(embed=emb)
        caso["msg"], caso["canal"] = msg.id, canal.id
    except discord.HTTPException:
        await interaction.followup.send("⚠️ La acción se aplicó, pero no pude escribir en el canal de registros.", ephemeral=True)

    m["casos"][str(caso["n"])] = caso
    if anula:
        anular_caso(m, usuario.id, anula[0], caso["n"], anula[1])
    save()
    return caso, dm_ok


async def responder_caso(interaction, res, avisaba=True):
    if res is None:
        return
    caso, dm_ok = res
    txt = f"✅ Caso **#{caso['n']}** ({caso['tipo']}) registrado."
    if avisaba:
        txt += " 📬 Aviso enviado por MD." if dm_ok else " ⚠️ No pude enviarle el MD."
    await interaction.followup.send(txt, ephemeral=True)


DURACIONES = [
    app_commands.Choice(name="10 minutos", value=600),
    app_commands.Choice(name="1 hora", value=3600),
    app_commands.Choice(name="6 horas", value=21600),
    app_commands.Choice(name="1 día", value=86400),
    app_commands.Choice(name="7 días", value=604800),
    app_commands.Choice(name="28 días", value=2419200),
]


@tree.command(name="ban", description="Banea a un usuario (requiere prueba en foto)")
@app_commands.describe(usuario="Usuario a banear", razon="Motivo", prueba="Foto de prueba")
@app_commands.guild_only()
async def ban_cmd(interaction: discord.Interaction, usuario: discord.User,
                  razon: app_commands.Range[str, 1, 500], prueba: discord.Attachment):
    if not await precheck_mod(interaction, prueba):
        return
    g = interaction.guild
    if not g.me.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ No tengo el permiso **Banear miembros**.", ephemeral=True)
    miembro = g.get_member(usuario.id)
    if miembro and not await jerarquia(interaction, miembro):
        return
    await interaction.response.defer(ephemeral=True)
    res = await registrar_caso(interaction, "Ban", usuario, razon, prueba,
                               accion=lambda: g.ban(usuario, reason=f"[Nexus] {razon}", delete_message_seconds=0))
    await responder_caso(interaction, res)


@tree.command(name="unban", description="Quita el ban a un usuario")
@app_commands.describe(usuario="Usuario baneado (ID o mención)", razon="Motivo", prueba="Foto de prueba (opcional)")
@app_commands.guild_only()
async def unban_cmd(interaction: discord.Interaction, usuario: discord.User,
                    razon: app_commands.Range[str, 1, 500], prueba: Optional[discord.Attachment] = None):
    if not await precheck_mod(interaction, prueba):
        return
    g = interaction.guild
    try:
        await g.fetch_ban(usuario)
    except discord.NotFound:
        return await interaction.response.send_message("⚠️ Ese usuario no está baneado.", ephemeral=True)
    except discord.Forbidden:
        return await interaction.response.send_message("❌ No tengo el permiso **Banear miembros**.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    res = await registrar_caso(interaction, "Unban", usuario, razon, prueba,
                               accion=lambda: g.unban(usuario, reason=f"[Nexus] {razon}"), anula=("Ban", None))
    await responder_caso(interaction, res)


@tree.command(name="kick", description="Expulsa a un miembro (requiere prueba en foto)")
@app_commands.describe(usuario="Miembro a expulsar", razon="Motivo", prueba="Foto de prueba")
@app_commands.guild_only()
async def kick_cmd(interaction: discord.Interaction, usuario: discord.Member,
                   razon: app_commands.Range[str, 1, 500], prueba: discord.Attachment):
    if not await precheck_mod(interaction, prueba):
        return
    if not interaction.guild.me.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ No tengo el permiso **Expulsar miembros**.", ephemeral=True)
    if not await jerarquia(interaction, usuario):
        return
    await interaction.response.defer(ephemeral=True)
    res = await registrar_caso(interaction, "Kick", usuario, razon, prueba,
                               accion=lambda: usuario.kick(reason=f"[Nexus] {razon}"))
    await responder_caso(interaction, res)


@tree.command(name="warn", description="Advierte a un miembro (requiere prueba en foto)")
@app_commands.describe(usuario="Miembro a advertir", razon="Motivo", prueba="Foto de prueba")
@app_commands.guild_only()
async def warn_cmd(interaction: discord.Interaction, usuario: discord.Member,
                   razon: app_commands.Range[str, 1, 500], prueba: discord.Attachment):
    if not await precheck_mod(interaction, prueba):
        return
    if not await jerarquia(interaction, usuario):
        return
    await interaction.response.defer(ephemeral=True)
    res = await registrar_caso(interaction, "Warn", usuario, razon, prueba)
    await responder_caso(interaction, res)


@tree.command(name="unwarn", description="Quita un warn (indica el número de caso del warn)")
@app_commands.describe(usuario="Miembro", caso="Número del caso del warn", razon="Motivo", prueba="Foto de prueba (opcional)")
@app_commands.guild_only()
async def unwarn_cmd(interaction: discord.Interaction, usuario: discord.Member, caso: app_commands.Range[int, 1, 10_000_000],
                     razon: app_commands.Range[str, 1, 500], prueba: Optional[discord.Attachment] = None):
    if not await precheck_mod(interaction, prueba):
        return
    c = cfg(interaction.guild.id)["mod"]["casos"].get(str(caso))
    if not c or c["tipo"] != "Warn" or c["usuario"] != usuario.id:
        return await interaction.response.send_message("⚠️ Ese caso no es un warn de ese usuario.", ephemeral=True)
    if c.get("anulado"):
        return await interaction.response.send_message("⚠️ Ese warn ya fue anulado.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    res = await registrar_caso(interaction, "Unwarn", usuario, f"{razon} (anula el caso #{caso})", prueba, anula=("Warn", caso))
    await responder_caso(interaction, res)


@tree.command(name="mute", description="Aísla (timeout) a un miembro (requiere prueba en foto)")
@app_commands.describe(usuario="Miembro", duracion="Duración", razon="Motivo", prueba="Foto de prueba")
@app_commands.choices(duracion=DURACIONES)
@app_commands.guild_only()
async def mute_cmd(interaction: discord.Interaction, usuario: discord.Member, duracion: app_commands.Choice[int],
                   razon: app_commands.Range[str, 1, 500], prueba: discord.Attachment):
    if not await precheck_mod(interaction, prueba):
        return
    if not interaction.guild.me.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ No tengo el permiso **Aislar miembros**.", ephemeral=True)
    if not await jerarquia(interaction, usuario):
        return
    await interaction.response.defer(ephemeral=True)
    res = await registrar_caso(interaction, "Mute", usuario, razon, prueba, duracion=duracion.name,
                               accion=lambda: usuario.timeout(timedelta(seconds=duracion.value), reason=f"[Nexus] {razon}"))
    await responder_caso(interaction, res)


@tree.command(name="unmute", description="Quita el aislamiento a un miembro")
@app_commands.describe(usuario="Miembro", razon="Motivo", prueba="Foto de prueba (opcional)")
@app_commands.guild_only()
async def unmute_cmd(interaction: discord.Interaction, usuario: discord.Member,
                     razon: app_commands.Range[str, 1, 500], prueba: Optional[discord.Attachment] = None):
    if not await precheck_mod(interaction, prueba):
        return
    if not usuario.is_timed_out():
        return await interaction.response.send_message("⚠️ Ese miembro no está aislado.", ephemeral=True)
    if not await jerarquia(interaction, usuario):
        return
    await interaction.response.defer(ephemeral=True)
    res = await registrar_caso(interaction, "Unmute", usuario, razon, prueba,
                               accion=lambda: usuario.timeout(None, reason=f"[Nexus] {razon}"), anula=("Mute", None))
    await responder_caso(interaction, res)


@tree.command(name="nota", description="Agrega una nota interna a un miembro (no se le avisa)")
@app_commands.describe(usuario="Miembro", razon="Texto de la nota", prueba="Foto (opcional)")
@app_commands.guild_only()
async def nota_cmd(interaction: discord.Interaction, usuario: discord.Member,
                   razon: app_commands.Range[str, 1, 500], prueba: Optional[discord.Attachment] = None):
    if not await precheck_mod(interaction, prueba):
        return
    await interaction.response.defer(ephemeral=True)
    res = await registrar_caso(interaction, "Nota", usuario, razon, prueba, avisar=False)
    await responder_caso(interaction, res, avisaba=False)


@tree.command(name="historial", description="Historial de sanciones de un usuario")
@app_commands.describe(usuario="Usuario a consultar")
@app_commands.guild_only()
async def historial(interaction: discord.Interaction, usuario: discord.User):
    if not puede_moderar(interaction.user):
        return await interaction.response.send_message("❌ No tienes permiso para esto.", ephemeral=True)
    g = interaction.guild
    casos = sorted((c for c in cfg(g.id)["mod"]["casos"].values() if c["usuario"] == usuario.id),
                   key=lambda c: c["n"], reverse=True)
    e = discord.Embed(title=f"📚 Historial de {usuario}", color=0x5865F2)
    e.set_thumbnail(url=usuario.display_avatar.url)
    if not casos:
        e.description = "Sin casos registrados ✅"
    else:
        cuenta = {}
        for c in casos:
            cuenta[c["tipo"]] = cuenta.get(c["tipo"], 0) + 1
        activos = sum(1 for c in casos if c["tipo"] == "Warn" and not c["anulado"])
        lineas = []
        for c in casos[:15]:
            l = f"`#{c['n']}` {TIPOS[c['tipo']]} **{c['tipo']}** · <t:{c['ts']}:d> · {c['razon'][:60].replace(chr(10), ' ')}"
            if c["anulado"]:
                l += f" ↩️ *anulado (#{c['anulado']})*"
            url = caso_url(g.id, c)
            if url:
                l += f" · [ver]({url})"
            lineas.append(l)
        e.description = (
            "**Resumen:** " + " · ".join(f"{TIPOS[t]} {t}: {n}" for t, n in cuenta.items())
            + f"\n⚠️ Warns activos: **{activos}**\n\n" + "\n".join(lineas)
        )
        if len(casos) > 15:
            e.set_footer(text=f"Mostrando los 15 más recientes de {len(casos)} casos · Usa /caso para ver uno")
    await interaction.response.send_message(embed=e, ephemeral=True)


@tree.command(name="caso", description="Muestra un caso de moderación por su número")
@app_commands.describe(numero="Número de caso")
@app_commands.guild_only()
async def caso_cmd(interaction: discord.Interaction, numero: app_commands.Range[int, 1, 10_000_000]):
    if not puede_moderar(interaction.user):
        return await interaction.response.send_message("❌ No tienes permiso para esto.", ephemeral=True)
    g = interaction.guild
    m = cfg(g.id)["mod"]
    c = m["casos"].get(str(numero))
    if not c:
        return await interaction.response.send_message("⚠️ Ese caso no existe.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    emb = None
    canal = g.get_channel(c["canal"]) if c.get("canal") else None
    if canal and c.get("msg"):
        try:
            msg = await canal.fetch_message(c["msg"])
            emb = msg.embeds[0].copy()
            if msg.attachments:
                emb.set_image(url=msg.attachments[0].url)
        except (discord.HTTPException, IndexError):
            emb = None
    if emb is None:
        emb = post_embed(m["embeds"]["registro"], mod_vars(g, c))
    if c.get("anulado"):
        emb.add_field(name="Estado", value=f"↩️ Anulado por el caso #{c['anulado']}", inline=False)
    await interaction.followup.send(embed=emb, ephemeral=True)


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
        if k == "moderacion":
            return await interaction.response.edit_message(embed=mod_home_embed(interaction.guild.id), view=ModHomeView())
        if k == "postulaciones":
            return await interaction.response.edit_message(embed=post_home_embed(interaction.guild.id), view=PostHomeView())
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


POST_EMBED_NOMBRES = {
    "publica": "Embed público (con botón)",
    "respuestas": "Embed de respuestas (canal staff)",
    "aprobada": "MD: postulación aprobada",
    "rechazada": "MD: postulación rechazada",
}


def _roles(ids, vacio):
    return " ".join(f"<@&{r}>" for r in ids) or vacio


def post_home_embed(gid: int):
    p = cfg(gid)["post"]
    e = discord.Embed(title="📝 Configurar postulaciones", color=0x5865F2)
    forms = "\n".join(f"• **{n}** ({len(q)} preguntas)" for n, q in p["forms"].items())
    e.add_field(name="Formularios", value=forms or "Ninguno todavía. Entra a **Formularios** para crear uno.", inline=False)
    e.add_field(name="Pueden enviar postulaciones", value=_roles(p["roles_enviar"], "Solo administradores"), inline=False)
    e.add_field(name="Aprueban / rechazan", value=_roles(p["roles_revisar"], "Solo administradores"), inline=False)
    e.add_field(name="Canal de respuestas", value=f"<#{p['canal']}>" if p["canal"] else "No configurado", inline=False)
    return e


def post_forms_embed(gid: int):
    p = cfg(gid)["post"]
    e = discord.Embed(title="📋 Formularios", color=0x5865F2)
    if not p["forms"]:
        e.description = "Aún no hay formularios. Pulsa **Agregar / editar formulario**."
    for n, qs in p["forms"].items():
        e.add_field(name=n, value="\n".join(f"{i}. {q}" for i, q in enumerate(qs, 1))[:1024], inline=False)
    e.set_footer(text="Si agregas un formulario con un nombre que ya existe, se reemplaza.")
    return e


def post_embeds_menu_embed():
    return discord.Embed(
        title="🎨 Embeds de postulación",
        description="Elige cuál quieres editar:\n\n" + "\n".join(f"• **{v}**" for v in POST_EMBED_NOMBRES.values())
        + "\n\nUsa `/variables` para ver las variables disponibles.",
        color=0x5865F2,
    )


def post_embed_panel(guild, user_id: int, key: str):
    p = cfg(guild.id)["post"]
    info = discord.Embed(
        title=f"🎨 Editando: {POST_EMBED_NOMBRES[key]}",
        description="Variables: " + ", ".join(f"`{k}`" for k in VARIABLES) + "\n\nAbajo ves la vista previa en vivo.",
        color=0x5865F2,
    )
    rec = {
        "candidato": user_id, "ejecutor": user_id, "numero": 1, "formulario": "Staff",
        "respuestas": [["¿Por qué quieres unirte?", "Respuesta de ejemplo."]],
    }
    if key == "respuestas":
        prev = build_resp_embed(guild, rec)
    else:
        prev = post_embed(p["embeds"][key], post_vars(guild, rec, staff=f"<@{user_id}>", nota="Nota de ejemplo."))
    return [info, prev]


class PostDelSelect(discord.ui.Select):
    def __init__(self, nombres):
        super().__init__(
            placeholder="🗑️ Eliminar un formulario",
            options=[discord.SelectOption(label=n[:100], value=n) for n in nombres],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        cfg(interaction.guild.id)["post"]["forms"].pop(self.values[0], None)
        save()
        await interaction.response.edit_message(embed=post_forms_embed(interaction.guild.id), view=PostFormsView(interaction.guild.id))


class PostFormModal(discord.ui.Modal, title="Agregar / editar formulario"):
    def __init__(self):
        super().__init__()
        self.nombre = discord.ui.TextInput(label="Nombre del formulario", max_length=50, placeholder="Ej: Staff")
        self.preguntas = discord.ui.TextInput(
            label="Preguntas (una por línea, máx. 10)",
            style=discord.TextStyle.paragraph,
            max_length=1500,
            placeholder="¿Cuántos años tienes?\n¿Por qué quieres ser staff?",
        )
        self.add_item(self.nombre)
        self.add_item(self.preguntas)

    async def on_submit(self, interaction: discord.Interaction):
        qs = [l.strip() for l in self.preguntas.value.splitlines() if l.strip()]
        if not qs or len(qs) > 10 or any(len(q) > 100 for q in qs):
            return await interaction.response.send_message(
                "❌ Escribe entre 1 y 10 preguntas, de máximo 100 caracteres cada una.", ephemeral=True
            )
        cfg(interaction.guild.id)["post"]["forms"][self.nombre.value.strip()] = qs
        save()
        await interaction.response.edit_message(embed=post_forms_embed(interaction.guild.id), view=PostFormsView(interaction.guild.id))


class PostFormsView(AdminView):
    def __init__(self, gid: int):
        super().__init__()
        nombres = list(cfg(gid)["post"]["forms"])[:25]
        if nombres:
            self.add_item(PostDelSelect(nombres))

    @discord.ui.button(label="➕ Agregar / editar formulario", style=discord.ButtonStyle.success, row=1)
    async def agregar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PostFormModal())

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=post_home_embed(interaction.guild.id), view=PostHomeView())


class PostRolesView(AdminView):
    @discord.ui.select(cls=discord.ui.RoleSelect, min_values=0, max_values=10,
                       placeholder="Roles que pueden enviar postulaciones", row=0)
    async def enviar(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        cfg(interaction.guild.id)["post"]["roles_enviar"] = [r.id for r in select.values]
        save()
        await interaction.response.edit_message(embed=post_home_embed(interaction.guild.id), view=PostRolesView())

    @discord.ui.select(cls=discord.ui.RoleSelect, min_values=0, max_values=10,
                       placeholder="Roles que aprueban / rechazan", row=1)
    async def revisar(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        cfg(interaction.guild.id)["post"]["roles_revisar"] = [r.id for r in select.values]
        save()
        await interaction.response.edit_message(embed=post_home_embed(interaction.guild.id), view=PostRolesView())

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                       placeholder="Canal donde llegan las respuestas", row=2)
    async def canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        cfg(interaction.guild.id)["post"]["canal"] = select.values[0].id
        save()
        await interaction.response.edit_message(embed=post_home_embed(interaction.guild.id), view=PostRolesView())

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=3)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=post_home_embed(interaction.guild.id), view=PostHomeView())


class PostTextoModal(discord.ui.Modal, title="Título, autor y color"):
    def __init__(self, key: str, gid: int):
        super().__init__()
        self.key = key
        st = cfg(gid)["post"]["embeds"][key]
        self.titulo = discord.ui.TextInput(label="Título", default=st.get("titulo") or "", required=False, max_length=256)
        self.autor = discord.ui.TextInput(label="Autor", default=st.get("autor") or "", required=False, max_length=100)
        self.color = discord.ui.TextInput(label="Color (hex, ej: 5865F2)", default=st["color"], min_length=6, max_length=7)
        self.footer = discord.ui.TextInput(label="Pie de página", default=st.get("footer") or "", required=False, max_length=100)
        for i in (self.titulo, self.autor, self.color, self.footer):
            self.add_item(i)

    async def on_submit(self, interaction: discord.Interaction):
        hexa = self.color.value.lstrip("#")
        try:
            if len(hexa) != 6:
                raise ValueError
            int(hexa, 16)
        except ValueError:
            return await interaction.response.send_message("❌ Color inválido. Usa 6 dígitos hex.", ephemeral=True)
        st = cfg(interaction.guild.id)["post"]["embeds"][self.key]
        st["titulo"] = self.titulo.value or None
        st["autor"] = self.autor.value or None
        st["color"] = hexa
        st["footer"] = self.footer.value or None
        save()
        await interaction.response.edit_message(
            embeds=post_embed_panel(interaction.guild, interaction.user.id, self.key), view=PostEmbedEditView(self.key)
        )


class PostDescModal(discord.ui.Modal, title="Descripción"):
    def __init__(self, key: str, gid: int):
        super().__init__()
        self.key = key
        st = cfg(gid)["post"]["embeds"][key]
        self.desc = discord.ui.TextInput(
            label="Descripción (puedes usar variables)", style=discord.TextStyle.paragraph,
            default=st.get("descripcion") or "", required=False, max_length=2000,
        )
        self.add_item(self.desc)

    async def on_submit(self, interaction: discord.Interaction):
        cfg(interaction.guild.id)["post"]["embeds"][self.key]["descripcion"] = self.desc.value or None
        save()
        await interaction.response.edit_message(
            embeds=post_embed_panel(interaction.guild, interaction.user.id, self.key), view=PostEmbedEditView(self.key)
        )


class PostImgModal(discord.ui.Modal, title="Imágenes"):
    def __init__(self, key: str, gid: int):
        super().__init__()
        self.key = key
        st = cfg(gid)["post"]["embeds"][key]
        self.mini = discord.ui.TextInput(label="URL de la imagen chica (miniatura)", default=st.get("miniatura") or "", required=False)
        self.img = discord.ui.TextInput(label="URL de la imagen grande", default=st.get("imagen") or "", required=False)
        self.add_item(self.mini)
        self.add_item(self.img)

    async def on_submit(self, interaction: discord.Interaction):
        for url in (self.mini.value, self.img.value):
            if url and not url.startswith(("http://", "https://")):
                return await interaction.response.send_message("❌ Las URLs deben empezar con http:// o https://", ephemeral=True)
        st = cfg(interaction.guild.id)["post"]["embeds"][self.key]
        st["miniatura"] = self.mini.value or None
        st["imagen"] = self.img.value or None
        save()
        await interaction.response.edit_message(
            embeds=post_embed_panel(interaction.guild, interaction.user.id, self.key), view=PostEmbedEditView(self.key)
        )


class PostEmbedEditView(AdminView):
    def __init__(self, key: str):
        super().__init__()
        self.key = key

    @discord.ui.button(label="✏️ Título, autor y color", style=discord.ButtonStyle.primary, row=0)
    async def texto(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PostTextoModal(self.key, interaction.guild.id))

    @discord.ui.button(label="📄 Descripción", style=discord.ButtonStyle.primary, row=0)
    async def descripcion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PostDescModal(self.key, interaction.guild.id))

    @discord.ui.button(label="🖼️ Imágenes", style=discord.ButtonStyle.primary, row=0)
    async def imagenes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PostImgModal(self.key, interaction.guild.id))

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=post_embeds_menu_embed(), view=PostEmbedsMenuView())


class PostEmbedsMenuView(AdminView):
    @discord.ui.select(
        placeholder="¿Qué embed quieres editar?",
        options=[discord.SelectOption(label=v, value=k) for k, v in POST_EMBED_NOMBRES.items()],
        row=0,
    )
    async def elegir(self, interaction: discord.Interaction, select: discord.ui.Select):
        key = select.values[0]
        await interaction.response.edit_message(
            embeds=post_embed_panel(interaction.guild, interaction.user.id, key), view=PostEmbedEditView(key)
        )

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=post_home_embed(interaction.guild.id), view=PostHomeView())


class PostHomeView(AdminView):
    @discord.ui.button(label="📋 Formularios", style=discord.ButtonStyle.primary, row=0)
    async def formularios(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=post_forms_embed(interaction.guild.id), view=PostFormsView(interaction.guild.id))

    @discord.ui.button(label="🎨 Embeds", style=discord.ButtonStyle.primary, row=0)
    async def embeds(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=post_embeds_menu_embed(), view=PostEmbedsMenuView())

    @discord.ui.button(label="⚙️ Roles y canal", style=discord.ButtonStyle.primary, row=0)
    async def roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=post_home_embed(interaction.guild.id), view=PostRolesView())

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=home_embed(), view=HomeView())


MOD_EMBED_NOMBRES = {"dm": "MD al usuario sancionado", "registro": "Registro de casos (canal)"}


def mod_home_embed(gid: int):
    m = cfg(gid)["mod"]
    e = discord.Embed(title="🔨 Configurar moderación", color=0x5865F2)
    e.add_field(name="Canal de registros", value=f"<#{m['canal']}>" if m["canal"] else "No configurado", inline=False)
    e.add_field(name="Roles que pueden sancionar",
                value=" ".join(f"<@&{r}>" for r in m["roles"]) or "Solo administradores", inline=False)
    e.add_field(name="Casos registrados", value=str(m["contador"]), inline=False)
    return e


def mod_embeds_menu_embed():
    return discord.Embed(
        title="🎨 Embeds de moderación",
        description="Elige cuál quieres editar:\n\n" + "\n".join(f"• **{v}**" for v in MOD_EMBED_NOMBRES.values()),
        color=0x5865F2,
    )


def mod_embed_panel(guild, user_id: int, key: str):
    m = cfg(guild.id)["mod"]
    info = discord.Embed(
        title=f"🎨 Editando: {MOD_EMBED_NOMBRES[key]}",
        description="Variables: " + ", ".join(f"`{k}`" for k in MOD_VARIABLES) + "\n\nAbajo ves la vista previa en vivo.",
        color=0x5865F2,
    )
    caso = {"n": 1, "tipo": "Ban", "usuario": user_id, "staff": user_id, "razon": "Razón de ejemplo",
            "duracion": None, "ts": int(discord.utils.utcnow().timestamp())}
    return [info, post_embed(m["embeds"][key], mod_vars(guild, caso))]


# ── Editor de estilo genérico (título, autor, color, descripción, imágenes) ──
class StyleTextoModal(discord.ui.Modal, title="Título, autor y color"):
    def __init__(self, parent, gid: int):
        super().__init__()
        self.parent = parent
        st = cfg(gid)[parent.seccion]["embeds"][parent.key]
        self.titulo = discord.ui.TextInput(label="Título", default=st.get("titulo") or "", required=False, max_length=256)
        self.autor = discord.ui.TextInput(label="Autor", default=st.get("autor") or "", required=False, max_length=100)
        self.color = discord.ui.TextInput(label="Color (hex, ej: 5865F2)", default=st["color"], min_length=6, max_length=7)
        self.footer = discord.ui.TextInput(label="Pie de página", default=st.get("footer") or "", required=False, max_length=100)
        for i in (self.titulo, self.autor, self.color, self.footer):
            self.add_item(i)

    async def on_submit(self, interaction: discord.Interaction):
        hexa = self.color.value.lstrip("#")
        try:
            if len(hexa) != 6:
                raise ValueError
            int(hexa, 16)
        except ValueError:
            return await interaction.response.send_message("❌ Color inválido. Usa 6 dígitos hex.", ephemeral=True)
        st = cfg(interaction.guild.id)[self.parent.seccion]["embeds"][self.parent.key]
        st["titulo"] = self.titulo.value or None
        st["autor"] = self.autor.value or None
        st["color"] = hexa
        st["footer"] = self.footer.value or None
        save()
        await interaction.response.edit_message(**self.parent.refrescar(interaction))


class StyleDescModal(discord.ui.Modal, title="Descripción"):
    def __init__(self, parent, gid: int):
        super().__init__()
        self.parent = parent
        st = cfg(gid)[parent.seccion]["embeds"][parent.key]
        self.desc = discord.ui.TextInput(
            label="Descripción (puedes usar variables)", style=discord.TextStyle.paragraph,
            default=st.get("descripcion") or "", required=False, max_length=2000,
        )
        self.add_item(self.desc)

    async def on_submit(self, interaction: discord.Interaction):
        cfg(interaction.guild.id)[self.parent.seccion]["embeds"][self.parent.key]["descripcion"] = self.desc.value or None
        save()
        await interaction.response.edit_message(**self.parent.refrescar(interaction))


class StyleImgModal(discord.ui.Modal, title="Imágenes"):
    def __init__(self, parent, gid: int):
        super().__init__()
        self.parent = parent
        st = cfg(gid)[parent.seccion]["embeds"][parent.key]
        self.mini = discord.ui.TextInput(label="URL de la imagen chica (miniatura)", default=st.get("miniatura") or "", required=False)
        self.img = discord.ui.TextInput(label="URL de la imagen grande", default=st.get("imagen") or "", required=False)
        self.add_item(self.mini)
        self.add_item(self.img)

    async def on_submit(self, interaction: discord.Interaction):
        for url in (self.mini.value, self.img.value):
            if url and not url.startswith(("http://", "https://")):
                return await interaction.response.send_message("❌ Las URLs deben empezar con http:// o https://", ephemeral=True)
        st = cfg(interaction.guild.id)[self.parent.seccion]["embeds"][self.parent.key]
        st["miniatura"] = self.mini.value or None
        st["imagen"] = self.img.value or None
        save()
        await interaction.response.edit_message(**self.parent.refrescar(interaction))


class StyleEditView(AdminView):
    def __init__(self, seccion, key, preview, volver):
        super().__init__()
        self.seccion, self.key, self.preview, self.volver_fn = seccion, key, preview, volver

    def refrescar(self, interaction):
        return {"embeds": self.preview(interaction.guild, interaction.user.id, self.key), "view": self}

    @discord.ui.button(label="✏️ Título, autor y color", style=discord.ButtonStyle.primary, row=0)
    async def texto(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StyleTextoModal(self, interaction.guild.id))

    @discord.ui.button(label="📄 Descripción", style=discord.ButtonStyle.primary, row=0)
    async def descripcion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StyleDescModal(self, interaction.guild.id))

    @discord.ui.button(label="🖼️ Imágenes", style=discord.ButtonStyle.primary, row=0)
    async def imagenes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StyleImgModal(self, interaction.guild.id))

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.volver_fn(interaction)


async def volver_mod_menu(interaction: discord.Interaction):
    await interaction.response.edit_message(embed=mod_embeds_menu_embed(), view=ModEmbedsMenuView())


class ModEmbedsMenuView(AdminView):
    @discord.ui.select(
        placeholder="¿Qué embed quieres editar?",
        options=[discord.SelectOption(label=v, value=k) for k, v in MOD_EMBED_NOMBRES.items()],
        row=0,
    )
    async def elegir(self, interaction: discord.Interaction, select: discord.ui.Select):
        key = select.values[0]
        view = StyleEditView("mod", key, mod_embed_panel, volver_mod_menu)
        await interaction.response.edit_message(embeds=mod_embed_panel(interaction.guild, interaction.user.id, key), view=view)

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=mod_home_embed(interaction.guild.id), view=ModHomeView())


class ModHomeView(AdminView):
    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                       placeholder="Canal de registros de sanciones", row=0)
    async def canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        cfg(interaction.guild.id)["mod"]["canal"] = select.values[0].id
        save()
        await interaction.response.edit_message(embed=mod_home_embed(interaction.guild.id), view=ModHomeView())

    @discord.ui.select(cls=discord.ui.RoleSelect, min_values=0, max_values=10,
                       placeholder="Roles que pueden sancionar", row=1)
    async def roles(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        cfg(interaction.guild.id)["mod"]["roles"] = [r.id for r in select.values]
        save()
        await interaction.response.edit_message(embed=mod_home_embed(interaction.guild.id), view=ModHomeView())

    @discord.ui.button(label="🎨 Embeds", style=discord.ButtonStyle.primary, row=2)
    async def embeds(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=mod_embeds_menu_embed(), view=ModEmbedsMenuView())

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
    embed.add_field(
        name="📝 Postulaciones",
        value="`/postulacion` envía un formulario a un candidato (solo él puede iniciarlo, por MD)\n"
        "El staff aprueba/rechaza con nota y el candidato recibe el resultado por MD\n"
        "`/variables` muestra las variables para los embeds · Todo se configura en `/configuracion → Postulaciones`",
        inline=False,
    )
    embed.add_field(
        name="🔨 Moderación",
        value="`/ban` `/kick` `/warn` `/mute` (piden foto de prueba) · `/nota` (interna)\n"
        "`/unban` `/unwarn` `/unmute` para quitar sanciones · `/historial` y `/caso` para consultar\n"
        "Cada acción es un caso numerado y el usuario recibe un MD. Se configura en `/configuracion → Moderación`.",
        inline=False,
    )
    embed.add_field(
        name="🔎 Estado de postulaciones",
        value="`/postulacion-estado formulario número` (solo staff)",
        inline=False,
    )
    embed.add_field(name="🚧 Próximamente", value="Seguridad (Anti-Bot/Raid/Spam) y adivina la palabra.", inline=False)
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