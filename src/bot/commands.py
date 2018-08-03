import io
import math
import random
import time
import urllib.request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from groupy import attachments
from PIL import Image, ImageEnhance, ImageOps

from src import app, db, groupme, strings, utils
from src.bot import CommandContext, GroupMeBot
from src.models import Command, Group, Member, Reminder

RNG = random.SystemRandom()


@GroupMeBot.command('reset', restricted=True, hidden=True)
def reset(ctx: CommandContext):
    """
    Reset stats for a specific group
    """
    db_members = Member.get_members(ctx.group_id)
    db.session.delete(ctx.db_group)

    for member in db_members:
        db.session.delete(member)

    db.session.commit()
    ctx.bot.send('Group reset')


@GroupMeBot.command('initialize')
def initialize(ctx: CommandContext):
    """
    Adds group and group members into the database
    """
    for group in Group.query.all():
        if group.group_id == ctx.group_id:
            ctx.bot.send('Group already initialized')
            return

    new_group = Group(ctx.group)
    db.session.add(new_group)

    ctx.bot.refresh()
    for member in ctx.bot.members:
        Member.create_member(member)

    db.session.commit()

    ctx.bot.send('Group successfully initialized')


@GroupMeBot.command('add', extra_args=True)
def add(ctx: CommandContext):
    """
    Add a text command to the database
    """
    if ctx.message.split()[0].lower() == 'description':
        try:
            command_name = ctx.message.split()[1].strip().lower()
            command = Command.get_command(ctx.group_id, command_name)
            desription = ctx.message.split(':', 1)[1].strip()

            command.description = desription
            db.session.commit()
            ctx.bot.send(f'{command_name} description added!')
        except IndexError:
            ctx.bot.send(strings.add.error)
    else:
        try:
            command = ctx.message.split(':')[0].strip().lower()
            response = ctx.message.split(':', 1)[1].strip()
            existing = utils.get_all_commands(ctx.group_id)

            if command.lower() not in existing:
                new_command = Command(command, response, ctx.group_id)
                db.session.add(new_command)
                db.session.commit()
                ctx.bot.send(strings.add.success.format(command))
            else:
                ctx.bot.send(strings.add.failure.format(command))
        except IndexError:
            ctx.bot.send(strings.add.error)


@GroupMeBot.command('edit', extra_args=True, restricted=True)
def edit(ctx: CommandContext):
    """
    Edit an already existing command in the database
    """
    try:
        command = ctx.message.split(':')[0].strip()
        response = ctx.message.split(':', 1)[1].strip()
        cmd = Command.get_command(ctx.group_id, command)
        cmd.response = response
        db.session.commit()
        ctx.bot.send(strings.edit.success.format(command))
    except IndexError:
        ctx.bot.send(strings.edit.error)


@GroupMeBot.command('delete', extra_args=True, restricted=True)
def delete(ctx: CommandContext):
    """
    Delete a command from the database
    """
    if ctx.message.lower() in utils.get_all_commands(ctx.group_id):
        command = Command.get_command(ctx.group_id, ctx.message)
        db.session.delete(command)
        db.session.commit()
        ctx.bot.send(strings.delete.success.format(ctx.message))
    else:
        ctx.send(strings.delete.error.format(ctx.message))


@GroupMeBot.command('mod', restricted=True)
def mod(ctx: CommandContext):
    """
    Add a moderator to the bot
    """
    Member.save_new_members(ctx.bot)
    member = Member.get_member(ctx.group_id, username=ctx.message)

    if member.is_mod:
        ctx.bot.send(f'{member.username} is already a mod')
        return

    member.is_mod = True
    db.session.commit()
    ctx.bot.send(f'{member.username} added as a mod')


@GroupMeBot.command('unmod', restricted=True)
def unmod(ctx: CommandContext):
    """
    Remove a moderator from the bot
    """
    member = Member.get_member(ctx.group_id, username=ctx.message)
    if member.is_mod:
        member.is_mod = False
        db.session.commit()
        ctx.bot.send(f'{member.username} removed as mod')
    else:
        ctx.bot.send(f'{member.username} is not a mod')


