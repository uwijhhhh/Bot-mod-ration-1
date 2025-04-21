import discord
from discord.ext import commands
from discord.ui import Button, View
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Tu dois ajouter ton TOKEN dans Railway.")

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user.name}")

# ========= CONFIGURATION AUTOMATIQUE =========

@bot.command()
@commands.has_permissions(administrator=True)
async def config(ctx):
    guild = ctx.guild
    await ctx.send("Configuration du système de tickets en cours...")

    # 1. Rôle modérateur
    mod_role = discord.utils.get(guild.roles, name="Modérateur")
    if not mod_role:
        mod_role = await guild.create_role(name="Modérateur", color=discord.Color.orange())
        await ctx.send("Rôle `Modérateur` créé.")

    # 2. Catégories
    ticket_cat = discord.utils.get(guild.categories, name="Tickets")
    mod_cat = discord.utils.get(guild.categories, name="Tickets-Modération")

    if not ticket_cat:
        ticket_cat = await guild.create_category("Tickets")
        await ctx.send("Catégorie `Tickets` créée.")
    if not mod_cat:
        mod_cat = await guild.create_category("Tickets-Modération")
        await ctx.send("Catégorie `Tickets-Modération` créée.")

    # 3. Canaux support + logs
    support_channel = discord.utils.get(guild.text_channels, name="support")
    if not support_channel:
        support_channel = await guild.create_text_channel("support", category=ticket_cat)
        await ctx.send("Canal `support` créé.")

    log_channel = discord.utils.get(guild.text_channels, name="ticket-logs")
    if not log_channel:
        log_channel = await guild.create_text_channel("ticket-logs", category=mod_cat)
        await ctx.send("Canal `ticket-logs` créé.")

    # 4. Panel ticket
    embed = discord.Embed(
        title="Besoin d'aide ?",
        description="Clique ci-dessous pour ouvrir un ticket !",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Système de tickets 24/7")

    view = View()
    view.add_item(Button(label="Ouvrir un ticket", style=discord.ButtonStyle.green, custom_id="open_ticket"))

    await support_channel.send(embed=embed, view=view)
    await ctx.send("Panel envoyé dans `#support`. Configuration terminée !")


# ========= INTERACTION TICKET =========

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data.get("custom_id") != "open_ticket":
        return

    guild = interaction.guild
    user = interaction.user
    await interaction.response.defer(ephemeral=True)

    # Permissions du salon
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True),
    }

    # Créer le salon de ticket
    ticket_cat = discord.utils.get(guild.categories, name="Tickets")
    channel = await ticket_cat.create_text_channel(f"ticket-{user.name}", overwrites=overwrites)

    # Embed dans le ticket
    embed = discord.Embed(
        title="Ticket ouvert",
        description=f"{user.mention}, merci d'avoir contacté le support. Un membre du staff va bientôt répondre.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Support automatique")

    view = TicketButtons()
    await channel.send(embed=embed, view=view)

    # Logs
    log_channel = discord.utils.get(guild.text_channels, name="ticket-logs")
    if log_channel:
        log_embed = discord.Embed(
            title="Nouveau ticket",
            description=f"Ticket de {user.mention} ouvert : {channel.mention}",
            color=discord.Color.blue()
        )
        await log_channel.send(embed=log_embed)

    await user.send(f"Ton ticket a été créé ici : {channel.mention}")


# ========= BOUTONS DU TICKET =========

class TicketButtons(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Prendre en charge", style=discord.ButtonStyle.primary, custom_id="take_ticket")
    async def take_ticket(self, interaction: discord.Interaction, button: Button):
        mod_role = discord.utils.get(interaction.guild.roles, name="Modérateur")
        if mod_role in interaction.user.roles:
            await interaction.response.send_message(f"{interaction.user.mention} a pris en charge ce ticket.", ephemeral=True)
            log_channel = discord.utils.get(interaction.guild.text_channels, name="ticket-logs")
            if log_channel:
                await log_channel.send(f"{interaction.user.mention} a pris en charge {interaction.channel.mention}")
        else:
            await interaction.response.send_message("Tu n'as pas la permission (Modérateur requis).", ephemeral=True)

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Fermeture du ticket...", ephemeral=True)
        log_channel = discord.utils.get(interaction.guild.text_channels, name="ticket-logs")
        if log_channel:
            await log_channel.send(f"Ticket {interaction.channel.name} fermé par {interaction.user.mention}")
        await interaction.channel.delete()

# ========= LANCEMENT =========

bot.run(TOKEN)
