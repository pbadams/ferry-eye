#! /bin/bash
DIR=$1
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
DATE=$(date +%Y-%m-%d)

curl \
-H "Connection: close" \
-o $DIR/HSB-Route03-$TIMESTAMP.html \
'http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp?DEPT=HSB&route=03' 

tidy -q --vertical-space no -c -asxhtml -i -o $DIR/HSB-Route03-$DATE.CLEAN.html $DIR/HSB-Route03-$TIMESTAMP.html 
 