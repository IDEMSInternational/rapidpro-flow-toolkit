#!/bin/sh
python3 -m coverage run --source . --omit="*/test*" -m unittest
python3 -m coverage html
