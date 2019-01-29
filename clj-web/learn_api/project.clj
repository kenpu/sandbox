(defproject learn_api "0.1.0-SNAPSHOT"
  :dependencies [[org.clojure/clojure "1.8.0"]
                 [metosin/compojure-api "2.0.0-alpha21"]]
  :plugins [[lein-ring "0.12.4"]]
  :ring {:handler learn-api.core/app}
  )
