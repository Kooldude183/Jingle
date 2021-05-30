import discord, traceback
from jingle import db
dbconn = db.dbconn

async def serversettings(ctx, setting, client):
    if not setting:
        try: result = await dbconn("ifexists", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        except Exception as e:
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send("<@{0}> Unable to fetch the settings for this server.".format(str(ctx.author.id)))
            return
        else:
            prefix = result[2]
            if result[6] == "1":
                stayinvc = "Enabled"
            else:
                stayinvc = "Disabled"
            embed = discord.Embed(title="Bot Settings")
            embed.add_field(name="Bot Prefix", value="`{0}settings prefix`\nChanges the bot's prefix for this server".format(prefix), inline=True)
            embed.add_field(name="24/7 Mode", value="`{0}settings 24/7`\nEnables/disables 24/7 mode (bot remaining in the voice channel)\nCurrent setting: `{1}`".format(prefix, stayinvc), inline=True)
            try: await ctx.send(embed=embed)
            except discord.errors.Forbidden:
                await ctx.send("Please enable the **Embed Links** permission for NWS Bot.")
                return
        return
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(embed=discord.Embed(description="You need Administrator permission to change the bot's settings for this server.", color=discord.Color.red()))
        return
    if setting == "prefix":
        await ctx.send(embed=discord.Embed(description="Enter a new prefix (send `cancel` to cancel)", color=discord.Color.blue()))
        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        response = await client.wait_for('message', check=check)
        if "cancel" in response.content.lower():
            await ctx.send(embed=discord.Embed(description="Canceled", color=discord.Color.red()))
            return
        newprefix = response.content.lower()
        try:
            await dbconn("newentry", "UPDATE `settings` SET prefix = '{0}' WHERE `guild_id` = '{1}'".format(newprefix, ctx.guild.id), "")
        except Exception as e:
            await ctx.send("An exception has occurred: ```{0}```".format(e))
            await ctx.send(embed=discord.Embed(description="Unable to update the bot's prefix. Please try again later.", color=discord.Color.red()))
            return
        else:
            await ctx.send(embed=discord.Embed(description="Successfully changed the bot's prefix to `{0}`".format(newprefix), color=discord.Color.green()))
    if setting == "24/7":
        await ctx.send(embed=discord.Embed(description="Coming Soon", color=discord.Color.red()))
        # try: stayinvc = await dbconn("getvalue", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), 4)
        # except:
        #     print(traceback.format_exc())
        #     await ctx.send("<@{0}> Unable to fetch the setting.".format(str(ctx.author.id)))
        #     return
        # if stayinvc == "1":
        #     try: await dbconn("newentry", "UPDATE `settings` SET stayinvc = '0' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        #     except Exception as e:
        #         await ctx.send("An exception has occurred: ```{0}```".format(e))
        #         await ctx.send("<@{0}> Unable to disable 24/7 mode. Please try again later.".format(str(ctx.author.id)))
        #         return
        #     await ctx.send("<@{0}> 24/7 mode has been **disabled** for this server.".format(str(ctx.author.id)))
        # else:
        #     try: await dbconn("newentry", "UPDATE `settings` SET stayinvc = '1' WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
        #     except Exception as e:
        #         await ctx.send("An exception has occurred: ```{0}```".format(e))
        #         await ctx.send("<@{0}> Unable to enable 24/7 mode. Please try again later.".format(str(ctx.author.id)))
        #         return
        #     await ctx.send("<@{0}> 24/7 mode has been **enabled** for this server.".format(str(ctx.author.id)))