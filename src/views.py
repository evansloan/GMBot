from datetime import datetime

from flask import Blueprint, render_template, request
from groupy import attachments

from src import app, bots, db, groupme, q, strings, utils
from src.models import Command, Group, Member, Reminder
from src.bot import commands, CommandContext, GroupMeBot

main_blueprint = Blueprint('main', __name__)


@main_blueprint.route('/callback', methods=['POST'])
def callback():
    data = request.get_json()
    data['text'] = data['text'].strip()
    app.logger.info(data)
    bot = groupme.get_bot(data['group_id'])
    db_group = Group.get_group(data['group_id'])
    ignored = [member.user_id for member in Member.get_ignored(data['group_id'])]
    mods = [member.user_id for member in Member.get_mods(data['group_id'])]
    sender = groupme.get_member(bot.group_id, user_id=data['user_id'])

    if db_group is None:
        bot.send(strings.initialize.help)

    if data['sender_type'] != 'user':
        return 'no response', 200

    valid_command, command_name = utils.validate_command(data['text'].lower())
    if valid_command:
        if data['user_id'] in ignored:
            bot.send('No')
            return

        if command_name in GroupMeBot.commands:
            command_obj = GroupMeBot.commands[command_name]

            try:
                message = data['text'].split(' ', 1)[1].strip()
            except IndexError:
                message = None

            cmd_ctx = CommandContext(command_name, message, sender, bot)

            if command_obj.restricted and data['user_id'] not in mods:
                bot.send(f'You must be a mod to use !{command_name}')
                return

            if command_obj.extra_args and message is None:
                bot.send(command_obj.help)
                return

            if command_obj.queue:
                q.enqueue(command_obj.command, cmd_ctx, timeout=1000)
            else:
                command_obj.command(cmd_ctx)
        else:
            utils.search(data['text'][1:].lower(), bot)

    check_for_reminders(data['group_id'], bot)

    return 'ok', 200


@main_blueprint.route('/info', methods=['GET'])
def info_view():
    group_id = request.args.get('group_id', default=1, type=str)
    group = groupme.get_group(group_id)
    db_group = Group.get_group(group_id)
    bot = groupme.get_bot(group_id)
    user_cmds = Command.get_commands(group_id)
    creator = Member.get_member(bot.group_id, user_id=group.creator_user_id)

    built_in = [cmd.name for cmd in GroupMeBot.get_commands() if not cmd.hidden]

    mods = []
    for mod in Member.get_mods(group_id):
        mods.append(groupme.get_member(bot.group_id, user_id=mod.user_id))

    mods_dict = {}
    for mod in mods:
        try:
            mods_dict[mod.nickname] = mod.image_url
        except AttributeError:
            pass

    return render_template('info.html', cmds=built_in, user_cmds=user_cmds, group=group,
                           db_group=db_group, mods=mods_dict, creator=creator,
                           title=group.name)


@main_blueprint.route('/stats', methods=['GET'])
def stats_view():
    group_id = request.args.get('group_id', default=1, type=str)
    group = Group.get_group(group_id)
    members = Member.get_members(group_id)

    graph_colors = [
        '#F7464A', '#46BFBD', '#FDB45C', '#FEDCBA', '#ABCDEF',
        '#DDDDDD', '#ABCABC', '#2C79E0', '#4DE02C', '#C21010',
        '#8110C2', '#10C2AA', '#C21026', '#FBFF0F', '#FF0FE6',
        '#990FFF', '#9AF0FF', '#FFEB9A', '#FF9AC0', '#FF9A9A',
        '#8FF032', '#4AFEDC', '#341943', '#BDBD99', '#994529',
        '#CDB23D', '#23F3A0', '#342343', '#343453', '#475453',
    ]

    # chart labels/values
    labels = [member.username for member in members]
    likes_recv_values = [member.like_count for member in members]
    likes_given_values = [member.likes_given for member in members]
    msg_values = [member.message_count for member in members]
    colors = graph_colors[:len(members)]

    # ratio stuff
    ratio_info = {
        'likes_recv': {},
        'likes_given': {},
        'messages': {},
        'ratio': {}
    }
    for member in members:
        ratio_info['likes_recv'][member.username] = member.like_count
        ratio_info['likes_given'][member.username] = member.likes_given
        ratio_info['messages'][member.username] = member.message_count
        try:
            ratio = round(member.like_count / member.message_count, 2)
            ratio_info['ratio'][member.username] = ratio
        except ZeroDivisionError:
            ratio_info['ratio'][member.username] = 0.00

    likes_list = utils.order_dict(ratio_info['likes_recv'])
    message_list = utils.order_dict(ratio_info['messages'])
    given_list = utils.order_dict(ratio_info['likes_given'])
    ratio_list = utils.order_dict(ratio_info['ratio'])

    ratio_values = [ratio_info['ratio'][label] for label in labels]
    pics = [member.avatar_url for member in members]

    return render_template('stats.html', members=members, group=group,
                           likes_set=zip(labels, likes_recv_values),
                           given_set=zip(labels, likes_given_values),
                           messages_set=zip(labels, msg_values),
                           ratios_set=zip(labels, ratio_values, colors, pics),
                           likes=likes_list, messages=message_list,
                           given=given_list, ratios=ratio_list)


def check_for_reminders(group_id, bot):
    """
    Checks a group for any reninders that are past the current time

    :param group_id: group to check for active reminders
    """
    reminders = Reminder.query.filter_by(group_id=group_id).all()

    for reminder in reminders:
        if datetime.now() >= reminder.remind_time:
            member = groupme.get_member(bot.group_id, user_id=reminder.user_id)
            send_reminder(member, reminder.message, bot)
            db.session.delete(reminder)
            db.session.commit()


def send_reminder(member, message, bot):
    loci = [10, len(member.nickname) + 1]
    mention = attachments.Mentions(loci=[loci], user_ids=[member.user_id])
    bot.send(f'Reminding @{member.nickname}:\n{message}', attachments=[mention])
