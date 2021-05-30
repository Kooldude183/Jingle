print("Loading libraries...")
from discord import guild
import discord, os, sys, yaml, traceback
from jingle import db, prefix, main, player, botsettings
from discord.ext.commands.errors import CommandNotFound
from discord.ext import commands
from discord.ext.commands import CommandNotFound
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from importlib import reload

dbconn = db.dbconn

f = open(os.path.join(sys.path[0], "config.yml"), "r")
config = yaml.load(f, Loader=yaml.FullLoader)
defprefix = config["prefix"]
token = config["token"]
authorized_users = config["authorized_users"]

async def serverprefix(client, message):
    try: result = await dbconn("ifexists", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(message.guild.id), "")
    except: return defprefix
    else:
        if result: return result[2]
        else:
            try: await dbconn("newentry", "INSERT INTO settings(guild_id, prefix, current) VALUES('{0}', '{1}', '0')".format(message.guild.id, defprefix), "")
            except: pass
            finally: return defprefix

client = commands.Bot(command_prefix=serverprefix, help_command=None)
slash = SlashCommand(client, sync_commands=True, override_type=True)

print("Jingle v{0}".format(main.getversion()))

@client.event
async def on_ready():
    print("Bot is now running")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="{0}help".format(defprefix)))
    await dbconn("createtables", "", "")

@client.event
async def on_message(message):
    botprefix = await prefix.serverprefix(message)
    try: message.content[0]
    except: return
    if botprefix == "$" and message.content[0] == "$":
        command = message.content[1:]
        if command.isnumeric(): return
        elif "." in command and command[command.find("$") + 1:command.find(".")].isnumeric(): return
        elif " " in command and command[command.find("$") + 1:command.find(" ")].isnumeric(): return
    if not message.content == "{0}reload".format(botprefix):
        await client.process_commands(message)
        return
    if not message.author.id in authorized_users:
        await message.channel.send("```Insufficient permissions```")
        await client.process_commands(message)
        return
    try:
        reload(db)
        reload(main)
        reload(player)
    except:
        await message.channel.send("An exception has occurred: ```{0}```".format(traceback.format_exc()))
    else:
        await message.channel.send("Successfully reloaded modules")

@slash.slash(name="help", description="List bot commands")
async def help(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await main.help(ctx)

@client.command()
async def help(ctx, command=None):
    await main.help(ctx, command)

@slash.slash(name="p", description="Play music from a YouTube video, Spotify track or playlist, or search term", options=[create_option(name="query", description="The URL or title", option_type=3, required=True)])
async def p(ctx:SlashContext, **kwargs):
    await prefix.serverprefix(ctx)
    arg = []
    arg.append(kwargs["query"])
    await player.play(ctx, arg)

@client.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def p(ctx, *args):
    await player.play(ctx, args)

@slash.slash(name="play", description="Play music from a YouTube video, Spotify track or playlist, or search term", options=[create_option(name="query", description="The URL or title", option_type=3, required=True)])
async def play(ctx:SlashContext, **kwargs):
    await prefix.serverprefix(ctx)
    arg = []
    arg.append(kwargs["query"])
    await player.play(ctx, arg)

@client.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def play(ctx, *args):
    await player.play(ctx, args)

@slash.slash(name="j", description="Make the bot join the channel")
async def j(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.join(ctx)

@client.command()
async def j(ctx, arg=None):
    await player.join(ctx, arg)

@slash.slash(name="join", description="Make the bot join the channel")
async def join(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.join(ctx)

@client.command()
async def join(ctx, arg=None):
    await player.join(ctx, arg)

@slash.slash(name="q", description="List the song queue")
async def q(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.fetchqueue(ctx)

@client.command()
async def q(ctx):
    await player.fetchqueue(ctx)

@slash.slash(name="queue", description="List the song queue")
async def queue(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.fetchqueue(ctx)

@client.command()
async def queue(ctx):
    await player.fetchqueue(ctx)

@slash.slash(name="dc", description="Disconnect the bot")
async def dc(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.disconnect(ctx)

@client.command()
async def dc(ctx):
    await player.disconnect(ctx)

@slash.slash(name="disconnect", description="Disconnect the bot")
async def disconnect(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.disconnect(ctx)

@client.command()
async def disconnect(ctx):
    await player.disconnect(ctx)

@slash.slash(name="l", description="Disconnect the bot")
async def l(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.disconnect(ctx)

@client.command()
async def l(ctx):
    await player.disconnect(ctx)

@slash.slash(name="leave", description="Disconnect the bot")
async def leave(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.disconnect(ctx)

@client.command()
async def leave(ctx):
    await player.disconnect(ctx)

@slash.slash(name="stop", description="Stop the currently playing song")
async def stop(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.stop(ctx, "stop")

@client.command()
async def stop(ctx):
    await player.stop(ctx, "stop")

@slash.slash(name="skip", description="Skip the current track")
async def skip(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.stop(ctx, "skip")

@client.command()
async def skip(ctx):
    await player.stop(ctx, "skip")

@slash.slash(name="c", description="Clear the queue")
async def c(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.clear(ctx)

@client.command()
async def c(ctx):
    await player.clear(ctx)

@slash.slash(name="clear", description="Clear the queue")
async def clear(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.clear(ctx)

@client.command()
async def clear(ctx):
    await player.clear(ctx)

@slash.slash(name="remove", description="Remove a song from the queue", options=[create_option(name="position", description="The position of the song in the queue", option_type=4, required=True)])
async def remove(ctx:SlashContext, position):
    await prefix.serverprefix(ctx)
    await player.remove(ctx, position)

@client.command()
async def remove(ctx, position):
    await player.remove(ctx, position)

@slash.slash(name="r", description="Remove a song from the queue", options=[create_option(name="position", description="The position of the song in the queue", option_type=4, required=True)])
async def r(ctx:SlashContext, position):
    await prefix.serverprefix(ctx)
    await player.remove(ctx, position)

@client.command()
async def r(ctx, position):
    await player.remove(ctx, position)

@slash.slash(name="loop", description="Loop the queue")
async def loop(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.loop(ctx)

@client.command()
async def loop(ctx):
    await player.loop(ctx)

@slash.slash(name="shuffle", description="Shuffle the queue")
async def shuffle(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.shuffle(ctx)

@client.command()
async def shuffle(ctx):
    await player.shuffle(ctx)

@slash.slash(name="pause", description="Pause the player")
async def pause(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.pause(ctx)

@client.command()
async def pause(ctx):
    await player.pause(ctx)

@slash.slash(name="resume", description="Resume the player")
async def resume(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.resume(ctx)

@client.command()
async def resume(ctx):
    await player.resume(ctx)

@slash.slash(name="lyrics", description="Get lyrics for the currently playing song")
async def lyrics(ctx:SlashContext):
    await prefix.serverprefix(ctx)
    await player.lyrics(ctx)

@client.command()
async def lyrics(ctx):
    await player.lyrics(ctx)

@client.command()
async def settings(ctx, setting=None):
    await botsettings.serversettings(ctx, setting, client)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        await ctx.send(embed=discord.Embed(description="Unknown command.", color=discord.Color.red()))
        return
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=discord.Embed(description="Please wait {0} seconds before using this command.".format(int(error.retry_after)), color=discord.Color.red()))
        return
    raise error

print("Starting bot...")
client.run(token)