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

# Parse strings into Date object and return an ISO 8601 string


def isoDate(dateStr, timeStr):
    if len(timeStr) > 0:
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
    cur.execute("CREATE TABLE IF NOT EXISTS dept (dept_id INTEGER PRIMARY KEY AUTOINCREMENT, dept_name TEXT, route TEXT, leg TEXT, vessel TEXT, departure_sched TEXT, departure_actual TEXT, arrival TEXT, status TEXT);")
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
delta_one_day = timedelta(days=1)

archiveFileTemplate = dir + '/*.CLEAN.html'
cleanFiles = glob(archiveFileTemplate)

# filename format HSB-Route03-2017-12-28.CLEAN.html
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
            break

        dbRows = []

        for tr in tables[0].find_all('tr')[1:]:
            tds = tr.find_all('td')
            # If there is no Actual Departure Time then skip this record
            if len(tds[2].text) > 0:
                isoDepartureSched = isoDate(dateString, tds[1].text)
                isoDepartureActual = isoDate(dateString, tds[2].text)
                isoArrival = isoDate(dateString, tds[3].text)
                status = " ".join(tds[4].text.split())
                dbRows.append(
                    (dept, route, "OUT", tds[0].text, isoDepartureSched, isoDepartureActual, isoArrival, status))

        for tr in tables[1].find_all('tr')[1:]:
            tds = tr.find_all('td')
            # If there is no Actual Departure Time then skip this record
            if len(tds[2].text) > 0:
                isoDepartureSched = isoDate(dateString, tds[1].text)
                isoDepartureActual = isoDate(dateString, tds[2].text)
                isoArrival = isoDate(dateString, tds[3].text)
                status = " ".join(tds[4].text.split())
                dbRows.append(
                    (dept, route, "RET", tds[0].text, isoDepartureSched, isoDepartureActual, isoArrival, status))

        ####
        # Write to Sqlite DB
        ####
        con = None
        try:
            con = lite.connect(db)
            cur = con.cursor()

            # Create table if none exists
            cur.execute("CREATE TABLE IF NOT EXISTS dept (dept_id INTEGER PRIMARY KEY AUTOINCREMENT, dept_name TEXT, route TEXT, leg TEXT, vessel TEXT, departure_sched TEXT, departure_actual TEXT, arrival TEXT, status TEXT);")
            cur.executemany(
                "INSERT INTO dept(dept_name, route, leg, vessel, departure_sched, departure_actual, arrival, status) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", dbRows)
            con.commit()

        except lite.Error as e:

            if con:
                con.rollback()

            print("Error %s:" % e.args[0])
            sys.exit(1)

        finally:

            if con:
                con.close()
