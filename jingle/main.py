import discord
from jingle import prefix
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType

serverprefix = prefix.serverprefix

version = "0.9.1"

def getversion():
    return version

async def help(ctx, command):
    prefix = await serverprefix(ctx)

    embed = discord.Embed(title="Jingle Commands")
    embed.add_field(name=":arrow_forward: Play Music", value="`{0}play [URL or title]`\nPlay music from a YouTube video, Spotify track or playlist, or search term".format(prefix), inline=True)
    embed.add_field(name=":page_with_curl: Queue", value="`{0}queue`\nList the song queue".format(prefix), inline=True)
    embed.add_field(name=":white_check_mark: Join", value="`{0}join`\nMake the bot join the channel".format(prefix), inline=True)
    embed.add_field(name=":x: Disconnect", value="`{0}join`\nDisconnect the bot".format(prefix), inline=True)
    embed.add_field(name=":stop_button: Stop", value="`{0}stop`\nStop the currently playing song".format(prefix), inline=True)
    embed.add_field(name=":pause_button: Pause", value="`{0}stop`\nPause the currently playing song".format(prefix), inline=True)
    embed.add_field(name=":arrow_forward: Resume", value="`{0}resume`\nResume the currently playing song (when paused)".format(prefix), inline=True)
    embed.add_field(name=":track_next: Skip", value="`{0}skip`\nSkip the current track".format(prefix), inline=True)
    embed.add_field(name=":o: Clear", value="`{0}clear`\nClear the queue".format(prefix), inline=True)
    embed.add_field(name=":repeat: Loop", value="`{0}loop`\nLoop the queue".format(prefix), inline=True)
    embed.add_field(name=":twisted_rightwards_arrows: Shuffle", value="`{0}shuffle`\nShuffle the queue".format(prefix), inline=True)
    embed.add_field(name=":page_facing_up: Lyrics", value="`{0}lyrics`\nGet lyrics for the currently playing song".format(prefix), inline=True)
    embed.add_field(name=":gear: Settings", value="`{0}settings`\nConfigure the bot's settings for this server".format(prefix), inline=True)
    # embed.add_field(name="Links", value="[Website](https://jingle.kdgaming.net) | [Privacy](https://nwsbot.kdgaming.net/privacy)", inline=False)
    embed.set_footer(text="Jingle v{0} | Developed by Kooldude183#4986 | Website: https://jingle.kdgaming.net".format(version))
    await ctx.send(embed=embed, components=[[Button(style=5, label="Website", url="https://jingle.kdgaming.net"), Button(style=5, label="Privacy", url="https://nwsbot.kdgaming.net/privacy")]])