import os
import json
import asyncio
import io
import re
import time
import unicodedata
import inspect
import typing
import traceback
from collections import deque
import random
from typing import Optional
from datetime import timedelta
import discord
from discord import app_commands
from datos import TRIVIA, IMAGENES  # preguntas e imágenes de /trivia

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
    g.setdefault("juegos", {"embeds": default_juegos_embeds()})
    for _k, _v in default_juegos_embeds().items():
        g["juegos"]["embeds"].setdefault(_k, _v)
    g.setdefault("sort", {"roles": [], "items": {}, "embeds": default_sort_embeds()})
    g.setdefault("tk", {
        "categoria": None, "canal": None, "roles": [], "max": 1, "contador": 0,
        "cats": [{"nombre": "Soporte", "desc": "Ayuda general"}], "abiertos": {},
        "embeds": default_tk_embeds(), "valoraciones": {}, "rating_pending": {}, "canal_valoraciones": None,
    })
    g["tk"].setdefault("valoraciones", {})
    g["tk"].setdefault("rating_pending", {})
    g["tk"].setdefault("canal_valoraciones", None)
    for _k, _v in default_tk_embeds().items():
        g["tk"]["embeds"].setdefault(_k, _v)
    g.setdefault("autoroles", {"on": False, "miembros": [], "bots": []})
    g.setdefault("reaccion_roles", {"on": False, "mensajes": {}})
    g.setdefault("autopings", {"on": False, "items": {}})
    g.setdefault("auto", {
        "on": False, "canal": None, "trigger": "solicitar alianza",
        "respuesta": {"titulo": "🤝 Solicitar alianza", "descripcion": "Para solicitar una alianza, completa el formulario correspondiente.",
                      "color": "5865F2", "autor": None, "miniatura": None, "imagen": None, "footer": None},
        "borrar_trigger": False,
    })

    g.setdefault("seg", {
        "canal": None,
        "antibot": {"on": False},
        "antiraid": {"on": False, "joins": 5, "segundos": 10, "accion": "kick"},
        "antispam": {"on": False, "mensajes": 5, "segundos": 5, "timeout": 10, "menciones": 6},
        "antichannel": {"on": False},
        "antiroles": {"on": False},
        "staff_guard": {"on": False, "roles": [], "warnings_before_kick": 2, "accion": "kick",
                        "pending": {}, "warnings": {}},
        "wl": {"usuarios": [], "roles": []},
    })
    g["seg"].setdefault("antichannel", {"on": False})
    g["seg"].setdefault("antiroles", {"on": False})
    g["seg"].setdefault("staff_guard", {"on": False, "roles": [], "warnings_before_kick": 2, "accion": "kick",
                                        "pending": {}, "warnings": {}})

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
    g.setdefault("prefijo", "!")  # prefijo para usar los comandos con texto (!comando)
    for _cat in g["tk"].get("cats", []):
        _cat.setdefault("roles", [])
        _cat.setdefault("ping", [])
        _cat.setdefault("nombre_canal", "ticket-{numero}")
    g["tk"].setdefault("panel_roles", [])  # roles que pueden usar /ticket-panel
    g["tk"].setdefault("placeholder", "🎫 Elige una categoría para abrir un ticket")  # texto del menú del panel
    g.setdefault("afk", {})  # usuarios AFK: {id: {razon, desde, nick, cambiado}}
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
        self.add_view(SorteoView())
        self.add_view(TicketPanelView())
        self.add_view(TicketControlView())
        self.add_view(RatingView())
        self.add_view(StaffApprovalView())
        # Restaurar botones persistentes de mensajes automáticos tras reiniciar.
        for _gid, _gdata in data.items():
            for _key, _item in _gdata.get("autopings", {}).get("items", {}).items():
                try:
                    self.add_view(AutoPingMessageView(_key))
                except Exception:
                    pass
        asyncio.create_task(bucle_sorteos())
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
    embed = estilo_juego(interaction.guild_id, "dado", embed, {"{caras}": str(caras)})
    await interaction.response.send_message(embed=embed)


# ─────────────────────────────── /ppt ────────────────────────────────────────
OPC = {"piedra": "🪨 Piedra", "papel": "📄 Papel", "tijera": "✂️ Tijera"}
GANA = {"piedra": "tijera", "papel": "piedra", "tijera": "papel"}


class PPTView(discord.ui.View):
    def __init__(self, a: discord.User, b: discord.User, gid=None):
        super().__init__(timeout=60)
        self.gid = gid
        self.players = [a.id, b.id]
        self.picks = {}
        self.message = None

    def estado(self):
        lineas = [
            f"<@{p}> — {'✅ ya eligió' if p in self.picks else '⏳ eligiendo...'}"
            for p in self.players
        ]
        return estilo_juego(self.gid, "ppt", discord.Embed(
            title="🪨📄✂️ Piedra, Papel o Tijera",
            description="\n".join(lineas) + "\n\nLas elecciones son secretas hasta que ambos elijan.",
            color=0x3498DB,
        ))

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
        embed = estilo_juego(self.gid, "ppt", embed, titulo=False)
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
    view = PPTView(interaction.user, oponente, interaction.guild_id)
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


# ──────────────────────────────── Seguridad ──────────────────────────────────
JOINS = {}        # guild_id -> deque[(timestamp, member)]
RAID_HASTA = {}   # guild_id -> timestamp hasta el que dura el "modo raid"
SPAM = {}         # (guild_id, user_id) -> deque[(timestamp, message)]


def en_whitelist(member, s) -> bool:
    wl = s["wl"]
    return (
        member.id == member.guild.owner_id
        or member.id in wl["usuarios"]
        or any(r.id in wl["roles"] for r in getattr(member, "roles", []))
    )


async def log_seg(guild, s, titulo, descripcion, color=0xE74C3C):
    canal = guild.get_channel(s["canal"]) if s["canal"] else None
    emb = discord.Embed(title=titulo, description=descripcion, color=color, timestamp=discord.utils.utcnow())
    if canal:
        try:
            await canal.send(embed=emb)
        except discord.HTTPException:
            pass
    # Seguridad: cada activación/detección también avisa al dueño por MD.
    try:
        owner = await client.fetch_user(guild.owner_id)
        await owner.send(embed=emb)
    except discord.HTTPException:
        pass


async def manejar_bot(bot: discord.Member, s):
    """Anti-Bot: banea al bot (esté online u offline) y a quien lo agregó."""
    g = bot.guild
    if bot.id in s["wl"]["usuarios"]:
        await log_seg(g, s, "🤖 Bot permitido", f"{bot.mention} está en la White-List.", 0x2ECC71)
        return

    adder = None
    if g.me.guild_permissions.view_audit_log:
        for _ in range(3):  # el registro de auditoría tarda un poco en actualizarse
            await asyncio.sleep(1.5)
            try:
                async for entry in g.audit_logs(limit=10, action=discord.AuditLogAction.bot_add):
                    reciente = (discord.utils.utcnow() - entry.created_at).total_seconds() < 120
                    if entry.target and entry.target.id == bot.id and reciente:
                        adder = entry.user
                        break
            except discord.HTTPException:
                break
            if adder:
                break

    adder_m = g.get_member(adder.id) if adder else None
    if adder and (adder.id == g.owner_id or (adder_m and en_whitelist(adder_m, s))):
        await log_seg(g, s, "🤖 Bot permitido", f"{bot.mention} fue agregado por {adder.mention} (dueño/White-List).", 0x2ECC71)
        return

    res = []
    try:
        await g.ban(bot, reason="[Nexus Anti-Bot] Bot no autorizado", delete_message_seconds=0)
        res.append(f"🔨 Bot **{bot}** baneado")
    except discord.HTTPException as e:
        res.append(f"❌ No pude banear al bot: {e.text or e}")

    if adder is None:
        res.append("⚠️ No pude identificar quién lo agregó (revisa que tenga el permiso *Ver registro de auditoría*).")
    elif adder.bot:
        res.append(f"ℹ️ Lo agregó otro bot ({adder.mention}); no se banea.")
    else:
        try:
            await g.ban(adder, reason=f"[Nexus Anti-Bot] Agregó un bot no autorizado ({bot})", delete_message_seconds=0)
            res.append(f"🔨 {adder.mention} baneado por agregar el bot")
        except discord.HTTPException as e:
            res.append(f"❌ No pude banear a {adder.mention}: {e.text or e}")
    await log_seg(g, s, "🚫 Anti-Bot: bot no autorizado", "\n".join(res))


async def aplicar_raid(member: discord.Member, accion: str):
    try:
        if accion == "ban":
            await member.guild.ban(member, reason="[Nexus Anti-Raid]", delete_message_seconds=0)
        else:
            await member.kick(reason="[Nexus Anti-Raid]")
        return True
    except discord.HTTPException:
        return False


async def manejar_raid(member: discord.Member, s):
    g = member.guild
    r = s["antiraid"]
    ahora = time.time()
    dq = JOINS.setdefault(g.id, deque())
    dq.append((ahora, member))
    while dq and ahora - dq[0][0] > r["segundos"]:
        dq.popleft()

    if ahora < RAID_HASTA.get(g.id, 0):  # ya estamos en modo raid
        await aplicar_raid(member, r["accion"])
        return
    if len(dq) < r["joins"]:
        return

    RAID_HASTA[g.id] = ahora + 120
    objetivos = [m for _, m in dq]
    dq.clear()
    ok = 0
    for m in objetivos:
        if await aplicar_raid(m, r["accion"]):
            ok += 1
    verbo = "baneadas" if r["accion"] == "ban" else "expulsadas"
    await log_seg(
        g, s, "🚨 Anti-Raid: raid detectado",
        f"Entraron **{len(objetivos)}** cuentas en menos de {r['segundos']} s.\n"
        f"**{ok}** cuentas {verbo}. Modo raid activo durante 2 minutos: cada nueva entrada recibirá la misma acción.",
    )


async def antispam(m: discord.Message) -> bool:
    """Devuelve True si el mensaje fue tratado como spam (y ya no hay que procesarlo más)."""
    g = m.guild
    s = cfg(g.id)["seg"]
    a = s["antispam"]
    if not a["on"] or not isinstance(m.author, discord.Member):
        return False
    u = m.author
    if u.guild_permissions.administrator or en_whitelist(u, s) or puede_moderar(u) or m.channel.id in JUEGOS_ADIVINA:
        return False

    ahora = time.time()
    if len(SPAM) > 5000:
        SPAM.clear()
    dq = SPAM.setdefault((g.id, u.id), deque())
    dq.append((ahora, m))
    while dq and ahora - dq[0][0] > a["segundos"]:
        dq.popleft()

    menciones = len(m.mentions) + len(m.role_mentions)
    flood = len(dq) >= a["mensajes"]
    if not flood and menciones < a["menciones"]:
        return False

    msgs = [x for _, x in dq] if flood else [m]
    dq.clear()
    for x in msgs:
        try:
            await x.delete()
        except discord.HTTPException:
            pass

    estado = "sin aislamiento (no tengo permisos o su rol es superior al mío)"
    if g.me.guild_permissions.moderate_members and u.id != g.owner_id and u.top_role < g.me.top_role:
        try:
            await u.timeout(timedelta(minutes=a["timeout"]), reason="[Nexus Anti-Spam]")
            estado = f"aislado {a['timeout']} min"
        except discord.HTTPException:
            pass
    motivo = "flood de mensajes" if flood else "menciones masivas"
    try:
        await m.channel.send(f"🚫 {u.mention}, detecté **{motivo}**. Tus mensajes fueron eliminados.", delete_after=8)
    except discord.HTTPException:
        pass
    await log_seg(g, s, "💬 Anti-Spam", f"**Usuario:** {u.mention}\n**Motivo:** {motivo}\n"
                  f"**Mensajes borrados:** {len(msgs)}\n**Canal:** {m.channel.mention}\n**Acción:** {estado}", 0xE67E22)
    return True



# ─────────────────────── Seguridad avanzada: canales, roles y staff ─────────────

DANGEROUS_ROLE_PERMS = (
    "administrator", "manage_guild", "manage_roles", "manage_channels",
    "manage_permissions", "ban_members", "kick_members", "manage_webhooks"
)

async def obtener_ejecutor(guild, action, target_id):
    if not guild.me.guild_permissions.view_audit_log:
        return None
    try:
        async for entry in guild.audit_logs(limit=8, action=action):
            if entry.target and entry.target.id == target_id:
                if (discord.utils.utcnow() - entry.created_at).total_seconds() <= 15:
                    return entry.user
    except (discord.Forbidden, discord.HTTPException):
        pass
    return None


def actor_exento(guild, member):
    if not member:
        return False
    if member.id == guild.owner_id or member.id == client.user.id:
        return True
    s = cfg(guild.id)["seg"]
    return en_whitelist(member, s)


async def avisar_dueno(guild, titulo, descripcion, color=0xE74C3C):
    try:
        owner = await client.fetch_user(guild.owner_id)
        await owner.send(embed=discord.Embed(title=titulo, description=descripcion, color=color))
    except discord.HTTPException:
        pass


async def manejar_staff_role_change(before, after):
    guild = after.guild
    s = cfg(guild.id)["seg"]
    guard = s["staff_guard"]
    if not guard.get("on") or not guard.get("roles"):
        return

    old = {r.id for r in before.roles}
    added = [r for r in after.roles if r.id not in old and r.id in guard["roles"]]
    if not added:
        return

    actor = await obtener_ejecutor(guild, discord.AuditLogAction.member_role_update, after.id)
    if actor_exento(guild, actor):
        return

    for role in added:
        # Si Nexus acaba de poner el rol después de una aprobación, se permite.
        pair = f"{after.id}:{role.id}"
        approved = guard.setdefault("approved_pairs", [])
        if pair in approved:
            approved.remove(pair)
            save()
            continue

        try:
            await after.remove_roles(role, reason="[Nexus Protección Staff] Requiere aprobación del dueño")
        except discord.HTTPException:
            pass

        staff_id = actor.id if actor else 0
        warnings = guard.setdefault("warnings", {})
        key = str(staff_id)
        warnings[key] = int(warnings.get(key, 0)) + 1
        count = warnings[key]
        limite = int(guard.get("warnings_before_kick", 2))
        pendiente = any(
            p.get("staff") == staff_id and p.get("target") == after.id and p.get("role") == role.id
            for p in guard.setdefault("pending", {}).values()
        )

        if count > limite:
            accion = guard.get("accion", "kick")
            resultado = "no se pudo ejecutar"
            if actor and actor.id != guild.owner_id and actor.id != client.user.id:
                try:
                    if accion == "ban":
                        await guild.ban(actor, reason="[Nexus Protección Staff] Excedió advertencias")
                    else:
                        await actor.kick(reason="[Nexus Protección Staff] Excedió advertencias")
                    resultado = accion.upper()
                except discord.HTTPException:
                    pass
            await avisar_dueno(
                guild, "🚨 Protección Staff — sanción ejecutada",
                f"**Staff:** {actor.mention if actor else f'<@{staff_id}>'}\n"
                f"**Intento:** dar {role.mention} a {after.mention}\n"
                f"**Advertencias:** {count}\n**Sanción:** {resultado}",
            )
            continue

        if pendiente:
            msg = (
                f"⚠️ **Advertencia de Protección Staff**\n\n"
                f"{actor.mention if actor else f'<@{staff_id}>'} volvió a intentar dar "
                f"{role.mention} a {after.mention} mientras la solicitud seguía pendiente.\n\n"
                f"Advertencias: **{count}/{limite}**. Si supera el límite, se aplicará **{guard.get('accion','kick').upper()}**."
            )
            await avisar_dueno(guild, "⚠️ Intento repetido de asignar Staff", msg)
            if actor:
                try:
                    await actor.send(msg)
                except discord.HTTPException:
                    pass
            continue

        owner = await client.fetch_user(guild.owner_id)
        embed = discord.Embed(
            title="🔐 Solicitud de permiso para dar un rol de Staff",
            description=(
                f"¡Hola! El staff {actor.mention if actor else f'<@{staff_id}>'} solicita permiso para darle "
                f"el rol de staff {role.mention} al usuario {after.mention}.\n\n"
                f"**Advertencias del staff:** {count}/{limite}"
            ),
            color=0xF1C40F,
        )
        embed.set_footer(text=f"Servidor: {guild.name} · Rol protegido: {role.id}")
        try:
            dm = await owner.send(embed=embed, view=StaffApprovalView())
            guard["pending"][str(dm.id)] = {
                "staff": staff_id, "target": after.id, "role": role.id, "created": int(time.time())
            }
            save()
        except discord.HTTPException:
            pass


@client.event
async def on_member_update(before: discord.Member, after: discord.Member):
    try:
        await manejar_staff_role_change(before, after)
    except Exception:
        traceback.print_exc()


@client.event
async def on_guild_channel_create(channel):
    guild = channel.guild
    s = cfg(guild.id)["seg"]
    if not s["antichannel"]["on"]:
        return
    actor = await obtener_ejecutor(guild, discord.AuditLogAction.channel_create, channel.id)
    if actor_exento(guild, actor):
        return
    try:
        await channel.delete(reason="[Nexus Anti-Channel] Creación no autorizada")
    except discord.HTTPException:
        pass
    await log_seg(guild, s, "📁 Anti-Channel: canal eliminado",
                  f"**Canal:** #{channel.name}\n**Autor:** {actor.mention if actor else 'desconocido'}")
    await avisar_dueno(guild, "📁 Anti-Channel activado",
                       f"Se eliminó el canal **#{channel.name}** creado sin autorización por "
                       f"{actor.mention if actor else 'un usuario desconocido'}.")


@client.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    s = cfg(guild.id)["seg"]
    if not s["antichannel"]["on"]:
        return
    actor = await obtener_ejecutor(guild, discord.AuditLogAction.channel_delete, channel.id)
    if actor_exento(guild, actor):
        return
    await log_seg(guild, s, "📁 Anti-Channel: eliminación no autorizada",
                  f"**Canal eliminado:** #{channel.name}\n**Autor:** {actor.mention if actor else 'desconocido'}")
    await avisar_dueno(guild, "🚨 Anti-Channel — canal eliminado",
                       f"Se detectó la eliminación no autorizada de **#{channel.name}** por "
                       f"{actor.mention if actor else 'un usuario desconocido'}. Discord no permite restaurar automáticamente un canal borrado.")


@client.event
async def on_guild_channel_update(before, after):
    guild = after.guild
    s = cfg(guild.id)["seg"]
    if not s["antichannel"]["on"] or before.overwrites == after.overwrites and before.name == after.name and before.category_id == after.category_id:
        return
    actor = await obtener_ejecutor(guild, discord.AuditLogAction.channel_update, after.id)
    if actor_exento(guild, actor):
        return
    try:
        await after.edit(
            name=before.name, category=before.category,
            overwrites=before.overwrites, reason="[Nexus Anti-Channel] Revirtiendo cambio no autorizado"
        )
    except discord.HTTPException:
        pass
    await log_seg(guild, s, "📁 Anti-Channel: cambio revertido",
                  f"**Canal:** #{after.name}\n**Autor:** {actor.mention if actor else 'desconocido'}")


@client.event
async def on_guild_role_create(role):
    guild = role.guild
    s = cfg(guild.id)["seg"]
    if not s["antiroles"]["on"] or role.managed:
        return
    actor = await obtener_ejecutor(guild, discord.AuditLogAction.role_create, role.id)
    if actor_exento(guild, actor):
        return
    try:
        await role.delete(reason="[Nexus Anti-Roles] Rol no autorizado")
    except discord.HTTPException:
        pass
    await log_seg(guild, s, "🎭 Anti-Roles: rol eliminado",
                  f"**Rol:** @{role.name}\n**Autor:** {actor.mention if actor else 'desconocido'}")
    await avisar_dueno(guild, "🎭 Anti-Roles activado",
                       f"Se eliminó el rol **@{role.name}** creado sin autorización.")


@client.event
async def on_guild_role_delete(role):
    guild = role.guild
    s = cfg(guild.id)["seg"]
    if not s["antiroles"]["on"] or role.managed:
        return
    actor = await obtener_ejecutor(guild, discord.AuditLogAction.role_delete, role.id)
    if actor_exento(guild, actor):
        return
    await log_seg(guild, s, "🚨 Anti-Roles — rol eliminado",
                  f"**Rol:** @{role.name}\n**Autor:** {actor.mention if actor else 'desconocido'}")
    await avisar_dueno(guild, "🚨 Anti-Roles — rol eliminado",
                       f"Se detectó la eliminación no autorizada del rol **@{role.name}**. Discord no permite restaurar automáticamente un rol borrado.")


@client.event
async def on_guild_role_update(before, after):
    guild = after.guild
    s = cfg(guild.id)["seg"]
    if not s["antiroles"]["on"] or after.managed:
        return
    dangerous = any(getattr(after.permissions, p, False) for p in DANGEROUS_ROLE_PERMS)
    changed = before.name != after.name or before.permissions != after.permissions or before.position != after.position
    if not changed:
        return
    actor = await obtener_ejecutor(guild, discord.AuditLogAction.role_update, after.id)
    if actor_exento(guild, actor):
        return

    # Quita inmediatamente cualquier permiso peligroso del rol no autorizado.
    perms = after.permissions
    for p in DANGEROUS_ROLE_PERMS:
        setattr(perms, p, False)
    try:
        await after.edit(permissions=perms, reason="[Nexus Anti-Roles] Permisos peligrosos bloqueados")
    except discord.HTTPException:
        pass
    await log_seg(guild, s, "🎭 Anti-Roles: permisos bloqueados",
                  f"**Rol:** @{after.name}\n**Autor:** {actor.mention if actor else 'desconocido'}\n"
                  f"**Permisos peligrosos detectados:** {'sí' if dangerous else 'cambio de rol no autorizado'}")
    await avisar_dueno(guild, "🎭 Anti-Roles activado",
                       f"Se bloquearon permisos peligrosos/cambios no autorizados en **@{after.name}**.")


@client.event
async def on_member_join(member: discord.Member):
    s = cfg(member.guild.id)["seg"]
    if member.bot:
        if s["antibot"]["on"]:
            await manejar_bot(member, s)
        return
    if s["antiraid"]["on"] and not en_whitelist(member, s):
        await manejar_raid(member, s)


# ───────────────────────────── Tres en raya ──────────────────────────────────
LINEAS_3R = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


