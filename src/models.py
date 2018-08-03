from src import db


class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.String(20), unique=True)
    group_name = db.Column(db.String(120))
    message_count = db.Column(db.Integer)
    like_count = db.Column(db.Integer)
    member_count = db.Column(db.Integer)
    ml_message = db.Column(db.String(1000))
    ml_likes = db.Column(db.Integer)
    date_created = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime)

    def __init__(self, group):
        self.group_id = group.group_id
        self.group_name = group.name
        self.message_count = group.data['messages']['count']
        self.like_count = 0
        self.member_count = len(group.members)
        self.ml_message = 'None'
        self.ml_likes = 0
        self.date_created = group.created_at
        self.last_updated = group.created_at

    @classmethod
    def get_group(cls, group_id):
        """
        Retrieve a specific Group object from the database

        :param group_id: Group ID of the group
        :return: Group object
        """

        return cls.query.filter_by(group_id=group_id).first()

    @classmethod
    def get_groups(cls):
        return cls.query.all()

    def update(self, group, like_count, update_time):
        self.group_name = group.name
        self.message_count = group.data['messages']['count']
        self.like_count += like_count
        self.last_updated = update_time


class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20))
    group_id = db.Column(db.String(20))
    username = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500))
    message_count = db.Column(db.Integer)
    like_count = db.Column(db.Integer)
    likes_given = db.Column(db.Integer)
    is_ignored = db.Column(db.Boolean)
    is_mod = db.Column(db.Boolean)

    def __init__(self, member, group_id):
        self.user_id = member.user_id
        self.group_id = member.group_id
        self.username = member.nickname
        self.avatar_url = member.image_url
        self.message_count = 0
        self.like_count = 0
        self.likes_given = 0
        self.is_ignored = False
        self.is_mod = False

    @classmethod
    def get_members(cls, group_id):
        """
        Retrieve a list of all Member entries in the database
        from a particular group.

        :param group_id: Group ID of the members
        :return: List of Member entries
        """

        return cls.query.filter_by(group_id=group_id).all()

    @classmethod
    def get_member(cls, group_id, user_id=None, username=None):
        """
        Retrieve a Member entry in the database (NOT A GROUPME MEMBER)

        :param group_id: Group ID of the member
        :param user_id: User ID of the member, defaults to None
        :param username: Username of the member, defaults to None
        :return: Member database entry
        """
        if user_id:
            return cls.query.filter_by(group_id=group_id, user_id=user_id).first()
        if username:
            for member in cls.get_members(group_id):
                if member.username.lower() == username.lower():
                    return member

    @classmethod
    def get_ignored(cls, group_id):
        """
        Get all ignored members from a specific group

        :param group_id: Group ID of the members
        :return: List of ignored Member database objects
        """
        return cls.query.filter_by(group_id=group_id, is_ignored=True).all()

    @classmethod
    def get_mods(cls, group_id):
        """
        Get all mods from a specific group

        :param group_id: Group ID of the members
        :return: List of moderator Member database objects
        """
        return cls.query.filter_by(group_id=group_id, is_mod=True).all()

    @classmethod
    def create_member(cls, member, group_id):
        """
        Creates a new member entry in the database

        :param member: GroupMe member object to store in database
        :param group_id: Group id of the group the member belongs to
        """
        new_member = cls(member, group_id)
        db.session.add(new_member)
        db.session.commit()

    @classmethod
    def save_new_members(cls, bot):
        """
        Saves/updates new members into the database

        :param bot: GroupMeBot object from the group of which to save members
        """
        existing = [member.user_id for member in cls.get_members(bot.group_id)]

        bot.refresh()
        for member in bot.members:
            if member.user_id not in existing:
                cls.create_member(member, bot.group_id)
            else:
                db_member = Member.get_member(bot.group_id, user_id=member.user_id)
                db_member.update(member)
        db.session.commit()

    def update(self, member):
        self.username = member.nickname
        self.avatar_url = member.image_url


class Command(db.Model):
    __tablename__ = 'commands'
    id = db.Column(db.Integer, primary_key=True)
    command = db.Column(db.String(120))
    response = db.Column(db.String(1000))
    description = db.Column(db.String(1000))
    group_id = db.Column(db.String(20))
    times_used = db.Column(db.Integer)

    def __init__(self, command, response, group_id):
        self.command = command
        self.response = response
        self.description = 'No description added yet!'
        self.group_id = group_id
        self.times_used = 0

    @classmethod
    def get_commands(cls, group_id):
        """
        Retrieve all Command objects from the database (user-added commands only)

        :param group_id: Group ID of the commands
        :return: List of Command objects
        """
        return cls.query.filter_by(group_id=group_id).all()

    @classmethod
    def get_command(cls, group_id, command_name):
        """
        Retrieve a specific Command object from the database (user-added commands only)

        :param group_id: Group ID of the command
        :param command_name: The name of the command
        :return: Command object
        """
        return cls.query.filter_by(group_id=group_id,
                                   command=command_name.lower()).first()


class Reminder(db.Model):
    __tablename__ = 'reminders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50))
    group_id = db.Column(db.String(50))
    message = db.Column(db.String(1000))
    remind_time = db.Column(db.DateTime)

    def __init__(self, user_id, group_id, message, remind_time):
        self.user_id = user_id
        self.group_id = group_id
        self.message = message
        self.remind_time = remind_time

    @classmethod
    def get_reminders(cls, group_id):
        """
        Retrieve all Reminder objects belonging to a specific group

        :param group_id: Group ID of the group
        :return: List of Reminder objects
        """
        return cls.query.filter_by(group_id=group_id).all()
