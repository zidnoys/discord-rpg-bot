import asyncio
import discord
from discord.ext import commands

from config import DISCORD_TOKEN
import database as db

COGS = [
    "cogs.character",
    "cogs.combat",
    "cogs.inventory",
    "cogs.shop",
    "cogs.skills",
    "cogs.dungeon",
    "cogs.ranking",
]


class RPGBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await db.init_db()
        for cog in COGS:
            await self.load_extension(cog)
        await self.tree.sync()
        print(f"[RPG Bot] {len(COGS)} cogs carregados. Slash commands sincronizados.")

    async def on_ready(self):
        print(f"[RPG Bot] Conectado como {self.user} (ID: {self.user.id})")
        print(f"[RPG Bot] Servidores: {len(self.guilds)}")
        await self.change_presence(
            activity=discord.Game(name="/criar — RPG Interativo!")
        )


def main():
    if not DISCORD_TOKEN:
        print(
            "ERRO: DISCORD_TOKEN não configurado!\n"
            "Crie um arquivo .env com:\n"
            "DISCORD_TOKEN=seu_token_aqui\n\n"
            "Ou defina a variável de ambiente DISCORD_TOKEN."
        )
        return
    bot = RPGBot()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
