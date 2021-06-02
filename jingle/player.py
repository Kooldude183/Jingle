import urllib, re, discord, asyncio, spotipy, random, lyricsgenius, traceback, os, sys, string, yaml
from datetime import datetime
from aiohttp_requests import requests
from jingle import prefix, db
from youtube_dl import YoutubeDL
from youtubesearchpython.__future__ import VideosSearch, Video, Playlist
from spotipy.oauth2 import SpotifyClientCredentials
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
from discord import PartialEmoji

dbconn = db.dbconn
serverprefix = prefix.serverprefix

f = open(os.path.join(sys.path[0], "config.yml"), "r")
config = yaml.load(f, Loader=yaml.FullLoader)

genius = lyricsgenius.Genius(config["lyrics"]["genius_access_token"])
genius.verbose = False
genius.remove_section_headers = True
genius.excluded_terms = ["(Live)"]

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=config["spotify"]["client_id"], client_secret=config["spotify"]["client_secret"]))

ydl_opts = {'format': 'bestaudio/best', 'noplaylist':'True', 'youtube_include_dash_manifest': False, 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'aac', 'preferredquality': '192'}]}
ydl_opts_pl = {'format': 'bestaudio/best', 'youtube_include_dash_manifest': False, 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'aac', 'preferredquality': '192'}]}

stopped = []
skipped = []

async def queuebuttons(cpg, pgs):
    prevdisabled = False
    nextdisabled = False
    if cpg == 1: prevdisabled = True
    if cpg == pgs: nextdisabled = True
    return [[Button(style=ButtonStyle.blue, id="previous queue {0}".format(cpg), label="❮", disabled=prevdisabled), Button(style=ButtonStyle.grey, id="page queue", label="Page {0} / {1}".format(cpg, pgs), disabled=True), Button(style=ButtonStyle.blue, id="next queue {0}".format(cpg), label="❯", disabled=nextdisabled), Button(style=ButtonStyle.blue, id="refresh queue", label="Refresh", emoji=PartialEmoji(name="🔄"))], [Button(style=ButtonStyle.green, id="loop queue", label="Loop", emoji=PartialEmoji(name="🔁")), Button(style=ButtonStyle.green, id="shuffle queue", label="Shuffle", emoji=PartialEmoji(name="🔀")), Button(style=ButtonStyle.red, id="clear queue", label="Clear", emoji=PartialEmoji(name="⭕"))]]

async def getintidofcurrentsong(ctx):
    try: queue = await dbconn("fetchqueue", "", ctx.guild.id)
    except Exception as e:
        await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
        await ctx.channel.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
        return False
    try:
        current = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 3)
        current = int(current)
    except Exception as e:
        await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
        await ctx.channel.send(embed=discord.Embed(description="Unable to fetch the current position in the queue.", color=discord.Color.red()))
        return False
    try: intid = queue[current - 1][0]
    except Exception as e: return False
    return intid

async def checkifpaused(ctx):
    try:
        paused = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 8)
        try: paused = int(paused)
        except: paused = False
        else:
            if paused == 1: paused = True
            else: paused = False
    except Exception as e:
        await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
        await ctx.channel.send(embed=discord.Embed(description="Unable to determine if the player was paused.", color=discord.Color.red()))
        return False
    intid = await getintidofcurrentsong(ctx)
    if not intid: return False, False
    return paused, intid

