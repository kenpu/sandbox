(ns clj-db.core
  (:require [clojure.java.jdbc :as j]
            [clojure.java.io :as io]
            [clojure.string :as string]))
"
https://github.com/clojure-cookbook/clojure-cookbook/blob/master/06_databases/6-03_manipulating-an-SQL-database.asciidoc
"

(def db-spec {:classname "org.sqlite.JDBC"
              :subprotocol "sqlite"
              :subname "abc.sqlite"})

(def sql-create-table
  "create table T (
    id integer primary key autoincrement,
    c1 text,
    c2 real)")

(defn init-db []
  (try (j/db-do-commands
         db-spec
         [sql-create-table])
       (catch Exception e
         (println "error" (.getMessage e)))))

(defn get-str [n]
  (string/join ""
               (map str 
                    (take n (repeatedly #(rand-int 10))))))

(defn insert-data []
  (j/with-db-transaction 
    [tx db-spec]
    (let [ret (j/insert-multi!
                tx 
                "T" 
                [ 
                 {:c1 (get-str 10) :c2 (rand)}
                 {:c1 (get-str 10) :c2 (rand)}
                 {:c1 (get-str 10) :c2 (rand)}
                 ])]
      (println (map #(-> % vals first) ret)))))

(defn test-1 []
  (println (get-str 10))
  (println (slurp (io/resource "hello.txt"))))

(defn main []
  (println "Test"))
