#! /bin/bash
DIR=$1
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
DATE=$(date +%Y-%m-%d)

declare -a DEPT=( "TSA", "HSB" )
 
# http://orca.bcferries.com:8080/cc/marqui/actualDepartures.asp

curl \
-H "Connection: close" \
-o $DIR/HSB/route02/HSB-Route02-$TIMESTAMP.html \
'http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp?DEPT=HSB&route=02' 

tidy -q --vertical-space no -c -asxhtml -i -o $DIR/HSB/route02/HSB-Route02-$DATE.CLEAN.html $DIR/HSB/route02/HSB-Route02-$TIMESTAMP.html 

curl \
-H "Connection: close" \
-o $DIR/HSB/route03/HSB-Route03-$TIMESTAMP.html \
'http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp?DEPT=HSB&route=03' 

tidy -q --vertical-space no -c -asxhtml -i -o $DIR/HSB/route03/HSB-Route03-$DATE.CLEAN.html $DIR/HSB/route03/HSB-Route03-$TIMESTAMP.html 


curl \
-H "Connection: close" \
-o $DIR/HSB/route08/HSB-Route08-$TIMESTAMP.html \
'http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp?DEPT=HSB&route=08' 

tidy -q --vertical-space no -c -asxhtml -i -o $DIR/HSB/route08/HSB-Route08-$DATE.CLEAN.html $DIR/HSB/route08/HSB-Route08-$TIMESTAMP.html


curl \
-H "Connection: close" \
-o $DIR/TSA/route01/TSA-Route01-$TIMESTAMP.html \
'http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp?DEPT=TSA&route=01' 

tidy -q --vertical-space no -c -asxhtml -i -o $DIR/TSA/route01/TSA-Route01-$DATE.CLEAN.html $DIR/TSA/route01/TSA-Route01-$TIMESTAMP.html


curl \
-H "Connection: close" \
-o $DIR/TSA/route30/TSA-Route30-$TIMESTAMP.html \
'http://orca.bcferries.com:8080/cc/marqui/arrivals-departures.asp?DEPT=TSA&route=30' 

tidy -q --vertical-space no -c -asxhtml -i -o $DIR/TSA/route30/TSA-Route30-$DATE.CLEAN.html $DIR/TSA/route30/TSA-Route30-$TIMESTAMP.html