async def startqueue(ctx, info, player):
    try: await dbconn("newentry", "UPDATE `settings` SET `stop` = '0' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        return
    try: await dbconn("newentry", "UPDATE `settings` SET `pause` = '0' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        return
    try:
        stopped.remove(ctx.guild.id)
        skipped.remove(ctx.guild.id)
    except: pass
    while True:
        try: queue = await dbconn("fetchqueue", "", ctx.guild.id)
        except Exception as e:
            await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
            await ctx.channel.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
            return
        try:
            current = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 3)
            current = int(current)
        except Exception as e:
            await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
            await ctx.channel.send(embed=discord.Embed(description="Unable to fetch the current position in the queue.", color=discord.Color.red()))
            return
        try: queue[current]
        except:
            try: loopmode = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 4)
            except: return
            try: int(loopmode)
            except: return
            else:
                if not int(loopmode) == 1: return
                current = 0
                await dbconn("newentry", "UPDATE `settings` SET `current` = '{0}' WHERE `guild_id` = '{1}'".format(current, ctx.guild.id), "")
        hours = 0
        minutes = 0
        seconds = round(int(queue[current][4]) / 1000)
        duration = ""
        while seconds >= 60:
            seconds -= 60
            minutes += 1
        while minutes >= 60:
            minutes -= 60
            hours += 1
        if len(str(minutes)) == 1 and not hours == 0: minutes = "0{0}".format(minutes)
        if len(str(seconds)) == 1: seconds = "0{0}".format(seconds)
        if not hours == 0: duration = "{0}:{1}:{2}".format(hours, minutes, seconds)
        else: duration = "{0}:{1}".format(minutes, seconds)
        serviceicon = ""
        if "https://open.spotify.com/" in queue[current][3]: serviceicon = "<:spotify:844277927604125696>"
        elif "https://music.apple.com/" in queue[current][3]: serviceicon = "<:apple_music:844280729395134466>"
        elif "https://www.youtube.com/" in queue[current][3]: serviceicon = "<:youtube:844282392616894504>"
        # embed = discord.Embed(title="Now Playing", description="{0} [{1}]({2}) `[{3}]`".format(serviceicon, queue[current][2], queue[current][3], duration), color=discord.Color.blue())
        # songinfo = await ctx.channel.send(embed=embed)
        if not "https://open.spotify.com/track/" in queue[current][3] and not "https://music.apple.com/" in queue[current][3]:
            try:
                with YoutubeDL(ydl_opts) as ydl: videoinfo = ydl.extract_info(queue[current][3], download=False)
            except Exception as e:
                error = str(e)
                if "Sign in to confirm your age" in error: await ctx.channel.send(embed=discord.Embed(description="The track **{0}** is age restricted on YouTube.".format(queue[current][2]), color=discord.Color.red()))
                else:
                    await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
                    await ctx.channel.send(embed=discord.Embed(description="Unable to play the song in the queue.", color=discord.Color.red()))
                try: await dbconn("newentry", "UPDATE `settings` SET `current` = '{0}' WHERE `guild_id` = '{1}'".format(current + 1, ctx.guild.id), "")
                except Exception as e: 
                    await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
                    await ctx.channel.send(embed=discord.Embed(description="Unable to update the queue.", color=discord.Color.red()))
                    return
                continue
            videourl = videoinfo['formats'][0]['url']
        else:
            searchquery = "{0} (Official Audio)".format(queue[current][2])
            if "Various Artists - " in searchquery: searchquery = searchquery.replace("Various Artists - ", "")
            searchlimit = 10
            search = VideosSearch(searchquery, limit = searchlimit)
            resultduration = -50000
            try: page = await search.next()
            except:
                await ctx.channel.send(embed=discord.Embed(description="YouTube returned an invalid response while searching song **{0}**.".format(queue[current][2]), color=discord.Color.red()))
                continue
            index = 0
            while not abs(int(resultduration) - int(queue[current][4])) <= 10000:
                if index == searchlimit:
                    await ctx.channel.send(embed=discord.Embed(description="No YouTube results found for **{0}**.".format(queue[current][2]), color=discord.Color.red()))
                    break
                try: videoresult = page["result"][index]
                except:
                    index +=1
                    continue
                #   break
                colons = 0
                try: ytdn = videoresult["duration"]
                except:
                    index += 1
                    continue
                try:
                    while ":" in ytdn:
                        ytdn = ytdn[ytdn.find(":") + 1:]
                        colons += 1
                except:
                    index += 1
                    continue
                resultduration = 0
                tempdn = videoresult["duration"]
                hrs = 0
                mins = 0
                secs = 0
                if colons == 1:
                    mins = tempdn[:tempdn.find(":")]
                    secs = tempdn[tempdn.find(":") + 1:]
                    resultduration += (int(mins) * 60000) + (int(secs) * 1000)
                else:
                    hrs = tempdn[:tempdn.find(":")]
                    tempdn = tempdn[tempdn.find(":") + 1:]
                    mins = tempdn[:tempdn.find(":")]
                    secs = tempdn[tempdn.find(":") + 1:]
                    resultduration += (int(hrs) * 3600000) + (int(mins) * 60000) + (int(secs) * 1000)
                # print("Ms: " + str(ms))
                # tryindex = 0
                # video = None
                # while not video:
                #     if tryindex == 5:
                #         await songinfo.edit(embed=discord.Embed(description="YouTube returned an invalid response while searching song **{0}**.".format(queue[current][2]), color=discord.Color.red()))
                #         break
                #     try: video = await Video.get(videoresult["id"])
                #     except:
                #         tryindex += 1
                index += 1
                # try: resultduration = video["streamingData"]["adaptiveFormats"][0]["approxDurationMs"]
                # except: break
                print(abs(int(resultduration) - int(queue[current][4])))
                print(videoresult["id"])
            if index == searchlimit:
                try: await dbconn("newentry", "UPDATE `settings` SET `current` = '{0}' WHERE `guild_id` = '{1}'".format(current + 1, ctx.guild.id), "")
                except Exception as e: 
                    await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
                    await ctx.channel.send(embed=discord.Embed(description="Unable to update the queue.", color=discord.Color.red()))
                    return
                continue
            try:
                # statuscode = 0
                # while not statuscode == 200:
                videourl = "https://www.youtube.com/watch?v={0}".format(videoresult["id"])
                rs = ''.join(random.choice(string.ascii_letters) for i in range(24))
                videourl = "{0}?{1}".format(videourl, rs)
                try:
                    with YoutubeDL(ydl_opts) as ydl: videoinfo = ydl.extract_info(videourl, download=False)
                except Exception as e:
                    error = str(e)
                    if "Sign in to confirm your age" in error: await ctx.channel.send(embed=discord.Embed(description="The track **{0}** is age restricted on YouTube.".format(queue[current][2]), color=discord.Color.red()))
                    else:
                        await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
                        await ctx.channel.send(embed=discord.Embed(description="Unable to play the song in the queue.", color=discord.Color.red()))
                    try: await dbconn("newentry", "UPDATE `settings` SET `current` = '{0}' WHERE `guild_id` = '{1}'".format(current + 1, ctx.guild.id), "")
                    except Exception as e: 
                        await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
                        await ctx.channel.send(embed=discord.Embed(description="Unable to update the queue.", color=discord.Color.red()))
                        return
                    continue
                videourl = videoinfo['formats'][0]['url']
                a = datetime.now()
                #
                rs = ''.join(random.choice(string.ascii_letters) for i in range(24))
                reqvideourl = "{0}?{1}".format(videourl, rs)
                    #
                    # try:
                    #     print("S1")
                    #     videorequest = await requests.get(reqvideourl, timeout=10)
                    #     print("S2")
                    #     statuscode = videorequest.status
                    #     print("S3")
                    #     print("Status code: " + str(statuscode))
                    #     b = datetime.now()
                    #     responsetime = int(round((((b - a).seconds * 1000) + ((b - a).microseconds / 1000))))
                    #     print("Response time: " + str(responsetime))
                    # except Exception as e:
                    #     print(e)
                    #     print(reqvideourl)
                    #     print("Exc status code: " + str(statuscode))
                    #     continue
            except: break
            try: videourl
            except: continue
        embed = discord.Embed(title="Now Playing", description="{0} [{1}]({2}) `[{3}]`".format(serviceicon, queue[current][2], queue[current][3], duration), color=discord.Color.blue())
        songinfo = await ctx.channel.send(embed=embed, components=[[Button(style=ButtonStyle.green, id="pause np", label="Pause", emoji=PartialEmoji(name="⏸")), Button(style=ButtonStyle.red, id="stop np", label="Stop", emoji=PartialEmoji(name="⏹")), Button(style=ButtonStyle.blue, id="skip np", label="Skip", emoji=PartialEmoji(name="⏭")), Button(style=ButtonStyle.grey, id="lyrics np", label="Lyrics", emoji=PartialEmoji(name="📄")), Button(style=ButtonStyle.grey, id="queue np", label="Queue", emoji=PartialEmoji(name="📃"))]])
        try: player.play(discord.FFmpegOpusAudio(videourl, options="-vn -filter:a \"volume=0.2\" -b:a 192k", before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"))
        except Exception as e:
            await songinfo.delete()
            error = str(e)
            if not error == "Already playing audio.":
                await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
                await ctx.channel.send(embed=discord.Embed(description="Unable to play the song in the queue.", color=discord.Color.red()))
            return
        else:
            try: await dbconn("newentry", "UPDATE `settings` SET `current` = '{0}' WHERE `guild_id` = '{1}'".format(current + 1, ctx.guild.id), "")
            except Exception as e:
                await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
                await ctx.channel.send(embed=discord.Embed(description="Unable to update the queue.", color=discord.Color.red()))
                return
        while True:
            while player.is_playing(): await asyncio.sleep(0.1)
            paused, intid = await checkifpaused(ctx)
            if paused:
                await songinfo.edit(embed=embed, components=[[Button(style=ButtonStyle.green, id="resume np", label="Resume", emoji=PartialEmoji(name="▶")), Button(style=ButtonStyle.red, id="stop np", label="Stop", emoji=PartialEmoji(name="⏹")), Button(style=ButtonStyle.blue, id="skip np", label="Skip", emoji=PartialEmoji(name="⏭")), Button(style=ButtonStyle.grey, id="lyrics np", label="Lyrics", emoji=PartialEmoji(name="📄")), Button(style=ButtonStyle.grey, id="queue np", label="Queue", emoji=PartialEmoji(name="📃"))]])
                intidcheck = intid
                while paused:
                    await asyncio.sleep(0.5)
                    if ctx.guild.id in stopped:
                        stopped.remove(ctx.guild.id)
                        return
                    if ctx.guild.id in skipped: break
                    paused, intid = await checkifpaused(ctx)
                    if not paused and not intid: return
                if ctx.guild.id in skipped:
                    skipped.remove(ctx.guild.id)
                    break
                intid = await getintidofcurrentsong(ctx)
                if not intid == intidcheck: return
                await songinfo.edit(embed=embed, components=[[Button(style=ButtonStyle.green, id="pause np", label="Pause", emoji=PartialEmoji(name="⏸")), Button(style=ButtonStyle.red, id="stop np", label="Stop", emoji=PartialEmoji(name="⏹")), Button(style=ButtonStyle.blue, id="skip np", label="Skip", emoji=PartialEmoji(name="⏭")), Button(style=ButtonStyle.grey, id="lyrics np", label="Lyrics", emoji=PartialEmoji(name="📄")), Button(style=ButtonStyle.grey, id="queue np", label="Queue", emoji=PartialEmoji(name="📃"))]])
                player.resume()
            else: break
        await songinfo.delete()
        try: stop = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 7)
        except: return
        stop = int(stop)
        if stop == 1:
            try: await dbconn("newentry", "UPDATE `settings` SET `stop` = '0' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
            except: pass
            return
        if not ctx.guild.voice_client: return

async def fetchqueue(ctx, client, page, mode):
    default = False
    if page == 0: default = True
    try: queue = await dbconn("fetchqueue", "", ctx.guild.id)
    except Exception as e:
        try:
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
        except:
            await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
            await ctx.channel.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
        return
    try: 
        current = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 3)
        current = int(current)
    except Exception as e:
        try:
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to fetch the current position in the queue.", color=discord.Color.red()))
        except:
            await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
            await ctx.channel.send(embed=discord.Embed(description="Unable to fetch the current position in the queue.", color=discord.Color.red()))
        return
    songs = ""
    displayedsongs = ""
    index = 0
    currentpage = 0
    for song in queue:
        index += 1
        indent = "     "
        for i in range(len(str(index))): indent = indent[1:]
        nowplaying = ""
        if float(current) == index and ctx.guild.voice_client:
            if not ctx.guild.voice_client.is_playing(): return
            nowplaying = ":arrow_forward: "
            if default == True: page = currentpage + 1
        hours = 0
        minutes = 0
        seconds = round(int(song[4]) / 1000)
        duration = ""
        while seconds >= 60:
            seconds -= 60
            minutes += 1
        while minutes >= 60:
            minutes -= 60
            hours += 1
        if len(str(minutes)) == 1 and not hours == 0: minutes = "0{0}".format(minutes)
        if len(str(seconds)) == 1: seconds = "0{0}".format(seconds)
        if not hours == 0: duration = "{0}:{1}:{2}".format(hours, minutes, seconds)
        else: duration = "{0}:{1}".format(minutes, seconds)
        songtitle = song[2]
        if "*" in songtitle: songtitle = songtitle.replace("*", "\*")
        line = "\n{0}.{1}{2}{3} `[{4}]`".format(index, indent, nowplaying, songtitle, duration)
        if len(songs) + len(line) > 2048:
            if default == True:
                if ":arrow_forward:" in songs:
                    displayedsongs = songs
                    songs = ""
                    currentpage += 1
                else:
                    songs = ""
                    currentpage += 1
            elif not currentpage + 1 == page:
                songs = ""
                currentpage += 1
            else:
                displayedsongs = songs
                songs = ""
                currentpage += 1
        songs += line
    if displayedsongs == "":
        displayedsongs = songs
    if page == 0: page = 1
    currentpage += 1
    try: shufflemode = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 5)
    except: queuetitle = "Queue"
    try: int(shufflemode)
    except: queuetitle = "Queue"
    else:
        if int(shufflemode) == 1: queuetitle = "Shuffled Queue"
        else: queuetitle = "Queue"
    embed = discord.Embed(title=queuetitle, description=displayedsongs, color=discord.Color.blue())
    embed.set_footer(text="{0} tracks".format(len(queue)))
    rs = ''.join(random.choice(string.ascii_letters) for i in range(24))
    if mode == 1:
        try: await ctx.send(embed=embed, components=await queuebuttons(page, currentpage))
        except: await ctx.channel.send(embed=embed, components=await queuebuttons(page, currentpage))
    else: return embed, page, currentpage

