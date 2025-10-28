import sqlite3
import json
import logging
from flask_apscheduler import APScheduler
from datetime import datetime,timezone,timedelta
from flask import Flask, jsonify, request,g

app = Flask(__name__)
scheduler = APScheduler()
dateFormat='%Y-%m-%d %H:%M:%S'
dbPath="niuniu.db"
maxAge = "300"
apiVersion="0.0.3"

sqlite3.register_adapter(datetime, lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S"))
sqlite3.register_converter("DATETIME", lambda s: datetime.strptime(s.decode(), "%Y-%m-%d %H:%M:%S"))

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
app.logger.setLevel(logging.INFO)


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(dbPath)
        #g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def creatTable():
    conn = sqlite3.connect(dbPath)
    conn.execute('''CREATE TABLE IF NOT EXISTS party (
        id INTEGER PRIMARY KEY,
        players TEXT,
        map TEXT,
        reporter TEXT,
        updateAt DATETIME
        )'''
    )
    conn.execute('''CREATE TABLE IF NOT EXISTS player (
        id INTEGER PRIMARY KEY,
        name TEXT,
        weapon TEXT,
        skill TEXT,
        reporter TEXT,
        updateAt DATETIME,
        last TEXt,
        lastAt DATETIME,
        "selfReport" INTEGER
        )'''
    )
    conn.commit()
    conn.close()
creatTable()

@app.route("/api/party",methods=['POST'])
def party():
    userApiVersion = request.headers.get('apiVersion')
    reporter = request.headers.get('reporter')
    if((userApiVersion is None) or (userApiVersion != apiVersion)):
        app.logger.error("api version error:" + userApiVersion + "," + reporter)
        return "api version"

    data = request.get_json(force=True)
    id = int(data['id'])
    players = data['players']
    map = data['map']
    reporter = request.headers.get('reporter')
    if (id is None) or (players is None) or (map is None) or (reporter is None) or (len(players)>200) or (len(map)>100) or (len(reporter)>100) :
        return "error"

    updateAt = datetime.now(timezone.utc)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO party (id,players,map,reporter,updateAt) VALUES (?,?,?,?,?)",(id,players,map,reporter,updateAt))
    conn.commit()
    return "ok"

@app.route("/api/party",methods=['GET'])
def getParty():
    conn = get_db()
    cursor = conn.cursor()
    ret = cursor.execute("SELECT players,map,updateAt from party")
    updateAt = datetime.now(timezone.utc)
    return json.dumps({"data":ret.fetchall(),"updateAt":updateAt.strftime(dateFormat)},ensure_ascii=False),200,[("cache-control","public,max-age="+maxAge)]

@app.route("/api/player",methods=['POST'])
def player():
    userApiVersion = request.headers.get('apiVersion')
    reporter = request.headers.get('reporter')
    if((userApiVersion is None) or (userApiVersion != apiVersion)):
        app.logger.error("api version error:" + userApiVersion + "," + reporter)
        return "api version"

    data = request.get_json(force=True)
    id=int(data['id'])
    name=data['name']
    weapon=data['weapon']
    skill = data['skill']
    

    if(name is None) or(skill is None) or (reporter is None) or (len(name)>200) or (len(skill)>100) or (len(reporter)>100):
        return "error"
    if(weapon and (len(name)>200)):
        return "error"
    
    conn = get_db()
    cursor = conn.cursor()
    updateAt = datetime.now(timezone.utc)
    ret = cursor.execute("SELECT skill,updateAt,last,lastAt,weapon,selfReport FROM player WHERE id = ?",(id,))
    last = None
    lastAt = None
    selfReport = 0
    temp = ret.fetchone()
    if (temp) :
        if weapon is None:
            weapon = temp[4]
        last = temp[2]
        lastAt = temp[3]
        selfReport = temp[5]
        if((selfReport == 0) and (id == int(reporter))):
            selfReport = 1

        if(updateAt - datetime.strptime(temp[1],dateFormat).replace(tzinfo=timezone.utc) > timedelta(minutes=240)):      # "%Y-%m-%d %H:%M:%S.%f%z"
            last = temp[0]
            lastAt = temp[1]
    else:
        last = skill
        lastAt = updateAt

    cursor.execute("INSERT OR REPLACE INTO player (id,name,weapon,skill,reporter,updateAt,last,lastAt,selfReport) VALUES (?,?,?,?,?,?,?,?,?)",
                   (id,name,weapon,skill,reporter,updateAt,last,lastAt,selfReport))
    conn.commit()
    return "ok"


@app.route("/api/player",methods=['GET'])
def getPlayer():
    conn = get_db()
    cursor = conn.cursor()
    ret = cursor.execute("SELECT name,weapon,skill,updateAt,last,lastAt,selfReport from player")
    updateAt = datetime.now(timezone.utc)
    response  = json.dumps({"data" : ret.fetchall(),"updateAt" : updateAt.strftime(dateFormat)},ensure_ascii=False)
    
    return response,200,[("cache-control","public,max-age="+maxAge)]

@scheduler.task('interval',id="cleanParty",hours=2)
def cleanParty():
    conn = sqlite3.connect(dbPath)
    cursor = conn.cursor()
    cleanDate = datetime.now(timezone.utc)-timedelta(hours=23)
    cursor.execute("DELETE FROM party WHERE updateAt < ?",(cleanDate,))
    conn.commit()
    conn.execute("VACUUM;")
    conn.close()

@scheduler.task('interval',id="cleanPlayer",hours=24)
def cleanPlayer():
    conn = sqlite3.connect(dbPath)
    cursor = conn.cursor()
    cleanDate = datetime.now(timezone.utc)-timedelta(days=7)
    cursor.execute("DELETE FROM player WHERE updateAt < ?",(cleanDate,))
    conn.commit()
    conn.execute("VACUUM;")
    conn.close()

if __name__ == '__main__':
    app.teardown_appcontext(close_db)
    scheduler.init_app(app)
    scheduler.start()

    app.run(debug=False)