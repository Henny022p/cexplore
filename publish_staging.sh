#!/bin/sh
docker container stop cexplore_staging || true && docker container rm cexplore_staging || true
docker container run -d --name "cexplore_staging" --restart=always -it -p 10243:10240 octorock/cexplore:staging