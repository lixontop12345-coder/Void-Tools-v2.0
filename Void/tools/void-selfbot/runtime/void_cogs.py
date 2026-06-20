"""Recovered cogs stripped during refactor."""
from __future__ import annotations

import json
import os

from discord.ext import commands

event_react_rules: dict = {}


def load_event_react_data() -> None:
    global event_react_rules
    path = os.path.join(os.path.dirname(__file__), "data", "event_react.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            event_react_rules = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        event_react_rules = {}


class RonMessageCog(commands.Cog):
    """Auto react / reply / edit on message triggers."""

    def __init__(self, bot):
        self.bot = bot
        self.reactions: dict = {}
        self.responses: dict = {}
        self.edits: dict = {}
        self._load()

    def _data_path(self, name: str) -> str:
        root = os.path.dirname(os.path.abspath(__file__))
        folder = os.path.join(root, "data")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, name)

    def _load(self) -> None:
        for attr, fname in (
            ("reactions", "ronmessage.json"),
            ("responses", "sonmessage.json"),
            ("edits", "eonmessage.json"),
        ):
            path = self._data_path(fname)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    setattr(self, attr, json.load(handle))
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                setattr(self, attr, {})

    def _save(self, attr: str, fname: str) -> None:
        with open(self._data_path(fname), "w", encoding="utf-8") as handle:
            json.dump(getattr(self, attr), handle, indent=2, ensure_ascii=False)

    @commands.group(invoke_without_command=True)
    async def ronmessage(self, ctx):
        await ctx.send("```.ronmessage add <msg> <emoji> | list | remove <msg> | clear | on/off <msg>```")

    @ronmessage.command(name="add")
    async def ron_add(self, ctx, trigger: str, emoji: str):
        self.reactions[trigger.lower()] = {"emoji": emoji, "enabled": True}
        self._save("reactions", "ronmessage.json")
        await ctx.send("```Reaction added.```")

    @ronmessage.command(name="list")
    async def ron_list(self, ctx):
        if not self.reactions:
            await ctx.send("```No triggers configured.```")
            return
        lines = [f"{k}: {v.get('emoji')} ({'on' if v.get('enabled', True) else 'off'})" for k, v in self.reactions.items()]
        await ctx.send("```" + "\n".join(lines[:30]) + "```")

    @ronmessage.command(name="remove")
    async def ron_remove(self, ctx, trigger: str):
        self.reactions.pop(trigger.lower(), None)
        self._save("reactions", "ronmessage.json")
        await ctx.send("```Removed.```")

    @ronmessage.command(name="clear")
    async def ron_clear(self, ctx):
        self.reactions.clear()
        self._save("reactions", "ronmessage.json")
        await ctx.send("```Cleared.```")

    @ronmessage.command(name="on")
    async def ron_on(self, ctx, trigger: str):
        key = trigger.lower()
        if key in self.reactions:
            self.reactions[key]["enabled"] = True
            self._save("reactions", "ronmessage.json")
        await ctx.send("```Enabled.```")

    @ronmessage.command(name="off")
    async def ron_off(self, ctx, trigger: str):
        key = trigger.lower()
        if key in self.reactions:
            self.reactions[key]["enabled"] = False
            self._save("reactions", "ronmessage.json")
        await ctx.send("```Disabled.```")

    @commands.group(invoke_without_command=True)
    async def sonmessage(self, ctx):
        await ctx.send("```.sonmessage add <msg> <response> | list | remove | clear | on/off```")

    @sonmessage.command(name="add")
    async def son_add(self, ctx, trigger: str, *, response: str):
        self.responses[trigger.lower()] = {"text": response, "enabled": True}
        self._save("responses", "sonmessage.json")
        await ctx.send("```Response added.```")

    @sonmessage.command(name="list")
    async def son_list(self, ctx):
        if not self.responses:
            await ctx.send("```No triggers.```")
            return
        lines = [f"{k}: {v.get('text', '')[:40]}" for k, v in self.responses.items()]
        await ctx.send("```" + "\n".join(lines[:25]) + "```")

    @commands.group(invoke_without_command=True)
    async def eonmessage(self, ctx):
        await ctx.send("```.eonmessage add <msg> <edit> | list | remove | clear | on/off```")

    @eonmessage.command(name="add")
    async def eon_add(self, ctx, trigger: str, *, new_text: str):
        self.edits[trigger.lower()] = {"text": new_text, "enabled": True}
        self._save("edits", "eonmessage.json")
        await ctx.send("```Edit rule added.```")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != self.bot.user.id:
            return
        content = (message.content or "").lower()
        for trigger, rule in self.reactions.items():
            if rule.get("enabled", True) and trigger in content:
                try:
                    await message.add_reaction(rule["emoji"])
                except Exception:
                    pass
                break
        for trigger, rule in self.responses.items():
            if rule.get("enabled", True) and trigger in content:
                try:
                    await message.channel.send(rule["text"])
                except Exception:
                    pass
                break
