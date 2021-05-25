.PHONY: default build run antlr

default: build

build: antlr
	docker build -t henny022p/cexplore-tmc:parser .

run:
	docker container stop cexplore || true && docker container rm cexplore || true
	docker container run -d --name "cexplore" --restart=always -it -p 10240:10240 henny022p/cexplore-tmc:parser

antlr:
	cd frontends && java -jar /usr/share/java/antlr-4.9.2-complete.jar -o antlr ASM.g4 -no-listener -visitor -Dlanguage=Python3

clean:
	rm -r frontends/antlr
