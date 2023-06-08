#!/bin/sh
python3 -m coverage run --source src --omit="*/test*" -m unittest discover -s src
python3 -m coverage html
