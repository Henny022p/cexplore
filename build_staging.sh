#!/bin/sh

cp c.local.properties compiler-explorer/etc/config/
docker build -t octorock/cexplore:staging .
