(ns clj-postgresql.core
  (:require [clojure.java.jdbc :as j]
            [clojure.pprint :refer [pprint]]))

(def db-spec {:classname "org.postgresql.Driver"
              :subprotocol "postgresql"
              :subname "//localhost:5433/kenpu"
              :user "kenpu"
              :password "abc"})

(defn -main [& [inst]]
  (-> (j/query db-spec ["select distinct semester 
                        from schedule
                        where instructor like ?"
                        (or inst "%")]
               {:raw? true
                :keywordize? false})
      (pprint)))