class CasillaBtn(discord.ui.Button):
    def __init__(self, i: int):
        super().__init__(label="\u200b", style=discord.ButtonStyle.secondary, row=i // 3)
        self.i = i

    async def callback(self, interaction: discord.Interaction):
        await self.view.jugar(interaction, self)


class TresRayaView(discord.ui.View):
    def __init__(self, a: discord.abc.User, b: discord.abc.User, gid=None):
        super().__init__(timeout=120)
        self.gid = gid
        self.jugadores = [a.id, b.id]  # el primero es ❌, el segundo ⭕
        self.turno = 0
        self.tablero = [None] * 9
        self.message = None
        for i in range(9):
            self.add_item(CasillaBtn(i))

    def embed(self, final: str = None):
        a, b = self.jugadores
        desc = f"❌ <@{a}>   vs   ⭕ <@{b}>\n\n"
        desc += final or f"Turno de <@{self.jugadores[self.turno]}> {'❌' if self.turno == 0 else '⭕'}"
        return estilo_juego(self.gid, "tres_raya", discord.Embed(title="❌⭕ Tres en raya", description=desc, color=0x9B59B6 if not final else 0x2ECC71))

    async def jugar(self, interaction: discord.Interaction, boton: CasillaBtn):
        if interaction.user.id not in self.jugadores:
            return await interaction.response.send_message("No participas en esta partida.", ephemeral=True)
        if interaction.user.id != self.jugadores[self.turno]:
            return await interaction.response.send_message("⏳ Aún no es tu turno.", ephemeral=True)

        marca = "X" if self.turno == 0 else "O"
        self.tablero[boton.i] = marca
        boton.emoji = "❌" if marca == "X" else "⭕"
        boton.label = None
        boton.style = discord.ButtonStyle.danger if marca == "X" else discord.ButtonStyle.primary
        boton.disabled = True

        ganador = any(all(self.tablero[x] == marca for x in l) for l in LINEAS_3R)
        if ganador or all(self.tablero):
            for c in self.children:
                c.disabled = True
            self.stop()
            final = f"🏆 **¡Gana <@{interaction.user.id}>!**" if ganador else "🤝 **¡Empate!**"
            return await interaction.response.edit_message(content=None, embed=self.embed(final), view=self)

        self.turno = 1 - self.turno
        await interaction.response.edit_message(content=None, embed=self.embed(), view=self)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(embed=self.embed("⌛ Partida cancelada por inactividad."), view=self)
            except discord.HTTPException:
                pass


@tree.command(name="tres-en-raya", description="Juega al tres en raya contra otra persona")
@app_commands.describe(oponente="Con quién quieres jugar")
@app_commands.guild_only()
async def tres_en_raya(interaction: discord.Interaction, oponente: discord.Member):
    if oponente.bot or oponente.id == interaction.user.id:
        return await interaction.response.send_message("Elige a otra persona (ni un bot ni tú mismo).", ephemeral=True)
    view = TresRayaView(interaction.user, oponente, interaction.guild_id)
    await interaction.response.send_message(
        content=f"{oponente.mention}, {interaction.user.mention} te retó a un tres en raya.",
        embed=view.embed(), view=view,
    )
    view.message = await interaction.original_response()


# ─────────────────────────── Estilo de embeds de juegos ──────────────────────
def default_juegos_embeds():
    base = {"autor": None, "descripcion": None, "miniatura": None, "imagen": None, "footer": None}
    return {
        "ppt": {**base, "titulo": "🪨📄✂️ Piedra, Papel o Tijera", "color": "3498DB"},
        "dado": {**base, "titulo": "🎲 Dado de {caras} caras", "color": "E67E22"},
        "tres_raya": {**base, "titulo": "❌⭕ Tres en raya", "color": "9B59B6"},
        "adivina": {**base, "titulo": "🔤 Adivina la palabra — {tema}", "color": "9B59B6"},
        "numero": {**base, "titulo": "🔢 Adivina el número", "color": "1ABC9C"},
        "desordenada": {**base, "titulo": "🔀 Palabra desordenada — {tema}", "color": "E91E63"},
        "reflejos": {**base, "titulo": "⚡ Duelo de reflejos", "color": "F1C40F"},
        "trivia": {**base, "titulo": "🧠 Trivia — {tema}", "color": "3498DB"},
        "bola8": {**base, "titulo": "🎱 Bola 8 mágica", "color": "2C3E50"},
        "conecta4": {**base, "titulo": "🔴🟡 Conecta 4", "color": "E74C3C"},
        "blackjack": {**base, "titulo": "🃏 Blackjack", "color": "27AE60"},
        "slots": {**base, "titulo": "🎰 Tragamonedas", "color": "F1C40F"},
    }


def estilo_juego(gid, key, emb, vars=None, titulo=True):
    """Aplica a un embed de juego el diseño que el admin configuró (si lo hay)."""
    if gid is None:
        return emb
    st = cfg(gid)["juegos"]["embeds"].get(key)
    if not st:
        return emb
    vars = vars or {}
    if titulo and st.get("titulo"):
        emb.title = render(st["titulo"], vars)[:256]
    try:
        emb.color = int(st["color"].lstrip("#"), 16)
    except (ValueError, KeyError):
        pass
    if st.get("autor"):
        emb.set_author(name=render(st["autor"], vars)[:256])
    if st.get("miniatura"):
        emb.set_thumbnail(url=st["miniatura"])
    if st.get("imagen"):
        emb.set_image(url=st["imagen"])
    if st.get("footer"):
        emb.set_footer(text=render(st["footer"], vars)[:2048])
    return emb


# ───────────────────────────── Adivina la palabra ────────────────────────────
TEMAS = {"anime": ("🎌", "Anime"), "historia": ("📜", "Historia"), "videojuegos": ("🎮", "Videojuegos")}
JUEGOS_ADIVINA = set()  # canales con una partida en curso

PALABRAS = {
    "anime": [
        ("naruto", "Ninja que sueña con ser Hokage"),
        ("one piece", "Piratas en busca del tesoro más grande del mundo"),
        ("dragon ball", "Siete esferas que conceden deseos"),
        ("death note", "Una libreta que mata a quien se escribe en ella"),
        ("ataque a los titanes", "La humanidad vive tras enormes murallas"),
        ("fullmetal alchemist", "Dos hermanos y la alquimia"),
        ("hunter x hunter", "Gon busca a su padre"),
        ("demon slayer", "Tanjiro y su hermana convertida en demonio"),
        ("my hero academia", "Un mundo de superpoderes llamados Quirks"),
        ("jujutsu kaisen", "Maldiciones y hechiceros"),
        ("one punch man", "Héroe que derrota a todos de un solo golpe"),
        ("sailor moon", "Guerreras que luchan en nombre de la luna"),
        ("pokemon", "Atrápalos a todos"),
        ("evangelion", "Robots gigantes y un joven piloto"),
        ("cowboy bebop", "Cazarrecompensas en el espacio"),
        ("spy x family", "Espía, asesina y telépata fingiendo ser familia"),
        ("chainsaw man", "Un demonio con motosierra en la cabeza"),
        ("haikyuu", "Anime de voleibol"),
        ("bleach", "Shinigamis y almas perdidas"),
        ("tokyo ghoul", "Un humano convertido en mitad ghoul"),
        ("fairy tail", "Un gremio de magos"),
        ("black clover", "Asta, sin magia, sueña con ser rey mago"),
        ("doraemon", "Gato robot del futuro con un bolsillo mágico"),
        ("goku", "Saiyajin criado en la Tierra"),
        ("luffy", "Capitán de los Sombrero de Paja"),
    ],
    "historia": [
        ("napoleon", "Emperador francés derrotado en Waterloo"),
        ("cleopatra", "Última reina del antiguo Egipto"),
        ("julio cesar", "Dictador romano asesinado en los idus de marzo"),
        ("alejandro magno", "Rey macedonio que conquistó Persia"),
        ("cristobal colon", "Llegó a América en 1492"),
        ("simon bolivar", "El Libertador de varios países sudamericanos"),
        ("revolucion francesa", "Cayó la Bastilla en 1789"),
        ("imperio romano", "Gobernó el Mediterráneo desde la ciudad de las siete colinas"),
        ("imperio inca", "Civilización andina con capital en el Cusco"),
        ("aztecas", "Pueblo que fundó Tenochtitlan"),
        ("mayas", "Civilización de pirámides y un calendario famoso"),
        ("muralla china", "Gran construcción para frenar invasores del norte"),
        ("guerra fria", "Tensión entre EE.UU. y la URSS sin combate directo"),
        ("primera guerra mundial", "Estalló tras el asesinato de Francisco Fernando"),
        ("segunda guerra mundial", "Conflicto global de 1939 a 1945"),
        ("renacimiento", "Época de Leonardo da Vinci y Miguel Ángel"),
        ("edad media", "Época de castillos y feudalismo"),
        ("piramides de egipto", "Tumbas monumentales de los faraones"),
        ("carlomagno", "Emperador coronado el año 800"),
        ("isabel la catolica", "Reina de Castilla que apoyó a Colón"),
        ("mahatma gandhi", "Líder de la independencia de la India"),
        ("nelson mandela", "Presidente que puso fin al apartheid"),
        ("abraham lincoln", "Presidente de EE.UU. durante la Guerra Civil"),
        ("revolucion industrial", "Nacen las fábricas y la máquina de vapor"),
        ("caida del muro de berlin", "En 1989 terminó la división de Alemania"),
    ],
    "videojuegos": [
        ("minecraft", "Mundo de bloques para construir y sobrevivir"),
        ("fortnite", "Battle royale con construcciones"),
        ("super mario", "Fontanero que rescata a una princesa"),
        ("the legend of zelda", "Un héroe con espada que salva Hyrule"),
        ("pac man", "Círculo amarillo que come puntos y evita fantasmas"),
        ("tetris", "Piezas que caen y forman líneas"),
        ("sonic", "Erizo azul muy veloz"),
        ("among us", "Impostores en una nave espacial"),
        ("league of legends", "MOBA con campeones y la Grieta del Invocador"),
        ("counter strike", "Terroristas contra antiterroristas"),
        ("grand theft auto", "Crimen en mundo abierto; sus siglas son GTA"),
        ("call of duty", "Shooter bélico muy famoso"),
        ("the sims", "Simulador de vida con personajes que controlas"),
        ("animal crossing", "Vida tranquila en una isla con Tom Nook"),
        ("dark souls", "Saga muy difícil con fogatas"),
        ("resident evil", "Zombis y la corporación Umbrella"),
        ("god of war", "Un espartano que desafía a los dioses"),
        ("halo", "Un supersoldado con armadura verde llamado Jefe Maestro"),
        ("overwatch", "Shooter de héroes con habilidades únicas"),
        ("valorant", "Shooter táctico con agentes"),
        ("rocket league", "Fútbol jugado con autos"),
        ("stardew valley", "Granja, cultivos y un pueblo encantador"),
        ("hollow knight", "Insecto caballero en un reino subterráneo"),
        ("elden ring", "Las Tierras Intermedias, de FromSoftware"),
        ("metal gear solid", "Snake y el sigilo"),
    ],
}


def norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return " ".join("".join(c for c in t if unicodedata.category(c) != "Mn").split())


async def jugar_adivina(canal, jugadores, tema):
    gid = canal.guild.id
    emoji, nombre = TEMAS[tema]
    vars_ = {"{tema}": nombre}
    try:
        palabra, pista = random.choice(PALABRAS[tema])
        vidas = {u.id: 5 for u in jugadores}
        orden = jugadores[:]
        random.shuffle(orden)
        letras = set(palabra.replace(" ", ""))
        acertadas, falladas = set(), []

        def mascara():
            grupos = [" ".join(c.upper() if c in acertadas else "_" for c in parte) for parte in palabra.split(" ")]
            return "   /   ".join(grupos)

        def tablero(turno):
            e = discord.Embed(color=0x9B59B6)
            e.add_field(name="💡 Pista", value=pista, inline=False)
            e.add_field(name="Palabra", value=f"```{mascara()}```", inline=False)
            e.add_field(name="Letras falladas", value=" ".join(falladas).upper() or "—", inline=False)
            e.add_field(
                name="Vidas",
                value="\n".join(
                    f"{'👉 ' if u.id == turno.id else ''}{u.mention}: {'❤️' * vidas[u.id] or '💀'}" for u in orden
                ),
                inline=False,
            )
            e.set_footer(text="En tu turno escribe UNA letra o la palabra completa (30 s)")
            e.title = f"🔤 Adivina la palabra — {emoji} {nombre}"
            return estilo_juego(gid, "adivina", e, vars_)

        ganador, motivo, idx, previo = None, "", 0, None
        while ganador is None:
            vivos = [u for u in orden if vidas[u.id] > 0]
            if len(vivos) == 1:
                ganador, motivo = vivos[0], "es el último jugador en pie"
                break
            u = orden[idx % len(orden)]
            idx += 1
            if vidas[u.id] <= 0:
                continue
            if previo:
                try:
                    await previo.delete()
                except discord.HTTPException:
                    pass
            previo = await canal.send(content=u.mention, embed=tablero(u))

            limite = time.monotonic() + 30
            while True:
                try:
                    r = await client.wait_for(
                        "message",
                        check=lambda x: x.author.id == u.id and x.channel.id == canal.id,
                        timeout=max(limite - time.monotonic(), 0.1),
                    )
                except asyncio.TimeoutError:
                    vidas[u.id] -= 1
                    await canal.send(f"⌛ {u.mention} se quedó sin tiempo y pierde una vida.", delete_after=6)
                    break
                t = norm(r.content)
                if len(t) == 1 and t.isalpha():
                    if t in acertadas or t in falladas:
                        await canal.send("Esa letra ya se dijo. Prueba con otra.", delete_after=4)
                        continue
                    if t in letras:
                        acertadas.add(t)
                        if letras <= acertadas:
                            ganador, motivo = u, "completó la palabra"
                    else:
                        falladas.append(t)
                        vidas[u.id] -= 1
                    break
                if len(t) >= 2:
                    if t == palabra:
                        ganador, motivo = u, "adivinó la palabra"
                    else:
                        vidas[u.id] -= 1
                        await canal.send(f"❌ «{t}» no es la palabra.", delete_after=5)
                    break
                # un solo carácter que no es letra: se ignora y se sigue esperando

            if ganador is None and vidas[u.id] <= 0:
                await canal.send(f"💀 {u.mention} se quedó sin vidas y fue eliminado.", delete_after=8)

        if previo:
            try:
                await previo.delete()
            except discord.HTTPException:
                pass
        final = discord.Embed(
            title=f"🏆 ¡Gana {ganador.display_name}!",
            description=f"{ganador.mention} {motivo}.\n\nLa palabra era **{palabra.upper()}**.",
            color=0x2ECC71,
        )
        await canal.send(content=ganador.mention, embed=final)
    except discord.HTTPException:
        pass
    finally:
        JUEGOS_ADIVINA.discard(canal.id)


class AdivinaLobbyView(discord.ui.View):
    def __init__(self, host, n, tema, canal):
        super().__init__(timeout=120)
        self.host, self.n, self.tema, self.canal = host, n, tema, canal
        self.jugadores = [host]
        self.message = None

    def embed(self, texto=None):
        emoji, nombre = TEMAS[self.tema]
        e = discord.Embed(title="🔤 Adivina la palabra — Sala", color=0x9B59B6)
        e.add_field(name="Temática", value=f"{emoji} {nombre}", inline=True)
        e.add_field(name="Jugadores", value=f"{len(self.jugadores)}/{self.n}", inline=True)
        e.add_field(name="En la sala", value="\n".join(u.mention for u in self.jugadores), inline=False)
        e.set_footer(text=texto or "Pulsa «Unirse». La partida empieza cuando se complete la sala (2 min).")
        return e

    @discord.ui.button(label="Unirse", emoji="🎮", style=discord.ButtonStyle.success)
    async def unirse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if any(u.id == interaction.user.id for u in self.jugadores):
            return await interaction.response.send_message("Ya estás en la sala.", ephemeral=True)
        self.jugadores.append(interaction.user)
        if len(self.jugadores) >= self.n:
            for c in self.children:
                c.disabled = True
            self.stop()
            await interaction.response.edit_message(embed=self.embed("¡Sala completa! Empezando..."), view=self)
            asyncio.create_task(jugar_adivina(self.canal, self.jugadores, self.tema))
        else:
            await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Salir", style=discord.ButtonStyle.secondary)
    async def salir(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.host.id:
            return await interaction.response.send_message("Eres el anfitrión; usa «Cancelar» si quieres cerrar la sala.", ephemeral=True)
        self.jugadores = [u for u in self.jugadores if u.id != interaction.user.id]
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host.id:
            return await interaction.response.send_message("Solo el anfitrión puede cancelar.", ephemeral=True)
        JUEGOS_ADIVINA.discard(self.canal.id)
        for c in self.children:
            c.disabled = True
        self.stop()
        await interaction.response.edit_message(embed=self.embed("🚫 Sala cancelada por el anfitrión."), view=self)

    async def on_timeout(self):
        JUEGOS_ADIVINA.discard(self.canal.id)
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(embed=self.embed("⌛ Sala cerrada: no se completaron los jugadores."), view=self)
            except discord.HTTPException:
                pass


class AdivinaSetupView(discord.ui.View):
    def __init__(self, host):
        super().__init__(timeout=120)
        self.host = host
        self.n = None
        self.tema = None
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.host.id:
            await interaction.response.send_message("Solo quien ejecutó el comando puede configurar la partida.", ephemeral=True)
            return False
        return True

    def embed(self):
        e = discord.Embed(
            title="🔤 Adivina la palabra",
            description="Elige cuántos van a jugar y la temática, y pulsa **Crear partida**.",
            color=0x9B59B6,
        )
        e.add_field(name="Jugadores", value=f"{self.n}" if self.n else "—", inline=True)
        e.add_field(name="Temática", value=" ".join(TEMAS[self.tema]) if self.tema else "—", inline=True)
        e.add_field(
            name="Reglas",
            value="Cada jugador tiene 5 vidas ❤️. En tu turno (30 s) escribe **una letra** o **la palabra completa**.\n"
            "Fallar o quedarte sin tiempo cuesta 1 vida. Gana quien adivine la palabra o quede último en pie.",
            inline=False,
        )
        return e

    @discord.ui.select(
        placeholder="¿Cuántos jugadores? (2, 3 o 4)",
        options=[discord.SelectOption(label=f"{n} jugadores", value=str(n), emoji="👥") for n in (2, 3, 4)],
        row=0,
    )
    async def jugadores(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.n = int(select.values[0])
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.select(
        placeholder="¿De qué temática?",
        options=[discord.SelectOption(label=n, value=k, emoji=e) for k, (e, n) in TEMAS.items()],
        row=1,
    )
    async def tematica(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.tema = select.values[0]
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Crear partida", style=discord.ButtonStyle.success, row=2)
    async def crear(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.n or not self.tema:
            return await interaction.response.send_message("Elige primero los jugadores y la temática.", ephemeral=True)
        if interaction.channel_id in JUEGOS_ADIVINA:
            return await interaction.response.send_message("Ya hay una partida en este canal.", ephemeral=True)
        JUEGOS_ADIVINA.add(interaction.channel_id)
        self.stop()
        lobby = AdivinaLobbyView(self.host, self.n, self.tema, interaction.channel)
        await interaction.response.edit_message(embed=lobby.embed(), view=lobby)
        lobby.message = await interaction.original_response()

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


@tree.command(name="adivina-la-palabra", description="Adivina la palabra con 2 a 4 jugadores")
@app_commands.guild_only()
async def adivina_cmd(interaction: discord.Interaction):
    view = AdivinaSetupView(interaction.user)
    await interaction.response.send_message(embed=view.embed(), view=view)
    view.message = await interaction.original_response()


# ───────────────────── Más juegos: número, desordenada, reflejos ─────────────
@tree.command(name="adivina-el-numero", description="Adivina el número secreto antes que los demás")
@app_commands.describe(maximo="Número máximo posible (por defecto 100)")
@app_commands.guild_only()
async def adivina_numero(interaction: discord.Interaction, maximo: app_commands.Range[int, 10, 10000] = 100):
    canal = interaction.channel
    if canal.id in JUEGOS_ADIVINA:
        return await interaction.response.send_message("Ya hay una partida en este canal.", ephemeral=True)
    JUEGOS_ADIVINA.add(canal.id)
    try:
        secreto = random.randint(1, maximo)
        e = discord.Embed(
            title="🔢 Adivina el número",
            description=f"Pensé un número entre **1** y **{maximo}**.\nEscriban sus intentos en el chat: "
            "⬆️ significa que es más alto y ⬇️ que es más bajo.\n\nTienen **60 segundos**.",
            color=0x1ABC9C,
        )
        await interaction.response.send_message(embed=estilo_juego(interaction.guild_id, "numero", e))
        intentos, ganador = {}, None
        fin = time.monotonic() + 60
        while ganador is None:
            restante = fin - time.monotonic()
            if restante <= 0:
                break
            try:
                m = await client.wait_for(
                    "message",
                    check=lambda x: x.channel.id == canal.id and not x.author.bot and x.content.strip().isdigit(),
                    timeout=restante,
                )
            except asyncio.TimeoutError:
                break
            n = int(m.content.strip())
            intentos[m.author.id] = intentos.get(m.author.id, 0) + 1
            if n == secreto:
                ganador = m
                break
            try:
                await m.add_reaction("⬆️" if n < secreto else "⬇️")
            except discord.HTTPException:
                pass
        if ganador:
            final = discord.Embed(
                title="🏆 ¡Número adivinado!",
                description=f"{ganador.author.mention} acertó: era el **{secreto}** "
                f"(en {intentos[ganador.author.id]} intento(s)).",
                color=0x2ECC71,
            )
        else:
            final = discord.Embed(title="⌛ Se acabó el tiempo", description=f"Nadie lo adivinó. Era el **{secreto}**.", color=0x95A5A6)
        await canal.send(embed=estilo_juego(interaction.guild_id, "numero", final, titulo=False))
    finally:
        JUEGOS_ADIVINA.discard(canal.id)


def desordenar(palabra: str) -> str:
    grupos = []
    for parte in palabra.split(" "):
        letras = list(parte)
        for _ in range(10):
            random.shuffle(letras)
            if "".join(letras) != parte or len(set(parte)) < 2:
                break
        grupos.append(" ".join(l.upper() for l in letras))
    return "   /   ".join(grupos)


async def esperar_palabra(canal, palabra: str, segundos: float):
    fin = time.monotonic() + segundos
    while True:
        restante = fin - time.monotonic()
        if restante <= 0:
            return None
        try:
            m = await client.wait_for(
                "message", check=lambda x: x.channel.id == canal.id and not x.author.bot, timeout=restante
            )
        except asyncio.TimeoutError:
            return None
        if norm(m.content) == palabra:
            return m


@tree.command(name="palabra-desordenada", description="Ordena las letras y adivina la palabra antes que los demás")
@app_commands.describe(tematica="Temática (por defecto, al azar)")
@app_commands.choices(tematica=[
    app_commands.Choice(name="Anime", value="anime"),
    app_commands.Choice(name="Historia", value="historia"),
    app_commands.Choice(name="Videojuegos", value="videojuegos"),
    app_commands.Choice(name="Al azar", value="azar"),
])
@app_commands.guild_only()
async def palabra_desordenada(interaction: discord.Interaction, tematica: Optional[app_commands.Choice[str]] = None):
    canal = interaction.channel
    if canal.id in JUEGOS_ADIVINA:
        return await interaction.response.send_message("Ya hay una partida en este canal.", ephemeral=True)
    JUEGOS_ADIVINA.add(canal.id)
    try:
        tema = tematica.value if tematica and tematica.value != "azar" else random.choice(list(TEMAS))
        emoji, nombre = TEMAS[tema]
        palabra, pista = random.choice(PALABRAS[tema])
        vars_ = {"{tema}": f"{emoji} {nombre}"}
        e = discord.Embed(title=f"🔀 Palabra desordenada — {emoji} {nombre}", color=0xE91E63)
        e.add_field(name="Letras desordenadas", value=f"```{desordenar(palabra)}```", inline=False)
        e.add_field(name="💡 Pista", value=pista, inline=False)
        e.set_footer(text="Escribe la respuesta en el chat · Tienen 45 segundos")
        await interaction.response.send_message(embed=estilo_juego(interaction.guild_id, "desordenada", e, vars_))

        ganador = await esperar_palabra(canal, palabra, 20)
        if ganador is None:
            await canal.send(f"🔎 Pista extra: empieza con **{palabra[0].upper()}** y tiene {len(palabra.replace(' ', ''))} letras.")
            ganador = await esperar_palabra(canal, palabra, 25)
        if ganador:
            try:
                await ganador.add_reaction("✅")
            except discord.HTTPException:
                pass
            final = discord.Embed(title="🏆 ¡Correcto!", description=f"{ganador.author.mention} la adivinó: **{palabra.upper()}**", color=0x2ECC71)
        else:
            final = discord.Embed(title="⌛ Se acabó el tiempo", description=f"Nadie acertó. Era **{palabra.upper()}**.", color=0x95A5A6)
        await canal.send(embed=estilo_juego(interaction.guild_id, "desordenada", final, vars_, titulo=False))
    finally:
        JUEGOS_ADIVINA.discard(canal.id)


class ReflejosView(discord.ui.View):
    def __init__(self, a, b, gid):
        super().__init__(timeout=30)
        self.jugadores = [a.id, b.id]
        self.gid = gid
        self.listo = False
        self.terminado = False
        self.t0 = None
        self.message = None

    def embed(self, resultado=None):
        a, b = self.jugadores
        desc = f"<@{a}> vs <@{b}>\n\n" + (resultado or "Cuando el botón se ponga **verde**, ¡púlsalo lo más rápido que puedas!\nSi lo pulsas antes, **pierdes**.")
        e = discord.Embed(title="⚡ Duelo de reflejos", description=desc, color=0xF1C40F)
        return estilo_juego(self.gid, "reflejos", e)

    async def correr(self):
        await asyncio.sleep(random.uniform(2, 6))
        if self.terminado:
            return
        self.boton.label, self.boton.emoji, self.boton.style = "¡YA!", "⚡", discord.ButtonStyle.success
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            return
        self.listo = True
        self.t0 = time.monotonic()

    @discord.ui.button(label="Espera...", emoji="⏳", style=discord.ButtonStyle.danger)
    async def boton(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid not in self.jugadores:
            return await interaction.response.send_message("No participas en este duelo.", ephemeral=True)
        if self.terminado:
            return await interaction.response.send_message("El duelo ya terminó.", ephemeral=True)
        self.terminado = True
        otro = self.jugadores[1] if uid == self.jugadores[0] else self.jugadores[0]
        if not self.listo:
            res = f"🚫 <@{uid}> se adelantó. ¡Gana <@{otro}>!"
        else:
            res = f"⚡ ¡<@{uid}> fue más rápido! (**{int((time.monotonic() - self.t0) * 1000)} ms**)"
        button.disabled = True
        self.stop()
        await interaction.response.edit_message(content=None, embed=self.embed(res), view=self)

    async def on_timeout(self):
        self.terminado = True
        self.boton.disabled = True
        if self.message:
            try:
                await self.message.edit(embed=self.embed("⌛ Nadie pulsó el botón."), view=self)
            except discord.HTTPException:
                pass


@tree.command(name="reflejos", description="Duelo de reflejos: pulsa el botón cuando se ponga verde")
@app_commands.describe(oponente="Con quién quieres competir")
@app_commands.guild_only()
async def reflejos(interaction: discord.Interaction, oponente: discord.Member):
    if oponente.bot or oponente.id == interaction.user.id:
        return await interaction.response.send_message("Elige a otra persona (ni un bot ni tú mismo).", ephemeral=True)
    view = ReflejosView(interaction.user, oponente, interaction.guild_id)
    await interaction.response.send_message(
        content=f"{oponente.mention}, {interaction.user.mention} te retó a un duelo de reflejos.", embed=view.embed(), view=view
    )
    view.message = await interaction.original_response()
    asyncio.create_task(view.correr())


# ───────────────────────────────── Trivia ────────────────────────────────────
TRIVIA_SEGUNDOS = 15
LETRAS = ["A", "B", "C", "D"]


class TriviaBtn(discord.ui.Button):
    def __init__(self, i: int):
        super().__init__(label=LETRAS[i], style=discord.ButtonStyle.primary, row=0)
        self.i = i

    async def callback(self, interaction: discord.Interaction):
        v = self.view
        if interaction.user.id in v.respuestas:
            return await interaction.response.send_message("Ya respondiste esta pregunta.", ephemeral=True)
        v.respuestas[interaction.user.id] = (self.i, time.monotonic() - v.t0)
        await interaction.response.send_message(
            f"✅ Elegiste **{LETRAS[self.i]}**. ¡Veremos si acertaste!", ephemeral=True
        )


class TriviaPreguntaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=TRIVIA_SEGUNDOS)
        self.respuestas = {}  # user_id -> (opción elegida, segundos que tardó)
        self.t0 = time.monotonic()
        for i in range(4):
            self.add_item(TriviaBtn(i))


def embed_trivia(gid, tema, n, total, texto, opciones, img, idx_ok=None, extra=""):
    emoji, nombre = TEMAS[tema]
    lineas = []
    for i, o in enumerate(opciones):
        if idx_ok is None:
            lineas.append(f"**{LETRAS[i]})** {o}")
        elif i == idx_ok:
            lineas.append(f"✅ **{LETRAS[i]}) {o}**")
        else:
            lineas.append(f"▫️ {LETRAS[i]}) {o}")
    cabecera = f"{emoji} Pregunta **{n}/{total}**" + (f" · ⏱️ {TRIVIA_SEGUNDOS} s · cualquiera puede responder" if idx_ok is None else "")
    desc = f"{cabecera}\n\n**{texto}**\n\n" + "\n".join(lineas) + (f"\n\n{extra}" if extra else "")
    e = discord.Embed(title=f"🧠 Trivia — {nombre}", description=desc, color=0x3498DB)
    e = estilo_juego(gid, "trivia", e, {"{tema}": nombre})
    if img:  # la imagen de la pregunta tiene prioridad sobre la imagen fija del estilo
        e.set_image(url=img)
    return e


async def jugar_trivia(msg: discord.Message, canal, tema: str, total: int, gid: int):
    emoji, nombre = TEMAS[tema]
    puntos, aciertos = {}, {}
    try:
        await asyncio.sleep(3)
        banco = TRIVIA[tema]
        preguntas = random.sample(banco, min(total, len(banco)))
        pool = IMAGENES.get(tema) or []
        for n, item in enumerate(preguntas, 1):
            texto, correcta, m1, m2, m3, *resto = item
            img = resto[0] if resto else (random.choice(pool) if pool else None)
            opciones = [correcta, m1, m2, m3]
            random.shuffle(opciones)
            idx_ok = opciones.index(correcta)

            view = TriviaPreguntaView()
            await msg.edit(embed=embed_trivia(gid, tema, n, len(preguntas), texto, opciones, img), view=view)
            await view.wait()

            acertaron = []
            for uid, (i, t) in view.respuestas.items():
                if i == idx_ok:
                    pts = 10 + max(0, int(TRIVIA_SEGUNDOS - t))  # 10 base + hasta 15 por rapidez
                    puntos[uid] = puntos.get(uid, 0) + pts
                    aciertos[uid] = aciertos.get(uid, 0) + 1
                    acertaron.append((uid, pts))
            if acertaron:
                extra = "🎯 **Acertaron:** " + ", ".join(f"<@{u}> (+{p})" for u, p in acertaron[:10])
            elif view.respuestas:
                extra = "😅 Nadie acertó esta vez."
            else:
                extra = "💤 Nadie respondió."
            await msg.edit(embed=embed_trivia(gid, tema, n, len(preguntas), texto, opciones, img, idx_ok, extra), view=None)
            await asyncio.sleep(4)

        if puntos:
            orden = sorted(puntos.items(), key=lambda x: -x[1])[:10]
            medallas = ["🥇", "🥈", "🥉"]
            lineas = []
            for pos, (uid, p) in enumerate(orden):
                prefijo = medallas[pos] if pos < 3 else f"**{pos + 1}.**"
                lineas.append(f"{prefijo} <@{uid}> — **{p}** pts · {aciertos[uid]}/{len(preguntas)} aciertos")
            desc = f"{emoji} Tema: **{nombre}**\n\n" + "\n".join(lineas)
            ganador = orden[0][0]
        else:
            desc = f"{emoji} Tema: **{nombre}**\n\nNadie participó 😴"
            ganador = None
        final = discord.Embed(title="🏁 Trivia finalizada", description=desc, color=0x2ECC71)
        final = estilo_juego(gid, "trivia", final, {"{tema}": nombre}, titulo=False)
        await msg.edit(embed=final, view=None)
        if ganador:
            await canal.send(f"🏆 ¡Felicidades <@{ganador}>, ganaste la trivia!")
    except discord.NotFound:
        pass  # borraron el mensaje: se cancela la partida
    finally:
        JUEGOS_ADIVINA.discard(canal.id)


class TriviaTemaView(discord.ui.View):
    def __init__(self, host, total: int):
        super().__init__(timeout=60)
        self.host, self.total = host, total
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.host.id:
            await interaction.response.send_message("Solo quien ejecutó el comando puede elegir el tema.", ephemeral=True)
            return False
        return True

    def embed(self):
        return discord.Embed(
            title="🧠 Trivia",
            description=f"¿De qué quieres la trivia? Serán **{self.total} preguntas** de {TRIVIA_SEGUNDOS} s cada una.\n"
            "Cualquiera del canal puede responder con los botones. Aciertas = puntos, y respondes más rápido = más puntos.",
            color=0x3498DB,
        )

    @discord.ui.select(
        placeholder="Elige la temática",
        options=[discord.SelectOption(label=n, value=k, emoji=e) for k, (e, n) in TEMAS.items()],
    )
    async def tema(self, interaction: discord.Interaction, select: discord.ui.Select):
        canal = interaction.channel
        if canal.id in JUEGOS_ADIVINA:
            return await interaction.response.send_message("Ya hay una partida en este canal.", ephemeral=True)
        JUEGOS_ADIVINA.add(canal.id)
        self.stop()
        tema = select.values[0]
        emoji, nombre = TEMAS[tema]
        intro = discord.Embed(
            title=f"🧠 Trivia — {nombre}",
            description=f"{emoji} Tema: **{nombre}** · {self.total} preguntas\n¡Prepárense, empieza en 3 segundos!",
            color=0x3498DB,
        )
        intro = estilo_juego(interaction.guild_id, "trivia", intro, {"{tema}": nombre})
        await interaction.response.edit_message(embed=intro, view=None)
        asyncio.create_task(jugar_trivia(interaction.message, canal, tema, self.total, interaction.guild_id))

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(content="⌛ No elegiste temática a tiempo.", embed=None, view=None)
            except discord.HTTPException:
                pass


@tree.command(name="trivia", description="Trivia de Anime, Historia o Videojuegos (100 preguntas por tema)")
@app_commands.describe(preguntas="Cuántas preguntas quieres (3-20, por defecto 10)")
@app_commands.guild_only()
async def trivia_cmd(interaction: discord.Interaction, preguntas: app_commands.Range[int, 3, 20] = 10):
    if interaction.channel_id in JUEGOS_ADIVINA:
        return await interaction.response.send_message("Ya hay una partida en este canal.", ephemeral=True)
    view = TriviaTemaView(interaction.user, preguntas)
    await interaction.response.send_message(embed=view.embed(), view=view)
    view.message = await interaction.original_response()


# ─────────────────────────────────── Sorteos ─────────────────────────────────
SORT_VARIABLES = {
    "{premio}": "Premio del sorteo",
    "{num_ganadores}": "Cantidad de ganadores",
    "{fin}": "Cuenta regresiva hasta que termina",
    "{anfitrion}": "Quien creó el sorteo",
    "{participantes}": "Cantidad de participantes",
    "{ganadores}": "Ganadores (al finalizar)",
    "{requisito}": "Rol requerido para participar",
    "{servidor}": "Nombre del servidor",
}


def default_sort_embeds():
    base = {"autor": None, "miniatura": None, "imagen": None, "footer": None}
    return {
        "sorteo": {
            **base, "titulo": "🎉 SORTEO: {premio}",
            "descripcion": "Pulsa el botón **Participar** para entrar.\n\n**Termina:** {fin}\n**Ganadores:** {num_ganadores}\n"
            "**Requisito:** {requisito}\n**Organiza:** {anfitrion}\n**Participantes:** {participantes}",
            "color": "F1C40F",
        },
        "final": {
            **base, "titulo": "🏆 Sorteo finalizado: {premio}",
            "descripcion": "**Ganadores:** {ganadores}\n**Participantes:** {participantes}\n**Organizó:** {anfitrion}",
            "color": "2ECC71",
        },
    }


def puede_sortear(member: discord.Member) -> bool:
    s = cfg(member.guild.id)["sort"]
    return member.guild_permissions.administrator or any(r.id in s["roles"] for r in member.roles)


def parse_duracion(txt: str):
    t = txt.lower().replace(" ", "")
    partes = re.findall(r"(\d+)([smhd])", t)
    if not partes or "".join(f"{n}{u}" for n, u in partes) != t:
        return None
    mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return sum(int(n) * mult[u] for n, u in partes)


def sort_vars(guild, rec, ganadores=None):
    return {
        "{num_ganadores}": str(rec["ganadores"]),
        "{fin}": f"<t:{rec['fin']}:R>",
        "{anfitrion}": f"<@{rec['anfitrion']}>",
        "{participantes}": str(len(rec["participantes"])),
        "{ganadores}": ganadores or "—",
        "{requisito}": f"<@&{rec['requisito']}>" if rec.get("requisito") else "Ninguno",
        "{servidor}": guild.name,
        "{premio}": rec["premio"],  # al final para no re-sustituir variables escritas en el premio
    }


def build_sort_embed(guild, rec):
    return post_embed(cfg(guild.id)["sort"]["embeds"]["sorteo"], sort_vars(guild, rec))


class SorteoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Participar", emoji="🎉", style=discord.ButtonStyle.success, custom_id="sort:join")
    async def participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        rec = cfg(interaction.guild.id)["sort"]["items"].get(str(interaction.message.id))
        if not rec or rec["estado"] != "activo":
            return await interaction.response.send_message("🔒 Este sorteo ya terminó.", ephemeral=True)
        if rec.get("requisito") and rec["requisito"] not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message(f"❌ Necesitas el rol <@&{rec['requisito']}> para participar.", ephemeral=True)
        uid = interaction.user.id
        if uid in rec["participantes"]:
            rec["participantes"].remove(uid)
            texto = "👋 Saliste del sorteo."
        else:
            rec["participantes"].append(uid)
            texto = "🎉 ¡Estás participando! Suerte."
        save()
        await interaction.response.edit_message(embed=build_sort_embed(interaction.guild, rec))
        await interaction.followup.send(texto, ephemeral=True)


async def anunciar_ganadores(guild, mid, rec, nuevos, reroll=False):
    canal = guild.get_channel(rec["canal"])
    if canal is None:
        return
    texto = " ".join(f"<@{u}>" for u in nuevos) or "Nadie participó 😢"
    mensaje = (f"🔁 Nuevo ganador: {texto}. ¡Felicidades!" if reroll
               else (f"🎉 ¡Felicidades {texto}! Ganaron **{rec['premio']}**." if nuevos else "😢 Nadie participó en el sorteo."))
    permitidos = discord.AllowedMentions(users=True)
    try:
        msg = await canal.fetch_message(int(mid))
        await msg.reply(mensaje, allowed_mentions=permitidos)
    except discord.HTTPException:
        await canal.send(mensaje, allowed_mentions=permitidos)


async def finalizar_sorteo(guild, mid, rec):
    s = cfg(guild.id)["sort"]
    rec["estado"] = "finalizado"
    validos = [u for u in rec["participantes"] if guild.get_member(u)]
    ganadores = random.sample(validos, min(rec["ganadores"], len(validos)))
    rec["ganadores_ids"] = ganadores
    save()
    texto = " ".join(f"<@{u}>" for u in ganadores) or "Nadie participó"
    canal = guild.get_channel(rec["canal"])
    if canal is None:
        return
    try:
        msg = await canal.fetch_message(int(mid))
        await msg.edit(embed=post_embed(s["embeds"]["final"], sort_vars(guild, rec, texto)), view=None)
    except discord.HTTPException:
        pass
    await anunciar_ganadores(guild, mid, rec, ganadores)


async def bucle_sorteos():
    await client.wait_until_ready()
    while not client.is_closed():
        ahora = int(time.time())
        for gid in list(data.keys()):
            g = client.get_guild(int(gid))
            s = data[gid].get("sort")
            if not g or not s:
                continue
            for mid, rec in list(s["items"].items()):
                if rec["estado"] == "activo" and rec["fin"] <= ahora:
                    try:
                        await finalizar_sorteo(g, mid, rec)
                    except Exception as e:
                        print("Error finalizando sorteo:", e)
        await asyncio.sleep(15)


sorteo = app_commands.Group(name="sorteo", description="Sistema de sorteos", guild_only=True)
tree.add_command(sorteo)


@sorteo.command(name="crear", description="Crea un sorteo")
@app_commands.describe(
    premio="Qué se sortea", duracion="Ej: 30m, 2h, 1d, 1h30m", ganadores="Cantidad de ganadores (por defecto 1)",
    canal="Canal del sorteo (por defecto, este)", requisito="Rol necesario para participar (opcional)",
)
async def sorteo_crear(
    interaction: discord.Interaction, premio: app_commands.Range[str, 1, 200], duracion: str,
    ganadores: app_commands.Range[int, 1, 20] = 1, canal: Optional[discord.TextChannel] = None,
    requisito: Optional[discord.Role] = None,
):
    if not puede_sortear(interaction.user):
        return await interaction.response.send_message("❌ No tienes permiso para crear sorteos.", ephemeral=True)
    seg = parse_duracion(duracion)
    if seg is None or not 10 <= seg <= 30 * 86400:
        return await interaction.response.send_message(
            "❌ Duración inválida. Usa por ejemplo `30m`, `2h`, `1d` o `1h30m` (entre 10 segundos y 30 días).", ephemeral=True
        )
    destino = canal or interaction.channel
    rec = {
        "premio": premio, "ganadores": ganadores, "fin": int(time.time()) + seg, "anfitrion": interaction.user.id,
        "canal": destino.id, "requisito": requisito.id if requisito else None, "participantes": [], "estado": "activo",
    }
    try:
        msg = await destino.send(embed=build_sort_embed(interaction.guild, rec), view=SorteoView())
    except discord.HTTPException:
        return await interaction.response.send_message(f"❌ No puedo enviar mensajes en {destino.mention}.", ephemeral=True)
    cfg(interaction.guild.id)["sort"]["items"][str(msg.id)] = rec
    save()
    await interaction.response.send_message(f"✅ Sorteo creado: {msg.jump_url}", ephemeral=True)


def _opciones_sorteo(interaction, current, estado):
    items = cfg(interaction.guild.id)["sort"]["items"]
    out = []
    for mid, rec in reversed(list(items.items())):
        if rec["estado"] != estado:
            continue
        nombre = f"{rec['premio'][:70]} (#{mid[-4:]})"
        if current.lower() in nombre.lower():
            out.append(app_commands.Choice(name=nombre, value=mid))
    return out[:25]


@sorteo.command(name="finalizar", description="Termina un sorteo ahora y elige ganadores")
@app_commands.describe(sorteo="Sorteo activo")
async def sorteo_finalizar(interaction: discord.Interaction, sorteo: str):
    if not puede_sortear(interaction.user):
        return await interaction.response.send_message("❌ No tienes permiso para esto.", ephemeral=True)
    rec = cfg(interaction.guild.id)["sort"]["items"].get(sorteo)
    if not rec or rec["estado"] != "activo":
        return await interaction.response.send_message("⚠️ Ese sorteo no existe o ya terminó.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    await finalizar_sorteo(interaction.guild, sorteo, rec)
    await interaction.followup.send("✅ Sorteo finalizado.", ephemeral=True)


@sorteo_finalizar.autocomplete("sorteo")
async def ac_sorteo_activo(interaction: discord.Interaction, current: str):
    return _opciones_sorteo(interaction, current, "activo")


@sorteo.command(name="reroll", description="Elige un nuevo ganador de un sorteo terminado")
@app_commands.describe(sorteo="Sorteo finalizado")
async def sorteo_reroll(interaction: discord.Interaction, sorteo: str):
    if not puede_sortear(interaction.user):
        return await interaction.response.send_message("❌ No tienes permiso para esto.", ephemeral=True)
    rec = cfg(interaction.guild.id)["sort"]["items"].get(sorteo)
    if not rec or rec["estado"] != "finalizado":
        return await interaction.response.send_message("⚠️ Ese sorteo no existe o aún no termina.", ephemeral=True)
    previos = rec.get("ganadores_ids", [])
    candidatos = [u for u in rec["participantes"] if u not in previos and interaction.guild.get_member(u)]
    if not candidatos:
        return await interaction.response.send_message("⚠️ No quedan participantes disponibles para un nuevo ganador.", ephemeral=True)
    nuevo = random.choice(candidatos)
    rec.setdefault("ganadores_ids", []).append(nuevo)
    save()
    await interaction.response.send_message("✅ Nuevo ganador elegido.", ephemeral=True)
    await anunciar_ganadores(interaction.guild, sorteo, rec, [nuevo], reroll=True)


@sorteo_reroll.autocomplete("sorteo")
async def ac_sorteo_final(interaction: discord.Interaction, current: str):
    return _opciones_sorteo(interaction, current, "finalizado")


# ────────────────────────────────── Tickets ──────────────────────────────────
TK_VARIABLES = {
    "{usuario}": "Menciona a quien abrió el ticket",
    "{numero}": "Número del ticket",
    "{categoria}": "Categoría elegida",
    "{staff}": "Staff que cierra el ticket",
    "{servidor}": "Nombre del servidor",
}


def default_tk_embeds():
    base = {"autor": None, "miniatura": None, "imagen": None, "footer": None}
    return {
        "panel": {**base, "titulo": "🎫 Soporte — {servidor}",
                  "descripcion": "¿Necesitas ayuda? Elige una categoría en el menú de abajo y se abrirá un canal privado con el staff.",
                  "color": "5865F2"},
        "ticket": {**base, "titulo": "🎫 Ticket #{numero} — {categoria}",
                   "descripcion": "Hola {usuario}, gracias por abrir un ticket. Cuéntanos tu consulta con el mayor detalle posible; el staff te atenderá pronto.",
                   "color": "2ECC71"},
        "cierre": {**base, "titulo": "🔒 Ticket #{numero} cerrado",
                   "descripcion": "**Usuario:** {usuario}\n**Categoría:** {categoria}\n**Cerrado por:** {staff}",
                   "color": "E74C3C"},
        "reclamacion": {**base, "titulo": "🙋 Ticket #{numero} reclamado",
                   "descripcion": "Hola {usuario}, el staff {staff} ha reclamado tu ticket.",
                   "color": "5865F2"},
    }


def tk_vars(guild, rec=None, staff="—"):
    return {
        "{usuario}": f"<@{rec['usuario']}>" if rec else "—",
        "{numero}": str(rec["numero"]) if rec else "—",
        "{categoria}": rec["categoria"] if rec else "—",
        "{staff}": staff,
        "{servidor}": guild.name,
    }


TK_PLACEHOLDER_DEFECTO = "🎫 Elige una categoría para abrir un ticket"


def _cat_de(t, categoria):
    return next((c for c in t["cats"] if c["nombre"][:100] == (categoria or "")[:100]), None)


def roles_atienden(t, categoria) -> list:
    """Roles que atienden una categoría; si no tiene propios, los de staff generales."""
    c = _cat_de(t, categoria)
    return c["roles"] if c and c.get("roles") else t["roles"]


def roles_ping(t, categoria) -> list:
    c = _cat_de(t, categoria)
    return c["ping"] if c and c.get("ping") else roles_atienden(t, categoria)


def tk_es_staff(member, t, rec=None) -> bool:
    if member.guild_permissions.administrator:
        return True
    ids = roles_atienden(t, rec["categoria"]) if rec else t["roles"]
    return any(r.id in ids for r in member.roles)


def puede_panel_tk(member) -> bool:
    """Administradores o roles elegidos en /configuracion → Tickets pueden enviar el panel."""
    t = cfg(member.guild.id)["tk"]
    return member.guild_permissions.administrator or any(r.id in t.get("panel_roles", []) for r in member.roles)


async def abrir_ticket(interaction: discord.Interaction, categoria: str):
    g = interaction.guild
    t = cfg(g.id)["tk"]
    await interaction.response.defer(ephemeral=True)

    propios = [r for r in t["abiertos"].values() if r["usuario"] == interaction.user.id]
    if len(propios) >= t["max"]:
        return await interaction.followup.send(
            f"⚠️ Ya tienes {len(propios)} ticket(s) abierto(s): " + " ".join(f"<#{r['canal']}>" for r in propios), ephemeral=True
        )
    if not g.me.guild_permissions.manage_channels:
        return await interaction.followup.send("❌ No tengo el permiso **Gestionar canales**.", ephemeral=True)

    permisos_user = discord.PermissionOverwrite(
        view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True
    )
    overwrites = {
        g.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: permisos_user,
        g.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True, manage_messages=True,
            embed_links=True, attach_files=True, read_message_history=True,
        ),
    }
    for rid in roles_atienden(t, categoria):
        rol = g.get_role(rid)
        if rol:
            overwrites[rol] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, attach_files=True,
                embed_links=True, manage_messages=True,
            )
    cat = g.get_channel(t["categoria"]) if t["categoria"] else None
    t["contador"] += 1
    n = t["contador"]
    c_cfg = _cat_de(t, categoria) or {}
    plantilla = c_cfg.get("nombre_canal") or "ticket-{numero}"
    nombre_canal = render(
        plantilla,
        {"{numero}": str(n), "{usuario}": interaction.user.name.lower(), "{categoria}": categoria.lower()}
    )
    nombre_canal = re.sub(r"[^a-z0-9áéíóúüñ_-]+", "-", unicodedata.normalize("NFKC", nombre_canal).lower()).strip("-")[:95] or f"ticket-{n:04d}"
    try:
        canal = await g.create_text_channel(
            nombre_canal, category=cat, overwrites=overwrites,
            topic=f"Ticket #{n} · {interaction.user} ({interaction.user.id}) · {categoria}",
            reason=f"[Nexus] Ticket de {interaction.user}",
        )
    except discord.HTTPException as e:
        t["contador"] -= 1
        return await interaction.followup.send(f"❌ No pude crear el canal: {e.text or e}", ephemeral=True)

    rec = {"numero": n, "usuario": interaction.user.id, "categoria": categoria, "canal": canal.id, "reclamado": None}
    t["abiertos"][str(canal.id)] = rec
    save()
    ping = " ".join(f"<@&{r}>" for r in roles_ping(t, categoria))
    await canal.send(
        content=f"{interaction.user.mention} {ping}".strip(),
        embed=post_embed(t["embeds"].get(f"cat:{categoria}") or t["embeds"]["ticket"], tk_vars(g, rec)),
        view=TicketControlView(),
        allowed_mentions=discord.AllowedMentions(users=True, roles=True),
    )
    await interaction.followup.send(f"✅ Tu ticket está listo: {canal.mention}", ephemeral=True)
    try:  # reinicia el menú del panel para que se pueda volver a elegir
        await interaction.message.edit(view=TicketPanelView(t["cats"], t.get("placeholder")))
    except discord.HTTPException:
        pass


class TicketSelect(discord.ui.Select):
    def __init__(self, opciones, placeholder=None):
        super().__init__(custom_id="tk:open", placeholder=(placeholder or TK_PLACEHOLDER_DEFECTO)[:150], options=opciones)

    async def callback(self, interaction: discord.Interaction):
        await abrir_ticket(interaction, self.values[0])


class TicketPanelView(discord.ui.View):
    def __init__(self, cats=None, placeholder=None):
        super().__init__(timeout=None)
        cats = cats or [{"nombre": "Soporte", "desc": "Ayuda general"}]
        self.add_item(TicketSelect([
            discord.SelectOption(label=c["nombre"][:100], value=c["nombre"][:100], description=(c.get("desc") or "")[:100] or None)
            for c in cats[:25]
        ], placeholder))


async def iniciar_cierre_ticket(interaction: discord.Interaction, rec, razon):
    """Pide la valoración dentro del ticket. El canal solo se elimina después de valorar."""
    g = interaction.guild
    t = cfg(g.id)["tk"]
    canal = interaction.channel
    staff_id = rec.get("reclamado") or interaction.user.id

    # Evita que se pueda iniciar el cierre varias veces.
    if str(canal.id) in t.get("rating_pending", {}):
        return await interaction.response.send_message("⭐ Este ticket ya está esperando una valoración.", ephemeral=True)

    t["rating_pending"][str(canal.id)] = {
        "numero": rec["numero"],
        "usuario": rec["usuario"],
        "staff": staff_id,
        "categoria": rec["categoria"],
        "razon": razon or "",
        "cerrado_por": interaction.user.id,
        "ts": int(time.time()),
    }
    save()

    e = discord.Embed(
        title="⭐ Antes de cerrar este ticket",
        description=(
            f"{interaction.user.mention}, el ticket **#{rec['numero']}** está listo para cerrarse.\n\n"
            "Por favor, **valora la atención del staff** que te atendió antes de finalizar el ticket.\n"
            "Tu valoración se guardará en el canal configurado por la administración."
        ),
        color=0xF1C40F,
    )
    e.set_footer(text="El ticket se cerrará automáticamente después de registrar la valoración.")
    await interaction.response.send_message(embed=e, view=RatingView())


async def cerrar_ticket(interaction: discord.Interaction, rec, razon, rating=None):
    """Finaliza el ticket, guarda transcript y registra la valoración si existe."""
    g = interaction.guild
    t = cfg(g.id)["tk"]
    canal = interaction.channel
    mensaje_cierre = "🔒 Cerrando el ticket y guardando la transcripción... el canal se eliminará en unos segundos."
    if interaction.response.is_done():
        await interaction.followup.send(mensaje_cierre, ephemeral=True)
    else:
        await interaction.response.send_message(mensaje_cierre, ephemeral=True)

    lineas = []
    async for m in canal.history(limit=1000, oldest_first=True):
        texto = m.content
        for e in m.embeds:
            partes = [x for x in (e.title, e.description) if x]
            if partes:
                texto += f" [embed: {' - '.join(partes)}]"
        for a in m.attachments:
            texto += f" [adjunto: {a.url}]"
        lineas.append(f"[{m.created_at:%Y-%m-%d %H:%M}] {m.author} ({m.author.id}): {texto.strip()}")
    datos = ("\n".join(lineas) or "(sin mensajes)").encode("utf-8")
    nombre = f"transcripcion-ticket-{rec['numero']:04d}.txt"
    vars_ = tk_vars(g, rec, staff=f"<@{rec.get('reclamado') or interaction.user.id}>")

    def embed_cierre():
        e = post_embed(t["embeds"]["cierre"], vars_)
        if razon:
            e.add_field(name="Razón", value=razon[:1000], inline=False)
        if rec.get("reclamado"):
            e.add_field(name="Reclamado por", value=f"<@{rec['reclamado']}>", inline=True)
        return e

    log = g.get_channel(t["canal"]) if t["canal"] else None
    if log:
        try:
            await log.send(embed=embed_cierre(), file=discord.File(io.BytesIO(datos), filename=nombre))
        except discord.HTTPException:
            pass

    # Guarda la valoración y envía el resultado al canal configurado.
    if rating is not None:
        entry_id = str(len(t["valoraciones"]) + 1)
        pending = t.get("rating_pending", {}).get(str(canal.id), {})
        t["valoraciones"][entry_id] = {
            "numero": rec["numero"], "usuario": rec["usuario"],
            "staff": rec.get("reclamado") or interaction.user.id,
            "categoria": rec["categoria"], "rating": rating,
            "ts_rating": int(time.time()),
        }
        valor_channel = g.get_channel(t.get("canal_valoraciones")) if t.get("canal_valoraciones") else None
        if valor_channel:
            estrellas = "⭐" * rating + "☆" * (5 - rating)
            ve = discord.Embed(
                title="⭐ Nueva valoración de ticket",
                description=f"**Ticket:** #{rec['numero']}\n**Usuario:** <@{rec['usuario']}>\n**Staff:** <@{rec.get('reclamado') or interaction.user.id}>\n**Categoría:** {rec['categoria']}\n\n**Valoración:** {estrellas} — **{rating}/5**",
                color=0xF1C40F,
            )
            if razon:
                ve.add_field(name="Razón de cierre", value=razon[:1000], inline=False)
            try:
                await valor_channel.send(embed=ve)
            except discord.HTTPException:
                pass

    t["rating_pending"].pop(str(canal.id), None)
    t["abiertos"].pop(str(canal.id), None)
    save()

    await asyncio.sleep(4)
    try:
        await canal.delete(reason=f"[Nexus] Ticket #{rec['numero']} cerrado por {interaction.user}")
    except discord.HTTPException:
        pass


class TkCierreModal(discord.ui.Modal, title="Cerrar ticket"):
    def __init__(self, rec):
        super().__init__()
        self.rec = rec
        self.razon = discord.ui.TextInput(label="Razón de cierre (opcional)", style=discord.TextStyle.paragraph, required=False, max_length=500)
        self.add_item(self.razon)

    async def on_submit(self, interaction: discord.Interaction):
        await iniciar_cierre_ticket(interaction, self.rec, self.razon.value)


class TkUserView(discord.ui.View):
    def __init__(self, canal, agregar: bool, dueno: int):
        super().__init__(timeout=60)
        self.canal, self.agregar, self.dueno = canal, agregar, dueno

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Elige a la(s) persona(s)", min_values=1, max_values=5)
    async def elegir(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        nombres = []
        for u in select.values:
            if self.agregar:
                await self.canal.set_permissions(
                    u, view_channel=True, send_messages=True, read_message_history=True, attach_files=True
                )
                nombres.append(u.mention)
            elif u.id != self.dueno:
                await self.canal.set_permissions(u, overwrite=None)
                nombres.append(u.mention)
        await interaction.response.edit_message(content="✅ Listo.", view=None)
        if nombres:
            accion = "agregó a" if self.agregar else "quitó a"
            await self.canal.send(f"👥 {interaction.user.mention} {accion} {', '.join(nombres)}.", allowed_mentions=discord.AllowedMentions.none())



class RatingButton(discord.ui.Button):
    def __init__(self, stars: int):
        super().__init__(label=f"{stars} ⭐", style=discord.ButtonStyle.primary,
                         custom_id=f"tk:rating:{stars}", row=0)
        self.stars = stars

    async def callback(self, interaction: discord.Interaction):
        # La valoración se realiza dentro del ticket; al elegirla, el ticket se cierra.
        if not interaction.guild or not interaction.channel:
            return await interaction.response.send_message("⚠️ Esta valoración ya no está disponible.", ephemeral=True)
        t = cfg(interaction.guild.id)["tk"]
        pending = t.get("rating_pending", {}).get(str(interaction.channel.id))
        if not pending:
            return await interaction.response.send_message("⚠️ Este ticket ya no está esperando una valoración.", ephemeral=True)
        if interaction.user.id != pending.get("usuario"):
            return await interaction.response.send_message("❌ Solo quien abrió el ticket puede valorar la atención.", ephemeral=True)

        rec = t["abiertos"].get(str(interaction.channel.id))
        if not rec:
            return await interaction.response.send_message("⚠️ Este ticket ya no está registrado.", ephemeral=True)

        # Deshabilita los botones mientras se procesa el cierre.
        for item in interaction.message.components:
            pass
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="⭐ Valoración registrada",
                description=f"Gracias por valorar la atención con **{self.stars}/5 ⭐**.\n\n🔒 Cerrando el ticket...",
                color=0x2ECC71,
            ), view=None
        )
        await cerrar_ticket(interaction, rec, pending.get("razon", ""), rating=self.stars)


class RatingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for stars in range(1, 6):
            self.add_item(RatingButton(stars))


class StaffApprovalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def _find(self, message_id):
        for gid, gdata in data.items():
            pending = gdata.get("seg", {}).get("staff_guard", {}).get("pending", {})
            if str(message_id) in pending:
                return int(gid), pending[str(message_id)]
        return None, None

    async def _resolve(self, interaction, approve: bool):
        gid, rec = self._find(interaction.message.id)
        if not rec:
            return await interaction.response.send_message("⚠️ Esta solicitud ya fue resuelta.", ephemeral=True)
        guild = client.get_guild(gid)
        if guild is None:
            return await interaction.response.send_message("❌ No encuentro el servidor.", ephemeral=True)
        target = guild.get_member(rec["target"])
        role = guild.get_role(rec["role"])
        staff = guild.get_member(rec["staff"])
        s = cfg(gid)["seg"]["staff_guard"]

        s["pending"].pop(str(interaction.message.id), None)
        if approve:
            ok = False
            if target and role and guild.me.top_role > role:
                try:
                    await target.add_roles(role, reason="[Nexus] Aprobación del dueño")
                    ok = True
                except discord.HTTPException:
                    pass
            estado = "aprobada" if ok else "aprobada, pero no pude entregar el rol por jerarquía/permisos"
        else:
            estado = "rechazada"

        save()
        e = discord.Embed(
            title="🔐 Solicitud de rol de staff",
            description=f"Solicitud **{estado}**.\n\n"
                        f"**Staff:** {staff.mention if staff else f'<@{rec["staff"]}>'}\n"
                        f"**Rol:** {role.mention if role else f'<@&{rec["role"]}>'}\n"
                        f"**Usuario:** {target.mention if target else f'<@{rec["target"]}>'}",
            color=0x2ECC71 if approve and ok else 0xE74C3C
        )
        await interaction.response.edit_message(embed=e, view=None)
        if staff:
            try:
                await staff.send(
                    f"🔐 La solicitud para dar **{role.name if role else rec['role']}** a "
                    f"**{target}** fue **{estado}** por el dueño."
                )
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Aprobar", emoji="✅", style=discord.ButtonStyle.success, custom_id="staffguard:approve")
    async def aprobar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, True)

    @discord.ui.button(label="Rechazar", emoji="❌", style=discord.ButtonStyle.danger, custom_id="staffguard:reject")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, False)


class TicketControlView(discord.ui.View):
    def __init__(self, reclamado: bool = False):
        super().__init__(timeout=None)
        if reclamado:
            self.reclamar.disabled = True

    def _ctx(self, interaction):
        t = cfg(interaction.guild.id)["tk"]
        return t, t["abiertos"].get(str(interaction.channel.id))

    @discord.ui.button(label="Cerrar", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="tk:close")
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        t, rec = self._ctx(interaction)
        if not rec:
            return await interaction.response.send_message("❌ Este ticket ya no está registrado.", ephemeral=True)
        if not (tk_es_staff(interaction.user, t, rec) or interaction.user.id == rec["usuario"]):
            return await interaction.response.send_message("❌ Solo el staff o quien abrió el ticket puede cerrarlo.", ephemeral=True)
        await interaction.response.send_modal(TkCierreModal(rec))

    @discord.ui.button(label="Reclamar", emoji="🙋", style=discord.ButtonStyle.primary, custom_id="tk:claim")
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        t, rec = self._ctx(interaction)
        if not rec:
            return await interaction.response.send_message("❌ Este ticket ya no está registrado.", ephemeral=True)
        if not tk_es_staff(interaction.user, t, rec):
            return await interaction.response.send_message("❌ Solo el staff puede reclamar tickets.", ephemeral=True)
        if rec.get("reclamado"):
            return await interaction.response.send_message(f"Ya lo reclamó <@{rec['reclamado']}>.", ephemeral=True)
        # Al reclamar: ocultar el ticket de TODOS los roles de staff de la categoría,
        # excepto del staff que lo reclamó. El creador, Nexus y el reclamante siguen viendo el canal.
        staff_ids = set(roles_atienden(t, rec["categoria"]))
        for rid in staff_ids:
            rol = interaction.guild.get_role(rid)
            if rol:
                try:
                    await interaction.channel.set_permissions(
                        rol, view_channel=False, send_messages=False, read_message_history=False
                    )
                except discord.HTTPException:
                    pass
        try:
            await interaction.channel.set_permissions(
                interaction.user, view_channel=True, send_messages=True,
                read_message_history=True, attach_files=True, embed_links=True,
                manage_messages=True
            )
        except discord.HTTPException:
            pass
        rec["reclamado"] = interaction.user.id
        save()
        e = interaction.message.embeds[0].copy()
        e.add_field(name="🙋 Reclamado por", value=interaction.user.mention, inline=False)
        aviso = post_embed(t["embeds"].get("reclamacion", default_tk_embeds()["reclamacion"]), tk_vars(interaction.guild, rec, staff=interaction.user.mention))
        try:
            await interaction.channel.send(embed=aviso, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
        except discord.HTTPException:
            pass
        await interaction.response.edit_message(embed=e, view=TicketControlView(reclamado=True))

    @discord.ui.button(label="Agregar", emoji="➕", style=discord.ButtonStyle.secondary, custom_id="tk:add")
    async def agregar(self, interaction: discord.Interaction, button: discord.ui.Button):
        t, rec = self._ctx(interaction)
        if not rec or not tk_es_staff(interaction.user, t, rec):
            return await interaction.response.send_message("❌ Solo el staff puede hacer esto.", ephemeral=True)
        await interaction.response.send_message("¿A quién quieres agregar al ticket?", view=TkUserView(interaction.channel, True, rec["usuario"]), ephemeral=True)

    @discord.ui.button(label="Quitar", emoji="➖", style=discord.ButtonStyle.secondary, custom_id="tk:rem")
    async def quitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        t, rec = self._ctx(interaction)
        if not rec or not tk_es_staff(interaction.user, t, rec):
            return await interaction.response.send_message("❌ Solo el staff puede hacer esto.", ephemeral=True)
        await interaction.response.send_message("¿A quién quieres quitar del ticket?", view=TkUserView(interaction.channel, False, rec["usuario"]), ephemeral=True)


@tree.command(name="ticket-panel", description="Envía el panel para que abran tickets")
@app_commands.describe(canal="Canal donde se enviará el panel (por defecto, este)")
@app_commands.guild_only()
async def ticket_panel(interaction: discord.Interaction, canal: Optional[discord.TextChannel] = None):
    if not puede_panel_tk(interaction.user):
        return await interaction.response.send_message(
            "❌ No tienes permiso para enviar el panel de tickets. "
            "Un administrador puede darte acceso en `/configuracion → Tickets`.", ephemeral=True)
    t = cfg(interaction.guild.id)["tk"]
    destino = canal or interaction.channel
    try:
        await destino.send(embed=post_embed(t["embeds"]["panel"], tk_vars(interaction.guild)), view=TicketPanelView(t["cats"], t.get("placeholder")))
    except discord.HTTPException:
        return await interaction.response.send_message(f"❌ No puedo enviar mensajes en {destino.mention}.", ephemeral=True)
    aviso = "" if t["roles"] else "\n⚠️ Aún no configuraste roles de staff en `/configuracion → Tickets`."
    await interaction.response.send_message(f"✅ Panel enviado en {destino.mention}.{aviso}", ephemeral=True)


# ───────────────────────────── /configuracion ────────────────────────────────
SECCIONES = {
    "sugerencias": ("💡", "Sugerencias", "Canal y roles que aprueban"),
    "postulaciones": ("📝", "Postulaciones", "Formularios, embeds y canal"),
    "eventos": ("🎉", "Eventos", "Roles y embed de eventos"),
    "seguridad": ("🛡️", "Seguridad", "Solo el dueño: Anti-Bot, Anti-Raid, Anti-Spam, Whitelist"),
    "moderacion": ("🔨", "Moderación", "Sanciones, casos y registros"),
    "juegos": ("🎮", "Juegos", "Editar embeds de los juegos"),
    "tickets": ("🎫", "Tickets", "Canales privados de soporte"),
    "autoresponder": ("💬", "Auto-Responder", "Respuestas automáticas con embeds"),
    "sorteos": ("🎁", "Sorteos", "Roles y embeds de sorteos"),
    "autoroles": ("🏷️", "Auto-Rol", "Roles automáticos para miembros y bots"),
    "reaccionroles": ("🎭", "Roles por reacción", "Asigna roles mediante reacciones"),
    "autopings": ("🔔", "Mensajes automáticos", "Mensajes repetitivos con activar/desactivar pings"),
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


_ALERTAS_SEG = {}  # (servidor, usuario) -> última vez que se avisó al dueño


async def alertar_intento_seguridad(interaction: discord.Interaction, donde: str):
    """Avisa por MD al dueño cuando alguien que NO es el dueño intenta editar la seguridad."""
    guild, user = interaction.guild, interaction.user
    clave = (guild.id, user.id)
    ahora = time.monotonic()
    if ahora - _ALERTAS_SEG.get(clave, -999.0) < 30:  # evita llenar de MDs al dueño si insiste
        return
    _ALERTAS_SEG[clave] = ahora
    embed = discord.Embed(
        title="🚨 Intento de editar la seguridad",
        description=f"{user.mention} (`{user}` · `{user.id}`) intentó modificar la configuración de seguridad "
        f"de **{guild.name}** y fue bloqueado.",
        color=0xE74C3C,
    )
    embed.add_field(name="Dónde", value=donde, inline=True)
    canal = interaction.channel
    embed.add_field(name="Canal", value=getattr(canal, "mention", "—"), inline=True)
    embed.add_field(name="Cuándo", value=discord.utils.format_dt(discord.utils.utcnow(), "F"), inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="Solo el dueño del servidor puede editar la seguridad.")
    try:
        dueno = guild.owner or await client.fetch_user(guild.owner_id)
        await dueno.send(embed=embed)
    except discord.HTTPException:
        pass  # el dueño tiene los MD cerrados
    try:
        await log_seg(guild, cfg(guild.id)["seg"], "🚨 Intento de editar la seguridad",
                      f"{user.mention} intentó editar **{donde}** y fue bloqueado.")
    except Exception:
        pass


class SoloDuenoView(AdminView):
    """Vista de seguridad: SOLO el dueño del servidor puede usarla. Si otro lo intenta, se avisa al dueño por MD."""
    nombre_panel = "Panel de seguridad"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "🔒 Solo el **dueño del servidor** puede editar la seguridad. Ya le avisé de este intento.", ephemeral=True)
            await alertar_intento_seguridad(interaction, self.nombre_panel)
            return False
        return True



def auto_embed(gid):
    a = cfg(gid)["auto"]
    r = a["respuesta"]
    e = discord.Embed(title="💬 Auto-Responder", color=0x5865F2)
    e.add_field(name="Estado", value=_estado(a["on"]), inline=True)
    e.add_field(name="Canal", value=f"<#{a['canal']}>" if a["canal"] else "Todos los canales", inline=True)
    e.add_field(name="Disparador", value=f"`{a['trigger']}`", inline=False)
    e.add_field(name="Borrar mensaje original", value="Sí" if a.get("borrar_trigger") else "No", inline=True)
    e.add_field(name="Respuesta", value=r.get("titulo") or "Sin título", inline=False)
    return e


class AutoResponderModal(discord.ui.Modal, title="Configurar auto-responder"):
    def __init__(self, gid):
        super().__init__()
        a = cfg(gid)["auto"]
        self.trigger = discord.ui.TextInput(label="Mensaje/disparador", default=a.get("trigger",""), max_length=100)
        self.title = discord.ui.TextInput(label="Título del embed", default=a["respuesta"].get("titulo",""), required=False, max_length=256)
        self.desc = discord.ui.TextInput(label="Descripción del embed", default=a["respuesta"].get("descripcion",""), style=discord.TextStyle.paragraph, max_length=2000)
        self.color = discord.ui.TextInput(label="Color HEX", default=a["respuesta"].get("color","5865F2"), max_length=7)
        self.add_item(self.trigger); self.add_item(self.title); self.add_item(self.desc); self.add_item(self.color)

    async def on_submit(self, interaction: discord.Interaction):
        a = cfg(interaction.guild.id)["auto"]
        color = self.color.value.strip().lstrip("#")
        try:
            int(color, 16)
            if len(color) not in (6, 3): raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ El color debe ser HEX, por ejemplo `5865F2`.", ephemeral=True)
        a["trigger"] = self.trigger.value.strip()
        a["respuesta"].update({"titulo": self.title.value.strip(), "descripcion": self.desc.value, "color": color})
        save()
        await interaction.response.edit_message(embed=auto_embed(interaction.guild.id), view=AutoResponderView())


class AutoResponderView(AdminView):
    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                       placeholder="Canal específico (o deja el actual sin cambiar)", row=0)
    async def canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        cfg(interaction.guild.id)["auto"]["canal"] = select.values[0].id
        save()
        await interaction.response.edit_message(embed=auto_embed(interaction.guild.id), view=AutoResponderView())

    @discord.ui.button(label="⚙️ Editar respuesta", style=discord.ButtonStyle.primary, row=1)
    async def editar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AutoResponderModal(interaction.guild.id))

    @discord.ui.button(label="🟢 Activar / 🔴 Desactivar", style=discord.ButtonStyle.success, row=1)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg(interaction.guild.id)["auto"]["on"] = not cfg(interaction.guild.id)["auto"]["on"]
        save()
        await interaction.response.edit_message(embed=auto_embed(interaction.guild.id), view=AutoResponderView())

    @discord.ui.button(label="🗑️ Borrar mensaje", style=discord.ButtonStyle.secondary, row=1)
    async def borrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        a = cfg(interaction.guild.id)["auto"]
        a["borrar_trigger"] = not a.get("borrar_trigger", False)
        save()
        await interaction.response.edit_message(embed=auto_embed(interaction.guild.id), view=AutoResponderView())

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=2)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=home_embed(), view=HomeView())


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
        if k == "tickets":
            return await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkHomeView())
        if k == "autoresponder":
            return await interaction.response.edit_message(embed=auto_embed(interaction.guild.id), view=AutoResponderView())
        if k == "sorteos":
            return await interaction.response.edit_message(embed=sort_home_embed(interaction.guild.id), view=SortHomeView())
        if k == "autoroles":
            return await interaction.response.edit_message(embed=autoroles_embed(interaction.guild.id), view=AutoRolesView())
        if k == "reaccionroles":
            return await interaction.response.edit_message(embed=reaction_roles_embed(interaction.guild.id), view=ReactionRolesView())
        if k == "autopings":
            return await interaction.response.edit_message(embed=autopings_embed(interaction.guild.id), view=AutoPingsView())
        if k == "juegos":
            return await interaction.response.edit_message(embed=juegos_menu_embed(), view=JuegosMenuView())
        if k == "seguridad":
            if interaction.user.id != interaction.guild.owner_id:
                await interaction.response.send_message(
                    "🔒 Solo el **dueño del servidor** puede editar la seguridad. Ya le avisé de este intento.", ephemeral=True)
                return await alertar_intento_seguridad(interaction, "Menú de configuración → Seguridad")
            return await interaction.response.edit_message(embed=seg_home_embed(interaction.guild.id), view=SegHomeView())
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
    def __init__(self, seccion, key, preview, volver, con_desc=True):
        super().__init__()
        self.seccion, self.key, self.preview, self.volver_fn = seccion, key, preview, volver
        if not con_desc:
            self.remove_item(self.descripcion)

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


