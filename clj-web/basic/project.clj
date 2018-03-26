(defproject basic "0.1.0-SNAPSHOT"
  :plugins [[lein-ring "0.12.1"]]
  :dependencies [;-------------------------------
                 [org.clojure/clojure "1.8.0"]
                 [compojure "1.6.0"]
                 ;[funcool/clojure.jdbc "0.9.0"]
                 [org.clojure/java.jdbc "0.7.5"]
                 [hiccup "1.0.5"]
                 [org.postgresql/postgresql "42.2.2"]
                 [ring "1.6.3"]
                 [ring/ring-json "0.4.0"]
                 [selmer "1.11.7"]
                 ;-------------------------------
                 ]
  :main basic.core/main
  :ring {:handler basic.core/app-routes}
  )