@GroupMeBot.command('commands')
def info(ctx: CommandContext):
    """
    Sends URL for the commands page
    """
    ctx.bot.send(f'{app.config["BASE_URL"]}/info?group_id={ctx.group_id}')


@GroupMeBot.command('ignore', restricted=True)
def ignore(ctx: CommandContext):
    """
    Ignore a specific member from the bot.
    Prevents that user from issuing any commands.
    """
    Member.save_new_members(ctx.bot)
    victim = Member.get_member(ctx.group_id, username=ctx.message)
    mods = [mod.user_id for mod in Member.get_mods(ctx.group_id)]
    if victim.user_id in mods:
        ctx.bot.send('You can not ignore a mod')
        return

    if victim.is_ignored:
        ctx.bot.send(f'{victim.username} is already ignored')
    else:
        victim.is_ignored = True
        db.session.commit()
        ctx.bot.send(f'{victim.username} ignored')


@GroupMeBot.command('unignore', restricted=True)
def unignore(ctx: CommandContext):
    ex_con = Member.get_member(ctx.group_id, username=ctx.message)
    if ex_con.is_ignored:
        ex_con.is_ignored = False
        db.session.commit()
        ctx.bot.send(f'{ex_con.username} unignored')
    else:
        ctx.bot.send(f'{ex_con.username} is not currently ignored')


@GroupMeBot.command('stats', queue=True)
def stats(ctx: CommandContext, new_messages: list=None):
    """
    Gathers and sends a message containing total messages, likes,
    users' total likes, and most liked messages from a GroupMe group

    :param bot: bot to gather info from and send message
    """
    ctx.bot.send('Gathering group stats')
    ctx.bot.refresh()
    Member.save_new_members(ctx.bot)
    db_group = Group.get_group(ctx.group_id)

    if new_messages is None:
        new_messages = groupme.load_messages(ctx.bot, db_group.last_updated)

    total_likes = 0
    for message in new_messages:
        try:
            db_member = Member.get_member(ctx.group_id, user_id=message.user_id)
            db_member.message_count += 1
            db_member.like_count += len(message.favorited_by)

            for user_id in message.favorited_by:
                total_likes += 1
                Member.get_member(ctx.group_id, user_id=user_id).likes_given += 1

            if len(message.favorited_by) >= db_group.ml_likes:
                db_group.ml_likes = len(message.favorited_by)
                db_group.ml_message = f'{message.name}: {message.text}'
        except AttributeError:
            # Throws an AttributeError when it comes across a message from a
            # bot since they aren't real members.
            pass

    db_group.update(ctx.group, total_likes, new_messages[0].created_at)
    db.session.commit()

    ctx.bot.send(f'{app.config["BASE_URL"]}/stats?group_id={ctx.group_id}')


@GroupMeBot.command('slow_stats', queue=True, hidden=True)
def slow_stats(ctx: CommandContext):
    """
    Loads every message in a group and sends it to stats function
    """
    members = Member.get_members(ctx.group_id)

    for member in members:
        member.like_count = 0
        member.message_count = 0
        member.likes_given = 0

    ctx.bot.refresh()
    ctx.bot.send('Loading all messages...')
    messages = list(ctx.group.messages.list_all())
    ctx.db_group.last_updated = messages[-1].created_at
    db.session.commit()
    stats(ctx, new_messages=messages)


@GroupMeBot.command('roll', extra_args=True)
def roll(ctx: CommandContext):
    """
    Rolls a die with user supplied sides
    """
    try:
        sides = math.floor(float(ctx.message))
        if sides >= 1:
            result = RNG.randint(1, sides)
            ctx.bot.send(f'Rolling {sides} sided die...')
            time.sleep(3)
            ctx.bot.send(str(result))
        else:
            ctx.bot.send(strings.roll.number_error)
    except ValueError:
        ctx.bot.send(strings.roll.number_error)


