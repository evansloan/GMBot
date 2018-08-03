from src import app, groupy_client, strings


class GroupMeBot:

    commands = {}

    def __init__(self, b_id):
        self.bot_id = b_id
        self.group_id = self.bot.group_id
        self.group = groupy_client.groups.get(self.group_id)
        self.msg_count = self.group.data['messages']['count']
        self.members = self.group.members
        self.me = groupy_client.user.get_me()
        self.test_mode = False

    @property
    def bot(self):
        for bot in groupy_client.bots.list():
            if bot.bot_id == self.bot_id:
                return bot

    def send(self, message, attachments=None):
        if self.test_mode:
            app.logger.info(f'\nMessage:\n{message}\n\nAttachments:\n{attachments}')
        else:
            char_limit = 1000
            if len(message) > char_limit:
                messages = [message[i:i + char_limit] for i in range(0, len(message), char_limit)]
                for message in messages:
                    self.bot.post(message, attachments=attachments)
            else:
                self.bot.post(message, attachments=attachments)

    def refresh(self):
        self.group.refresh_from_server()

    @classmethod
    def command(cls, name, extra_args=False, queue=False, restricted=False,
                hidden=False):
        """
        Use to add a built-in command to the active GroupMeBot objects

        :param name: How the command will be called in the group chat.
        :param queue: If the command will take longer than 180 seconds to complete,
                      set this to True
        :param restricted: If the command requires moderator status, set this
                           to True
        :param hidden: Set to true to hide in the commands page
        """
        def wrapper(func):
            command_obj = Command(name.lower(), func, extra_args, queue,
                                  restricted, hidden)
            cls.commands[name.lower()] = command_obj
            return func
        return wrapper

    @classmethod
    def get_commands(cls):
        return [cmd for _, cmd in GroupMeBot.commands.items()]

    def load_messages(self):
        return [message for message in self.group.messages.list_all()]


class Command:
    def __init__(self, name, command, extra_args, queue, restricted, hidden):
        self.name = name
        self.command = command
        self.extra_args = extra_args
        self.queue = queue
        self.restricted = restricted
        self.hidden = hidden

    @property
    def help(self):
        if self.extra_args:
            return getattr(strings, self.name).help
