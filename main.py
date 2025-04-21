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
        title="Support Ticket",
        description="Cliquez sur le bouton ci-dessous pour ouvrir un ticket.",
        color=discord.Color.blue()
    )
    
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
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        category = discord.utils.get(guild.categories, name=ticket_category_name)
        if not category:
            category = await guild.create_category(ticket_category_name)

        ticket_channel = await category.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        await ticket_channel.send(
            f"{interaction.user.mention}, ton ticket a été créé ! Un membre du staff te répondra bientôt.",
            view=TicketButtons()
        )

        await interaction.user.send(f"Ton ticket a été ouvert ici : {ticket_channel.mention}")
        await interaction.message.delete()  # Supprime le bouton après l'utilisation

# ====== Vue pour le bouton "Fermer" dans le ticket ======

class TicketButtons(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Fermeture du ticket...")
        await interaction.channel.delete()

# ====== Lancement du bot ======

bot.run(TOKEN)