SEG_SECCIONES = {
    "antibot": ("🤖", "Anti-Bot", "Banea bots no autorizados y a quien los agrega"),
    "antiraid": ("🚨", "Anti-Raid", "Detecta entradas masivas de cuentas"),
    "antispam": ("💬", "Anti-Spam", "Frena el flood y las menciones masivas"),
    "antichannel": ("📁", "Anti-Channel", "Protege la creación y cambios de canales"),
    "antiroles": ("🎭", "Anti-Roles", "Protege roles y permisos peligrosos"),
    "staff_guard": ("🔐", "Protección Staff", "Aprueba cualquier asignación de roles de staff"),
    "whitelist": ("📃", "White-List", "Usuarios, bots y roles exentos"),
}

SEG_INFO = {
    "antibot": (
        "🤖 Anti-Bot",
        "Cuando está activo, **cualquier bot que entre al servidor** (aunque esté offline, oculto o sea un "
        "«bot fantasma») es **baneado**, y también se banea a **quien lo agregó**.\n\n"
        "**Excepciones:** bots en la White-List y bots agregados por el dueño o por alguien de la White-List.\n\n"
        "⚠️ Necesito los permisos *Banear miembros* y *Ver registro de auditoría* (para saber quién lo agregó). "
        "Mi rol debe estar por encima del de quien agregue el bot.",
    ),
    "antiraid": (
        "🚨 Anti-Raid",
        "Si entran demasiadas cuentas en pocos segundos, aplico la acción elegida a esas cuentas y activo un "
        "**modo raid de 2 minutos**: cada nueva entrada recibe la misma acción.\n\nLa White-List queda exenta.",
    ),
    "antispam": (
        "💬 Anti-Spam",
        "Borra los mensajes de quien manda demasiados en poco tiempo, o menciona a demasiada gente en uno solo, "
        "y lo **aísla (timeout)**.\n\n**Exentos:** administradores, roles de moderación configurados y la White-List.",
    ),
    "antichannel": (
        "📁 Anti-Channel",
        "Protege los canales contra creación, eliminación o cambios no autorizados. El dueño y la White-List quedan exentos.",
    ),
    "antiroles": (
        "🎭 Anti-Roles",
        "Protege la creación, eliminación y modificación de roles. Además bloquea permisos peligrosos en roles no autorizados.",
    ),
    "staff_guard": (
        "🔐 Protección Staff",
        "Los roles marcados como **roles de staff** no se pueden asignar directamente. Nexus retira el rol y pide aprobación al dueño por MD.",
    ),
}


