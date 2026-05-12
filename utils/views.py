import discord
from utils.embeds import get_classes_data


class ClassSelectView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.selected_class: str | None = None
        classes = get_classes_data()

        options = []
        for class_id, cls in classes.items():
            options.append(
                discord.SelectOption(
                    label=cls["name"],
                    value=class_id,
                    description=cls["description"][:100],
                    emoji=cls["emoji"],
                )
            )

        select = discord.ui.Select(
            placeholder="Escolha sua classe...",
            options=options,
            custom_id="class_select",
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Este menu não é para você!", ephemeral=True
            )
            return
        self.selected_class = interaction.data["values"][0]
        self.stop()
        await interaction.response.defer()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id


class CombatView(discord.ui.View):
    def __init__(self, user_id: int, skills: list[dict]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.action: str | None = None
        self.skill_index: int | None = None
        self.skills = skills

    @discord.ui.button(label="⚔️ Atacar", style=discord.ButtonStyle.danger, row=0)
    async def attack_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Não é seu turno!", ephemeral=True
            )
            return
        self.action = "attack"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="🎯 Habilidade", style=discord.ButtonStyle.primary, row=0)
    async def skill_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Não é seu turno!", ephemeral=True
            )
            return
        skill_view = SkillSelectView(self.user_id, self.skills)
        await interaction.response.send_message(
            "🎯 Escolha uma habilidade:", view=skill_view, ephemeral=True
        )
        await skill_view.wait()
        if skill_view.selected_index is not None:
            self.action = "skill"
            self.skill_index = skill_view.selected_index
            self.stop()

    @discord.ui.button(label="🧪 Usar Item", style=discord.ButtonStyle.success, row=0)
    async def item_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Não é seu turno!", ephemeral=True
            )
            return
        self.action = "item"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="🏃 Fugir", style=discord.ButtonStyle.secondary, row=0)
    async def flee_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Não é seu turno!", ephemeral=True
            )
            return
        self.action = "flee"
        self.stop()
        await interaction.response.defer()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id


class SkillSelectView(discord.ui.View):
    def __init__(self, user_id: int, skills: list[dict]):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.selected_index: int | None = None

        options = []
        for i, skill in enumerate(skills):
            options.append(
                discord.SelectOption(
                    label=f"{skill['name']} (MP: {skill['mp_cost']})",
                    value=str(i),
                    description=skill["description"][:100],
                    emoji=skill["emoji"],
                )
            )

        if options:
            select = discord.ui.Select(
                placeholder="Escolha uma habilidade...",
                options=options,
                custom_id="skill_select",
            )
            select.callback = self.select_callback
            self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Este menu não é para você!", ephemeral=True
            )
            return
        self.selected_index = int(interaction.data["values"][0])
        self.stop()
        await interaction.response.defer()


class ItemSelectView(discord.ui.View):
    def __init__(self, user_id: int, consumables: list[dict]):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.selected_item: str | None = None

        options = []
        for item in consumables:
            options.append(
                discord.SelectOption(
                    label=f"{item['name']} (x{item['quantity']})",
                    value=item["item_id"],
                    description=item.get("description", "")[:100],
                    emoji=item.get("emoji", "🧪"),
                )
            )

        if options:
            select = discord.ui.Select(
                placeholder="Escolha um item...",
                options=options,
                custom_id="item_select",
            )
            select.callback = self.select_callback
            self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return
        self.selected_item = interaction.data["values"][0]
        self.stop()
        await interaction.response.defer()


class ConfirmView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.confirmed: bool | None = None

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            return
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            return
        self.confirmed = False
        self.stop()
        await interaction.response.defer()
