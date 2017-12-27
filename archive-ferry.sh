#! /bin/bash
DIR=$1
DATE=$(date +%Y-%m-%d_%H-%M-%S)

curl \
-H "Connection: close" \
-o $DIR/HSB-Route03-$DATE.html \
'http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp?DEPT=HSB&route=03' 

tidy -q --vertical-space no -i -o $DIR/HSB-Route03-$DATE.CLEAN.html $DIR/HSB-Route03-$DATE.html 
