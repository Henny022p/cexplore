#!/bin/sh

# Remove other languages
rm compiler-explorer/etc/config/*.properties
cp c.local.properties compiler-explorer/etc/config/
cp assembly.local.properties compiler-explorer/etc/config/
docker build -t octorock/cexplore:latest .