async def addtoshufflequeue(ctx, info):
    try:
        shufflemode = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 5)
    except Exception as e:
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to add the song to the shuffle queue.", color=discord.Color.red()))
        return
    try: int(shufflemode)
    except: return
    if int(shufflemode) == 1:
        try: intid = await dbconn("getvalue", "SELECT * FROM `queue` WHERE `guild_id` = '{0}' ORDER BY `int_id` DESC".format(ctx.guild.id), 0)
        except Exception as e:
            await ctx.send("An exception has occurred: ```{0}```".format(traceback.format_exc()))
            await ctx.send(embed=discord.Embed(description="Unable to add the song to the shuffle queue.", color=discord.Color.red()))
            return
        try: await dbconn("newentry", "UPDATE `queue` SET `shuffle_int` = '{0}' WHERE `int_id` = '{0}'".format(intid), "")
        except Exception as e:
            await ctx.send("An exception has occurred: ```{0}```".format(traceback.format_exc()))
            await ctx.send(embed=discord.Embed(description="Unable to add the song to the shuffle queue.", color=discord.Color.red()))
            return

async def addtoqueue(ctx, args, info, player):
    url = args[0]
    if "http://" in url[0:7]: url = url.replace("http://", "https://")
    if "https://youtu.be/" in url: url = url.replace("https://youtu.be/", "https://www.youtube.com/watch?v=")
    if "<" in url: url = url.replace("<", "")
    if ">" in url: url = url.replace(">", "")
    if not "https://www.youtube.com/watch?v=" in url and not "https://www.youtube.com/playlist?list=" in url and not "https://open.spotify.com/playlist/" in url and not "https://open.spotify.com/album/" in url and not "https://open.spotify.com/track/" in url and not "https://music.apple.com/us/playlist/" in url and not "https://music.apple.com/us/album/" in url:
        if "https://" in url:
            await info.edit(embed=discord.Embed(description="Please input a valid YouTube video, Spotify track/playlist URL, or Apple Music playlist URL. Other services are not supported at this time.", color=discord.Color.red()))
            return
        query = ""
        for arg in args:
            query += arg
            query += " "
        query = query[:-1]
        await info.edit(embed=discord.Embed(description="Searching for video...", color=discord.Color.gold()))
        search = VideosSearch(query, limit = 1)
        try: page = await search.next()
        except: await info.edit(embed=discord.Embed(description="YouTube returned an invalid response.", color=discord.Color.red()))
        try: videoresult = page["result"][0]
        except:
            await info.edit(embed=discord.Embed(description="No results found.", color=discord.Color.red()))
            return
        try: video = await Video.get(videoresult["id"])
        except Exception as e:
            await info.edit(embed=discord.Embed(description=e, color=discord.Color.red()))
            return
        try: title = video["title"]
        except Exception as e:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to add the song to the queue. Please try again later.", color=discord.Color.red()))
            return
        videourl = "https://www.youtube.com/watch?v={0}".format(videoresult["id"])
        try: duration = video["streamingData"]["adaptiveFormats"][0]["approxDurationMs"]
        except Exception as e:
            await info.edit(embed=discord.Embed(description="Could not find a valid format to download for this video. The video might also be age restricted.", color=discord.Color.red()))
            return
        if '"' in title: title = title.replace('"', '\\"')
        try: await dbconn("newentry", "INSERT INTO queue(guild_id, title, url, duration) VALUES('{0}', \"{1}\", '{2}', '{3}')".format(ctx.guild.id, title, videourl, duration), "")
        except Exception as e:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to add the song to the queue. Please try again later.", color=discord.Color.red()))
            return
        else: await info.edit(embed=discord.Embed(description="Successfully added <:youtube:844282392616894504> **{0}** to the queue.".format(title), color=discord.Color.green()))
        await addtoshufflequeue(ctx, info)
    else:
        if "https://www.youtube.com/watch?v=" in url or "https://www.youtube.com/playlist?list=" in url:
            await info.edit(embed=discord.Embed(description="Verifying URL...", color=discord.Color.gold()))
            if "list=" in url:
                if "&list=" in url: url = "https://www.youtube.com/playlist?list={0}".format(url[url.find("&list=") + 6:])
                try:
                    playlist = Playlist(url)
                    # .getVideos(url)
                    while playlist.hasMoreVideos: await playlist.getNextVideos()
                    playlist = playlist.videos
                except Exception as e:
                    await info.edit(embed=discord.Embed(description=e, color=discord.Color.red()))
                    return
                index = 0
                for video in playlist:
                    try: title = video["title"]
                    except: continue
                    videourl = "https://www.youtube.com/watch?v={0}".format(video["id"])
                    colons = 0
                    try: ytdn = video["duration"]
                    except: continue
                    try:
                        while ":" in ytdn:
                            ytdn = ytdn[ytdn.find(":") + 1:]
                            colons += 1
                    except:
                        continue
                    resultduration = 0
                    tempdn = video["duration"]
                    hrs = 0
                    mins = 0
                    secs = 0
                    if colons == 1:
                        mins = tempdn[:tempdn.find(":")]
                        secs = tempdn[tempdn.find(":") + 1:]
                        resultduration += (int(mins) * 60000) + (int(secs) * 1000)
                    else:
                        hrs = tempdn[:tempdn.find(":")]
                        tempdn = tempdn[tempdn.find(":") + 1:]
                        mins = tempdn[:tempdn.find(":")]
                        secs = tempdn[tempdn.find(":") + 1:]
                        resultduration += (int(hrs) * 3600000) + (int(mins) * 60000) + (int(secs) * 1000)
                    duration = resultduration
                    if '"' in title: title = title.replace('"', '\\"')
                    try: await dbconn("newentry", "INSERT INTO queue(guild_id, title, url, duration) VALUES('{0}', \"{1}\", '{2}', '{3}')".format(ctx.guild.id, title, videourl, duration), "")
                    except Exception as e:
                        await info.delete()
                        await ctx.send("An exception has occurred: ```{0}```".format(e))
                        await ctx.send(embed=discord.Embed(description="Unable to add the song to the queue. Please try again later.", color=discord.Color.red()))
                        return
                    await addtoshufflequeue(ctx, info)
                    index += 1
                await info.edit(embed=discord.Embed(description="Successfully added <:youtube:844282392616894504> **{0} tracks** to the queue.".format(index), color=discord.Color.green()))
            else:
                try: video = await Video.get(url)
                except Exception as e:
                    await info.edit(embed=discord.Embed(description=e, color=discord.Color.red()))
                    return
                try: title = video["title"]
                except Exception as e:
                    await info.delete()
                    await ctx.send("An exception has occurred: ```{0}```".format(e))
                    await ctx.send(embed=discord.Embed(description="Unable to add the song to the queue. Please try again later.", color=discord.Color.red()))
                    return
                videourl = url
                try: duration = video["streamingData"]["adaptiveFormats"][0]["approxDurationMs"]
                except Exception as e:
                    await info.edit(embed=discord.Embed(description="Could not find a valid format to download for this video. The video might also be age restricted.", color=discord.Color.red()))
                    return
                if '"' in title: title = title.replace('"', '\\"')
                try: await dbconn("newentry", "INSERT INTO queue(guild_id, title, url, duration) VALUES('{0}', \"{1}\", '{2}', '{3}')".format(ctx.guild.id, title, videourl, duration), "")
                except Exception as e:
                    await info.delete()
                    await ctx.send("An exception has occurred: ```{0}```".format(e))
                    await ctx.send(embed=discord.Embed(description="Unable to add the song to the queue. Please try again later.", color=discord.Color.red()))
                    return
                else: await info.edit(embed=discord.Embed(description="Successfully added <:youtube:844282392616894504> **{0}** to the queue.".format(title), color=discord.Color.green()))
                await addtoshufflequeue(ctx, info)
        elif "https://open.spotify.com/playlist/" in url or "https://open.spotify.com/album/" in url:
            if "https://open.spotify.com/playlist/" in url:
                await info.edit(embed=discord.Embed(description="Adding Spotify playlist track(s) to queue...", color=discord.Color.gold()))
                playlistid = url.replace("https://open.spotify.com/playlist/", "")
                if "?" in playlistid: playlistid = playlistid[:playlistid.find("?")]
                try: results = sp.playlist_items(playlistid)
                except spotipy.exceptions.SpotifyException:
                    await info.edit(embed=discord.Embed(description="Invalid Spotify playlist ID.", color=discord.Color.red()))
                    return
                except Exception as e:
                    await info.delete()
                    await ctx.send("An exception has occurred: ```{0}```".format(e))
                    await ctx.send(embed=discord.Embed(description="Unable to add the playlist's songs to the queue. Please try again later.", color=discord.Color.red()))
                    return
            elif "https://open.spotify.com/album/" in url:
                await info.edit(embed=discord.Embed(description="Adding Spotify album track(s) to queue...", color=discord.Color.gold()))
                albumid = url.replace("https://open.spotify.com/album/", "")
                if "?" in albumid: albumid = albumid[:albumid.find("?")]
                try: results = sp.album_tracks(albumid)
                except spotipy.exceptions.SpotifyException:
                    await info.edit(embed=discord.Embed(description="Invalid Spotify album ID.", color=discord.Color.red()))
                    return
                except Exception as e:
                    await info.delete()
                    await ctx.send("An exception has occurred: ```{0}```".format(e))
                    await ctx.send(embed=discord.Embed(description="Unable to add the playlist's songs to the queue. Please try again later.", color=discord.Color.red()))
                    return
            items = results["items"]
            while results["next"]:
                try: results = sp.next(results)
                except Exception as e:
                    await info.delete()
                    await ctx.send("An exception has occurred: ```{0}```".format(e))
                    await ctx.send(embed=discord.Embed(description="Unable to add the playlist's songs to the queue. Please try again later.", color=discord.Color.red()))
                    return
                items.extend(results["items"])
            tracks = len(items)
            index = 0
            for item in items:
                index += 1
                trackartists = ""
                try:
                    if "https://open.spotify.com/playlist/" in url:
                        for artist in item["track"]["album"]["artists"]: trackartists += "{0}, ".format(artist["name"])
                    elif "https://open.spotify.com/album/" in url:
                        for artist in item["artists"]: trackartists += "{0}, ".format(artist["name"])
                except: continue
                trackartists = trackartists[:-2]
                if "https://open.spotify.com/playlist/" in url: tracktitle = "{0} - {1}".format(trackartists, item["track"]["name"])
                elif "https://open.spotify.com/album/" in url: tracktitle = "{0} - {1}".format(trackartists, item["name"])
                if '"' in tracktitle: tracktitle = tracktitle.replace('"', '\\"')
                try:
                    if "https://open.spotify.com/playlist/" in url: trackurl = item["track"]["external_urls"]["spotify"]
                    elif "https://open.spotify.com/album/" in url: trackurl = item["external_urls"]["spotify"]
                except: continue
                if "https://open.spotify.com/playlist/" in url: trackduration = item["track"]["duration_ms"]
                elif "https://open.spotify.com/album/" in url: trackduration = item["duration_ms"]
                try: await dbconn("newentry", "INSERT INTO queue(guild_id, title, url, duration) VALUES('{0}', \"{1}\", '{2}', '{3}')".format(ctx.guild.id, tracktitle, trackurl, trackduration), "")
                except Exception as e:
                    await info.delete()
                    await ctx.send("An exception has occurred: ```{0}```".format(e))
                    await ctx.send(embed=discord.Embed(description="Unable to add the playlist's songs to the queue. Please try again later. You can also report this error by sending the playlist link along with the following error code: {0}".format(index), color=discord.Color.red()))
                    return
                await addtoshufflequeue(ctx, info)
            await info.edit(embed=discord.Embed(description="Successfully added <:spotify:844277927604125696> **{0} tracks** to the queue.".format(index), color=discord.Color.green()))
        elif "https://open.spotify.com/track/" in url:
            await info.edit(embed=discord.Embed(description="Adding Spotify track to queue...", color=discord.Color.gold()))
            trackid = url.replace("https://open.spotify.com/track/", "")
            if "?" in trackid: trackid = trackid[:trackid.find("?")]
            try: track = sp.track(trackid)
            except spotipy.exceptions.SpotifyException:
                await info.edit(embed=discord.Embed(description="Invalid Spotify track ID.", color=discord.Color.red()))
                return
            except Exception as e:
                await info.delete()
                await ctx.send("An exception has occurred: ```{0}```".format(e))
                await ctx.send(embed=discord.Embed(description="Unable to add the playlist's songs to the queue. Please try again later.", color=discord.Color.red()))
                return
            trackartists = ""
            try:
                for artist in track["artists"]: trackartists += "{0}, ".format(artist["name"])
            except:
                await info.edit(embed=discord.Embed(description="Could not get the track's artist(s).", color=discord.Color.red()))
                return
            trackartists = trackartists[:-2]
            tracktitle = "{0} - {1}".format(trackartists, track["name"])
            if '"' in tracktitle: tracktitle = tracktitle.replace('"', '\\"')
            try: trackurl = track["external_urls"]["spotify"]
            except:
                await info.edit(embed=discord.Embed(description="Could not get the track's Spotify track URL.", color=discord.Color.red()))
                return
            trackduration = track["duration_ms"]
            try: await dbconn("newentry", "INSERT INTO queue(guild_id, title, url, duration) VALUES('{0}', \"{1}\", '{2}', '{3}')".format(ctx.guild.id, tracktitle, trackurl, trackduration), "")
            except Exception as e:
                await info.delete()
                await ctx.send("An exception has occurred: ```{0}```".format(e))
                await ctx.send(embed=discord.Embed(description="Unable to add the Spotify track to the queue. Please try again later. You can also report this error by sending the track link.", color=discord.Color.red()))
                return
            await info.edit(embed=discord.Embed(description="Successfully added <:spotify:844277927604125696> **{0}** to the queue.".format(tracktitle), color=discord.Color.green()))
            await addtoshufflequeue(ctx, info)
        elif "https://music.apple.com/us/playlist/" in url or "https://music.apple.com/us/album/" in url:
            if "https://music.apple.com/us/playlist/" in url: await info.edit(embed=discord.Embed(description="Adding Apple Music playlist track(s) to queue...", color=discord.Color.gold()))
            elif "https://music.apple.com/us/album/" in url and not "?i=" in url: await info.edit(embed=discord.Embed(description="Adding Apple Music album track(s) to queue...", color=discord.Color.gold()))
            elif "https://music.apple.com/us/album/" in url and "?i=" in url: await info.edit(embed=discord.Embed(description="Adding Apple Music track to queue...", color=discord.Color.gold()))
            trackid = 1234567890
            if "?i=" in url: trackid = url[url.find("?1=") + 3:]
            rs = ''.join(random.choice(string.ascii_letters) for i in range(24))
            url = "{0}?{1}".format(url, rs)
            try:
                playlistpage = await requests.get(url, timeout=20)
                status = playlistpage.status
            except asyncio.exceptions.TimeoutError:
                await info.edit(embed=discord.Embed(description="Request timed out. Please try again later", color=discord.Color.red()))
                return
            except Exception as e:
                await info.delete()
                await ctx.send("An exception has occurred: ```{0}```".format(e))
                await ctx.send(embed=discord.Embed(description="Unable to make the request.", color=discord.Color.red()))
                return
            if not str(status).startswith('2') and not str(status).startswith('3'):
                sclist = open(os.path.join(sys.path[0], "data/statuscodes.txt"))
                for code in sclist.readlines():
                    code = code.replace("\n", "")
                    if str(status) in code:
                        await info.edit(embed=discord.Embed(description="Unable to make the request. Server returned status code `{0}`. Please try again later".format(code), color=discord.Color.red()))
                        return
                await info.edit(embed=discord.Embed(description="Unable to make the request. Server returned status code `{0}`. Please try again later".format(code), color=discord.Color.red()))
                return
            text = await playlistpage.text()
            playlistpage.close()
            if not "<script type=\"fastboot/shoebox\" id=\"shoebox-media-api-cache-amp-music\">" in text:
                await info.edit(embed=discord.Embed(description="Unable to get the Apple Music tracks from the URL provided. Please provide a valid Apple Music playlist, album, or track URL.", color=discord.Color.red()))
                with open(os.path.join(sys.path[0], "data/temp/test.txt"), "wb") as f: f.write(text.encode())
                return
            plcontents = ""
            plcontents = text[text.find("<script type=\"fastboot/shoebox\" id=\"shoebox-media-api-cache-amp-music\">"):text.find("</script><script type=\"x/boundary\" id=\"fastboot-body-end\"></script>")]
            plcontents = plcontents[plcontents.find(r"\"data\":") + len(r"\"data\":"):plcontents.find("]}}}]}")]
            with open(os.path.join(sys.path[0], "data/temp/test.txt"), "wb") as f: f.write(plcontents.encode())
            index = 0
            while r"\"songs\"" in plcontents:
                songsnippet = plcontents[plcontents.find(r"\"songs\""):plcontents.find(r"]},")]
                plcontents = plcontents[plcontents.find(r"]},") + len(r"]},"):]
                trackname = songsnippet[songsnippet.find(r"\"name\":\"") + len(r"\"name\":\""):]
                trackname = trackname[:trackname.find(r"\"")]
                if r"\u0026" in trackname: trackname = trackname.replace(r"\u0026", "&")
                if trackname == "": continue
                trackartist = songsnippet[songsnippet.find(r"\"artistName\":\"") + len(r"\"artistName\":\""):]
                trackurl = trackartist[trackartist.find(r"\"url\":\"") + len(r"\"url\":\""):]
                trackartist = trackartist[:trackartist.find(r"\"")]
                trackurl = trackurl[:trackurl.find(r"\"")]
                if r"\u0026" in trackartist: trackartist = trackartist.replace(r"\u0026", "&")
                trackduration = songsnippet[songsnippet.find(r"\"durationInMillis\":") + len(r"\"durationInMillis\":"):]
                trackduration = trackduration[:trackduration.find(",")]
                tracktitle = "{0} - {1}".format(trackartist, trackname)
                index += 1
                if (not trackid == 1234567890 and str(trackid) in trackurl) or trackid == 1234567890:
                    try: await dbconn("newentry", "INSERT INTO queue(guild_id, title, url, duration) VALUES('{0}', \"{1}\", '{2}', '{3}')".format(ctx.guild.id, tracktitle, trackurl, trackduration), "")
                    except Exception as e:
                        await info.delete()
                        await ctx.send("An exception has occurred: ```{0}```".format(e))
                        if trackid == 1234567890: await ctx.send(embed=discord.Embed(description="Unable to add the Apple Music track(s) to the queue. Please try again later. You can also report this error by sending the playlist link along with the following error code: {0}".format(index), color=discord.Color.red()))
                        elif not trackid == 1234567890 and str(trackid) in trackurl: await ctx.send(embed=discord.Embed(description="Unable to add the Apple Music track to the queue. Please try again later. You can also report this error by sending the track link.", color=discord.Color.red()))
                        return
                    if (not trackid == 1234567890 and str(trackid) in trackurl):
                        await addtoshufflequeue(ctx, info)
                        break
                    await addtoshufflequeue(ctx, info)
            if trackid == 1234567890: await info.edit(embed=discord.Embed(description="Successfully added <:apple_music:844280729395134466> **{0} tracks** to the queue.".format(index), color=discord.Color.green()))
            elif not trackid == 1234567890 and str(trackid) in trackurl: await info.edit(embed=discord.Embed(description="Successfully added <:apple_music:844280729395134466> **{0}** to the queue.".format(tracktitle), color=discord.Color.green()))
            elif not trackid == 1234567890 and not str(trackid) in trackurl: await info.edit(embed=discord.Embed(description="Invalid Apple Music track ID.".format(tracktitle), color=discord.Color.red()))
    if not player.is_playing(): await startqueue(ctx, info, player)

