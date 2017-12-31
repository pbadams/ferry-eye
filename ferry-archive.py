#! /usr/local/bin/python3
# import json
import sys
import requests
import os
import errno
import datetime
from tidylib import tidy_document, release_tidy_doc

# Make directory tree if it doesn't exist
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

# Ferry route numbers, using mainland port codes for departures 
# Used as paramters for HTTP GET request, and to form archive filepaths
routes = (
    {"route": "01", "DEPT": "TSA", },
    {"route": "02", "DEPT": "HSB", },
    {"route": "03", "DEPT": "HSB", },
    {"route": "08", "DEPT": "HSB", },
    {"route": "30", "DEPT": "TSA", }
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

# datestamp for clean archive files
datestamp = datetime.datetime.now().strftime('%Y-%m-%d')

# Main loop - Iterate over routes set
for route in routes:

    rt = route["route"]
    dep = route["DEPT"]
    print("Processing Route: {}, departing from {}".format( rt, dep, ))

    # Get current status page for route number from departure port
    resp = requests.get(url, params=route)

    # Timestamp for raw HTML archive (we could be doing this multiple times a day)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    # Build filepath for archive, create directory tree if not present
    filePath = "{}/Route{}/{}".format(archiveDir, rt, dep, )
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

print("Processing ended")