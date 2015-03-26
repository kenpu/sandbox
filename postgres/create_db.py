import psycopg2 as pg
import random
from time import time

K = 5

Tables = [
        ("points", """
                CREATE TABLE points (
                id SERIAL,
                x1 REAL,
                x2 REAL,
                x3 REAL,
                PRIMARY KEY (id))
                """),
        ("clusters",
                """
                CREATE TABLE clusters (
                cid INT,
                pid INT,
                FOREIGN KEY (pid) REFERENCES points (id))
                """),
        ("centroid",
            """
            CREATE TABLE centroid(cid, x1, x2, x3, delta) AS
            select *, 
                   random() * 2 - 1,
                   random() * 2 - 1,
                   random() * 2 - 1,
                   1000.0
            from generate_series(0, %s)
            """ % K),
        ]

def create_tables(conn):
    c = conn.cursor()

    for t in (x[0] for x in Tables):
        try:
            c.execute("drop table %s cascade" % t)
            conn.commit()
        except Exception, e:
            print "Unable to drop table %s: %s" % (t, e)
            conn.rollback()

    for t, sql in Tables:
        try:
            c.execute(sql)
        except Exception, e:
            print "Unable to create table %s: %s" % (t, e)
            conn.rollback()
        else:
            print "Table %s created" % t
            conn.commit()

def into_tables(conn):
    c = conn.cursor()
    start = time()
    for n in xrange(10000):
        p = [random.gauss(0, 1) for i in range(3)]
        c.execute(
            "insert into points(x1, x2, x3) values(%s, %s, %s)", p)
        if n % 10000 == 0:
            print "Inserted %d rows in %.2f seconds" % (n, time()-start)

    conn.commit()
    duration = time() - start
    print "Inserted into points %d rows in %.2f seconds" % (n, duration)

if __name__ == '__main__':
    conn = pg.connect(dbname="cluster")
    create_tables(conn)
    into_tables(conn)
