#!/bin/bash
# Basic while loop
x=1
while true; do
    echo $x
    curl -d "data=lets_mine_$x" -X POST http://127.0.0.1:5000/mineBlock
    x=$(( $x + 1 ))
    sleep .2
done