async def play(ctx, args):
    if ctx.author.id == 441405046727507968:
        await ctx.send(embed=discord.Embed(description="Sorry Andres", color=discord.Color.red()))
        return
    if not args:
        await ctx.send(embed=discord.Embed(description="Specify a song or URL to play.", color=discord.Color.red()))
        return
    await join(ctx, args)

async def clearqueue(ctx):
    try:
        await dbconn("newentry", "DELETE FROM `queue` WHERE `guild_id` = {0}".format(ctx.guild.id), "")
        await dbconn("newentry", "UPDATE `settings` SET `current` = '0' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        await dbconn("newentry", "UPDATE `settings` SET `shufflemode` = '0' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        await dbconn("newentry", "UPDATE `settings` SET `loopmode` = '0' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
    except Exception as e:
        try:
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="A database error has occurred. Please try again later.", color=discord.Color.red()))
        except: pass

async def join(ctx, args):
    try: args
    except: args = None
    prefix = await serverprefix(ctx)
    try: info = await ctx.send(embed=discord.Embed(description="Checking voice channel...", color=discord.Color.gold()))
    except:
        await ctx.send("I do not have permission to send embeds in this channel! The bot will not function correctly.")
        return
    if not ctx.author.voice:
        await info.edit(embed=discord.Embed(description="You are not currently in a voice channel!", color=discord.Color.red()))
        return
    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client
    if vc:
        if not vc.channel == channel and not len(vc.channel.voice_states) == 1:
            await info.edit(embed=discord.Embed(description="The bot is currently in a different voice channel. Please join that voice channel to queue songs.", color=discord.Color.red()))
            return
        if vc.is_connected() and args: await addtoqueue(ctx, args, info, vc)
        elif vc.is_connected() and not args: await info.edit(embed=discord.Embed(description="Joined", color=discord.Color.green()))
        else:
            try:
                await info.edit(embed=discord.Embed(description="Joining...", color=discord.Color.gold()))
                await vc.move_to(channel)
            except Exception as e:
                await info.delete()
                if e: await ctx.send("An exception has occurred: ```{0}```".format(e))
                await ctx.send(embed=discord.Embed(description="Unable to connect to the voice channel. Please try again later.", color=discord.Color.red()))
                return
            else:
                await addtoqueue(ctx, args, info, vc)
        return
    await info.edit(embed=discord.Embed(description="Joining...", color=discord.Color.gold()))
    try:
        player = await channel.connect(timeout=5, reconnect=True)
    except Exception as e:
        await info.delete()
        if e: await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to connect to the voice channel. Please try again later.", color=discord.Color.red()))
        return
    await clearqueue(ctx)
    if player.is_connected() and args: await addtoqueue(ctx, args, info, player)
    elif player.is_connected() and not args: await info.edit(embed=discord.Embed(description="Joined", color=discord.Color.green()))
    else:
        try:
            await info.edit(embed=discord.Embed(description="Joining...", color=discord.Color.gold()))
            await player.move_to(channel)
        except Exception as e:
            await info.delete()
            if e: await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to connect to the voice channel. Please try again later.", color=discord.Color.red()))
            return
        else:
            await addtoqueue(ctx, args, info, vc)

