#!/bin/bash
SESSION_NAME=exp_
COMMAND=python
i=0


# Standard way of reading a file line by line
while IFS= read -r line; do
	# just to run 10 python script
	screen -dmS "$SESSION_NAME$i" bash -c "$COMMAND $line"
    sleep 3
    if [[ "$i" == '9' ]]
    then
        break
    fi
	i=$((i+1))
done < "$1"
