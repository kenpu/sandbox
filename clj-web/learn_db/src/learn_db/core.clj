(ns learn-db.core
  (require [clojure.java.jdbc :as sql]))

(def db {:subprotocol "postgresql"
         :subname "//localhost:6432/mydb"
         :user "cljdb"
         :password "dbclj"})

(defn random-string [n]
  (clojure.string/join "" 
                       (map (fn [_]
                              (char (+ 65 (rand-int 26)))) 
                            (range n))))
  
(defn create-test-data [n]
  (sql/with-db-transaction [tx db]
    (dotimes [_ n]
      (sql/execute! tx 
                    ["insert into users values (?,?,?)"
                     (random-string 10)
                     (random-string 20)
                     (str (random-string 5) 
                          "@"
                          (random-string 10)
                          "."
                          (random-string 3))]))))

(defn query-data
  []
  (let [result (sql/query db 
                          ["select * from users
                           where id like 'Z%'"])]
    result))

