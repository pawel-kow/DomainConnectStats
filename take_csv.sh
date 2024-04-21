#!/bin/bash

tail --lines=+$(grep -aon "Scan finished" "$1" | cut -d":" -f1) "$1" | tail -n+2 > "$1.csv"
