#! /usr/local/bin/python3
import sys
import os
import errno
from datetime import datetime, date, time
import re
import sqlite3 as lite
from tidylib import tidy_document, release_tidy_doc
from bs4 import BeautifulSoup
import requests
from tabulate import tabulate


def clean_text( text ):
    return " ".join(text.split())


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
    time_str = " ".join(time_str.split())
    date_time_str = date_str + " " + time_str
    # test if clean time string is in the format "HH:MM XM"
    if time_format.match(time_str) is not None:
        # create a date object from date and time
        date = datetime.strptime(date_time_str, '%B %d, %Y %I:%M %p')
    else:
         # create a date object from date alone
        date = datetime.strptime(date_str, '%B %d, %Y')
    return date.isoformat()


if len(sys.argv) == 1:
    print("require directory and database")
    print("ferryeye.py /path/to/html_dir sqlite_db_name.db")
    exit(1)
archive_dir = sys.argv[1]
db = archive_dir + "/" + sys.argv[2]
# Parse strings into Date object and return an ISO 8601 string
# Regex to find valid time format string "HH:MM XM"
time_format = re.compile("^\d{1,2}:\d{2} (AM|PM)$")

url = "http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp"

# Ferry route numbers, using mainland port codes for departures
# Used as paramters for HTTP GET request, and to form archive filepaths
routes = (
    {"route": "01", "DEPT": "TSA", "arrive": "SWB"},
    {"route": "02", "DEPT": "HSB", "arrive": "NAN"},
    {"route": "03", "DEPT": "HSB", "arrive": "LNG"},
    {"route": "08", "DEPT": "HSB", "arrive": "BOW"},
    {"route": "30", "DEPT": "TSA", "arrive": "DUK"}
)

# LibTidy Options
BASE_OPTIONS = {
    "indent": 1,           # Pretty; not too much of a performance hit
    "tidy-mark": 0,        # No tidy meta tag in output
    "wrap": 1,             # No wrapping
    "alt-text": "",        # Help ensure validation
    "output-xhtml": 1,     # Convert to XHTML
    "doctype": "strict",
    "clean": 1,
    "drop-proprietary-attributes": 1,
    "join-styles": 1
}

####
# Get last date of entries in Sqlite DB
####
con = None
try:
    con = lite.connect(db)
    cur = con.cursor()

    # Create table if none exists
    cur.execute(
        "CREATE TABLE IF NOT EXISTS routes(dept_id INTEGER PRIMARY KEY, route TEXT, departure TEXT, vessel TEXT, departure_sched DATETIME, departure_actual DATETIME, arrival DATETIME, status TEXT);"
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
                status = clean_text(tds[4].text)
                dbRows.append(
                    (rt, dep, vessel, isoDepartureSched, isoDepartureActual, isoArrival, status))

    # Database insert

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
    print("Inserting records into SQLite databse " + db )
    cur.executemany(
        # "INSERT INTO dept(dept_name, route, from_port, vessel, departure_sched, departure_actual, arrival, status) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", dbRows)
        "INSERT OR REPLACE INTO routes(route, departure, vessel, departure_sched, departure_actual, arrival, status) VALUES(?, ?, ?, ?, ?, ?, ?)", dbRows)
    
    con.commit()
    cur.execute("SELECT COUNT(*) FROM routes;")
    afterRowCount = cur.fetchone()
    print("Rows inserted: {}".format(afterRowCount[0]-beforeRowCount[0]))
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
