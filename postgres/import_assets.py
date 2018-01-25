import json
import os
import time
import urllib

import psycopg2
from websocket import create_connection

import config


ws = create_connection(config.WEBSOCKET_URL)

con = psycopg2.connect(**config.POSTGRES)
cur = con.cursor()

query = "TRUNCATE assets"
cur.execute(query)
#con.commit()

query = "ALTER SEQUENCE assets_id_seq RESTART WITH 1;"
cur.execute(query)
#con.commit()

# alter sequence of the ops once a day here
query = "DELETE FROM ops WHERE oid NOT IN (SELECT oid FROM ops ORDER BY oid DESC LIMIT 10);"
cur.execute(query)
#con.commit()
for x in range(0, 10):
    query = "UPDATE ops set oid="+str(x+1)+" WHERE oid IN (SELECT oid FROM ops ORDER BY oid LIMIT 1 OFFSET "+str(x)+");"
    #print query
    cur.execute(query)

query = "ALTER SEQUENCE ops_oid_seq RESTART WITH 11;"
cur.execute(query)

con.commit()

all_assets = []

ws.send('{"id":1, "method":"call", "params":[0,"list_assets",["AAAAA", 100]]}')
result = ws.recv()
j = json.loads(result)

all_assets.append(j);

len_result = len(j["result"])

print len_result
#print all_assets

while len_result == 100:
    ws.send('{"id":1, "method":"call", "params":[0,"list_assets",["'+j["result"][99]["symbol"]+'", 100]]}')
    result = ws.recv()
    j = json.loads(result)
    len_result = len(j["result"])
    all_assets.append(j);

for x in range(0, len(all_assets)):
    size = len(all_assets[x]["result"])
    print size

    for i in range(0, size):
        symbol = all_assets[x]["result"][i]["symbol"]
        asset_id = all_assets[x]["result"][i]["id"]

        url = "http://23.94.69.140:5000/get_asset?asset_id=" + asset_id
        print url
        precision = 5
        response3 = urllib.urlopen(url)
        try:
            data3 = json.loads(response3.read())
            current_supply = data3[0]["current_supply"]
            precision = data3[0]["precision"]
            # print current_supply
        except:
            price = 0
            continue

        url = "http://23.94.69.140:5000/get_asset_holders_count?asset_id=" + asset_id
        # print url
        response4 = urllib.urlopen(url)
        try:
            data4 = json.loads(response4.read())
            holders = data4
            # print holders
        except:
            holders = 0
            continue

        if symbol == "BTS":
            type_ = "Core Token"
        elif all_assets[x]["result"][i]["issuer"] == "1.2.0":
            type_ = "SmartCoin"
        else:
            type_ = "User Issued"
        #print all_assets[x]["result"][i]


        url = "http://23.94.69.140:5000/get_volume?base=BTS&quote=" + symbol
        response = urllib.urlopen(url)

        try:
            data = json.loads(response.read())
        except:
            continue

        #print symbol
        #print data["quote_volume"]

        url = "http://23.94.69.140:5000/get_ticker?base=BTS&quote=" + symbol
        response2 = urllib.urlopen(url)
        try:
            data2 = json.loads(response2.read())
            price = data2["latest"]
            #print price

            if str(price) == 'inf':
               continue
            #    exit

            #print price
        except:
            price = 0
            continue

        mcap = int(current_supply) * float(price)

        query = "INSERT INTO assets (aname, aid, price, volume, mcap, type, current_supply, holders, wallettype, precision) VALUES('"+symbol+"', '"+asset_id+"', '"+price+"', '"+data['base_volume']+"', '"+str(mcap)+"', '"+type_+"', '"+str(current_supply)+"', '"+str(holders)+"', '','"+str(precision)+"')"
        #query = "INSERT INTO assets (aname, aid, price, volume, mcap, type, current_supply, holders) VALUES('" + symbol + "', '" + asset_id + "', '" + price + "', '0', '" + str(mcap) + "', '" + type_ + "', '" + str(current_supply) + "', '" + str(holders) + "')"

        print query
        cur.execute(query)
        con.commit()


# with updated volume, add stats
query = "select sum(volume) from assets WHERE aname!='BTS'"
cur.execute(query)
results = cur.fetchone()
volume = results[0]

query = "select sum(mcap) from assets"
cur.execute(query)
results = cur.fetchone()
market_cap = results[0]

query = "INSERT INTO stats (type, value, date) VALUES('volume_bts', '"+str(int(round(volume)))+"', NOW())"
print query
cur.execute(query)
con.commit()

"""query = "INSERT INTO stats (type, value, date) VALUES('market_cap_bts', '"+str(int(round(market_cap)))+"', NOW())" # out of range for bigint, fix.
print query
cur.execute(query)
con.commit()
"""

# insert core token manually
url = "http://23.94.69.140:5000/get_asset?asset_id=1.3.0"
response3 = urllib.urlopen(url)
data3 = json.loads(response3.read())
current_supply = data3[0]["current_supply"]

url = "http://23.94.69.140:5000/get_asset_holders_count?asset_id=1.3.0"
response4 = urllib.urlopen(url)
data4 = json.loads(response4.read())
holders = data4

mcap = int(current_supply)

query = "INSERT INTO assets (aname, aid, price, volume, mcap, type, current_supply, holders, wallettype) VALUES('BTS', '1.3.0', '1', '"+str(volume)+"', '"+str(mcap)+"', 'Core Token', '" + str(current_supply) + "', '" + str(holders) + "', '')"
cur.execute(query)
con.commit()

cur.close()
con.close()
