#!/bin/bash
echo "Removing result folder..."
rm -R result/
echo "Dropping db.."
mongo ccrawler --eval "printjson(db.dropDatabase())"
echo "Starting python.."
python main.py