async def disconnect(ctx):
    info = await ctx.send(embed=discord.Embed(description="Disconnecting...", color=discord.Color.gold()))
    if not ctx.author.voice:
        await info.edit(embed=discord.Embed(description="Please join the voice channel to disconnect the bot.", color=discord.Color.red()))
        return
    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client
    if not vc:
        await info.edit(embed=discord.Embed(description="The bot is not currently in a voice channel!", color=discord.Color.red()))
        return
    if not vc.channel == channel:
        await info.edit(embed=discord.Embed(description="The bot is currently in a different voice channel. Please join that voice channel and retry this command.", color=discord.Color.red()))
        return
    try: await dbconn("newentry", "UPDATE `settings` SET `stop` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
    except: pass
    await vc.disconnect()
    await info.edit(embed=discord.Embed(description="Disconnected", color=discord.Color.green()))

async def stop(ctx, func):
    if func == "stop:": info = await ctx.send(embed=discord.Embed(description="Stopping...", color=discord.Color.gold()))
    else: info = await ctx.send(embed=discord.Embed(description="Skipping...", color=discord.Color.gold()))
    if not ctx.author.voice:
        await info.edit(embed=discord.Embed(description="You are not currently in a voice channel!", color=discord.Color.red()))
        return
    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client
    if not vc:
        await info.edit(embed=discord.Embed(description="The bot is not currently in a voice channel!", color=discord.Color.red()))
        return
    if not vc.channel == channel:
        await info.edit(embed=discord.Embed(description="The bot is currently in a different voice channel. Please join that voice channel and retry this command.", color=discord.Color.red()))
        return
    if vc.is_playing():
        if func == "stop":
            try: await dbconn("newentry", "UPDATE `settings` SET `stop` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
            except: pass
        vc.stop()
        if func == "stop": await info.edit(embed=discord.Embed(description="Stopped", color=discord.Color.green()))
        else: await info.edit(embed=discord.Embed(description="Skipped", color=discord.Color.green()))
    else:
        try:
            paused = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 8)
            try: paused = int(paused)
            except: paused = False
            else:
                if paused == 1: paused = True
                else: paused = False
        except Exception as e:
            await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
            await ctx.channel.send(embed=discord.Embed(description="Unable to determine if the player was paused.", color=discord.Color.red()))
            return
        if paused:
            if func == "stop":
                stopped.append(ctx.guild.id)
                await info.edit(embed=discord.Embed(description="Stopped", color=discord.Color.green()))
            else:
                skipped.append(ctx.guild.id)
                await info.edit(embed=discord.Embed(description="Skipped", color=discord.Color.green()))
            return
        await info.edit(embed=discord.Embed(description="The bot is not currently playing anything!", color=discord.Color.red()))

async def remove(ctx, position):
    position = int(position)
    if not position:
        await ctx.send(embed=discord.Embed(description="Specify the position of the song in the queue.", color=discord.Color.red()))
        return
    info = await ctx.send(embed=discord.Embed(description="Removing song from queue...", color=discord.Color.gold()))
    if not ctx.author.voice:
        await info.edit(embed=discord.Embed(description="Please join the voice channel to remove a song from the queue.", color=discord.Color.red()))
        return
    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client
    if not vc:
        await info.edit(embed=discord.Embed(description="The bot is not currently in a voice channel!", color=discord.Color.red()))
        return
    if not vc.channel == channel:
        await info.edit(embed=discord.Embed(description="The bot is currently in a different voice channel. Please join that voice channel and retry this command.", color=discord.Color.red()))
        return
    try: queue = await dbconn("fetchqueue", "", ctx.guild.id)
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
        return
    try:
        current = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 3)
        current = int(current)
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to fetch the current position in the queue.", color=discord.Color.red()))
        return
    try: intid = queue[position - 1][0]
    except:
        await ctx.send(embed=discord.Embed(description="The requested song position does not currently exist in the queue.", color=discord.Color.red()))
        return
    try: await dbconn("newentry", "DELETE FROM `queue` WHERE `int_id` = {0}".format(intid), "")
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to remove that song from the queue.", color=discord.Color.red()))
        return
    if current >= position:
        try: await dbconn("newentry", "UPDATE `settings` SET `current` = '{0}' WHERE `guild_id` = '{1}'".format(current - 1, ctx.guild.id), "")
        except Exception as e:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to update the current position in queue.", color=discord.Color.red()))
            return
    await info.edit(embed=discord.Embed(description="Removed **{0}** from the queue.".format(queue[position - 1][2]), color=discord.Color.green()))

