all:
	lein run -m clj-db.core/init-db

select:
	echo "select * from T" | sqlite3 abc.sqlite

clean:
	rm -f *.sqlite
