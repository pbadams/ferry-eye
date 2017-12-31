#! /usr/local/bin/python3
# import json
import sys
import requests
import os
import errno
import datetime
from tidylib import tidy_document

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
    return


archiveDir = "/Users/pauladams/OneDrive/BCFerries"
url = "http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp"
params = {
    "DEPT": "HSB",
    "route": "03"
}

routes = (
    {"route": "01", "DEPT": "TSA", },
    {"route": "02", "DEPT": "HSB", },
    {"route": "03", "DEPT": "HSB", },
    {"route": "08", "DEPT": "HSB", },
    {"route": "30", "DEPT": "TSA", }
)

BASE_OPTIONS = {
    "indent": 1,         # Pretty; not too much of a performance hit
    "tidy-mark": 0,        # No tidy meta tag in output
    "wrap": 1,             # No wrapping
    "alt-text": "",        # Help ensure validation
    "output-xhtml": 1,     # Convert to XHTML
    "doctype": "strict",
    "clean": 1,
    "join-styles": 1
}

datestamp = datetime.datetime.now().strftime('%Y-%m-%d')

for route in routes:
    resp = requests.get(url, params=route)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    rt = route["route"]
    dep = route["DEPT"]
    # 'HSB-Route03-%Y-%m-%d.CLEAN.html'
    filePath = "{}/route{}/{}".format(archiveDir, rt, dep, )
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
