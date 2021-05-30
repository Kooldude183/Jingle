import os, sys, yaml
from jingle import db

dbconn = db.dbconn

f = open(os.path.join(sys.path[0], "config.yml"), "r")
config = yaml.load(f, Loader=yaml.FullLoader)
defprefix = config["prefix"]

async def serverprefix(ctx):
    try: result = await dbconn("ifexists", "SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(ctx.guild.id), "")
    except: return defprefix
    else:
        if result: return result[2]
        else:
            try: await dbconn("newentry", "INSERT INTO settings(guild_id, prefix, current) VALUES('{0}', '{1}', '0')".format(ctx.guild.id, defprefix), "")
            except: pass
            finally: return defprefix