async def clear(ctx):
    info = await ctx.send(embed=discord.Embed(description="Clearing queue...", color=discord.Color.gold()))
    if not ctx.author.voice:
        await info.edit(embed=discord.Embed(description="Please join the voice channel to clear the queue.", color=discord.Color.red()))
        return
    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client
    if not vc:
        await info.edit(embed=discord.Embed(description="The bot is not currently in a voice channel!", color=discord.Color.red()))
        return
    if not vc.channel == channel:
        await info.edit(embed=discord.Embed(description="The bot is currently in a different voice channel. Please join that voice channel and retry this command.", color=discord.Color.red()))
        return
    try: await clearqueue(ctx)
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to clear the queue.", color=discord.Color.red()))
        return
    await info.edit(embed=discord.Embed(description="Cleared the queue.", color=discord.Color.green()))

async def simpleloop(ctx):
    # if not ctx.author.voice: return
    # channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client
    if not vc: return
    try:
        loopmode = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 4)
    except Exception as e: return
    try: int(loopmode)
    except:
        try: await dbconn("newentry", "UPDATE `settings` SET `loopmode` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        except Exception as e: return
        return "enabled"
    if not int(loopmode) == 1:
        try: await dbconn("newentry", "UPDATE `settings` SET `loopmode` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        except Exception as e: return
        return "enabled"
    elif int(loopmode) == 1:
        try: await dbconn("newentry", "UPDATE `settings` SET `loopmode` = '0' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        except Exception as e: return
        return "disabled"

async def loop(ctx):
    info = await ctx.send(embed=discord.Embed(description="Changing the loop setting...", color=discord.Color.gold()))
    if not ctx.author.voice:
        await info.edit(embed=discord.Embed(description="Please join the voice channel to change the loop setting.", color=discord.Color.red()))
        return
    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client
    if not vc:
        await info.edit(embed=discord.Embed(description="The bot is not currently in a voice channel!", color=discord.Color.red()))
        return
    if not vc.channel == channel:
        await info.edit(embed=discord.Embed(description="The bot is currently in a different voice channel. Please join that voice channel and retry this command.", color=discord.Color.red()))
        return
    try:
        loopmode = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 4)
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to change the loop setting.", color=discord.Color.red()))
        return
    try: int(loopmode)
    except:
        try: await dbconn("newentry", "UPDATE `settings` SET `loopmode` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        except Exception as e:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to change the loop setting.", color=discord.Color.red()))
            return
        await info.edit(embed=discord.Embed(description="Looping **enabled**.", color=discord.Color.green()))
        return
    if not int(loopmode) == 1:
        try: await dbconn("newentry", "UPDATE `settings` SET `loopmode` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        except Exception as e:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to change the loop setting.", color=discord.Color.red()))
            return
        await info.edit(embed=discord.Embed(description="Looping **enabled**.", color=discord.Color.green()))
        return "enabled"
    elif int(loopmode) == 1:
        try: await dbconn("newentry", "UPDATE `settings` SET `loopmode` = '0' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        except Exception as e:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to change the loop setting.", color=discord.Color.red()))
            return "disabled"
        await info.edit(embed=discord.Embed(description="Looping **disabled**.", color=discord.Color.green()))

async def simpleshufflequeue(ctx):
    try: queue = await dbconn("fetchqueue", "", ctx.guild.id)
    except Exception as e: return
    try:
        current = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 3)
        current = int(current)
    except Exception as e: return
    try: unshuffledqueue = await dbconn("fetchqueue", "unshuffled", ctx.guild.id)
    except Exception as e: return
    queuelist = queue
    normallist = []
    shufflelist = []
    index = 0
    intid = 0
    for song in queuelist:
        index += 1
        normallist.append(int(song[0]))
        shufflelist.append(int(song[0]))
        if current == index:
            intid = song[0]
            intid = int(intid)
    currentintid = normallist[current - 1]
    lowestintid = unshuffledqueue[0][0]
    currentintid = int(currentintid)
    lowestintid = int(lowestintid)
    normallist.remove(currentintid)
    shufflelist.remove(lowestintid)
    random.shuffle(shufflelist)
    normallist = [currentintid] + normallist
    shufflelist = [lowestintid] + shufflelist
    for i in range(len(normallist)):
        try: await dbconn("newentry", "UPDATE `queue` SET `shuffle_int` = '{0}' WHERE `int_id` = '{1}'".format(shufflelist[i], normallist[i]), "")
        except Exception as e: return
    try: await dbconn("newentry", "UPDATE `settings` SET `current` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
    except Exception as e: return
    return intid

async def shufflequeue(ctx, info):
    try: queue = await dbconn("fetchqueue", "", ctx.guild.id)
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
        return
    try:
        current = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 3)
        current = int(current)
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to fetch the current position in the queue.", color=discord.Color.red()))
        return
    try: unshuffledqueue = await dbconn("fetchqueue", "unshuffled", ctx.guild.id)
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
        return
    queuelist = queue
    normallist = []
    shufflelist = []
    index = 0
    intid = 0
    for song in queuelist:
        index += 1
        normallist.append(int(song[0]))
        shufflelist.append(int(song[0]))
        if current == index:
            intid = song[0]
            intid = int(intid)
    currentintid = normallist[current - 1]
    lowestintid = unshuffledqueue[0][0]
    currentintid = int(currentintid)
    lowestintid = int(lowestintid)
    normallist.remove(currentintid)
    shufflelist.remove(lowestintid)
    random.shuffle(shufflelist)
    normallist = [currentintid] + normallist
    shufflelist = [lowestintid] + shufflelist
    for i in range(len(normallist)):
        try: await dbconn("newentry", "UPDATE `queue` SET `shuffle_int` = '{0}' WHERE `int_id` = '{1}'".format(shufflelist[i], normallist[i]), "")
        except Exception as e:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to update the queue.", color=discord.Color.red()))
            return
    try: await dbconn("newentry", "UPDATE `settings` SET `current` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to update the current song.", color=discord.Color.red()))
        return
    return intid