def _estado(on):
    return "🟢 Activado" if on else "🔴 Desactivado"


def seg_home_embed(gid: int):
    s = cfg(gid)["seg"]
    e = discord.Embed(title="🛡️ Configurar seguridad", color=0x5865F2,
                      description="Elige una opción en el menú. Cada una tiene su propio panel.")
    e.add_field(name="🤖 Anti-Bot", value=_estado(s["antibot"]["on"]), inline=True)
    e.add_field(name="🚨 Anti-Raid", value=_estado(s["antiraid"]["on"]), inline=True)
    e.add_field(name="💬 Anti-Spam", value=_estado(s["antispam"]["on"]), inline=True)
    e.add_field(name="📁 Anti-Channel", value=_estado(s["antichannel"]["on"]), inline=True)
    e.add_field(name="🎭 Anti-Roles", value=_estado(s["antiroles"]["on"]), inline=True)
    e.add_field(name="🔐 Protección Staff", value=_estado(s["staff_guard"]["on"]), inline=True)
    e.add_field(name="📃 White-List", value=f"{len(s['wl']['usuarios'])} usuario(s)/bot(s) · {len(s['wl']['roles'])} rol(es)", inline=False)
    e.add_field(name="Canal de registros de seguridad", value=f"<#{s['canal']}>" if s["canal"] else "No configurado", inline=False)
    e.set_footer(text="🔒 Solo el dueño del servidor puede editar esta sección.")
    return e


