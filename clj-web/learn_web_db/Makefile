run:
	lein run

db:
	docker run \
		-it --rm \
		--name pg_for_clojure \
		-e POSTGRES_USER=cljdb \
		-e POSTGRES_PASSWORD=dbclj \
		-e POSTGRES_DB=mydb \
		-e PGDATA=/pgdata \
		-v $(PWD)/pgdata:/pgdata \
		-p 6432:5432 \
		postgres
psql:
	psql -h localhost -p 6432 -U cljdb -d mydb