async def simpleshuffle(ctx):
    vc = ctx.guild.voice_client
    if not vc: return
    try:
        shufflemode = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 5)
    except Exception as e: return
    try: int(shufflemode)
    except:
        try:
            await dbconn("newentry", "UPDATE `settings` SET `shufflemode` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
            intid = await simpleshufflequeue(ctx)
        except Exception as e: return
        return "shuffled"
    if not int(shufflemode) == 1:
        try:
            await dbconn("newentry", "UPDATE `settings` SET `shufflemode` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
            intid = await simpleshufflequeue(ctx)
        except Exception as e: return
        return "shuffled"
    elif int(shufflemode) == 1:
        try:
            intid = await simpleshufflequeue(ctx)
            if not intid: return
        except Exception as e: return
        return "shuffled"

# async def shufflecurrent(ctx, info, intid):
#     try: queue = await dbconn("fetchqueue", "shuffled", ctx.guild.id)
#     except Exception as e:
#         await info.delete()
#         await ctx.send("An exception has occurred: ```{0}```".format(e))
#         await ctx.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
#         return
#     try:
#         newintid = await dbconn("getvalue", "SELECT * FROM `queue` WHERE `int_id` = '{0}'".format(intid), 5)
#         newintid = int(newintid)
#     except TypeError:
#         await info.delete()
#         await ctx.send(embed=discord.Embed(description="Unable to fetch the shuffled position in queue.", color=discord.Color.red()))
#         return
#     except Exception as e:
#         await info.delete()
#         await ctx.send("An exception has occurred: ```{0}```".format(traceback.format_exc()))
#         await ctx.send(embed=discord.Embed(description="Unable to fetch the shuffled position in queue.", color=discord.Color.red()))
#         return
#     shufflecurrent = 0
#     index = 0
#     for song in queue:
#         index += 1
#         if int(song[5]) == newintid: shufflecurrent = index
#     try: await dbconn("newentry", "UPDATE `settings` SET `current` = '{0}' WHERE `guild_id` = '{1}'".format(shufflecurrent, ctx.guild.id), "")
#     except Exception as e:
#         await info.delete()
#         await ctx.send("An exception has occurred: ```{0}```".format(e))
#         await ctx.send(embed=discord.Embed(description="Unable to update the current song.", color=discord.Color.red()))
#         return

async def shuffle(ctx):
    # if not ctx.author.id == 189198218251337728:
    #     await ctx.send(embed=discord.Embed(description="This feature is a work-in-progress, so it may not work properly yet.", color=discord.Color.red()))
    info = await ctx.send(embed=discord.Embed(description="Shuffling the queue...", color=discord.Color.gold()))
    if not ctx.author.voice:
        await info.edit(embed=discord.Embed(description="Please join the voice channel to shuffle the queue.", color=discord.Color.red()))
        return
    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client
    if not vc:
        await info.edit(embed=discord.Embed(description="The bot is not currently in a voice channel!", color=discord.Color.red()))
        return
    if not vc.channel == channel:
        await info.edit(embed=discord.Embed(description="The bot is currently in a different voice channel. Please join that voice channel and retry this command.", color=discord.Color.red()))
        return
    try:
        shufflemode = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 5)
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to shuffle the queue.", color=discord.Color.red()))
        return
    try: int(shufflemode)
    except:
        try:
            await dbconn("newentry", "UPDATE `settings` SET `shufflemode` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
            intid = await shufflequeue(ctx, info)
        except Exception as e:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to shuffle the queue.", color=discord.Color.red()))
            return
        # await shufflecurrent(ctx, info, intid)
        try: await info.edit(embed=discord.Embed(description="Shuffled the queue.", color=discord.Color.green()))
        except: return
        return
    if not int(shufflemode) == 1:
        try:
            await dbconn("newentry", "UPDATE `settings` SET `shufflemode` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
            intid = await shufflequeue(ctx, info)
        except Exception as e:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to shuffle the queue.", color=discord.Color.red()))
            return
        # await shufflecurrent(ctx, info, intid)
        try: await info.edit(embed=discord.Embed(description="Shuffled the queue.", color=discord.Color.green()))
        except: return
        return
    elif int(shufflemode) == 1:
        try:
            intid = await shufflequeue(ctx, info)
        except Exception as e:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to shuffle the queue.", color=discord.Color.red()))
            return
        # await shufflecurrent(ctx, info, intid)
        try: await info.edit(embed=discord.Embed(description="Shuffled the queue.", color=discord.Color.green()))
        except: return
        return

async def pause(ctx):
    # if not ctx.author.id == 189198218251337728:
    #     await ctx.send(embed=discord.Embed(description="This feature is a work-in-progress, so it may not work properly yet.", color=discord.Color.red()))
    info = await ctx.send(embed=discord.Embed(description="Pausing...", color=discord.Color.gold()))
    if not ctx.author.voice:
        await info.edit(embed=discord.Embed(description="Please join the voice channel to pause the player.", color=discord.Color.red()))
        return
    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client
    if not vc:
        await info.edit(embed=discord.Embed(description="The bot is not currently in a voice channel!", color=discord.Color.red()))
        return
    if not vc.channel == channel:
        await info.edit(embed=discord.Embed(description="The bot is currently in a different voice channel. Please join that voice channel and retry this command.", color=discord.Color.red()))
        return
    try:
        await dbconn("newentry", "UPDATE `settings` SET `pause` = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        vc.pause()
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to pause the player.", color=discord.Color.red()))
        return
    await info.edit(embed=discord.Embed(description="Paused", color=discord.Color.green()))

async def resume(ctx):
    # if not ctx.author.id == 189198218251337728:
    #     await ctx.send(embed=discord.Embed(description="This feature is a work-in-progress, so it may not work properly yet.", color=discord.Color.red()))
    info = await ctx.send(embed=discord.Embed(description="Resuming...", color=discord.Color.gold()))
    if not ctx.author.voice:
        await info.edit(embed=discord.Embed(description="Please join the voice channel to resume the player.", color=discord.Color.red()))
        return
    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client
    if not vc:
        await info.edit(embed=discord.Embed(description="The bot is not currently in a voice channel!", color=discord.Color.red()))
        return
    if not vc.channel == channel:
        await info.edit(embed=discord.Embed(description="The bot is currently in a different voice channel. Please join that voice channel and retry this command.", color=discord.Color.red()))
        return
    try:
        await dbconn("newentry", "UPDATE `settings` SET `pause` = '0' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        vc.resume()
    except Exception as e:
        await info.delete()
        await ctx.send("An exception has occurred: ```{0}```".format(e))
        await ctx.send(embed=discord.Embed(description="Unable to resume the player.", color=discord.Color.red()))
        return
    await info.edit(embed=discord.Embed(description="Resumed", color=discord.Color.green()))

async def lyrics(ctx):
    try: info = await ctx.send(embed=discord.Embed(description="Getting song information...", color=discord.Color.gold()))
    except: pass
    try: queue = await dbconn("fetchqueue", "", ctx.guild.id)
    except Exception as e:
        try:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
            return
        except:
            await ctx.channel.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
            return
    try:
        current = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 3)
        current = int(current)
    except Exception as e:
        try:
            await info.delete()
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to fetch the current position in the queue.", color=discord.Color.red()))
            return
        except:
            await ctx.channel.send(embed=discord.Embed(description="Unable to fetch the current position in queue.", color=discord.Color.red()))
            return
    try: queue[current - 1]
    except Exception as e:
        try:
            await info.edit(embed=discord.Embed(description="The current position in the queue exceeds the length of the queue. (Did you clear the queue?)", color=discord.Color.red()))
            return
        except:
            await ctx.channel.send(embed=discord.Embed(description="The current position in the queue exceeds the length of the queue. (Did you clear the queue?)", color=discord.Color.red()))
            return
    combinedtitle = ""
    combinedartists = ""
    combinedsong = ""
    sisong = ""
    siartist = ""
    combinedtitle = queue[current - 1][2]
    combinedartists = combinedtitle[:combinedtitle.find("-") - 1]
    if "," in combinedartists: siartist = combinedartists[:combinedartists.find(",")]
    else: siartist = combinedartists
    combinedsong = combinedtitle[combinedtitle.find("-") + 2:]
    if "(" in combinedsong: sisong = combinedsong[:combinedsong.find("(") - 1]
    elif "[" in combinedsong: sisong = combinedsong[:combinedsong.find("[") - 1]
    else: sisong = combinedsong
    try: await info.edit(embed=discord.Embed(description="Fetching lyrics...", color=discord.Color.gold()))
    except: pass
    try:
        song = genius.search_song(sisong, siartist)
        lyrics = song.lyrics
    except Exception as e:
        try:
            await info.edit(embed=discord.Embed(description="Could not fetch lyrics for this song.", color=discord.Color.red()))
            return
        except:
            await ctx.channel.send(embed=discord.Embed(description="Could not fetch lyrics for this song.", color=discord.Color.red()))
            return
    if "•" in lyrics or "1." in lyrics or "- \"" in lyrics:
        try:
            await info.edit(embed=discord.Embed(description="Could not fetch lyrics for this song.", color=discord.Color.red()))
            return
        except:
            await ctx.channel.send(embed=discord.Embed(description="Could not fetch lyrics for this song.", color=discord.Color.red()))
            return
    fields = []
    while lyrics:
        if len(lyrics) > 1024:
            temp2 = lyrics[0:1023]
            chunk = temp2[:temp2.rfind("\n")]
        else:
            chunk = lyrics
        fields.append(chunk)
        lyrics = lyrics.replace(chunk, "")
    iteration = 0
    embeds = []
    totalcharacters = 0
    sinfo = "{0} by {1}".format(sisong, siartist)
    totalcharacters = totalcharacters + len(sinfo) + 30
    while not iteration == len(fields):
        if totalcharacters + len(fields[iteration]) > 6000:
            embeds.append(iteration)
            totalcharacters = 26
        totalcharacters = totalcharacters + len(fields[iteration]) + 5
        iteration += 1
    if not iteration in embeds:
        embeds.append(iteration)
    embednum = 0
    try: await info.delete()
    except: pass
    prev = -1
    for i in embeds:
        embednum += 1
        embed = discord.Embed(title="Lyrics (page {0} of {1})".format(embednum, len(embeds)))
        if embednum == 1:
            embed.add_field(name="Song", value="[{0}]({1})".format(sinfo, queue[current - 1][3]), inline=False)
        for j in range(i):
            if j < prev:
                continue
            embed.add_field(name="** **", value=fields[j], inline=False)
        await ctx.channel.send(embed=embed)
        prev = i

async def buttonfetchqueue(ctx, client):
    try: queue = await dbconn("fetchqueue", "", ctx.guild.id)
    except Exception as e:
        try:
            await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
            await ctx.channel.send(embed=discord.Embed(description="Unable to fetch the queue.", color=discord.Color.red()))
        except: return
        return
    try: 
        current = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 3)
        current = int(current)
    except Exception as e:
        try:
            await ctx.channel.send("An exception has occurred: ```{0}```".format(e))
            await ctx.channel.send(embed=discord.Embed(description="Unable to fetch the current position in the queue.", color=discord.Color.red()))
        except: return
        return
    songs = ""
    index = 0
    overflow = 0
    for song in queue:
        index += 1
        indent = "     "
        for i in range(len(str(index))): indent = indent[1:]
        nowplaying = ""
        if float(current) == index and ctx.guild.voice_client:
            if not ctx.guild.voice_client.is_playing(): return
            nowplaying = ":arrow_forward: "
        hours = 0
        minutes = 0
        seconds = round(int(song[4]) / 1000)
        duration = ""
        while seconds >= 60:
            seconds -= 60
            minutes += 1
        while minutes >= 60:
            minutes -= 60
            hours += 1
        if len(str(minutes)) == 1 and not hours == 0: minutes = "0{0}".format(minutes)
        if len(str(seconds)) == 1: seconds = "0{0}".format(seconds)
        if not hours == 0: duration = "{0}:{1}:{2}".format(hours, minutes, seconds)
        else: duration = "{0}:{1}".format(minutes, seconds)
        line = "\n{0}.{1}{2}{3} `[{4}]`".format(index, indent, nowplaying, song[2], duration)
        if not len(songs) + len(line) > 2048: songs += line
        else:
            overflow = len(queue) - index + 1
            break
    try: shufflemode = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 5)
    except: queuetitle = "Queue"
    try: int(shufflemode)
    except: queuetitle = "Queue"
    else:
        if int(shufflemode) == 1: queuetitle = "Shuffled Queue"
        else: queuetitle = "Queue"
    embed = discord.Embed(title=queuetitle, description=songs, color=discord.Color.blue())
    if not overflow == 0:
        embed.set_footer(text="and {0} more".format(overflow))
    return embed

async def buttons(client, response):
    buttonid = response.component.id
    if "pause np" in buttonid:
        await response.respond(type=6)
        vc = response.guild.voice_client
        if not vc:
            await response.channel.respond(embed=discord.Embed(description="The bot is not currently in a voice channel", color=discord.Color.red()))
            return
        try:
            await dbconn("newentry", "UPDATE `settings` SET `pause` = '1' WHERE `guild_id` = '{0}'".format(response.guild.id), "")
            vc.pause()
        except Exception as e:
            await response.channel.send(embed=discord.Embed(description="Unable to pause the player.", color=discord.Color.red()))
            return
        # await response.channel.send(embed=discord.Embed(description="Paused", color=discord.Color.green()))
    if "resume np" in buttonid:
        await response.respond(type=6)
        vc = response.guild.voice_client
        if not vc:
            await response.channel.respond(embed=discord.Embed(description="The bot is not currently in a voice channel", color=discord.Color.red()))
            return
        try:
            await dbconn("newentry", "UPDATE `settings` SET `pause` = '0' WHERE `guild_id` = '{0}'".format(response.guild.id), "")
            vc.resume()
        except Exception as e:
            await response.channel.send(embed=discord.Embed(description="Unable to resume the player.", color=discord.Color.red()))
            return
        # await response.channel.send(embed=discord.Embed(description="Resumed", color=discord.Color.green()))
    if "stop np" in buttonid or "skip np" in buttonid:
        await response.respond(type=6)
        vc = response.guild.voice_client
        if not vc:
            await response.channel.respond(embed=discord.Embed(description="The bot is not currently in a voice channel", color=discord.Color.red()))
            return
        if vc.is_playing():
            if "stop" in buttonid:
                try: await dbconn("newentry", "UPDATE `settings` SET `stop` = '1' WHERE `guild_id` = '{0}'".format(response.guild.id), "")
                except: pass
            vc.stop()
            # if "stop" in buttonid: await response.channel.send(embed=discord.Embed(description="Stopped", color=discord.Color.green()))
            # else: await response.channel.send(embed=discord.Embed(description="Skipped", color=discord.Color.green()))
        else:
            try:
                paused = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(response.guild.id), 8)
                try: paused = int(paused)
                except: paused = False
                else:
                    if paused == 1: paused = True
                    else: paused = False
            except Exception as e:
                await response.channel.send(embed=discord.Embed(description="Unable to determine if the player was paused.", color=discord.Color.red()))
                return
            if paused:
                if "stop" in buttonid:
                    stopped.append(response.guild.id)
                    # await response.channel.send(embed=discord.Embed(description="Stopped", color=discord.Color.green()))
                else:
                    skipped.append(response.guild.id)
                    # await response.channel.send(embed=discord.Embed(description="Skipped", color=discord.Color.green()))
                return
    if "queue np" in buttonid:
        await response.respond(type=6)
        try: await fetchqueue(response, client, 0, 1)
        except: return
    if "loop queue" in buttonid:
        await response.respond(type=6)
        result = await simpleloop(response)
        if not result:
            await response.channel.send(embed=discord.Embed(description="Unable to loop the queue.", color=discord.Color.red()))
        else:
            await response.channel.send(embed=discord.Embed(description="Looping **{0}**.".format(result), color=discord.Color.green()))
    if "shuffle queue" in buttonid:
        await response.respond(type=6)
        result = await simpleshuffle(response)
        if not result:
            await response.channel.send(embed=discord.Embed(description="Unable to shuffle the queue.", color=discord.Color.red()))
        elif result == "shuffled":
            await response.channel.send(embed=discord.Embed(description="Shuffled the queue.", color=discord.Color.green()))
            embed, cpg, pgs = await fetchqueue(response, client, 0, 2)
            await response.message.edit(embed=embed, components=await queuebuttons(cpg, pgs))
        else:
            await response.channel.send(embed=discord.Embed(description="Unable to shuffle the queue.", color=discord.Color.red()))
    if "refresh queue" in buttonid:
        embed, cpg, pgs = await fetchqueue(response, client, 0, 2)
        await response.respond(type=7, embed=embed, components=await queuebuttons(cpg, pgs))
    if "clear queue" in buttonid:
        vc = response.guild.voice_client
        if not vc:
            await response.respond(embed=discord.Embed(description="The bot is not currently in a voice channel", color=discord.Color.red()))
            return
        try: await clearqueue(response)
        except:
            await response.respond(embed=discord.Embed(description="Unable to clear the queue.", color=discord.Color.red()))
            return
        embed, cpg, pgs = await fetchqueue(response, client, 0, 2)
        await response.respond(type=7, embed=embed, components=await queuebuttons(cpg, pgs))
    if "previous queue" in buttonid:
        vc = response.guild.voice_client
        cpg = int(buttonid.replace("previous queue ", ""))
        if not vc:
            await response.respond(embed=discord.Embed(description="The bot is not currently in a voice channel", color=discord.Color.red()))
            return
        embed, cpg, pgs = await fetchqueue(response, client, cpg - 1, 2)
        await response.respond(type=7, embed=embed, components=await queuebuttons(cpg, pgs))
    if "next queue" in buttonid:
        vc = response.guild.voice_client
        cpg = int(buttonid.replace("next queue ", ""))
        if not vc:
            await response.respond(embed=discord.Embed(description="The bot is not currently in a voice channel", color=discord.Color.red()))
            return
        embed, cpg, pgs = await fetchqueue(response, client, cpg + 1, 2)
        await response.respond(type=7, embed=embed, components=await queuebuttons(cpg, pgs))
    if "lyrics np" in buttonid:
        await response.respond(type=6)
        try: await lyrics(response)
        except:
            print(traceback.format_exc())
            return
    return

async def startThreads(client):
    while True:
        response = await client.wait_for("button_click")
        asyncio.create_task(buttons(client, response))