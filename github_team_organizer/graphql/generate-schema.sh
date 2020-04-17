#!/usr/bin/env sh

python3 -m sgqlc.introspection \
     --exclude-deprecated \
     --exclude-description \
     -H "Authorization: bearer ${TOKEN}" \
     https://api.github.com/graphql \
     github_schema.json

sgqlc-codegen github_schema.json github_schema.py
