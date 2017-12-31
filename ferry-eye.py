#! /usr/local/bin/python3
# import json
import sys
# import requests
# from openpyxl import load_workbook
import re
import sqlite3 as lite
from glob import glob
from os import path
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import dateutil.parser
from tabulate import tabulate

# Parse strings into Date object and return an ISO 8601 string
# Regex to find valid time format string "HH:MM XM"
timeFormat = re.compile("^\d{1,2}:\d{2} (AM|PM)$")


def isoDate(dateStr, timeStr):
    if timeFormat.match(timeStr) is not None:
        timeStr = " ".join(timeStr.split())
        if timeStr.startswith("ETA: "):
            timeStr = timeStr[5:]
        dateTimeStr = dateStr + " " + timeStr
        date = datetime.strptime(dateTimeStr, '%B %d, %Y %I:%M %p')
    else:
        date = datetime.strptime(dateStr, '%B %d, %Y')
    return date.isoformat()


# r = requests.get('http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp?DEPT=HSB&route=03')
# soup = BeautifulSoup(r.content, 'html.parser')
if len(sys.argv) == 1:
    print("require directory and database")
    print("ferryeye.py /path/to/html_dir /path/to/sqlite_db_name.db")
    exit(1)
dir = sys.argv[1]
db = sys.argv[2]
dept = "HSB"
route = "03"

####
# Write to Sqlite DB
####
con = None
try:
    con = lite.connect(db)
    cur = con.cursor()

    # Create table if none exists
    cur.execute(
        "CREATE TABLE IF NOT EXISTS dept(dept_id INTEGER PRIMARY KEY AUTOINCREMENT, dept_name TEXT, route TEXT, from_port TEXT, vessel TEXT, departure_sched TEXT, departure_actual TEXT, arrival TEXT, status TEXT);"
    )
    # Get date of last entry
    cur.execute(
        "SELECT departure_sched FROM dept WHERE departure_sched = (SELECT max(departure_sched) FROM dept);")
    dateStart = cur.fetchone()
    if dateStart == None:
        start_date = dateutil.parser.parse("2017-012-20T00:00")
    else:
        start_date = dateutil.parser.parse(dateStart[0])

except lite.Error as e:

    if con:
        con.rollback()

    print("Error %s:" % e.args[0])
    sys.exit(1)

finally:

    if con:
        con.close()

####
# get list of unprocessed archive files

end_date = datetime.now()

####
# Archive Status for all routes
# routes[0] contains dummy row, to make array match Ferry route numbers
# Department codes:
# TSA == Tsawwassen
# SWB ==  Swartz Bay
# HSB == Horseshoe Bay
# LNG == Langdale
# DUK == Nanaimo, Duke Point
# NAN == Nanaimo, Departure Bay
# BOW == Bowen Island
#  site: allinurl:DEPT
# routes=[    ("FROM", "TO")]
# routes[1] = ("TSA", "SWB")
# routes[2] = ("HSB", "NAN")
# routes[3] = ("HSB", "LNG")
# routes[4] = ("SWB", "")
# routes[5] = ("SWB", "")
# routes[6] = ("","")
# routes[7] = ("","")
# routes[8] = ("HSB","BOW")
# routes[9] = ("","")
# routes[10] = ("","")
# routes[11] = ("","")
# routes[12] = ("","")
# routes[13] = ("","")
# routes[14] = ("","")
# routes[15] = ("","")
# routes[16] = ("","")
# routes[17] = ("","")
# routes[18] = ("","")
# routes[19] = ("","")
# routes[20] = ("","")
# routes[21] = ("","")
# routes[22] = ("","")
# routes[23] = ("","")
# routes[24] = ("","")
# routes[25] = ("","")
# routes[26] = ("","")
# routes[27] = ("","")
# routes[28] = ("","")
# routes[29] = ("","")
# routes[30] = ("TSA","DUK")

archiveFileTemplate = dir + '/*.CLEAN.html'
cleanFiles = glob(archiveFileTemplate)

# filename format HSB-Route03-2017-12-28.CLEAN.html
dbRows = []

for archiveFile in cleanFiles:
    fileDate = datetime.strptime(path.basename(
        archiveFile), 'HSB-Route03-%Y-%m-%d.CLEAN.html')
    if start_date <= fileDate <= end_date:

        f = open(archiveFile, mode='r')
        soup = BeautifulSoup(f.read(), 'html.parser')
        # dir = os.path.dirname( f.name )
        f.close()

        # Find the last updated time on the page
        # elem = soup.find('td', style="font-size:11px", align="right")
        elem = soup.find("td", {"class": "c3"})
        dateList = elem.text.split(" ")[-3:]
        dateString = ' '.join(dateList)

        # find the travel data tables on the page
        # tables = soup.findAll('table', style="BORDER-TOP: #000 1px solid;font-size:11px", width="100%")
        tables = soup.findAll("table", {"class": "c5"})
        if len(tables) == 0:
            print("No data tables found on page: %s\n", archiveFile)
            break

        for tr in tables[0].find_all('tr')[1:]:
            tds = tr.find_all('td')
            # If there is no Actual Departure Time then skip this record
            if len(tds[2].text) > 0:
                isoDepartureSched = isoDate(dateString, tds[1].text)
                isoDepartureActual = isoDate(dateString, tds[2].text)
                isoArrival = isoDate(dateString, tds[3].text)
                status = " ".join(tds[4].text.split())
                dbRows.append(
                    (dept, route, "HSB", tds[0].text, isoDepartureSched, isoDepartureActual, isoArrival, status))
                print

        for tr in tables[1].find_all('tr')[1:]:
            tds = tr.find_all('td')
            # If there is no Actual Departure Time then skip this record
            if len(tds[2].text) > 0:
                isoDepartureSched = isoDate(dateString, tds[1].text)
                isoDepartureActual = isoDate(dateString, tds[2].text)
                isoArrival = isoDate(dateString, tds[3].text)
                status = " ".join(tds[4].text.split())
                dbRows.append(
                    (dept, route, "LNG", tds[0].text, isoDepartureSched, isoDepartureActual, isoArrival, status))

print(tabulate(dbRows,
               headers=["Department", "Route", "From", "Vessel", "Sched. Departure",
                        "Actual Departure", "Arrival", "Status"],
               tablefmt="grid")
      )

####
# Write to Sqlite DB
####
con = None
try:
    con = lite.connect(db)
    cur = con.cursor()

    # Create table if none exists
    # cur.execute("CREATE TABLE IF NOT EXISTS dept (dept_id INTEGER PRIMARY KEY AUTOINCREMENT, dept_name TEXT, route TEXT, from_port TEXT, vessel TEXT, departure_sched TEXT, departure_actual TEXT, arrival TEXT, status TEXT);")
    cur.executemany(
        "INSERT INTO dept(dept_name, route, from_port, vessel, departure_sched, departure_actual, arrival, status) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", dbRows)
    con.commit()

except lite.Error as e:

    if con:
        con.rollback()

    print("Error %s:" % e.args[0])
    sys.exit(1)

finally:

    if con:
        con.close()
