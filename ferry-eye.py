#! /usr/local/bin/python3
# import json
import sys
# import requests
# from openpyxl import load_workbook
import re
import sqlite3 as lite
# import os.path
from bs4 import BeautifulSoup
from datetime import datetime

# Parse strings into Date object and return an ISO 8601 string 
def isoDate( dateStr, timeStr ):
    dateTimeStr = dateStr + " " + timeStr
    date = datetime.strptime(dateTimeStr, '%B %d, %Y %H:%M %p')
    return date.isoformat()

# r = requests.get('http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp?DEPT=HSB&route=03')
# soup = BeautifulSoup(r.content, 'html.parser')
# html = BeautifulSoup(soup.prettify(), 'html.parser')

fileName = sys.argv[1]
db = sys.argv[2]
dept = "HSB"
route = "03"
leg = ""


f = open(fileName, mode='r') 
soup = BeautifulSoup(f.read(), 'html.parser')
# dir = os.path.dirname( f.name )
f.close()

 # Find the last updated time on the page
elem = soup.find('td', style="font-size:11px", align="right")
dateList = elem.text.split(" ")[-3:]
dateString = ' '.join(dateList)

# find the travel data tables on the page
tables = soup.findAll('table', style="BORDER-TOP: #000 1px solid;font-size:11px", width="100%")

dbRows = []

print("Horseshoe Bay Departures\n")
for tr in tables[0].find_all('tr')[1:]:
    tds = tr.find_all('td')
    isoDepartureSched = isoDate( dateString, tds[1].text )
    isoDepartureActual = isoDate( dateString, tds[2].text )
    isoArrival = isoDate( dateString, tds[3].text )
    status = " ".join(tds[4].text.split())
    dbRows.append((dept, route, "OUT", tds[0].text, isoDepartureSched, isoDepartureActual, isoArrival, status))
    # print("Vessel: %s, Scheduled: %s, Actual: %s, Arrival Time: %s, Status: %s" % \
    #     (tds[0].text, isoDepartureSched, isoDepartureActual, isoArrival, status) )

print("\n\nLangdale Departures\n")
for tr in tables[1].find_all('tr')[1:]:
    tds = tr.find_all('td')
    isoDepartureSched = isoDate( dateString, tds[1].text )
    isoDepartureActual = isoDate( dateString, tds[2].text )
    isoArrival = isoDate( dateString, tds[3].text )
    status = " ".join(tds[4].text.split())
    dbRows.append((dept, route, "RET", tds[0].text, isoDepartureSched, isoDepartureActual, isoArrival, status))
    # print("Vessel: %s, Scheduled: %s, Actual: %s, Arrival Time: %s, Status: %s" % \
    #     ( tds[0].text, isoDepartureSched, isoDepartureActual, isoArrival, status) )

####
# Write to Sqlite DB
####
con = None
try:
    con = lite.connect(db)
    cur = con.cursor()  

    # Create table if none exists  
    cur.execute( "CREATE TABLE IF NOT EXISTS dept (dept_id INTEGER PRIMARY KEY AUTOINCREMENT, dept_name TEXT, route TEXT, leg TEXT, vessel TEXT, departure_sched TEXT, departure_actual TEXT, arrival TEXT, status TEXT);" )
    cur.executemany("INSERT INTO dept(dept_name, route, leg, vessel, departure_sched, departure_actual, arrival, status) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", dbRows)
    con.commit()

except lite.Error as e:
    
    if con:
        con.rollback()
        
    print("Error %s:" % e.args[0])
    sys.exit(1)
    
finally:
    
    if con:
        con.close()

