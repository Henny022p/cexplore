FROM devkitpro/devkitarm

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y install apt-transport-https wget dirmngr build-essential git binutils-arm-none-eabi libsndfile1-dev libpng-dev python3 && curl -sL https://deb.nodesource.com/setup_12.x | bash - && apt-get -y install nodejs \
    && rm -rf /var/lib/apt/lists/*
COPY agbcc /agbcc
RUN cd /agbcc && ./build.sh && ./install.sh /agbcc_build
COPY compiler-explorer /ce/
RUN cd /ce && make prereqs webpack WEBPACK_ARGS="-p"
RUN mkdir -p /repos && cd /repos && git clone https://github.com/zeldaret/tmc.git && cd tmc && make setup
COPY update-repo.sh /scripts/update-repo.sh
COPY pycc.py /frontends/pycc.py
COPY pycat.py /frontends/pycat.py
EXPOSE 10240
CMD cd /ce && ./node_modules/.bin/supervisor -w app.js,lib,etc/config -e 'js|node|properties|yaml' --exec /usr/bin/node  -- -r esm ./app.js
