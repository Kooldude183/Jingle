import mysql.connector, traceback, yaml, os, sys

f = open(os.path.join(sys.path[0], "config.yml"), "r")
config = yaml.load(f, Loader=yaml.FullLoader)
Host = config["mysql"]["Host"]
Port = config["mysql"]["Port"]
Database = config["mysql"]["Database"]
Username = config["mysql"]["Username"]
Password = config["mysql"]["Password"]

async def dbconn(func, query, var1):
    conn = None
    try:
        conn = mysql.connector.connect(
            host = Host,    
            port = Port,
            database = Database,
            user = Username,
            password = Password
        )
        cursor = conn.cursor(buffered=True)
    except:
        print("Unable to connect to the MySQL database, some features may not work")
        print(traceback.format_exc())
    finally:
        if conn.is_connected():
            if func == "createtables":
                print('Connected to database')
                cursor.execute("CREATE TABLE IF NOT EXISTS queue (int_id int NOT NULL AUTO_INCREMENT, guild_id VARCHAR(32) NOT NULL, title VARCHAR(1024) NOT NULL, url VARCHAR(4096) NOT NULL, duration VARCHAR(16), shuffle_int VARCHAR(4), PRIMARY KEY (int_id))")
                cursor.execute("CREATE TABLE IF NOT EXISTS settings (int_id int NOT NULL AUTO_INCREMENT, guild_id VARCHAR(32) NOT NULL, prefix VARCHAR(12), current VARCHAR(4), loopmode VARCHAR(1), shufflemode VARCHAR(1), stayinvc VARCHAR(1), stop VARCHAR(1), pause VARCHAR(1), sivrestart VARCHAR(1), PRIMARY KEY (int_id))")
                cursor.close()
                conn.close()
            if func == "ifexists":
                cursor.execute(query)
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                return result
            if func == "getvalue":
                cursor.execute(query)
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                return result[var1]
            if func == "newentry":
                cursor.execute(query)
                conn.commit()
                cursor.close()
                conn.close()
            if func == "fetchqueue":
                cursor.execute("SELECT * FROM `settings` WHERE `guild_id` = '{0}'".format(var1))
                result = cursor.fetchone()
                if query == "shuffled":
                    cursor.execute("SELECT * FROM `queue` WHERE `guild_id` = '{0}' ORDER BY `shuffle_int` ASC".format(var1))
                else:
                    if query == "unshuffled":
                        cursor.execute("SELECT * FROM `queue` WHERE `guild_id` = '{0}'".format(var1))
                    else:
                        try: int(result[5])
                        except: cursor.execute("SELECT * FROM `queue` WHERE `guild_id` = '{0}'".format(var1))
                        else:
                            if int(result[5]) == 1: cursor.execute("SELECT * FROM `queue` WHERE `guild_id` = '{0}' ORDER BY `shuffle_int` ASC".format(var1))
                            else: cursor.execute("SELECT * FROM `queue` WHERE `guild_id` = '{0}'".format(var1))
                results = cursor.fetchall()
                cursor.close()
                conn.close()
                return results