def seg_panel_embed(gid: int, key: str):
    s = cfg(gid)["seg"]
    a = s[key]
    titulo, desc = SEG_INFO[key]
    e = discord.Embed(title=titulo, description=desc, color=0x2ECC71 if a["on"] else 0xE74C3C)
    e.add_field(name="Estado", value=_estado(a["on"]), inline=False)
    if key == "antiraid":
        e.add_field(name="Umbral", value=f"{a['joins']} entradas en {a['segundos']} s", inline=True)
        e.add_field(name="Acción", value="🔨 Banear" if a["accion"] == "ban" else "👢 Expulsar", inline=True)
    if key == "antispam":
        e.add_field(name="Límite", value=f"{a['mensajes']} mensajes en {a['segundos']} s", inline=True)
        e.add_field(name="Menciones", value=f"máx. {a['menciones']} por mensaje", inline=True)
        e.add_field(name="Aislamiento", value=f"{a['timeout']} min", inline=True)
    if key == "staff_guard":
        roles = " ".join(f"<@&{r}>" for r in a.get("roles", [])) or "Ninguno"
        e.add_field(name="Roles protegidos", value=roles, inline=False)
        e.add_field(name="Advertencias antes de sanción", value=str(a.get("warnings_before_kick", 2)), inline=True)
        e.add_field(name="Sanción final", value=a.get("accion", "kick").upper(), inline=True)
    return e


def wl_embed(guild):
    wl = cfg(guild.id)["seg"]["wl"]
    e = discord.Embed(
        title="📃 White-List", color=0x5865F2,
        description="Los usuarios, bots y roles de esta lista están **exentos** de Anti-Raid y Anti-Spam, "
        "los bots de la lista pueden entrar, y los bots que agreguen son permitidos.\n"
        "Para permitir un bot, agrégalo **antes** de invitarlo (puedes usar su ID).",
    )
    e.add_field(name="Usuarios y bots", value=" ".join(f"<@{u}>" for u in wl["usuarios"]) or "Nadie todavía", inline=False)
    e.add_field(name="Roles", value=" ".join(f"<@&{r}>" for r in wl["roles"]) or "Ninguno", inline=False)
    return e


class RaidAccionSelect(discord.ui.Select):
    def __init__(self, actual: str):
        super().__init__(
            placeholder="Acción contra los raiders",
            options=[
                discord.SelectOption(label="Expulsar (kick)", value="kick", emoji="👢", default=actual == "kick"),
                discord.SelectOption(label="Banear (ban)", value="ban", emoji="🔨", default=actual == "ban"),
            ],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        cfg(interaction.guild.id)["seg"]["antiraid"]["accion"] = self.values[0]
        save()
        await interaction.response.edit_message(
            embed=seg_panel_embed(interaction.guild.id, "antiraid"), view=SegPanelView("antiraid", interaction.guild.id)
        )


class SegAjustesModal(discord.ui.Modal, title="Ajustes"):
    CAMPOS = {
        "antiraid": [("joins", "Entradas para detectar raid (2-50)", 2, 50), ("segundos", "En cuántos segundos (3-120)", 3, 120)],
        "antispam": [
            ("mensajes", "Mensajes permitidos (2-20)", 2, 20),
            ("segundos", "En cuántos segundos (2-30)", 2, 30),
            ("timeout", "Minutos de aislamiento (1-1440)", 1, 1440),
            ("menciones", "Máx. menciones por mensaje (2-50)", 2, 50),
        ],
    }

    def __init__(self, key: str, gid: int):
        super().__init__()
        self.key = key
        a = cfg(gid)["seg"][key]
        self.inputs = {}
        for campo, etiqueta, _, _ in self.CAMPOS[key]:
            ti = discord.ui.TextInput(label=etiqueta, default=str(a[campo]), max_length=5)
            self.inputs[campo] = ti
            self.add_item(ti)

    async def on_submit(self, interaction: discord.Interaction):
        nuevos = {}
        for campo, etiqueta, lo, hi in self.CAMPOS[self.key]:
            try:
                v = int(self.inputs[campo].value)
            except ValueError:
                return await interaction.response.send_message(f"❌ «{etiqueta}» debe ser un número.", ephemeral=True)
            if not lo <= v <= hi:
                return await interaction.response.send_message(f"❌ «{etiqueta}» debe estar entre {lo} y {hi}.", ephemeral=True)
            nuevos[campo] = v
        cfg(interaction.guild.id)["seg"][self.key].update(nuevos)
        save()
        await interaction.response.edit_message(
            embed=seg_panel_embed(interaction.guild.id, self.key), view=SegPanelView(self.key, interaction.guild.id)
        )



class StaffGuardRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(min_values=0, max_values=10,
                         placeholder="Roles de staff que deben pedir aprobación", row=0)
    async def callback(self, interaction: discord.Interaction):
        cfg(interaction.guild.id)["seg"]["staff_guard"]["roles"] = [r.id for r in self.values]
        save()
        await interaction.response.edit_message(
            embed=seg_panel_embed(interaction.guild.id, "staff_guard"),
            view=SegPanelView("staff_guard", interaction.guild.id)
        )


class StaffGuardActionSelect(discord.ui.Select):
    def __init__(self, actual: str):
        super().__init__(
            placeholder="Sanción al superar las advertencias",
            options=[
                discord.SelectOption(label="Kick", value="kick", emoji="👢", default=actual == "kick"),
                discord.SelectOption(label="Ban", value="ban", emoji="🔨", default=actual == "ban"),
            ], row=2)
    async def callback(self, interaction: discord.Interaction):
        cfg(interaction.guild.id)["seg"]["staff_guard"]["accion"] = self.values[0]
        save()
        await interaction.response.edit_message(
            embed=seg_panel_embed(interaction.guild.id, "staff_guard"),
            view=SegPanelView("staff_guard", interaction.guild.id)
        )


class StaffGuardWarningsModal(discord.ui.Modal, title="Advertencias de Protección Staff"):
    def __init__(self, gid):
        super().__init__()
        actual = cfg(gid)["seg"]["staff_guard"].get("warnings_before_kick", 2)
        self.n = discord.ui.TextInput(
            label="Advertencias antes de sancionar", default=str(actual),
            min_length=1, max_length=2, placeholder="Ej: 2"
        )
        self.add_item(self.n)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            n = int(self.n.value)
            if not 1 <= n <= 10:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Escribe un número entre 1 y 10.", ephemeral=True)
        cfg(interaction.guild.id)["seg"]["staff_guard"]["warnings_before_kick"] = n
        save()
        await interaction.response.edit_message(
            embed=seg_panel_embed(interaction.guild.id, "staff_guard"),
            view=SegPanelView("staff_guard", interaction.guild.id)
        )


class SegPanelView(SoloDuenoView):
    def __init__(self, key: str, gid: int):
        super().__init__()
        self.key = key
        self.nombre_panel = f"Seguridad → {SEG_INFO[key][0]}"
        a = cfg(gid)["seg"][key]
        self.toggle.label = "Desactivar" if a["on"] else "Activar"
        self.toggle.style = discord.ButtonStyle.danger if a["on"] else discord.ButtonStyle.success
        if key in ("antibot", "antichannel", "antiroles", "staff_guard"):
            self.remove_item(self.ajustes)
        if key != "staff_guard":
            self.remove_item(self.roles_staff)
            self.remove_item(self.staff_warnings)
        if key == "antiraid":
            self.add_item(RaidAccionSelect(a["accion"]))
        if key == "staff_guard":
            self.add_item(StaffGuardRoleSelect())
            self.add_item(StaffGuardActionSelect(a.get("accion", "kick")))


    @discord.ui.button(label="🎭 Configurar roles staff", style=discord.ButtonStyle.primary, row=1)
    async def roles_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.key != "staff_guard":
            return await interaction.response.send_message("Esta opción solo corresponde a Protección Staff.", ephemeral=True)
        # El RoleSelect añadido arriba maneja la selección; este botón solo informa.
        await interaction.response.send_message("Usa el selector de roles de arriba para marcar los roles protegidos.", ephemeral=True)

    @discord.ui.button(label="⚙️ Advertencias", style=discord.ButtonStyle.secondary, row=1)
    async def staff_warnings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.key != "staff_guard":
            return await interaction.response.send_modal(SegAjustesModal(self.key, interaction.guild.id))
        await interaction.response.send_modal(StaffGuardWarningsModal(interaction.guild.id))

    @discord.ui.button(label="Activar", row=1)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        a = cfg(interaction.guild.id)["seg"][self.key]
        a["on"] = not a["on"]
        save()
        await interaction.response.edit_message(
            embed=seg_panel_embed(interaction.guild.id, self.key), view=SegPanelView(self.key, interaction.guild.id)
        )

    @discord.ui.button(label="⚙️ Ajustes", style=discord.ButtonStyle.primary, row=1)
    async def ajustes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SegAjustesModal(self.key, interaction.guild.id))

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=seg_home_embed(interaction.guild.id), view=SegHomeView())


class WLRemoveSelect(discord.ui.Select):
    def __init__(self, guild):
        wl = cfg(guild.id)["seg"]["wl"]
        opciones = []
        for uid in wl["usuarios"]:
            u = guild.get_member(uid) or client.get_user(uid)
            opciones.append(discord.SelectOption(label=f"👤 {u}"[:100] if u else f"👤 ID {uid}", value=f"u:{uid}"))
        for rid in wl["roles"]:
            r = guild.get_role(rid)
            opciones.append(discord.SelectOption(label=f"🎭 {r.name}"[:100] if r else f"🎭 ID {rid}", value=f"r:{rid}"))
        super().__init__(placeholder="🗑️ Quitar de la White-List", options=opciones[:25], row=2)

    async def callback(self, interaction: discord.Interaction):
        wl = cfg(interaction.guild.id)["seg"]["wl"]
        tipo, _, ident = self.values[0].partition(":")
        lista = wl["usuarios"] if tipo == "u" else wl["roles"]
        if int(ident) in lista:
            lista.remove(int(ident))
        save()
        await interaction.response.edit_message(embed=wl_embed(interaction.guild), view=WLView(interaction.guild))


class WLIdModal(discord.ui.Modal, title="Agregar por ID"):
    def __init__(self):
        super().__init__()
        self.ident = discord.ui.TextInput(label="ID del usuario o bot", min_length=15, max_length=22, placeholder="123456789012345678")
        self.add_item(self.ident)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.ident.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Eso no parece un ID válido.", ephemeral=True)
        wl = cfg(interaction.guild.id)["seg"]["wl"]
        if uid not in wl["usuarios"]:
            wl["usuarios"].append(uid)
            save()
        await interaction.response.edit_message(embed=wl_embed(interaction.guild), view=WLView(interaction.guild))


class WLView(SoloDuenoView):
    nombre_panel = "Seguridad → White-List"

    def __init__(self, guild):
        super().__init__()
        wl = cfg(guild.id)["seg"]["wl"]
        if wl["usuarios"] or wl["roles"]:
            self.add_item(WLRemoveSelect(guild))

    @discord.ui.select(cls=discord.ui.UserSelect, min_values=1, max_values=10,
                       placeholder="➕ Agregar usuarios / bots", row=0)
    async def agregar_usuarios(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        wl = cfg(interaction.guild.id)["seg"]["wl"]
        for u in select.values:
            if u.id not in wl["usuarios"]:
                wl["usuarios"].append(u.id)
        save()
        await interaction.response.edit_message(embed=wl_embed(interaction.guild), view=WLView(interaction.guild))

    @discord.ui.select(cls=discord.ui.RoleSelect, min_values=1, max_values=10,
                       placeholder="➕ Agregar roles", row=1)
    async def agregar_roles(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        wl = cfg(interaction.guild.id)["seg"]["wl"]
        for r in select.values:
            if r.id not in wl["roles"]:
                wl["roles"].append(r.id)
        save()
        await interaction.response.edit_message(embed=wl_embed(interaction.guild), view=WLView(interaction.guild))

    @discord.ui.button(label="➕ Agregar por ID", style=discord.ButtonStyle.primary, row=3)
    async def por_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WLIdModal())

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=3)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=seg_home_embed(interaction.guild.id), view=SegHomeView())


class SegHomeView(SoloDuenoView):
    nombre_panel = "Seguridad (menú principal)"

    @discord.ui.select(
        placeholder="¿Qué quieres configurar?",
        options=[discord.SelectOption(label=n, value=k, emoji=e, description=d) for k, (e, n, d) in SEG_SECCIONES.items()],
        row=0,
    )
    async def elegir(self, interaction: discord.Interaction, select: discord.ui.Select):
        k = select.values[0]
        if k == "whitelist":
            return await interaction.response.edit_message(embed=wl_embed(interaction.guild), view=WLView(interaction.guild))
        await interaction.response.edit_message(
            embed=seg_panel_embed(interaction.guild.id, k), view=SegPanelView(k, interaction.guild.id)
        )

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                       placeholder="Canal de registros de seguridad", row=1)
    async def canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        cfg(interaction.guild.id)["seg"]["canal"] = select.values[0].id
        save()
        await interaction.response.edit_message(embed=seg_home_embed(interaction.guild.id), view=SegHomeView())

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=2)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=home_embed(), view=HomeView())


JUEGOS_EMBED_NOMBRES = {
    "ppt": "Piedra, papel o tijera",
    "dado": "Dado",
    "tres_raya": "Tres en raya",
    "adivina": "Adivina la palabra",
    "numero": "Adivina el número",
    "desordenada": "Palabra desordenada",
    "reflejos": "Duelo de reflejos",
    "trivia": "Trivia",
    "bola8": "Bola 8 mágica",
    "conecta4": "Conecta 4",
    "blackjack": "Blackjack",
    "slots": "Tragamonedas",
}


def juegos_menu_embed():
    return discord.Embed(
        title="🎮 Embeds de los juegos",
        description="Elige el juego cuyo embed quieres editar:\n\n" + "\n".join(f"• **{v}**" for v in JUEGOS_EMBED_NOMBRES.values())
        + "\n\nPuedes cambiar título, autor, color, pie de página y las imágenes. "
        "En el título del dado puedes usar `{caras}` y en el de adivina la palabra, la palabra desordenada y la trivia, `{tema}`.",
        color=0x5865F2,
    )


def juego_embed_panel(guild, user_id: int, key: str):
    info = discord.Embed(
        title=f"🎨 Editando: {JUEGOS_EMBED_NOMBRES[key]}",
        description="Abajo ves la vista previa en vivo. El contenido de cada partida cambia solo.",
        color=0x5865F2,
    )
    base = discord.Embed(title="(título)", description="Aquí va el contenido de la partida.", color=0x5865F2)
    return [info, estilo_juego(guild.id, key, base, {"{caras}": "6", "{tema}": "Anime"})]


async def volver_juegos_menu(interaction: discord.Interaction):
    await interaction.response.edit_message(embed=juegos_menu_embed(), view=JuegosMenuView())


class JuegosMenuView(AdminView):
    @discord.ui.select(
        placeholder="¿Qué juego quieres editar?",
        options=[discord.SelectOption(label=v, value=k, emoji="🎮") for k, v in JUEGOS_EMBED_NOMBRES.items()],
        row=0,
    )
    async def elegir(self, interaction: discord.Interaction, select: discord.ui.Select):
        key = select.values[0]
        view = StyleEditView("juegos", key, juego_embed_panel, volver_juegos_menu, con_desc=False)
        await interaction.response.edit_message(embeds=juego_embed_panel(interaction.guild, interaction.user.id, key), view=view)

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=home_embed(), view=HomeView())


# ───────────────────────── Config: Sorteos ─────────────────────────
SORT_EMBED_NOMBRES = {"sorteo": "Embed del sorteo (activo)", "final": "Embed del sorteo finalizado"}


def sort_home_embed(gid: int):
    s = cfg(gid)["sort"]
    e = discord.Embed(title="🎁 Configurar sorteos", color=0x5865F2)
    e.add_field(name="Roles que pueden crear sorteos",
                value=" ".join(f"<@&{r}>" for r in s["roles"]) or "Solo administradores", inline=False)
    e.add_field(name="Sorteos activos", value=str(sum(1 for r in s["items"].values() if r["estado"] == "activo")), inline=True)
    e.add_field(name="Sorteos realizados", value=str(len(s["items"])), inline=True)
    e.set_footer(text="Comandos: /sorteo crear · /sorteo finalizar · /sorteo reroll")
    return e


def sort_embeds_menu_embed():
    return discord.Embed(
        title="🎨 Embeds de sorteos",
        description="Elige cuál quieres editar:\n\n" + "\n".join(f"• **{v}**" for v in SORT_EMBED_NOMBRES.values()),
        color=0x5865F2,
    )


def sort_embed_panel(guild, user_id: int, key: str):
    s = cfg(guild.id)["sort"]
    info = discord.Embed(
        title=f"🎨 Editando: {SORT_EMBED_NOMBRES[key]}",
        description="Variables: " + ", ".join(f"`{k}`" for k in SORT_VARIABLES) + "\n\nAbajo ves la vista previa en vivo.",
        color=0x5865F2,
    )
    rec = {"premio": "Nitro Classic", "ganadores": 1, "fin": int(time.time()) + 3600, "anfitrion": user_id,
           "participantes": [user_id], "requisito": None}
    return [info, post_embed(s["embeds"][key], sort_vars(guild, rec, f"<@{user_id}>"))]


async def volver_sort_menu(interaction: discord.Interaction):
    await interaction.response.edit_message(embed=sort_embeds_menu_embed(), view=SortEmbedsMenuView())


class SortEmbedsMenuView(AdminView):
    @discord.ui.select(
        placeholder="¿Qué embed quieres editar?",
        options=[discord.SelectOption(label=v, value=k) for k, v in SORT_EMBED_NOMBRES.items()],
        row=0,
    )
    async def elegir(self, interaction: discord.Interaction, select: discord.ui.Select):
        key = select.values[0]
        view = StyleEditView("sort", key, sort_embed_panel, volver_sort_menu)
        await interaction.response.edit_message(embeds=sort_embed_panel(interaction.guild, interaction.user.id, key), view=view)

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=sort_home_embed(interaction.guild.id), view=SortHomeView())


class SortHomeView(AdminView):
    @discord.ui.select(cls=discord.ui.RoleSelect, min_values=0, max_values=10,
                       placeholder="Roles que pueden crear sorteos", row=0)
    async def roles(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        cfg(interaction.guild.id)["sort"]["roles"] = [r.id for r in select.values]
        save()
        await interaction.response.edit_message(embed=sort_home_embed(interaction.guild.id), view=SortHomeView())

    @discord.ui.button(label="🎨 Embeds", style=discord.ButtonStyle.primary, row=1)
    async def embeds(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=sort_embeds_menu_embed(), view=SortEmbedsMenuView())

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=home_embed(), view=HomeView())


# ───────────────────────── Config: Tickets ─────────────────────────
TK_EMBED_NOMBRES = {
    "panel": "Panel (menú de categorías)",
    "ticket": "Mensaje dentro del ticket",
    "cierre": "Registro de cierre (canal y MD)",
    "reclamacion": "Aviso cuando un staff reclama el ticket",
}


