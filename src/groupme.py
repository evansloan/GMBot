import pytz
import requests
from groupy import attachments

from src import app, bots, groupme_token, groupy_client


def get_bot(group_id):
    """
    Looks through active GroupMeBots and returns the one that corresponds
    to the group_id parameter

    :param group_id: group id of the GroupMeBot object
    :return: GroupMeBot object
    """
    for bot in bots:
        if bot.group_id == group_id:
            return bot


def get_member(group_id, username=None, user_id=None):
    """
    Get a specific member from the group that corresponds to the group_id
    parameter. Must supply either a username or user id

    :param group_id: group id of the group to search in
    :param username: username of the member to search for, defaults to None
    ;param user_id: user id of the member to search for, defaults to None
    :return: Groupy Member object
    """
    group_members = get_group(group_id).members
    if username:
        for member in group_members:
            if member.nickname.lower() == username.lower():
                return member
    if user_id:
        for member in group_members:
            if member.user_id == user_id:
                return member


def get_group(group_id):
    """
    Retrieve a Groupy Group object by it's Group ID

    :return: Groupy Group object
    """
    return groupy_client.groups.get(group_id)


def load_messages(bot, tstamp, new_messages=None, messages=None):
    """
    Loads all messages in a GroupMe group back until a certain timestamp

    :param bot: The bot within the group being searched for messages
    :param tstamp: Timestamp of the oldest message to search for
    :param new_messages: List of new messages to be iterated over, defaults to None
    :param messages: List of messages that have already been looked over, defaults to None

    :return: List of Groupy Message objects dating back to tstamp parameter
    """
    tstamp = tstamp.replace(tzinfo=pytz.UTC)

    if new_messages is None:
        new_messages = bot.group.messages.list()
    if messages is None:
        messages = []

    for message in new_messages:
        message_tstamp = message.created_at.replace(tzinfo=pytz.UTC)
        if message_tstamp > tstamp:
            messages.append(message)
        else:
            app.logger.info('All messages loaded')
            return messages

    new_messages = bot.group.messages.list_before(new_messages[-1].id)
    return load_messages(bot, tstamp, new_messages, messages)


def api_call(path, method, params=None, payload=None):
    url = f'https://api.groupme.com/v3/{path}'
    if params:
        params['token'] = groupme_token
    else:
        params = {'token': groupme_token}

    if method.lower() == 'get':
        return requests.get(url=url, params=params, json=payload)
    elif method.lower() == 'post':
        return requests.post(url=url, params=params, json=payload)


def create_image_attachment(img_path):
    """
    Create a Groupy image attachment object to send in a message.

    :param img_path: Path to an image file
    :return: Groupy image attachment object
    """
    url = 'https://image.groupme.com/pictures'
    with open(img_path, 'rb') as f:
        data = f.read()
        r = requests.post(url, data=data, params={'token': groupme_token}).json()
        return attachments.Image(r['payload']['url'])
