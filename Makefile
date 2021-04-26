.PHONY: default build publish cexplore_setup

default: build publish


publish:
	docker container stop cexplore || true && docker container rm cexplore || true
	docker container run -d --name "cexplore" --restart=always -it -p 10240:10240 octorock/cexplore:latest


build: cexplore_setup
	docker build -t henny022p/cexplore-tmc:latest .


cexplore_setup:
	rm compiler-explorer/etc/config/*.properties
	cp c.local.properties compiler-explorer/etc/config/
	cp assembly.local.properties compiler-explorer/etc/config/
	