@GroupMeBot.command('flip')
def flip(ctx: CommandContext):
    """
    Flips a coin and sends 'Heads' or 'Tails'
    """
    ctx.bot.send('Flipping coin...')
    time.sleep(5)
    result = RNG.randint(0, 1)

    if result == 0:
        ctx.bot.send('Heads')
    else:
        ctx.bot.send('Tails')


@GroupMeBot.command('jpeg', extra_args=True)
def jpegify(ctx: CommandContext):
    """
    Turns any image into a terrible quality .jpeg image
    """
    img_path = io.BytesIO(urllib.request.urlopen(ctx.message).read())
    img = Image.open(img_path)

    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    # Absolutely devastate the image
    width, height = img.width, img.height
    img = img.resize((int(width ** .75), int(height ** .75)), resample=Image.LANCZOS)
    img = img.resize((int(width ** .88), int(height ** .88)), resample=Image.BILINEAR)
    img = img.resize((int(width ** .9), int(height ** .9)), resample=Image.BICUBIC)
    img = img.resize((width, height), resample=Image.BICUBIC)
    img = ImageOps.posterize(img, 4)

    # Generate red and yellow overlay for classic deepfry effect
    r = img.split()[0]
    r = ImageEnhance.Contrast(r).enhance(2.0)
    r = ImageEnhance.Brightness(r).enhance(1.5)
    r = ImageOps.colorize(r, (254, 0, 2), (255, 255, 15))

    # Overlay red and yellow onto main image and sharpen
    img = Image.blend(img, r, 0.75)
    img = ImageEnhance.Sharpness(img).enhance(100.0)

    temp = io.BytesIO()
    img.save(temp, format='JPEG')
    temp.seek(0)

    with open('tempjpg.jpeg', 'wb') as f:
        f.write(temp.read())

    img_attach = groupme.create_image_attachment('tempjpg.jpeg')
    ctx.bot.send(img_attach.url)
    temp.close()


@GroupMeBot.command('everyone')
def everyone(ctx: CommandContext):
    """
    Mentions everyone in a GroupMe group
    """
    user_ids = [member.user_id for member in ctx.bot.members]
    usernames = ['@' + member.nickname for member in ctx.bot.members]

    index = 0
    loci = []
    for user in usernames:
        loci.append([index, len(user)])
        index += len(user) + 1

    mentions = attachments.Mentions(loci=loci, user_ids=user_ids)
    ctx.bot.send('@everyone', attachments=[mentions])


@GroupMeBot.command('remindme', extra_args=True)
def remindme(ctx: CommandContext):
    """
    Allows users to set reminders within a GroupMe Group.
    Mentions users to remind them.
    """
    try:
        amount = abs(int(ctx.message.split()[0]))
        unit = ctx.message.split()[1]
        if amount > 1 and unit[-1] != 's':
            unit += 's'
        elif amount < 2 and unit[-1] == 's':
            unit = unit[:-1]
    except ValueError:
        ctx.bot.send(f'{ctx.message.split(" ", 2)[0]} is not a valid measurement of time')
        return

    message = ctx.message.split(' ', 2)[2]

    if 'minute' in unit:
        remind_time = datetime.now() + relativedelta(minutes=+amount)
    elif 'hour' in unit:
        remind_time = datetime.now() + relativedelta(hours=+amount)
    elif 'day' in unit:
        remind_time = datetime.now() + relativedelta(days=+amount)
    elif 'week' in unit:
        remind_time = datetime.now() + relativedelta(weeks=+amount)
    elif 'month' in unit:
        remind_time = datetime.now() + relativedelta(months=+amount)
    elif 'year' in unit:
        remind_time = datetime.now() + relativedelta(years=+amount)
    else:
        ctx.bot.send(strings.remindme.unit_error)

    new_reminder = Reminder(ctx.sender.user_id, ctx.group_id, message, remind_time)
    db.session.add(new_reminder)
    db.session.commit()

    ctx.bot.send(f'I will remind you in {amount} {unit} about {message}')