def tk_home_embed(gid: int):
    t = cfg(gid)["tk"]
    e = discord.Embed(title="🎫 Configurar tickets", color=0x5865F2)
    e.add_field(name="Categoría de Discord para los canales", value=f"<#{t['categoria']}>" if t["categoria"] else "Sin categoría (se crean sueltos)", inline=False)
    e.add_field(name="Canal de registros / transcripciones", value=f"<#{t['canal']}>" if t["canal"] else "No configurado", inline=False)
    e.add_field(name="Canal de valoraciones", value=f"<#{t['canal_valoraciones']}>" if t.get("canal_valoraciones") else "No configurado", inline=False)
    e.add_field(name="Roles de staff generales (si la categoría no tiene propios)", value=" ".join(f"<@&{r}>" for r in t["roles"]) or "Solo administradores", inline=False)
    e.add_field(name="Texto del menú desplegable", value=t.get("placeholder") or TK_PLACEHOLDER_DEFECTO, inline=False)
    e.add_field(name="Roles que pueden enviar el panel (/ticket-panel)", value=" ".join(f"<@&{r}>" for r in t.get("panel_roles", [])) or "Solo administradores", inline=False)
    e.add_field(name="Tickets abiertos por usuario", value=f"máx. {t['max']}", inline=True)
    e.add_field(name="Tickets abiertos ahora", value=str(len(t["abiertos"])), inline=True)
    e.add_field(name="Categorías del menú", value=", ".join(c["nombre"] for c in t["cats"]), inline=False)
    e.set_footer(text="En 📋 Categorías cada una tiene sus roles, ping y bienvenida. Texto del menú, máximo y roles del panel están en ⚙️ Más ajustes.")
    return e


def tk_cats_embed(gid: int):
    t = cfg(gid)["tk"]
    e = discord.Embed(title="📋 Categorías de tickets", color=0x5865F2)
    for c in t["cats"]:
        e.add_field(name=c["nombre"], value=c.get("desc") or "—", inline=False)
    e.set_footer(text="Elige una para configurar sus roles, ping y bienvenida. Tras cambiar categorías, reenvía el panel con /ticket-panel. Máximo 10.")
    return e


def tk_embeds_menu_embed():
    return discord.Embed(
        title="🎨 Embeds de tickets",
        description="Elige cuál quieres editar:\n\n" + "\n".join(f"• **{v}**" for v in TK_EMBED_NOMBRES.values()),
        color=0x5865F2,
    )


def tk_embed_panel(guild, user_id: int, key: str):
    t = cfg(guild.id)["tk"]
    info = discord.Embed(
        title="🎨 Editando: " + (f"Bienvenida de «{key[4:]}»" if key.startswith("cat:") else TK_EMBED_NOMBRES[key]),
        description="Variables: " + ", ".join(f"`{k}`" for k in TK_VARIABLES) + "\n\nAbajo ves la vista previa en vivo.",
        color=0x5865F2,
    )
    rec = {"numero": 1, "usuario": user_id, "categoria": key[4:] if key.startswith("cat:") else t["cats"][0]["nombre"]}
    return [info, post_embed(t["embeds"][key], tk_vars(guild, rec, staff=f"<@{user_id}>"))]


async def volver_tk_menu(interaction: discord.Interaction):
    await interaction.response.edit_message(embed=tk_embeds_menu_embed(), view=TkEmbedsMenuView())


class TkEmbedsMenuView(AdminView):
    @discord.ui.select(
        placeholder="¿Qué embed quieres editar?",
        options=[discord.SelectOption(label=v, value=k) for k, v in TK_EMBED_NOMBRES.items()],
        row=0,
    )
    async def elegir(self, interaction: discord.Interaction, select: discord.ui.Select):
        key = select.values[0]
        view = StyleEditView("tk", key, tk_embed_panel, volver_tk_menu)
        await interaction.response.edit_message(embeds=tk_embed_panel(interaction.guild, interaction.user.id, key), view=view)

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkHomeView())


def _cat_tk(t, nombre: str):
    return next((c for c in t["cats"] if c["nombre"][:100] == (nombre or "")[:100]), None)


def tk_cat_embed(gid: int, nombre: str):
    t = cfg(gid)["tk"]
    c = _cat_tk(t, nombre) or {"nombre": nombre}
    e = discord.Embed(title=f"⚙️ Categoría: {c['nombre']}", color=0x5865F2)
    e.add_field(name="Descripción", value=c.get("desc") or "—", inline=False)
    e.add_field(name="Nombre del canal", value=f"`{c.get('nombre_canal', 'ticket-{numero}')}`", inline=False)
    generales = " ".join(f"<@&{r}>" for r in t["roles"]) or "solo administradores"
    e.add_field(
        name="Roles que atienden esta categoría",
        value=" ".join(f"<@&{r}>" for r in c.get("roles", [])) or f"Los roles de staff generales ({generales})",
        inline=False,
    )
    e.add_field(
        name="Ping al abrir un ticket",
        value=" ".join(f"<@&{r}>" for r in c.get("ping", [])) or "Los mismos roles que la atienden",
        inline=False,
    )
    e.add_field(
        name="Mensaje de bienvenida",
        value="🎨 Personalizado para esta categoría" if f"cat:{c['nombre']}" in t["embeds"] else "Usa el embed general «Ticket abierto»",
        inline=False,
    )
    e.set_footer(text="Solo esos roles (y los administradores) verán y podrán atender los tickets de esta categoría.")
    return e


async def volver_tk_cat(interaction: discord.Interaction, nombre: str):
    await interaction.response.edit_message(embeds=[tk_cat_embed(interaction.guild.id, nombre)], view=TkCatConfigView(nombre))


class TkCatNameModal(discord.ui.Modal, title="Nombre del canal del ticket"):
    def __init__(self, nombre: str, gid: int):
        super().__init__()
        self.nombre = nombre
        c = _cat_tk(cfg(gid)["tk"], nombre) or {}
        self.plantilla = discord.ui.TextInput(
            label="Plantilla del canal",
            default=c.get("nombre_canal") or "ticket-{numero}",
            max_length=95,
            placeholder="Ej: alianza-{numero} o soporte-{numero}"
        )
        self.add_item(self.plantilla)

    async def on_submit(self, interaction: discord.Interaction):
        c = _cat_tk(cfg(interaction.guild.id)["tk"], self.nombre)
        if c is None:
            return await interaction.response.send_message("❌ Esa categoría ya no existe.", ephemeral=True)
        valor = self.plantilla.value.strip()
        if not valor:
            valor = "ticket-{numero}"
        c["nombre_canal"] = valor
        save()
        await interaction.response.edit_message(
            embeds=[tk_cat_embed(interaction.guild.id, self.nombre)],
            view=TkCatConfigView(self.nombre)
        )


class TkCatDescModal(discord.ui.Modal, title="Descripción de la categoría"):
    def __init__(self, nombre: str, gid: int):
        super().__init__()
        self.nombre = nombre
        c = _cat_tk(cfg(gid)["tk"], nombre) or {}
        self.desc = discord.ui.TextInput(label="Descripción (se ve en el menú)", default=c.get("desc") or "", required=False, max_length=100)
        self.add_item(self.desc)

    async def on_submit(self, interaction: discord.Interaction):
        c = _cat_tk(cfg(interaction.guild.id)["tk"], self.nombre)
        if c is None:
            return await interaction.response.send_message("❌ Esa categoría ya no existe.", ephemeral=True)
        c["desc"] = self.desc.value.strip()
        save()
        await interaction.response.edit_message(embeds=[tk_cat_embed(interaction.guild.id, self.nombre)], view=TkCatConfigView(self.nombre))


class TkCatConfigView(AdminView):
    def __init__(self, nombre: str):
        super().__init__()
        self.nombre = nombre

    async def _refrescar(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embeds=[tk_cat_embed(interaction.guild.id, self.nombre)], view=TkCatConfigView(self.nombre))

    @discord.ui.select(cls=discord.ui.RoleSelect, min_values=0, max_values=10,
                       placeholder="Roles que atienden esta categoría", row=0)
    async def roles(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        c = _cat_tk(cfg(interaction.guild.id)["tk"], self.nombre)
        if c is None:
            return await interaction.response.send_message("❌ Esa categoría ya no existe.", ephemeral=True)
        c["roles"] = [r.id for r in select.values]
        save()
        await self._refrescar(interaction)

    @discord.ui.select(cls=discord.ui.RoleSelect, min_values=0, max_values=10,
                       placeholder="Roles a mencionar (ping) al abrir un ticket", row=1)
    async def ping(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        c = _cat_tk(cfg(interaction.guild.id)["tk"], self.nombre)
        if c is None:
            return await interaction.response.send_message("❌ Esa categoría ya no existe.", ephemeral=True)
        c["ping"] = [r.id for r in select.values]
        save()
        await self._refrescar(interaction)

    @discord.ui.button(label="🎨 Mensaje de bienvenida", style=discord.ButtonStyle.primary, row=2)
    async def bienvenida(self, interaction: discord.Interaction, button: discord.ui.Button):
        t = cfg(interaction.guild.id)["tk"]
        key = f"cat:{self.nombre}"
        if key not in t["embeds"]:
            t["embeds"][key] = dict(t["embeds"]["ticket"])  # parte del embed general
            save()
        view = StyleEditView("tk", key, tk_embed_panel, lambda i, n=self.nombre: volver_tk_cat(i, n))
        await interaction.response.edit_message(embeds=tk_embed_panel(interaction.guild, interaction.user.id, key), view=view)

    @discord.ui.button(label="↩️ Usar la bienvenida general", style=discord.ButtonStyle.secondary, row=2)
    async def general(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg(interaction.guild.id)["tk"]["embeds"].pop(f"cat:{self.nombre}", None)
        save()
        await self._refrescar(interaction)

    @discord.ui.button(label="🔤 Nombre del canal", style=discord.ButtonStyle.primary, row=3)
    async def nombre_canal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TkCatNameModal(self.nombre, interaction.guild.id))

    @discord.ui.button(label="✏️ Descripción", style=discord.ButtonStyle.secondary, row=3)
    async def descripcion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TkCatDescModal(self.nombre, interaction.guild.id))

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=3)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=tk_cats_embed(interaction.guild.id), view=TkCatsView(interaction.guild.id))


class TkCatPickSelect(discord.ui.Select):
    def __init__(self, cats):
        super().__init__(
            placeholder="⚙️ Configurar una categoría (roles, ping y bienvenida)",
            options=[discord.SelectOption(label=c["nombre"][:100], value=c["nombre"][:100]) for c in cats], row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        nombre = self.values[0]
        await interaction.response.edit_message(embeds=[tk_cat_embed(interaction.guild.id, nombre)], view=TkCatConfigView(nombre))


class TkPlaceholderModal(discord.ui.Modal, title="Texto del menú desplegable"):
    def __init__(self, gid: int):
        super().__init__()
        actual = cfg(gid)["tk"].get("placeholder") or TK_PLACEHOLDER_DEFECTO
        self.texto = discord.ui.TextInput(label="Texto que se ve en el menú del panel", default=actual, max_length=150)
        self.add_item(self.texto)

    async def on_submit(self, interaction: discord.Interaction):
        cfg(interaction.guild.id)["tk"]["placeholder"] = self.texto.value.strip() or TK_PLACEHOLDER_DEFECTO
        save()
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkHomeView())
        await interaction.followup.send("✅ Guardado. Vuelve a enviar el panel con `/ticket-panel` para ver el cambio.", ephemeral=True)


class TkCatModal(discord.ui.Modal, title="Agregar categoría"):
    def __init__(self):
        super().__init__()
        self.nombre = discord.ui.TextInput(label="Nombre de la categoría", max_length=50, placeholder="Ej: Reportes")
        self.desc = discord.ui.TextInput(label="Descripción (opcional)", required=False, max_length=100)
        self.add_item(self.nombre)
        self.add_item(self.desc)

    async def on_submit(self, interaction: discord.Interaction):
        t = cfg(interaction.guild.id)["tk"]
        nombre = self.nombre.value.strip()
        existente = next((c for c in t["cats"] if c["nombre"].lower() == nombre.lower()), None)
        if existente:
            existente["desc"] = self.desc.value.strip()
        elif len(t["cats"]) >= 10:
            return await interaction.response.send_message("❌ Máximo 10 categorías.", ephemeral=True)
        else:
            t["cats"].append({"nombre": nombre, "desc": self.desc.value.strip(), "roles": [], "ping": [], "nombre_canal": "ticket-{numero}"})
        save()
        await interaction.response.edit_message(embed=tk_cats_embed(interaction.guild.id), view=TkCatsView(interaction.guild.id))


class TkCatDelSelect(discord.ui.Select):
    def __init__(self, cats):
        super().__init__(placeholder="🗑️ Eliminar una categoría",
                         options=[discord.SelectOption(label=c["nombre"][:100], value=c["nombre"][:100]) for c in cats], row=0)

    async def callback(self, interaction: discord.Interaction):
        t = cfg(interaction.guild.id)["tk"]
        if len(t["cats"]) <= 1:
            return await interaction.response.send_message("❌ Debe quedar al menos una categoría.", ephemeral=True)
        t["cats"] = [c for c in t["cats"] if c["nombre"][:100] != self.values[0]]
        t["embeds"].pop(f"cat:{self.values[0]}", None)
        save()
        await interaction.response.edit_message(embed=tk_cats_embed(interaction.guild.id), view=TkCatsView(interaction.guild.id))


class TkCatsView(AdminView):
    def __init__(self, gid: int):
        super().__init__()
        self.add_item(TkCatDelSelect(cfg(gid)["tk"]["cats"][:25]))
        self.add_item(TkCatPickSelect(cfg(gid)["tk"]["cats"][:25]))

    @discord.ui.button(label="➕ Agregar categoría", style=discord.ButtonStyle.success, row=2)
    async def agregar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TkCatModal())

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=2)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkHomeView())


class TkMaxModal(discord.ui.Modal, title="Tickets por usuario"):
    def __init__(self, gid: int):
        super().__init__()
        self.valor = discord.ui.TextInput(label="Máx. tickets abiertos por usuario (1-5)", default=str(cfg(gid)["tk"]["max"]), max_length=1)
        self.add_item(self.valor)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            v = int(self.valor.value)
            if not 1 <= v <= 5:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Escribe un número del 1 al 5.", ephemeral=True)
        cfg(interaction.guild.id)["tk"]["max"] = v
        save()
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkHomeView())


class TkAjustesView(AdminView):
    """Ajustes extra de tickets (separados para no pasar el límite de 5 filas de Discord)."""

    @discord.ui.select(cls=discord.ui.RoleSelect, min_values=0, max_values=10,
                       placeholder="Roles que pueden enviar el panel (/ticket-panel)", row=0)
    async def roles_panel(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        cfg(interaction.guild.id)["tk"]["panel_roles"] = [r.id for r in select.values]
        save()
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkAjustesView())

    @discord.ui.button(label="⚙️ Máx. por usuario", style=discord.ButtonStyle.secondary, row=1)
    async def maximo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TkMaxModal(interaction.guild.id))

    @discord.ui.button(label="🔤 Texto del menú", style=discord.ButtonStyle.secondary, row=1)
    async def texto_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TkPlaceholderModal(interaction.guild.id))

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=1)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkHomeView())


class TkHomeView(AdminView):
    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.category],
                       placeholder="Categoría de Discord donde se crean los tickets", row=0)
    async def categoria(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        cfg(interaction.guild.id)["tk"]["categoria"] = select.values[0].id
        save()
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkHomeView())

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                       placeholder="Canal de registros / transcripciones", row=1)
    async def canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        cfg(interaction.guild.id)["tk"]["canal"] = select.values[0].id
        save()
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkHomeView())

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
                       placeholder="Canal donde se enviarán las valoraciones", row=2)
    async def canal_valoraciones(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        cfg(interaction.guild.id)["tk"]["canal_valoraciones"] = select.values[0].id
        save()
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkHomeView())

    @discord.ui.select(cls=discord.ui.RoleSelect, min_values=0, max_values=10,
                       placeholder="Roles de staff que atienden tickets", row=3)
    async def roles(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        cfg(interaction.guild.id)["tk"]["roles"] = [r.id for r in select.values]
        save()
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkHomeView())

    @discord.ui.button(label="📋 Categorías", style=discord.ButtonStyle.primary, row=4)
    async def cats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=tk_cats_embed(interaction.guild.id), view=TkCatsView(interaction.guild.id))

    @discord.ui.button(label="🎨 Embeds", style=discord.ButtonStyle.primary, row=4)
    async def embeds(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=tk_embeds_menu_embed(), view=TkEmbedsMenuView())

    @discord.ui.button(label="⚙️ Más ajustes", style=discord.ButtonStyle.secondary, row=4)
    async def ajustes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=tk_home_embed(interaction.guild.id), view=TkAjustesView())

    @discord.ui.button(label="⬅ Volver", style=discord.ButtonStyle.secondary, row=4)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=home_embed(), view=HomeView())


# ───────────────────────────── Auto-Rol / Roles por reacción / Mensajes automáticos ─────────────────────────────
def autoroles_embed(gid):
    a=cfg(gid)["autoroles"]
    e=discord.Embed(title="🏷️ Auto-Rol",description="Entrega automáticamente roles al entrar un miembro o bot.",color=0x5865F2)
    e.add_field(name="Estado",value=_estado(a.get("on",False)),inline=True)
    e.add_field(name="Miembros",value=" ".join(f"<@&{r}>" for r in a.get("miembros",[])) or "Ninguno",inline=False)
    e.add_field(name="Bots",value=" ".join(f"<@&{r}>" for r in a.get("bots",[])) or "Ninguno",inline=False)
    return e

class AutoRolesView(AdminView):
    @discord.ui.select(cls=discord.ui.RoleSelect,min_values=0,max_values=10,placeholder="Roles automáticos para miembros",row=0)
    async def miembros(self,interaction,select):
        cfg(interaction.guild.id)["autoroles"]["miembros"]=[r.id for r in select.values]; save()
        await interaction.response.edit_message(embed=autoroles_embed(interaction.guild.id),view=AutoRolesView())
    @discord.ui.select(cls=discord.ui.RoleSelect,min_values=0,max_values=10,placeholder="Roles automáticos para bots",row=1)
    async def bots(self,interaction,select):
        cfg(interaction.guild.id)["autoroles"]["bots"]=[r.id for r in select.values]; save()
        await interaction.response.edit_message(embed=autoroles_embed(interaction.guild.id),view=AutoRolesView())
    @discord.ui.button(label="🟢 Activar / 🔴 Desactivar",style=discord.ButtonStyle.success,row=2)
    async def toggle(self,interaction,button):
        cfg(interaction.guild.id)["autoroles"]["on"]=not cfg(interaction.guild.id)["autoroles"].get("on",False); save()
        await interaction.response.edit_message(embed=autoroles_embed(interaction.guild.id),view=AutoRolesView())
    @discord.ui.button(label="⬅ Volver",style=discord.ButtonStyle.secondary,row=2)
    async def volver(self,interaction,button): await interaction.response.edit_message(embed=home_embed(),view=HomeView())

def reaction_roles_embed(gid):
    a=cfg(gid)["reaccion_roles"]
    e=discord.Embed(title="🎭 Roles por reacción",description="Configura mensajes existentes para que sus reacciones den o quiten roles.",color=0x5865F2)
    e.add_field(name="Estado",value=_estado(a.get("on",False)),inline=True)
    total=sum(len(x.get("roles",{})) for x in a.get("mensajes",{}).values())
    e.add_field(name="Configuraciones",value=f"{len(a.get('mensajes',{}))} mensaje(s) · {total} reacción(es)",inline=True)
    for mid,item in list(a.get("mensajes",{}).items())[:8]:
        pairs=" ".join(f"{emo} → <@&{rid}>" for emo,rid in item.get("roles",{}).items())
        e.add_field(name=f"Mensaje {mid}",value=f"Canal: <#{item.get('canal')}>\n{pairs or 'Sin roles'}",inline=False)
    return e

class ReactionRoleModal(discord.ui.Modal,title="Agregar rol por reacción"):
    canal=discord.ui.TextInput(label="ID del canal",placeholder="123456789012345678")
    mensaje=discord.ui.TextInput(label="ID del mensaje",placeholder="123456789012345678")
    emoji=discord.ui.TextInput(label="Emoji",placeholder="👍")
    rol=discord.ui.TextInput(label="ID del rol",placeholder="123456789012345678")
    async def on_submit(self,interaction):
        try: cid=int(self.canal.value); mid=int(self.mensaje.value); rid=int(self.rol.value)
        except ValueError: return await interaction.response.send_message("❌ Los IDs deben ser números.",ephemeral=True)
        if not interaction.guild.get_role(rid): return await interaction.response.send_message("❌ No encuentro ese rol.",ephemeral=True)
        try:
            ch=interaction.guild.get_channel(cid); msg=await ch.fetch_message(mid) if ch else None
            if not msg: raise ValueError
            await msg.add_reaction(self.emoji.value.strip())
        except Exception:
            return await interaction.response.send_message("❌ No pude encontrar el canal/mensaje o agregar la reacción.",ephemeral=True)
        rr=cfg(interaction.guild.id)["reaccion_roles"]["mensajes"].setdefault(str(mid),{"canal":cid,"roles":{}})
        rr["canal"]=cid; rr["roles"][self.emoji.value.strip()]=rid; save()
        await interaction.response.edit_message(embed=reaction_roles_embed(interaction.guild.id),view=ReactionRolesView())

class ReactionRolesView(AdminView):
    @discord.ui.button(label="➕ Agregar reacción → rol",style=discord.ButtonStyle.primary,row=0)
    async def agregar(self,interaction,button): await interaction.response.send_modal(ReactionRoleModal())
    @discord.ui.button(label="🟢 Activar / 🔴 Desactivar",style=discord.ButtonStyle.success,row=0)
    async def toggle(self,interaction,button):
        cfg(interaction.guild.id)["reaccion_roles"]["on"]=not cfg(interaction.guild.id)["reaccion_roles"].get("on",False); save()
        await interaction.response.edit_message(embed=reaction_roles_embed(interaction.guild.id),view=ReactionRolesView())
    @discord.ui.button(label="⬅ Volver",style=discord.ButtonStyle.secondary,row=1)
    async def volver(self,interaction,button): await interaction.response.edit_message(embed=home_embed(),view=HomeView())

def autopings_embed(gid):
    a=cfg(gid)["autopings"]
    e=discord.Embed(title="🔔 Mensajes automáticos",description="Crea mensajes que se envían cada cierta cantidad de mensajes, con botones para activar o desactivar un rol de ping.",color=0x5865F2)
    e.add_field(name="Estado",value=_estado(a.get("on",False)),inline=True)
    for key,item in list(a.get("items",{}).items())[:8]:
        estado="🟢" if item.get("on") else "🔴"; borrar="Sí" if item.get("delete_previous") else "No"
        e.add_field(name=f"{estado} {item.get('nombre',key)}",value=f"Canal: <#{item.get('canal')}>\nCada **{item.get('cada',2)}** mensajes · Rol de ping: <@&{item.get('rol')}>\nBorrar anterior: **{borrar}**",inline=False)
    return e

