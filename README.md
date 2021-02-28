# cexplore
Implementation for old, weird compilers to work with godbolts Compiler explorer

Compiler Explorer instance for tmc

## Usage
Clone the repository
```
git clone --recurse-submodules https://github.com/octorock/cexplore.git
```
Build the docker image
```
cd cexplore
./build.sh
```
Run the docker image
```
./publish.sh
```
The Compiler Explorer instance will be available after a short while at http://localhost:10240/.

### Updating
If there was an update to the tmc repository, execute
```
docker exec -it cexplore /scripts/update-repo.sh
```