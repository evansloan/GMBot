# gmbot.bot.__init__.py

from gmbot import groupme
from gmbot.bot.groupmebot import GroupMeBot
from gmbot.models import Group, Member


class CommandContext:
    """
    CommandContext holds information about the message in which a command
    was called.

    A CommandContext object is sent as an argument to all built-in commands.
    """

    def __init__(self, command, message, sender, bot):
        self.command = command
        self.message = message
        self.sender = sender
        self.bot = bot
        self.group = self.bot.group
        self.group_id = self.group.group_id

        self.db_group = Group.get_group(self.group_id)
        self.db_sender = Member.get_member(self.group_id,
                                           user_id=sender.user_id)
