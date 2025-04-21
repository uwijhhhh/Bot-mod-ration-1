import os
import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import Embed

# Récupère le TOKEN depuis les variables d'environnement Railway
TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    raise ValueError("Le TOKEN n'est pas défini. Ajoute-le dans les variables Railway.")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

ticket_category_name = "Tickets"
mod_category_name = "Tickets-Modération"
log_channel_name = "ticket-logs"  # Canal pour les logs des tickets

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

# ====== Commande Setup Ticket (admin) ======

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    """Crée un message avec un bouton pour ouvrir un ticket"""
    channel = discord.utils.get(ctx.guild.text_channels, name="support")  # Change le nom si tu veux un autre canal
    if not channel:
        channel = await ctx.guild.create_text_channel("support")

    embed = Embed(
        title="🔧 Support Ticket",
        description="Cliquez sur le bouton ci-dessous pour ouvrir un ticket.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Le bot de support 24/7")

    # Créer une vue avec un bouton
    view = View()
    button = Button(label="Ouvrir un ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")
    view.add_item(button)

    await channel.send(embed=embed, view=view)
    await ctx.send("Panel de tickets créé avec succès dans le canal support.")

# ====== Commande d'ouverture de ticket ======

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Réagit aux interactions des utilisateurs, comme un clic sur un bouton"""
    if interaction.data["custom_id"] == "open_ticket":
        await interaction.response.defer()

        # Créer le salon de ticket
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        # Créer une catégorie "Tickets" si elle n'existe pas
        category = discord.utils.get(guild.categories, name=ticket_category_name)
        if not category:
            category = await guild.create_category(ticket_category_name)

        # Créer une catégorie "Tickets-Modération" pour les modérateurs
        mod_category = discord.utils.get(guild.categories, name=mod_category_name)
        if not mod_category:
            mod_category = await guild.create_category(mod_category_name)

        # Créer le salon pour le ticket
        ticket_channel = await category.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)

        # Embed avec un message dans le ticket
        embed = Embed(
            title="🔨 Ticket Ouvert",
            description=f"Salut {interaction.user.mention}, merci d'avoir ouvert un ticket ! Un membre du staff va te répondre ici.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Ticket créé par le bot")

        # Ajouter le bouton "Fermer" et "Prendre en charge" dans le ticket
        view = TicketButtons()

        await ticket_channel.send(embed=embed, view=view)

        # Ajouter un message dans la catégorie "Tickets-Modération" pour les admins/modos
        mod_embed = Embed(
            title="Nouvelle demande de support",
            description=f"{interaction.user.mention} a ouvert un ticket. Cliquez pour y accéder.",
            color=discord.Color.orange()
        )
        mod_embed.set_footer(text="Modérateurs, intervenez ici !")

        # Ajouter le ticket dans la catégorie "Tickets-Modération" pour les modérateurs
        mod_channel = await mod_category.create_text_channel(f"ticket-{interaction.user.name}-mod", overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=False),  # Empêche l'utilisateur de voir ce channel
            discord.utils.get(guild.roles, name="Modérateur"): discord.PermissionOverwrite(read_messages=True),  # Modérateurs peuvent lire
            guild.me: discord.PermissionOverwrite(read_messages=True)
        })
        
        await mod_channel.send(embed=mod_embed)

        # Enregistrement des logs
        log_channel = discord.utils.get(guild.text_channels, name=log_channel_name)
        if not log_channel:
            log_channel = await guild.create_text_channel(log_channel_name)

        log_embed = Embed(
            title="🔔 Nouveau Ticket",
            description=f"Un nouveau ticket a été ouvert par {interaction.user.mention}.",
            color=discord.Color.blue()
        )
        log_embed.add_field(name="Nom du ticket", value=f"ticket-{interaction.user.name}")
        log_embed.set_footer(text="Ticket system logs")
        await log_channel.send(embed=log_embed)

        await interaction.user.send(f"Ton ticket a été ouvert ici : {ticket_channel.mention}")
        await interaction.message.delete()  # Supprime le bouton après l'utilisation

# ====== Vue pour le bouton "Fermer" et "Prendre en charge" dans le ticket ======

class TicketButtons(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        """Ferme le ticket en supprimant le salon et log la fermeture"""
        await interaction.response.send_message("Fermeture du ticket...")
        await interaction.channel.delete()

        # Log la fermeture du ticket
        log_channel = discord.utils.get(interaction.guild.text_channels, name=log_channel_name)
        if log_channel:
            log_embed = Embed(
                title="🔒 Ticket Fermé",
                description=f"Le ticket {interaction.channel.name} a été fermé.",
                color=discord.Color.red()
            )
            log_embed.add_field(name="Utilisateur", value=interaction.user.mention)
            log_embed.set_footer(text="Ticket system logs")
            await log_channel.send(embed=log_embed)

    @discord.ui.button(label="Prendre en charge", style=discord.ButtonStyle.green, custom_id="take_ticket")
    async def take_ticket(self, interaction: discord.Interaction, button: Button):
        """Permet à un modérateur de prendre en charge le ticket"""
        mod_role = discord.utils.get(interaction.guild.roles, name="Modérateur")
        if mod_role in interaction.user.roles:
            await interaction.response.send_message(f"{interaction.user.mention} a pris en charge ce ticket.", ephemeral=True)

            # Log la prise en charge du ticket
            log_channel = discord.utils.get(interaction.guild.text_channels, name=log_channel_name)
            if log_channel:
                log_embed = Embed(
                    title="🛠️ Ticket Pris en charge",
                    description=f"Le ticket {interaction.channel.name} a été pris en charge par {interaction.user.mention}.",
                    color=discord.Color.green()
                )
                log_embed.set_footer(text="Ticket system logs")
                await log_channel.send(embed=log_embed)
        else:
            await interaction.response.send_message("Tu n'as pas la permission de prendre en charge ce ticket.", ephemeral=True)

# ====== Lancement du bot ======

bot.run(TOKEN)