@GroupMeBot.command('summary', queue=True)
def summary(ctx: CommandContext):
    """
    Gives a brief stat summary of the past 2 hours
    """
    tstamp = ctx.bot.group.messages.list()[0].created_at - timedelta(hours=2)
    messages = groupme.load_messages(ctx.bot, tstamp)
    member_info = {
        'likes_given': {},
        'likes_recv': {},
        'messages': {},
        'ratio': {},
    }
    for member in ctx.bot.members:
        member_info['likes_given'][member.user_id] = 0
        member_info['likes_recv'][member.user_id] = 0
        member_info['messages'][member.user_id] = 0
        member_info['ratio'][member.user_id] = 0

    message_count = len(messages)
    total_likes = 0
    most_likes = 0
    most_liked_msg = None
    for message in messages:
        try:
            member_info['likes_recv'][message.user_id] += len(message.favorited_by)
            member_info['messages'][message.user_id] += 1
        except KeyError:
            pass

        if len(message.favorited_by) > most_likes:
            most_likes = len(message.favorited_by)
            if message.attachments:
                for attachment in message.attachments:
                    if attachment.type == 'image':
                        most_liked_msg = attachment.url
            else:
                most_liked_msg = message.text

        for like in message.favorited_by:
            try:
                member_info['likes_given'][like] += 1
            except KeyError:
                pass
            total_likes += 1

    for member in ctx.bot.members:
        try:
            ratio = member_info['likes_recv'][member.user_id] / member_info['messages'][member.user_id]
            member_info['ratio'][member.user_id] = round(ratio, 2)
        except ZeroDivisionError:
            member_info['ratio'][member.user_id] = 0.0

    # TODO make this not terrible
    max_recv = utils.max_dict(member_info['likes_recv'])
    max_given = utils.max_dict(member_info['likes_given'])
    max_msg = utils.max_dict(member_info['messages'])
    max_ratio = utils.max_dict(member_info['ratio'])
    recv_name = groupme.get_member(ctx.group_id, user_id=max_recv).nickname
    give_name = groupme.get_member(ctx.group_id, user_id=max_given).nickname
    msg_name = groupme.get_member(ctx.group_id, user_id=max_msg).nickname
    ratio_name = groupme.get_member(ctx.group_id, user_id=max_ratio).nickname
    recv = member_info['likes_recv'][max_recv]
    given = member_info['likes_given'][max_given]
    sent = member_info['messages'][max_msg]
    ratio = member_info['ratio'][max_ratio]

    message = (f'Summary of the past 2 hours:\n\n'
               f'Messages sent: {message_count}\n'
               f'Likes given out: {total_likes}\n\n'
               f'Most likes received:\n\xa0\xa0{recv_name} - {recv}\n'
               f'Most likes given:\n\xa0\xa0{give_name} - {given}\n'
               f'Most messages sent:\n\xa0\xa0{msg_name} - {sent}\n'
               f'Best best like/message ratio:\n\xa0\xa0{ratio_name} - {ratio}\n\n'
               f'Most liked message ({most_likes} likes):\n{most_liked_msg}')

    ctx.bot.send(message)


@GroupMeBot.command('randgal')
def random_gallery(ctx: CommandContext):
    """
    Gets a random gallery picture and sends it to the group
    """
    group = groupme.get_group(ctx.group_id)
    gallery_list = list(group.gallery.list_all())
    random_pic = random.choice(gallery_list)
    for attachment in random_pic.attachments:
        if attachment.type == 'image':
            ctx.bot.send(attachment.url)


@GroupMeBot.command('someone')
def someone(ctx: CommandContext):
    """
    Mentions a random person in a group
    """
    member = random.choice(ctx.bot.members)
    mentions = attachments.Mentions(loci=[[0, len(member.nickname) + 1]],
                                    user_ids=[member.user_id])
    ctx.bot.send(f'@{member.nickname}', attachments=[mentions])
