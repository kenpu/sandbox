build:
	docker build -t learn/jupyter .

run:
	docker run --rm -it \
		--name learn_extension \
		-p 8888:8888 \
		-v $(PWD)/jupyter_notebook_config.py:/etc/jupyter/jupyter_notebook_config.py \
		-v $(PWD)/nbextensions:/root/nbextensions \
		learn/jupyter bash

exec:
	docker exec -it learn_extension bash
