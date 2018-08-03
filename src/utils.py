import re

from src import db
from src.bot.groupmebot import GroupMeBot
from src.models import Command


def read_file(text_file):
    with open(text_file, 'r') as f:
        return [word.strip() for word in f]


def validate_command(text):
    """
    Checks to see if a message contains a command at the beginnging
    of the message.

    :param text: The message sent to be checked.
    """
    regex = re.compile(r'^!([\w\d.,\/#$%\^&\*;:{}=\-_`~()]+)', re.I)
    result = re.match(regex, text)
    if result:
        return True, result.group()[1:]
    return False, None


def get_all_commands(group_id):
    """
    Loads all command names. Includes built in commands and db commands

    :param group_id: ID of group to fetch commands from
    :return: list of command names
    """
    command_list = [v.name for _, v in GroupMeBot.commands.items() if not v.hidden]
    for cmd in Command.get_commands(group_id):
        command_list.append(cmd.command.lower())
    return command_list


def search(message, bot):
    if message in get_all_commands(bot.group_id):
        cmd = Command.get_command(bot.group_id, message)
        bot.send(cmd.response)
        cmd.times_used += 1
        db.session.commit()
    else:
        bot.send(f'Command !{message} does not exist')


def order_dict(d):
    """
    Sorts a dictionary by its values in descending order. Returns
    the sorted dictionary composed as a list of strings.

    :param d: dictionary to sort
    """
    d = sorted(d.items(), key=lambda x: x[1])
    return [f'{pair[0]}: {pair[1]}' for pair in list(reversed(d))]


def max_dict(d):
    return max(d, key=d.get)
