#! /usr/local/bin/python3
import sys
import os
import errno
import json
from datetime import datetime, date
import re
import sqlite3 as lite
from tidylib import tidy_document, release_tidy_doc
from bs4 import BeautifulSoup
import requests
from tabulate import tabulate


def clean_text(text):
    return " ".join(text.split())


def is_eta(t):
    if eta_format.match(t):
        return True
    else:
        return False

def mkdir_p(path):
    # Make directory tree if it doesn't exist
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
    return


def isoDate(date_str, time_str):
     # Clean out all white space characters from time string
    time_str = clean_text(time_str)
    date_time_str = date_str + " " + time_str
    # test if clean time string is in the format "HH:MM XM"
    if time_format.match(time_str):
        # create a date object from date and time
        d = datetime.strptime(date_time_str, '%B %d, %Y %I:%M %p').isoformat()
    else:
        if eta_format.match(time_str):
            d = datetime.strptime(date_time_str, '%B %d, %Y ETA: %I:%M %p').isoformat()
        else:
            # create a date object from date alone
            d = None
    return d


if len(sys.argv) == 1:
    print("require directory and database")
    print("ferryeye.py /path/to/html_dir sqlite_db_name.db")
    exit(1)


# Try loading config.json
try:
    with open('config.json') as json_data_file:
        CONFIG = json.load(json_data_file)
except EnvironmentError:  # parent of IOError, OSError *and* WindowsError where available
    print('Cannot open config.json')
    print(EnvironmentError.errno)
    exit()

archive_dir = CONFIG["archive_dir"]
db = CONFIG["db"]
# Regex to find valid time format string "HH:MM XM"
time_format = re.compile("^\d{1,2}:\d{2} (AM|PM)$")
# Regex to find valid time format string "ETA: HH:MM XM"
eta_format = re.compile("^ETA: \d{1,2}:\d{2} (AM|PM)$")

url = CONFIG["url"]

# Ferry route numbers, using mainland port codes for departures
# Used as paramters for HTTP GET request, and to form archive filepaths
routes = CONFIG["routes"]

# LibTidy Options
BASE_OPTIONS = CONFIG["BASE_OPTIONS"]

####
# Get last date of entries in Sqlite DB
####
con = None
try:
    con = lite.connect(db)
    cur = con.cursor()

    # Create table if none exists
    cur.execute(
        "CREATE TABLE IF NOT EXISTS routes(route TEXT, departure TEXT, vessel TEXT, departure_sched DATETIME, departure_actual DATETIME, arrival DATETIME, eta BOOLEAN, status TEXT, PRIMARY KEY (route, departure, departure_sched) );"
    )
    cur.execute("SELECT COUNT(*) FROM routes;")
    beforeRowCount = cur.fetchone()
    print("Current rows in database: {}".format(beforeRowCount[0]))

    # Get date of last entry
    cur.execute(
        "SELECT departure_sched FROM routes WHERE departure_sched = (SELECT max(departure_sched) FROM routes);")

    if cur.fetchone() is None:
        # Set start_date to before archives begin
        start_date = date(2017, 12, 20)
    else:
        start_date = cur.fetchone()

except lite.Error as e:

    if con:
        con.rollback()

    print("Error %s:" % e.args[0])
    sys.exit(1)

finally:

    if con:
        con.close()

# Today's datestamp for cleaned archive files
datestamp = datetime.now().strftime('%Y-%m-%d')

dbRows = []

# Main loop - Iterate over routes set
for route in routes:

    rt = route["route"]
    dep = route["DEPT"]
    print("Processing Route: {}, departing from {}".format(rt, dep, ))

    # Get current status page for route number from departure port
    resp = requests.get(url, params=route)

    # Timestamp for raw HTML archive (we could be doing this multiple times a day)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    # Build filepath for archive, create directory tree if not present
    filePath = "{}/Route{}/{}".format(archive_dir, rt, dep, )
    mkdir_p(filePath)

    ####
    # Write raw HTML archive
    fileName = "{}/{}-Route{}-{}.html".format(filePath, dep, rt, timestamp)
    file = open(fileName, "w+")
    file.write(resp.text)
    file.close()

    ####
    # write CLEAN HTML archive
    fileName = "{}/{}-Route{}-{}.CLEAN.html".format(
        filePath, dep, rt, datestamp)
    cleanHTML = tidy_document(resp.text)
    file = open(fileName, "w+")
    file.write(cleanHTML[0])
    file.close()

    # Release memory used by DOC tree
    release_tidy_doc()

    # Scrape HTML doc for tables containing ferry status
    soup = BeautifulSoup(cleanHTML[0], 'html.parser')

    # Find the last updated time on the page
    # elem = soup.find("td", {"class": "c3"})
    elem = soup.find('td', style="font-size:11px", align="right")
    dateList = clean_text(elem.text)
    dateList = dateList.split(" ")[-3:]
    dateString = ' '.join(dateList)

    # loop through tables and create array of sets ready for DB insert
    tables = soup.findAll(
        'table', style="BORDER-TOP: #000 1px solid;font-size:11px", width="100%")

    for idx, table in enumerate(tables):
        if idx == 1:
            dep = route["arrive"]

        for tr in table.find_all('tr')[1:]:
            tds = tr.find_all('td')
            # If there is no Actual Departure Time then skip this record
            if len(clean_text(tds[2].text)) > 0:
                vessel = clean_text(tds[0].text)
                isoDepartureSched = isoDate(dateString, tds[1].text)
                isoDepartureActual = isoDate(dateString, tds[2].text)
                isoArrival = isoDate(dateString, tds[3].text)
                eta = is_eta(clean_text(tds[3].text))
                status = clean_text(tds[4].text)
                dbRows.append(
                    (rt, dep, vessel, isoDepartureSched, isoDepartureActual, isoArrival, eta, status))

    # Database insert

print(tabulate(dbRows,
               headers=["Route", "From", "Vessel", "Sched. Departure",
                        "Actual Departure", "Arrival", "ETA", "Status"],
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
    print("Inserting records into SQLite databse " + db)
    cur.executemany(
        # "INSERT INTO dept(dept_name, route, from_port, vessel, departure_sched, departure_actual, arrival, status) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", dbRows)
        "INSERT OR REPLACE INTO routes(route, departure, vessel, departure_sched, departure_actual, arrival, eta, status) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", dbRows)

    con.commit()
    cur.execute("SELECT COUNT(*) FROM routes;")
    afterRowCount = cur.fetchone()
    print("Rows inserted: {}".format(afterRowCount[0] - beforeRowCount[0]))
    print("Total rows changed: ", con.total_changes)
    print("Total rows in database: {}".format(afterRowCount[0]))

except lite.Error as e:

    if con:
        con.rollback()

    print("Error %s:" % e.args[0])
    sys.exit(1)

finally:

    if con:
        con.close()

print("Processing ended")
