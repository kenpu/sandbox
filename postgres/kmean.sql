-- compute membership
delete from clusters;

WITH 
dist(cid, pid, d) AS (
    SELECT C.cid, P.id as pid, 
           ((C.x1-P.x1)^2+ (C.x2-P.x2)^2+ (C.x3-P.x3)^2) AS d
    from centroid C, points P),
T(cid, pid, d, dmin) AS (
    SELECT cid, pid, d, min(d) OVER (partition by pid) AS dmin
    from dist)
INSERT INTO clusters(cid, pid)
    SELECT max(cid), pid
    FROM T
    WHERE d = dmin
    group by pid;

-- cluster sizes
select cid, count(distinct pid)
from clusters
group by cid;

-- update centroid
WITH
Cnew (cid, x1, x2, x3) AS (
    select cid, avg(x1), avg(x2), avg(x3)
    from clusters C join points P on C.pid = P.id
    group by cid)
INSERT INTO centroid
    SELECT C.cid, 
        Cnew.x1, Cnew.x2, Cnew.x3,
        abs(Cnew.x1-C.x1) +
        abs(Cnew.x2-C.x2) +
        abs(Cnew.x3-C.x3) as delta
    FROM centroid C join Cnew using (cid);

