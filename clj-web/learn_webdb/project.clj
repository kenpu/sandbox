(defproject learn_webdb "0.1.0-SNAPSHOT"
  :dependencies [[org.clojure/clojure "1.8.0"]
                 [org.clojure/java.jdbc "0.7.6"]
                 [org.postgresql/postgresql "LATEST"]
                 [migratus "1.0.6"]
                 [io.aviso/pretty "0.1.34"]]

  :plugins [[migratus-lein "0.5.7"]
            [io.aviso/pretty "0.1.34"]]

  :migratus {:store :database
             :migration-dir "migrations"
             :db {:classname   "org.postgresql.jdbc.Driver"
                  :subprotocol "postgresql"
                  :subname     "//localhost:6432/mydb"
                  :user        "cljdb"
                  :password    "dbclj"}})