class AutoPingMessageView(discord.ui.View):
    def __init__(self,key):
        super().__init__(timeout=None)
        self.key=key
        self.add_item(discord.ui.Button(label="Activar",emoji="🔔",style=discord.ButtonStyle.success,custom_id=f"autoping:{key}:on"))
        self.add_item(discord.ui.Button(label="Desactivar",emoji="🔕",style=discord.ButtonStyle.secondary,custom_id=f"autoping:{key}:off"))
    async def interaction_check(self,interaction):
        if not interaction.guild: return False
        parts=interaction.data.get("custom_id","").split(":")
        item=cfg(interaction.guild.id)["autopings"]["items"].get(self.key)
        if not item: return False
        role=interaction.guild.get_role(item.get("rol"))
        if not role: return False
        accion=parts[-1]
        try:
            if accion=="on": await interaction.user.add_roles(role,reason="[Nexus] Activar ping")
            else: await interaction.user.remove_roles(role,reason="[Nexus] Desactivar ping")
            await interaction.response.send_message(f"{'🔔 Ping activado' if accion=='on' else '🔕 Ping desactivado'}.",ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("❌ No pude modificar tu rol.",ephemeral=True)
        return False

class AutoPingModal(discord.ui.Modal,title="Nuevo mensaje automático"):
    nombre=discord.ui.TextInput(label="Nombre",placeholder="Ej: Aviso general")
    canal=discord.ui.TextInput(label="ID del canal",placeholder="123456789012345678")
    rol=discord.ui.TextInput(label="ID del rol de ping",placeholder="123456789012345678")
    cada=discord.ui.TextInput(label="Cada cuántos mensajes",default="2",placeholder="2")
    texto=discord.ui.TextInput(label="Mensaje",style=discord.TextStyle.paragraph,placeholder="︶︶ Para activar/desactivar este ping usa los botones de abajo ☙☙")
    async def on_submit(self,interaction):
        try: cid=int(self.canal.value); rid=int(self.rol.value); cada=max(1,int(self.cada.value))
        except ValueError: return await interaction.response.send_message("❌ Canal, rol y cantidad deben ser válidos.",ephemeral=True)
        if not interaction.guild.get_channel(cid) or not interaction.guild.get_role(rid): return await interaction.response.send_message("❌ No encuentro el canal o rol.",ephemeral=True)
        import uuid
        key=str(uuid.uuid4())[:8]
        cfg(interaction.guild.id)["autopings"]["items"][key]={"nombre":self.nombre.value[:80],"canal":cid,"rol":rid,"cada":cada,"texto":self.texto.value,"on":True,"count":0,"last_message":None,"delete_previous":False}
        save(); await interaction.response.edit_message(embed=autopings_embed(interaction.guild.id),view=AutoPingsView())

class AutoPingDeleteModal(discord.ui.Modal,title="Eliminar mensaje automático"):
    nombre=discord.ui.TextInput(label="ID del mensaje automático")
    async def on_submit(self,interaction):
        cfg(interaction.guild.id)["autopings"]["items"].pop(self.nombre.value.strip(),None); save()
        await interaction.response.edit_message(embed=autopings_embed(interaction.guild.id),view=AutoPingsView())

class AutoPingDeletePreviousModal(discord.ui.Modal, title="Borrar mensaje anterior"):
    ident=discord.ui.TextInput(label="ID del mensaje automático",placeholder="Ej: a1b2c3d4")
    async def on_submit(self,interaction):
        item=cfg(interaction.guild.id)["autopings"]["items"].get(self.ident.value.strip())
        if not item:
            return await interaction.response.send_message("❌ No existe ese mensaje automático.",ephemeral=True)
        item["delete_previous"]=not item.get("delete_previous",False); save()
        estado="activado" if item["delete_previous"] else "desactivado"
        await interaction.response.send_message(f"✅ Borrar el mensaje anterior: **{estado}**.",ephemeral=True)

class AutoPingsView(AdminView):
    @discord.ui.button(label="➕ Crear mensaje",style=discord.ButtonStyle.primary,row=0)
    async def crear(self,interaction,button): await interaction.response.send_modal(AutoPingModal())
    @discord.ui.button(label="🗑️ Eliminar mensaje",style=discord.ButtonStyle.danger,row=0)
    async def eliminar(self,interaction,button): await interaction.response.send_modal(AutoPingDeleteModal())
    @discord.ui.button(label="🧹 Borrar mensaje anterior",style=discord.ButtonStyle.secondary,row=1)
    async def borrar(self,interaction,button):
        await interaction.response.send_modal(AutoPingDeletePreviousModal())
    @discord.ui.button(label="🟢 Activar / 🔴 Desactivar",style=discord.ButtonStyle.success,row=1)
    async def toggle(self,interaction,button):
        cfg(interaction.guild.id)["autopings"]["on"]=not cfg(interaction.guild.id)["autopings"].get("on",False); save()
        await interaction.response.edit_message(embed=autopings_embed(interaction.guild.id),view=AutoPingsView())
    @discord.ui.button(label="⬅ Volver",style=discord.ButtonStyle.secondary,row=2)
    async def volver(self,interaction,button): await interaction.response.edit_message(embed=home_embed(),view=HomeView())

async def procesar_autopings(m):
    a=cfg(m.guild.id)["autopings"]
    if not a.get("on"): return
    changed=False
    for key,item in a.get("items",{}).items():
        if not item.get("on") or item.get("canal")!=m.channel.id: continue
        item["count"]=int(item.get("count",0))+1
        if item["count"] % max(1,int(item.get("cada",2))) != 0: continue
        ch=m.channel
        if item.get("delete_previous") and item.get("last_message"):
            try: old=await ch.fetch_message(item["last_message"]); await old.delete()
            except (discord.NotFound,discord.HTTPException): pass
        try:
            role=ch.guild.get_role(item.get("rol"))
            texto=item.get("texto","")
            sent=await ch.send((role.mention if role else "")+"\n"+texto,view=AutoPingMessageView(key),allowed_mentions=discord.AllowedMentions(roles=True,users=False,everyone=False))
            item["last_message"]=sent.id; changed=True
        except discord.HTTPException: pass
    if changed: save()

@client.event
async def on_member_join(member: discord.Member):
    a=cfg(member.guild.id)["autoroles"]
    if not a.get("on"): return
    ids=a.get("bots" if member.bot else "miembros",[])
    for rid in ids:
        role=member.guild.get_role(rid)
        if role and member.guild.me.top_role > role:
            try: await member.add_roles(role,reason="[Nexus] Auto-Rol")
            except discord.HTTPException: pass

@client.event
async def on_raw_reaction_add(payload):
    if not payload.guild_id or payload.user_id==client.user.id: return
    rr=cfg(payload.guild_id)["reaccion_roles"]
    if not rr.get("on"): return
    item=rr.get("mensajes",{}).get(str(payload.message_id));
    if not item: return
    rid=item.get("roles",{}).get(str(payload.emoji)); guild=client.get_guild(payload.guild_id); member=guild.get_member(payload.user_id) if guild else None; role=guild.get_role(rid) if guild else None
    if member and role and guild.me.top_role>role:
        try: await member.add_roles(role,reason="[Nexus] Rol por reacción")
        except discord.HTTPException: pass

@client.event
async def on_raw_reaction_remove(payload):
    if not payload.guild_id or payload.user_id==client.user.id: return
    rr=cfg(payload.guild_id)["reaccion_roles"]
    if not rr.get("on"): return
    item=rr.get("mensajes",{}).get(str(payload.message_id));
    if not item: return
    rid=item.get("roles",{}).get(str(payload.emoji)); guild=client.get_guild(payload.guild_id); member=guild.get_member(payload.user_id) if guild else None; role=guild.get_role(rid) if guild else None
    if member and role:
        try: await member.remove_roles(role,reason="[Nexus] Rol por reacción")
        except discord.HTTPException: pass

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
        name="💬 Auto-Responder",
        value="En `/configuracion → Auto-Responder` puedes definir un disparador, canal y respuesta en embed.",
        inline=False,
    )
    embed.add_field(name="🤖 Próxima fase", value="El sistema de **chat con IA** se agregará en la próxima fase.", inline=False)
    embed.add_field(
        name="💡 Sugerencias",
        value="En `/configuracion → Sugerencias` elige el canal y los roles que aprueban. "
        "Cada mensaje en ese canal se vuelve un embed con botones Aprobar/Rechazar.",
        inline=False,
    )
    embed.add_field(
        name="🎮 Juegos",
        value="`/ppt @usuario` — piedra, papel o tijera (ambos eligen en secreto)\n`/dado [caras]` — dado de 2 a 16 caras\n`/tres-en-raya @usuario` — tres en raya para 2 jugadores\n`/adivina-la-palabra` — 2 a 4 jugadores con temática (Anime, Historia o Videojuegos)\n`/trivia [preguntas]` — Anime, Historia o Videojuegos (100 preguntas por tema, con imagen)\n`/adivina-el-numero` · `/palabra-desordenada` · `/reflejos @usuario`\n`/bola8 pregunta` · `/conecta4 @usuario` · `/blackjack` · `/tragamonedas`",
        inline=False,
    )
    embed.add_field(
        name="💤 AFK",
        value="`/afk [razón]` o `nexus afk [razón]` — agrega **[AFK]** a tu apodo y avisa (con tu motivo) a quien te mencione. "
        "Se quita solo cuando vuelves a escribir.",
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
    embed.add_field(
        name="🛡️ Seguridad",
        value="Se configura en `/configuracion → Seguridad`: **Anti-Bot** (banea al bot y a quien lo agregó), "
        "**Anti-Raid**, **Anti-Spam** y **White-List**. Cada uno tiene su propio panel.",
        inline=False,
    )
    embed.add_field(
        name="🎫 Tickets",
        value="En `/configuracion → Tickets` editas el texto del menú, los embeds y las categorías: **cada categoría** tiene sus propios "
        "roles que la atienden, ping y mensaje de bienvenida. Envía el panel con `/ticket-panel`. "
        "Cada ticket es un canal privado con botones para reclamar, agregar/quitar personas y cerrar (se guarda la transcripción).",
        inline=False,
    )
    embed.add_field(
        name="🎁 Sorteos",
        value="`/sorteo crear` (premio, duración, ganadores, requisito) · `/sorteo finalizar` · `/sorteo reroll`\n"
        "Roles y embeds en `/configuracion → Sorteos`.",
        inline=False,
    )
    p = cfg(interaction.guild_id)["prefijo"] if interaction.guild_id else "!"
    embed.add_field(
        name="⌨️ Prefijos (todos los comandos también con texto)",
        value=f"Escribe `{p}comando`, `nexus comando` o `@Nexus comando`. Ejemplos: `{p}dado 12` · `nexus trivia` · `nexus ayuda`\n"
        f"`{p}ayuda lista` muestra todos los comandos y `{p}ayuda <comando>` cómo se usa. "
        f"Un admin cambia el prefijo con `/prefijo` (ahora: `{p}`).",
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ───────────────────────── Prefijos: comandos con texto ──────────────────────
# Todos los comandos / también funcionan con texto:  !dado 12 · nexus trivia · @Nexus ayuda
#  · Prefijo del servidor (por defecto «!», cambia con /prefijo)
#  · La palabra «nexus»  →  «nexus ayuda»
#  · Mencionar al bot    →  «@Nexus ayuda»
# Nota: por texto no existen los mensajes privados (ephemeral): las respuestas privadas se borran solas.
class PrefijoError(Exception):
    def __init__(self, mensaje: str, uso: bool = True):
        super().__init__(mensaje)
        self.mensaje, self.uso = mensaje, uso


ALIAS_PREFIJO = {
    "config": "configuracion", "configurar": "configuracion", "panel": "configuracion",
    "tresenraya": "tres-en-raya", "3enraya": "tres-en-raya", "gato": "tres-en-raya", "ttt": "tres-en-raya",
    "numero": "adivina-el-numero", "adivinanumero": "adivina-el-numero",
    "palabra": "adivina-la-palabra", "ahorcado": "adivina-la-palabra",
    "desordenada": "palabra-desordenada", "rps": "ppt", "dice": "dado",
    "sugerir": "sugerencias", "sugerencia": "sugerencias", "postular": "postulacion",
    "estado": "postulacion-estado", "banear": "ban", "expulsar": "kick", "advertir": "warn",
    "silenciar": "mute", "aislar": "mute", "desilenciar": "unmute", "prefix": "prefijo",
    "ausente": "afk", "8ball": "bola8", "bola": "bola8", "conecta": "conecta4", "c4": "conecta4",
    "21": "blackjack", "bj": "blackjack", "slots": "tragamonedas", "tragaperras": "tragamonedas",
}
AYUDA_PREFIJO = {"ayuda", "help", "comandos"}
_MAPA_PFX = {}
_COOLDOWN_PFX = {}
_TOKEN_RE = re.compile(r'"([^"]*)"|“([^”]*)”|(\S+)')


def _clave(t: str) -> str:
    return norm(t).replace("-", "").replace("_", "")


def _mapa_prefijo():
    """Construye (una sola vez) el mapa  nombre/alias → comando  con todos los comandos slash."""
    if _MAPA_PFX:
        return _MAPA_PFX
    for c in tree.walk_commands():
        if isinstance(c, app_commands.Command):
            _MAPA_PFX[" ".join(_clave(w) for w in c.qualified_name.split())] = c
    for alias, destino in ALIAS_PREFIJO.items():
        c = _MAPA_PFX.get(" ".join(_clave(w) for w in destino.split()))
        if c is not None:
            _MAPA_PFX.setdefault(_clave(alias), c)
    return _MAPA_PFX


def _tokenizar(texto: str):
    out = []
    for mt in _TOKEN_RE.finditer(texto):
        valor = next(g for g in mt.groups() if g is not None)
        out.append((valor, mt.start(), mt.end()))
    return out


def _resolver_comando(toks):
    """→ (tipo, comando_o_grupo, tokens_usados). tipo: 'ayuda' | 'cmd' | 'grupo' | None"""
    if not toks:
        return None, None, 0
    mapa = _mapa_prefijo()
    a = _clave(toks[0][0])
    if a in AYUDA_PREFIJO:
        return "ayuda", None, 1
    if len(toks) > 1:
        c = mapa.get(f"{a} {_clave(toks[1][0])}")
        if c is not None:
            return "cmd", c, 2
    c = mapa.get(a)
    if c is not None:
        return "cmd", c, 1
    for g in tree.get_commands():
        if isinstance(g, app_commands.Group) and _clave(g.name) == a:
            return "grupo", g, 1
    return None, None, 0


def _uso(cmd, pref: str) -> str:
    partes = []
    for prm in cmd.parameters:
        nombre = ("📎" if prm.type is discord.AppCommandOptionType.attachment else "") + prm.display_name
        partes.append(f"<{nombre}>" if prm.required else f"[{nombre}]")
    return f"{pref}{cmd.qualified_name} " + " ".join(partes)


def _desenvolver(anot):
    """Quita Optional[...] de una anotación."""
    if typing.get_origin(anot) is typing.Union:
        resto = [a for a in typing.get_args(anot) if a is not type(None)]
        if len(resto) == 1:
            return resto[0]
    return anot


async def _opciones_autocompletar(cmd, prm, shim):
    """Opciones del autocompletado de un parámetro (eventos, sorteos, formularios...)."""
    try:
        cb = getattr(cmd, "_parameter_autocomplete", {}).get(prm.name)
        if cb is None:
            cand = getattr(getattr(cmd, "_params", {}).get(prm.name), "autocomplete", None)
            cb = cand if callable(cand) else None
        if cb is None:
            return []
        return list(await cb(shim, "")) or []
    except Exception:
        return []


def _texto_opciones(opciones) -> str:
    if not opciones:
        return ""
    return "\nOpciones: " + " · ".join(f"`{o.value}` ({o.name})" if str(o.value) != o.name else f"`{o.value}`" for o in opciones[:10])


async def _conv_usuario(v, guild, necesita_miembro: bool):
    mt = re.fullmatch(r"<@!?(\d+)>|(\d{15,22})", v)
    if not mt:
        bajo = v.lstrip("@").lower()
        cand = [mb for mb in guild.members if bajo in (mb.name.lower(), mb.display_name.lower())]
        if len(cand) == 1:
            return cand[0]
        raise PrefijoError(f"No encuentro a «{v}». Menciónalo o usa su ID.")
    uid = int(mt.group(1) or mt.group(2))
    miembro = guild.get_member(uid)
    if miembro is None:
        try:
            miembro = await guild.fetch_member(uid)
        except discord.HTTPException:
            miembro = None
    if miembro is not None:
        return miembro
    if necesita_miembro:
        raise PrefijoError("Esa persona no está en el servidor.")
    try:
        return await client.fetch_user(uid)
    except discord.HTTPException:
        raise PrefijoError("No encontré a ese usuario.")


def _conv_canal(v, guild, anot):
    mt = re.fullmatch(r"<#(\d+)>|(\d{15,22})", v)
    canal = guild.get_channel(int(mt.group(1) or mt.group(2))) if mt else discord.utils.find(
        lambda c: c.name.lower() == v.lstrip("#").lower(), guild.channels)
    if canal is None:
        raise PrefijoError(f"No encuentro el canal «{v}». Menciónalo con #canal.")
    if isinstance(anot, type) and issubclass(anot, discord.abc.GuildChannel) and not isinstance(canal, anot):
        raise PrefijoError(f"{canal.mention} no es un canal del tipo correcto.")
    return canal


def _conv_rol(v, guild):
    mt = re.fullmatch(r"<@&(\d+)>|(\d{15,22})", v)
    rol = guild.get_role(int(mt.group(1) or mt.group(2))) if mt else discord.utils.find(
        lambda r: r.name.lower() == v.lstrip("@").lower(), guild.roles)
    if rol is None:
        raise PrefijoError(f"No encuentro el rol «{v}». Menciónalo con @rol.")
    return rol


def _conv_opcion(v, prm, es_choice: bool):
    nv = norm(v)
    dur = parse_duracion(v) if all(isinstance(c.value, int) for c in prm.choices) else None
    for c in prm.choices:
        if nv == norm(c.name) or v == str(c.value) or (dur is not None and dur == c.value):
            return c if es_choice else c.value
    for c in prm.choices:
        if norm(c.name).startswith(nv):
            return c if es_choice else c.value
    raise PrefijoError(f"«{v}» no es una opción válida.\nOpciones: " + " · ".join(f"`{c.name}`" for c in prm.choices))


async def _convertir(v, prm, anot, guild, cmd, shim):
    base = _desenvolver(anot)
    es_choice = typing.get_origin(base) is app_commands.Choice or base is app_commands.Choice
    T = discord.AppCommandOptionType
    if prm.choices:
        return _conv_opcion(v, prm, es_choice)
    if prm.type is T.user:
        return await _conv_usuario(v, guild, base is discord.Member)
    if prm.type is T.channel:
        return _conv_canal(v, guild, base)
    if prm.type is T.role:
        return _conv_rol(v, guild)
    if prm.type is T.mentionable:
        mt = re.fullmatch(r"<@&(\d+)>", v)
        return _conv_rol(v, guild) if mt else await _conv_usuario(v, guild, False)
    if prm.type in (T.integer, T.number):
        try:
            n = int(v) if prm.type is T.integer else float(v.replace(",", "."))
        except ValueError:
            raise PrefijoError(f"**{prm.display_name}** debe ser un número.")
        if prm.min_value is not None and n < prm.min_value or prm.max_value is not None and n > prm.max_value:
            raise PrefijoError(f"**{prm.display_name}** debe estar entre {prm.min_value} y {prm.max_value}.")
        return n
    if prm.type is T.boolean:
        if norm(v) in ("si", "true", "yes", "1", "on", "activar"):
            return True
        if norm(v) in ("no", "false", "0", "off", "desactivar"):
            return False
        raise PrefijoError(f"**{prm.display_name}** debe ser «sí» o «no».")
    # texto
    if prm.min_value is not None and len(v) < prm.min_value or prm.max_value is not None and len(v) > prm.max_value:
        raise PrefijoError(f"**{prm.display_name}** debe tener entre {prm.min_value} y {prm.max_value} caracteres.")
    if prm.autocomplete:  # eventos, sorteos, formularios...
        opciones = await _opciones_autocompletar(cmd, prm, shim)
        if opciones:
            nv = norm(v.lstrip("#"))
            for o in opciones:
                if v == str(o.value) or nv == norm(str(o.value)) or nv == norm(o.name):
                    return o.value
            for o in opciones:
                if nv and nv in norm(o.name):
                    return o.value
            raise PrefijoError(f"No encuentro «{v}» en **{prm.display_name}**." + _texto_opciones(opciones))
    return v


async def _enlazar(cmd, toks, resto: str, msg: discord.Message, shim):
    """Convierte los argumentos escritos en los parámetros del comando slash."""
    firma = inspect.signature(cmd.callback).parameters
    params = list(cmd.parameters)
    T = discord.AppCommandOptionType
    adjuntos = list(msg.attachments)
    sin_adj = [p for p in params if p.type is not T.attachment]
    ultimo = sin_adj[-1].name if sin_adj else None
    kwargs, pos = {}, 0
    for prm in params:
        anot = firma[prm.name].annotation if prm.name in firma else None
        if prm.type is T.attachment:
            if adjuntos:
                kwargs[prm.name] = adjuntos.pop(0)
            elif prm.required:
                raise PrefijoError(f"Adjunta la imagen en el **mismo mensaje** (**{prm.display_name}**).")
            continue
        if pos >= len(toks):
            if prm.required:
                extra = _texto_opciones(await _opciones_autocompletar(cmd, prm, shim)) if prm.autocomplete else ""
                raise PrefijoError(f"Falta **{prm.display_name}**." + extra)
            continue
        if prm.type is T.string and prm.name == ultimo and not prm.choices and not prm.autocomplete:
            valor = resto[toks[pos][1]:].strip()  # el último texto toma todo lo que falta
            if len(valor) > 1 and valor[0] == valor[-1] == '"':
                valor = valor[1:-1]
            pos = len(toks)
        else:
            valor = toks[pos][0]
            pos += 1
        if valor in ("-", "_") and not prm.required:  # «-» para saltar un opcional
            continue
        kwargs[prm.name] = await _convertir(valor, prm, anot, msg.guild, cmd, shim)
    return kwargs


async def _permisos_prefijo(cmd, m: discord.Message, shim):
    obj = cmd
    while obj is not None:  # permisos por defecto del comando (y de su grupo)
        dp = getattr(obj, "default_permissions", None)
        if dp is not None and not m.author.guild_permissions.is_superset(dp):
            raise PrefijoError("No tienes permisos para usar este comando.", uso=False)
        obj = getattr(obj, "parent", None)
    for chk in getattr(cmd, "checks", []):
        r = chk(shim)
        if inspect.isawaitable(r):
            r = await r
        if not r:
            raise PrefijoError("No puedes usar este comando.", uso=False)


class _RespuestaPrefijo:
    def __init__(self, inter):
        self._i = inter
        self._hecho = False

    def is_done(self) -> bool:
        return self._hecho

    async def send_message(self, content=None, **kw):
        self._hecho = True
        await self._i._enviar(content, **kw)

    async def defer(self, **kw):
        self._hecho = True

    async def send_modal(self, modal):
        raise PrefijoError("Esa acción abre un formulario emergente y solo funciona con el comando `/` (slash).", uso=False)

    async def edit_message(self, **kw):
        raise PrefijoError("Esa acción solo funciona con botones o con el comando `/` (slash).", uso=False)


class _SeguimientoPrefijo:
    def __init__(self, inter):
        self._i = inter

    async def send(self, content=None, **kw):
        return await self._i._enviar(content, **kw)


class InteraccionPrefijo:
    """Imita a discord.Interaction para reutilizar los comandos slash cuando se escriben con prefijo."""

    def __init__(self, msg: discord.Message, cmd, persistente: bool = False):
        self._msg = msg
        self._ultimo = None
        self.persistente = persistente
        self.command = cmd
        self.client = client
        self.user = msg.author
        self.guild = msg.guild
        self.guild_id = msg.guild.id
        self.channel = msg.channel
        self.channel_id = msg.channel.id
        self.id = msg.id
        self.created_at = msg.created_at
        self.message = None
        self.data = {}
        self.permissions = msg.channel.permissions_for(msg.author)
        self.app_permissions = msg.channel.permissions_for(msg.guild.me)
        self.response = _RespuestaPrefijo(self)
        self.followup = _SeguimientoPrefijo(self)

    async def _enviar(self, content=None, **kw):
        efimero = kw.pop("ephemeral", False)
        args = {}
        for k in ("embed", "embeds", "view", "file", "files", "allowed_mentions", "silent", "suppress_embeds", "delete_after"):
            v = kw.get(k)
            if v is not None and v is not discord.utils.MISSING:
                args[k] = v
        if content is not None and content is not discord.utils.MISSING:
            args["content"] = content
        if efimero and not self.persistente and "delete_after" not in args:
            args["delete_after"] = 600 if "view" in args else 90  # sin mensajes privados: se borra solo
        try:
            msg = await self._msg.reply(mention_author=False, **args)
        except discord.HTTPException:
            msg = await self._msg.channel.send(**args)
        self._ultimo = msg
        return msg

    async def original_response(self):
        if self._ultimo is None:
            raise RuntimeError("Aún no hay respuesta")
        return self._ultimo

    async def edit_original_response(self, **kw):
        self._ultimo = await self._ultimo.edit(**kw)
        return self._ultimo

    async def delete_original_response(self):
        if self._ultimo is not None:
            await self._ultimo.delete()

    def is_expired(self) -> bool:
        return False


def _embed_uso(cmd, pref: str) -> discord.Embed:
    e = discord.Embed(title=f"⌨️ {pref}{cmd.qualified_name}", description=cmd.description, color=0x5865F2)
    e.add_field(name="Uso", value=f"`{_uso(cmd, pref)}`", inline=False)
    detalles = []
    for prm in cmd.parameters:
        marca = "obligatorio" if prm.required else "opcional"
        detalles.append(f"• **{prm.display_name}** ({marca}) — {prm.description or '—'}")
    if detalles:
        e.add_field(name="Parámetros", value="\n".join(detalles)[:1024], inline=False)
    e.set_footer(text='Textos con espacios entre comillas · "-" salta un opcional · imágenes adjuntas en el mismo mensaje')
    return e


async def _prefijo_ayuda(m: discord.Message, pref: str, toks):
    if not toks:
        shim = InteraccionPrefijo(m, help_cmd, persistente=True)
        return await help_cmd.callback(shim)
    primero = _clave(toks[0][0])
    if primero in ("lista", "todos", "todo", "comandos"):
        cmds = sorted({id(c): c for c in _mapa_prefijo().values()}.values(), key=lambda c: c.qualified_name)
        for i in range(0, len(cmds), 12):
            lineas = [f"`{_uso(c, pref)}`\n└ {c.description[:70]}" for c in cmds[i:i + 12]]
            e = discord.Embed(title="⌨️ Comandos con prefijo" + (f" ({i // 12 + 1})" if len(cmds) > 12 else ""),
                              description="\n".join(lineas), color=0x5865F2)
            if i == 0:
                e.set_footer(text=f"{pref}ayuda <comando> te explica cada parámetro")
            await (m.reply(embed=e, mention_author=False) if i == 0 else m.channel.send(embed=e))
        return
    tipo, cmd, _ = _resolver_comando(toks)
    if tipo == "cmd":
        return await m.reply(embed=_embed_uso(cmd, pref), mention_author=False)
    if tipo == "grupo":
        subs = [c for c in cmd.commands]
        e = discord.Embed(title=f"⌨️ {pref}{cmd.name}", description=cmd.description, color=0x5865F2)
        e.add_field(name="Subcomandos", value="\n".join(f"`{_uso(c, pref)}`" for c in subs)[:1024], inline=False)
        return await m.reply(embed=e, mention_author=False)
    await m.reply(f"❌ No conozco ese comando. Usa `{pref}ayuda lista` para ver todos.", mention_author=False, delete_after=20)


async def manejar_prefijo(m: discord.Message) -> bool:
    """Ejecuta un comando escrito con prefijo. Devuelve True si el mensaje era un comando."""
    texto = m.content
    if not texto:
        return False
    pref = cfg(m.guild.id)["prefijo"]
    bajo, uid = texto.lower(), client.user.id
    resto = None
    for p in (pref, "nexus ", f"<@{uid}> ", f"<@!{uid}> "):
        if (texto.startswith(p) if p == pref else bajo.startswith(p)):
            resto = texto[len(p):].strip()
            break
    if not resto:
        return False
    toks = _tokenizar(resto)
    tipo, cmd, usados = _resolver_comando(toks)
    if tipo is None:
        return False  # no era un comando: se ignora en silencio

    ahora = time.monotonic()
    if ahora - _COOLDOWN_PFX.get(m.author.id, 0) < 1.5:
        return True
    _COOLDOWN_PFX[m.author.id] = ahora

    try:
        if tipo == "ayuda":
            await _prefijo_ayuda(m, pref, toks[usados:])
        elif tipo == "grupo":
            e = discord.Embed(title=f"⌨️ {pref}{cmd.name}", description=cmd.description, color=0x5865F2)
            e.add_field(name="Subcomandos", value="\n".join(f"`{_uso(c, pref)}`" for c in cmd.commands)[:1024], inline=False)
            await m.reply(embed=e, mention_author=False)
        else:
            shim = InteraccionPrefijo(m, cmd)
            await _permisos_prefijo(cmd, m, shim)
            kwargs = await _enlazar(cmd, toks[usados:], resto, m, shim)
            await cmd.callback(shim, **kwargs)
    except PrefijoError as e:
        texto_err = f"❌ {e.mensaje}" + (f"\n**Uso:** `{_uso(cmd, pref)}`" if e.uso and cmd is not None else "")
        await m.reply(texto_err, mention_author=False, delete_after=40)
    except app_commands.CheckFailure as e:
        await m.reply(f"❌ {e}" if str(e) else "❌ No puedes usar este comando.", mention_author=False, delete_after=20)
    except Exception:
        traceback.print_exc()
        await m.reply("❌ Ocurrió un error al ejecutar el comando.", mention_author=False, delete_after=20)
    return True


@tree.command(name="prefijo", description="Cambia el prefijo para usar los comandos con texto (por defecto !)")
@app_commands.describe(nuevo="Nuevo prefijo (1 a 5 caracteres, sin espacios). Ej: ! . $ n!")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def prefijo_cmd(interaction: discord.Interaction, nuevo: app_commands.Range[str, 1, 5]):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
    if any(c.isspace() for c in nuevo) or nuevo.startswith("<@") or nuevo.startswith("@"):
        return await interaction.response.send_message("❌ El prefijo no puede tener espacios ni empezar con una mención.", ephemeral=True)
    cfg(interaction.guild_id)["prefijo"] = nuevo
    save()
    embed = discord.Embed(
        title="⌨️ Prefijo actualizado",
        description=f"Ahora los comandos con texto empiezan con `{nuevo}` (ej: `{nuevo}dado 12`, `{nuevo}ayuda`).\n"
        "También siguen funcionando `nexus ayuda` y `@Nexus ayuda`.",
        color=0x2ECC71,
    )
    await interaction.response.send_message(embed=embed)


# ─────────────────────────────────── AFK ─────────────────────────────────────
AFK_SUFIJO = " [AFK]"


def _hace(segundos: int) -> str:
    m = max(1, int(segundos) // 60)
    if m < 60:
        return f"{m} min"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h} h {m} min" if m else f"{h} h"
    d, h = divmod(h, 24)
    return f"{d} d {h} h" if h else f"{d} d"


def _apodo_afk(miembro: discord.Member) -> str:
    base = miembro.nick or miembro.display_name
    if base.endswith(AFK_SUFIJO):
        return base
    return base[: 32 - len(AFK_SUFIJO)] + AFK_SUFIJO


async def poner_afk(miembro: discord.Member, razon) -> bool:
    """Marca como AFK y agrega « [AFK]» al apodo. Devuelve True si pudo cambiar el apodo."""
    afk = cfg(miembro.guild.id)["afk"]
    previo = afk.get(str(miembro.id))
    original = previo["nick"] if previo else miembro.nick
    cambiado = bool(previo and previo.get("cambiado"))
    me = miembro.guild.me
    if me.guild_permissions.manage_nicknames and miembro.id != miembro.guild.owner_id and miembro.top_role < me.top_role:
        try:
            await miembro.edit(nick=_apodo_afk(miembro), reason="[Nexus] Estado AFK")
            cambiado = True
        except discord.HTTPException:
            pass
    afk[str(miembro.id)] = {"razon": razon, "desde": int(time.time()), "nick": original, "cambiado": cambiado}
    save()
    return cambiado


async def quitar_afk(miembro: discord.Member):
    """Quita el estado AFK y restaura el apodo. Devuelve el registro anterior (o None)."""
    rec = cfg(miembro.guild.id)["afk"].pop(str(miembro.id), None)
    if rec is None:
        return None
    save()
    if rec.get("cambiado") and miembro.nick and miembro.nick.endswith(AFK_SUFIJO):
        try:
            await miembro.edit(nick=rec.get("nick"), reason="[Nexus] Ya no está AFK")
        except discord.HTTPException:
            pass
    return rec


async def manejar_afk(m: discord.Message):
    afk = cfg(m.guild.id)["afk"]
    if not afk:
        return
    # 1) quien estaba AFK vuelve al escribir
    rec = afk.get(str(m.author.id))
    if rec and time.time() - rec["desde"] > 3:
        await quitar_afk(m.author)
        try:
            await m.channel.send(
                f"👋 ¡Bienvenido de vuelta {m.author.mention}! Quité tu estado AFK (estuviste ausente {_hace(time.time() - rec['desde'])}).",
                delete_after=10, allowed_mentions=discord.AllowedMentions(users=[m.author]),
            )
        except discord.HTTPException:
            pass
    # 2) mencionan a alguien que está AFK
    lineas = []
    for u in m.mentions:
        if u.id == m.author.id or u.bot:
            continue
        r = afk.get(str(u.id))
        if r:
            linea = f"💤 **{u.display_name}** está AFK desde <t:{r['desde']}:R>"
            if r.get("razon"):
                linea += f"\n└ **Motivo:** {r['razon']}"
            lineas.append(linea)
    if lineas:
        e = discord.Embed(title="💤 Usuario AFK", description="\n\n".join(lineas[:5]), color=0x95A5A6)
        try:
            await m.reply(embed=e, mention_author=False, delete_after=45, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            pass


@tree.command(name="afk", description="Te marca como AFK: agrega [AFK] a tu apodo y avisa cuando te mencionen")
@app_commands.describe(razon="Motivo de tu ausencia (opcional)")
@app_commands.guild_only()
async def afk_cmd(interaction: discord.Interaction, razon: Optional[app_commands.Range[str, 1, 100]] = None):
    cambiado = await poner_afk(interaction.user, razon)
    desc = f"{interaction.user.mention}, te marqué como AFK" + (f" — **{razon}**" if razon else "") + \
        ".\nVolverás a estar activo en cuanto escribas un mensaje."
    e = discord.Embed(title="💤 Ahora estás AFK", description=desc, color=0x95A5A6)
    if not cambiado:
        e.set_footer(text="No pude cambiar tu apodo (me faltan permisos o tu rol está por encima del mío).")
    await interaction.response.send_message(embed=e, allowed_mentions=discord.AllowedMentions.none())


# ─────────────────────────────── Juegos nuevos ───────────────────────────────
# 🎱 Bola 8
BOLA8_SI = ["Es cierto.", "Es decididamente así.", "Sin duda alguna.", "Sí, definitivamente.", "Puedes confiar en ello.",
            "Tal como lo veo, sí.", "Lo más probable.", "Las perspectivas son buenas.", "Sí.", "Todo apunta a que sí."]
BOLA8_QUIZAS = ["Respuesta confusa, vuelve a intentarlo.", "Pregunta de nuevo más tarde.", "Mejor no decírtelo ahora.",
                "No puedo predecirlo ahora.", "Concéntrate y vuelve a preguntar."]
BOLA8_NO = ["No cuentes con ello.", "Mi respuesta es no.", "Mis fuentes dicen que no.",
            "Las perspectivas no son tan buenas.", "Muy dudoso."]


@tree.command(name="bola8", description="Hazle una pregunta a la bola 8 mágica 🎱")
@app_commands.describe(pregunta="Tu pregunta (de sí o no)")
@app_commands.guild_only()
async def bola8_cmd(interaction: discord.Interaction, pregunta: app_commands.Range[str, 3, 200]):
    gid = interaction.guild_id
    agitando = discord.Embed(title="🎱 Bola 8 mágica", description="🎱 *Agitando la bola...*", color=0x2C3E50)
    agitando.add_field(name="❓ Pregunta", value=pregunta, inline=False)
    await interaction.response.send_message(embed=estilo_juego(gid, "bola8", agitando), allowed_mentions=discord.AllowedMentions.none())
    await asyncio.sleep(1.8)
    tipo = random.choices(["si", "quizas", "no"], weights=[10, 5, 5])[0]
    resp, color = {"si": (BOLA8_SI, 0x2ECC71), "quizas": (BOLA8_QUIZAS, 0xF1C40F), "no": (BOLA8_NO, 0xE74C3C)}[tipo]
    e = discord.Embed(title="🎱 Bola 8 mágica", color=color)
    e.add_field(name="❓ Pregunta", value=pregunta, inline=False)
    e.add_field(name="🎱 Respuesta", value=f"**{random.choice(resp)}**", inline=False)
    e.set_footer(text=f"Preguntó {interaction.user.display_name}")
    await interaction.edit_original_response(embed=estilo_juego(gid, "bola8", e))


# 🔴🟡 Conecta 4
C4_FICHAS = {0: "🔴", 1: "🟡"}


class C4Btn(discord.ui.Button):
    def __init__(self, col: int):
        super().__init__(label=str(col + 1), style=discord.ButtonStyle.secondary, row=0 if col < 4 else 1)
        self.col = col

    async def callback(self, interaction: discord.Interaction):
        await self.view.jugar(interaction, self)


class Conecta4View(discord.ui.View):
    def __init__(self, a: discord.abc.User, b: discord.abc.User, gid=None):
        super().__init__(timeout=180)
        self.gid = gid
        self.jugadores = [a.id, b.id]  # el primero es 🔴, el segundo 🟡
        self.turno = 0
        self.tablero = [[None] * 7 for _ in range(6)]  # [fila][columna]; la fila 0 es la de arriba
        self.message = None
        for c in range(7):
            self.add_item(C4Btn(c))

    def embed(self, final: str = None):
        a, b = self.jugadores
        filas = "\n".join("".join(C4_FICHAS[x] if x is not None else "⚫" for x in fila) for fila in self.tablero)
        desc = f"🔴 <@{a}>   vs   🟡 <@{b}>\n\n1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣\n{filas}\n\n"
        desc += final or f"Turno de <@{self.jugadores[self.turno]}> {C4_FICHAS[self.turno]}"
        return estilo_juego(self.gid, "conecta4", discord.Embed(
            title="🔴🟡 Conecta 4", description=desc, color=0xE74C3C if not final else 0x2ECC71))

    def _gana(self, f: int, c: int, ficha: int) -> bool:
        for df, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            n = 1
            for s in (1, -1):
                ff, cc = f + df * s, c + dc * s
                while 0 <= ff < 6 and 0 <= cc < 7 and self.tablero[ff][cc] == ficha:
                    n += 1
                    ff += df * s
                    cc += dc * s
            if n >= 4:
                return True
        return False

    async def jugar(self, interaction: discord.Interaction, boton: C4Btn):
        if interaction.user.id not in self.jugadores:
            return await interaction.response.send_message("No participas en esta partida.", ephemeral=True)
        if interaction.user.id != self.jugadores[self.turno]:
            return await interaction.response.send_message("⏳ Aún no es tu turno.", ephemeral=True)
        fila = next((f for f in range(5, -1, -1) if self.tablero[f][boton.col] is None), None)
        if fila is None:
            return await interaction.response.send_message("Esa columna está llena.", ephemeral=True)
        self.tablero[fila][boton.col] = self.turno

        final = None
        if self._gana(fila, boton.col, self.turno):
            final = f"🏆 **¡Gana <@{interaction.user.id}>!** {C4_FICHAS[self.turno]}"
        elif all(self.tablero[0][c] is not None for c in range(7)):
            final = "🤝 **¡Empate!**"
        if final:
            for c in self.children:
                c.disabled = True
            self.stop()
        else:
            self.turno = 1 - self.turno
            for c in self.children:
                c.disabled = self.tablero[0][c.col] is not None
        await interaction.response.edit_message(content=None, embed=self.embed(final), view=self)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(embed=self.embed("⌛ Partida cancelada por inactividad."), view=self)
            except discord.HTTPException:
                pass


@tree.command(name="conecta4", description="Juega Conecta 4 contra otra persona")
@app_commands.describe(oponente="Con quién quieres jugar")
@app_commands.guild_only()
async def conecta4_cmd(interaction: discord.Interaction, oponente: discord.Member):
    if oponente.bot or oponente.id == interaction.user.id:
        return await interaction.response.send_message("Elige a otra persona (ni un bot ni tú mismo).", ephemeral=True)
    view = Conecta4View(interaction.user, oponente, interaction.guild_id)
    await interaction.response.send_message(
        content=f"{oponente.mention}, {interaction.user.mention} te retó a Conecta 4.", embed=view.embed(), view=view)
    view.message = await interaction.original_response()


# 🃏 Blackjack (contra el crupier)
_PALOS = ["♠️", "♥️", "♦️", "♣️"]
_RANGOS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]


def _valor_mano(mano) -> int:
    total, ases = 0, 0
    for r, _ in mano:
        if r == "A":
            total += 11
            ases += 1
        elif r in ("J", "Q", "K"):
            total += 10
        else:
            total += int(r)
    while total > 21 and ases:
        total -= 10
        ases -= 1
    return total


def _txt_mano(mano, ocultar: bool = False) -> str:
    if ocultar:
        return f"`{mano[0][0]}{mano[0][1]}` `🂠`"
    return " ".join(f"`{r}{p}`" for r, p in mano)


class BlackjackView(discord.ui.View):
    def __init__(self, user: discord.abc.User, gid=None):
        super().__init__(timeout=120)
        self.user, self.gid, self.message = user, gid, None
        self.mazo = [(r, p) for r in _RANGOS for p in _PALOS]
        random.shuffle(self.mazo)
        self.jugador = [self.mazo.pop(), self.mazo.pop()]
        self.crupier = [self.mazo.pop(), self.mazo.pop()]
        self.final = None
        if _valor_mano(self.jugador) == 21:  # blackjack natural
            self._cerrar()

    def _cerrar(self):
        while _valor_mano(self.crupier) < 17:
            self.crupier.append(self.mazo.pop())
        j, c = _valor_mano(self.jugador), _valor_mano(self.crupier)
        natural = j == 21 and len(self.jugador) == 2
        if j > 21:
            self.final = "💥 **Te pasaste de 21. ¡Gana el crupier!**"
        elif c > 21:
            self.final = "🎉 **El crupier se pasó. ¡Ganaste!**"
        elif natural and not (c == 21 and len(self.crupier) == 2):
            self.final = "🃏 **¡BLACKJACK! Ganaste.**"
        elif j > c:
            self.final = "🎉 **¡Ganaste!**"
        elif j < c:
            self.final = "😢 **Gana el crupier.**"
        else:
            self.final = "🤝 **Empate.**"
        for b in self.children:
            b.disabled = True
        self.stop()

    def embed(self):
        ocultar = self.final is None
        e = discord.Embed(title="🃏 Blackjack", color=0x27AE60 if not self.final else 0x2ECC71)
        e.add_field(name=f"Tu mano ({_valor_mano(self.jugador)})", value=_txt_mano(self.jugador), inline=False)
        e.add_field(name=f"Crupier ({'?' if ocultar else _valor_mano(self.crupier)})",
                    value=_txt_mano(self.crupier, ocultar), inline=False)
        e.description = f"Jugador: {self.user.mention}\n\n" + (self.final or "¿Pides otra carta o te plantas? (el crupier pide hasta 17)")
        return estilo_juego(self.gid, "blackjack", e)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Esta partida es de otra persona. Usa `/blackjack` para jugar la tuya.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Pedir carta", emoji="🃏", style=discord.ButtonStyle.primary)
    async def pedir(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.jugador.append(self.mazo.pop())
        if _valor_mano(self.jugador) >= 21:
            self._cerrar()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Plantarse", emoji="✋", style=discord.ButtonStyle.success)
    async def plantarse(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._cerrar()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def on_timeout(self):
        for b in self.children:
            b.disabled = True
        if self.message and self.final is None:
            try:
                e = self.embed()
                e.description = f"Jugador: {self.user.mention}\n\n⌛ Partida cancelada por inactividad."
                await self.message.edit(embed=e, view=self)
            except discord.HTTPException:
                pass


@tree.command(name="blackjack", description="Juega al blackjack (21) contra el crupier 🃏")
@app_commands.guild_only()
async def blackjack_cmd(interaction: discord.Interaction):
    view = BlackjackView(interaction.user, interaction.guild_id)
    await interaction.response.send_message(embed=view.embed(), view=None if view.final else view)
    if not view.final:
        view.message = await interaction.original_response()


# 🎰 Tragamonedas
SLOTS_SIMBOLOS = ["🍒", "🍋", "🍇", "🔔", "⭐", "💎", "7️⃣"]
SLOTS_PESOS = [30, 26, 20, 12, 7, 4, 2]


def _embed_slots(gid, rodillos, texto, color):
    e = discord.Embed(title="🎰 Tragamonedas", description=f"# {' │ '.join(rodillos)}\n\n{texto}", color=color)
    return estilo_juego(gid, "slots", e)


class SlotsView(discord.ui.View):
    def __init__(self, uid: int, gid):
        super().__init__(timeout=60)
        self.uid, self.gid, self.message = uid, gid, None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.uid:
            await interaction.response.send_message("Esta máquina es de otra persona. Usa `/tragamonedas` para girar la tuya.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Girar otra vez", emoji="🔁", style=discord.ButtonStyle.primary)
    async def otra(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(embed=_embed_slots(self.gid, ["🔄"] * 3, "Girando...", 0xF1C40F), view=None)
        await girar_tragamonedas(interaction, self.gid, self.uid)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass


async def girar_tragamonedas(interaction, gid, uid: int):
    final = random.choices(SLOTS_SIMBOLOS, weights=SLOTS_PESOS, k=3)
    mostrados = ["🔄"] * 3
    for i in range(3):
        await asyncio.sleep(0.8)
        mostrados[i] = final[i]
        await interaction.edit_original_response(embed=_embed_slots(gid, mostrados, "Girando...", 0xF1C40F), view=None)
    distintos = len(set(final))
    if distintos == 1:
        texto, color = ("💰 **¡¡JACKPOT!! ¡Tres sietes!** 💰", 0xF1C40F) if final[0] == "7️⃣" else ("🎉 **¡Ganaste! Tres iguales.**", 0x2ECC71)
    elif distintos == 2:
        texto, color = "😮 **¡Casi! Dos iguales.**", 0xE67E22
    else:
        texto, color = "😢 **Perdiste, inténtalo de nuevo.**", 0xE74C3C
    view = SlotsView(uid, gid)
    view.message = await interaction.edit_original_response(embed=_embed_slots(gid, final, texto, color), view=view)


@tree.command(name="tragamonedas", description="Gira la máquina tragamonedas 🎰")
@app_commands.guild_only()
async def tragamonedas_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(embed=_embed_slots(interaction.guild_id, ["🔄"] * 3, "Girando...", 0xF1C40F))
    await girar_tragamonedas(interaction, interaction.guild_id, interaction.user.id)


# ───────────────────── Mensajes: sugerencias + presentación ──────────────────
@client.event
async def on_message(m: discord.Message):
    if m.author.bot or not m.guild:
        return

    # Anti-Spam (si está activo y detecta spam, no se procesa más)
    if await antispam(m):
        return

    await procesar_autopings(m)

    # Auto-Responder: responde automáticamente con un embed configurable.
    ar = cfg(m.guild.id)["auto"]
    if ar.get("on") and ar.get("trigger"):
        if (ar.get("canal") is None or m.channel.id == ar.get("canal")) and ar["trigger"].lower() in m.content.lower():
            st = ar["respuesta"]
            try:
                color = int(st.get("color", "5865F2").lstrip("#"), 16)
            except ValueError:
                color = 0x5865F2
            emb = discord.Embed(
                title=st.get("titulo") or None,
                description=st.get("descripcion") or None,
                color=color,
            )
            if st.get("autor"):
                emb.set_author(name=st["autor"])
            if st.get("miniatura"):
                emb.set_thumbnail(url=st["miniatura"])
            if st.get("imagen"):
                emb.set_image(url=st["imagen"])
            if st.get("footer"):
                emb.set_footer(text=st["footer"])
            try:
                await m.channel.send(embed=emb)
                if ar.get("borrar_trigger"):
                    await m.delete()
            except discord.HTTPException:
                pass

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

    # AFK: quita el estado a quien vuelve y avisa cuando mencionan a alguien AFK
    await manejar_afk(m)

    # Comandos con prefijo: !comando · nexus comando · @Nexus comando
    if await manejar_prefijo(m):
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
