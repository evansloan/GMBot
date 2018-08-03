from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from src import app, db, groupme, q
from src.bot import CommandContext, GroupMeBot

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)


@manager.command
def create_db():
    db.create_all()


@manager.command
def drop_db():
    db.drop_all()


@manager.command
def test_command(command_name, args=None):
    test_bot = GroupMeBot('<bot_id>')
    test_bot.test_mode = True
    try:
        command_obj = GroupMeBot.commands[command_name.lower()]
    except KeyError:
        app.logger.info(f'{command_name} does not exist')
        return

    command_args = {
        'command': command_name,
        'message': args,
        'sender': groupme.get_member('<group_id>', user_id='<user_id>'),
        'bot': test_bot
    }

    cmd_ctx = CommandContext(**command_args)

    if command_obj.queue:
        q.enqueue(command_obj.command, cmd_ctx)
    elif command_obj.extra_args and args is None:
        test_bot.send(command_obj.help)
    else:
        command_obj.command(cmd_ctx)


if __name__ == '__main__':
    manager.run()
