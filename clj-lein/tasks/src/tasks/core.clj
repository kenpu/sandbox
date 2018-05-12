(ns tasks.core
  (:require [clojure.java.io :as io]))

(defn -main
  []
  (with-open [f (io/reader "abc.txt")]
    (println (slurp f))))
