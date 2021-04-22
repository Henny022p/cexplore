FROM devkitpro/devkitarm

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y install apt-transport-https wget dirmngr build-essential git binutils-arm-none-eabi libsndfile1-dev libpng-dev python3 && curl -sL https://deb.nodesource.com/setup_12.x | bash - && apt-get -y install nodejs \
    && rm -rf /var/lib/apt/lists/*
COPY agbcc /agbcc
RUN cd /agbcc && ./build.sh && ./install.sh /agbcc_build
COPY compiler-explorer /ce/
RUN cd /ce && make prereqs
RUN mkdir -p /repos && cd /repos && git clone https://github.com/zeldaret/tmc.git
RUN cd /repos/tmc && make setup
RUN mkdir -p /scripts/
COPY update-repo.sh /scripts/
RUN mkdir -p /frontends
COPY pycc.py /frontends/
COPY pycat.py /frontends/
EXPOSE 10240
ENTRYPOINT cd /ce && make
