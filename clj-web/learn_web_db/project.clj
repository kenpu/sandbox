(defproject learn_web_db "0.1.0-SNAPSHOT"
  :dependencies [; clojure
                 [org.clojure/clojure "1.8.0"]
                 ; http / clojure adapter
                 [ring "1.6.3"]
                 ; routing
                 [compojure "1.6.1"]
                 ; middlwares
                 [ring/ring-defaults "0.3.1"]
                 ; logging
                 [org.clojure/tools.logging "0.4.1"]
                 ; HTML generation
                 [hiccup "1.0.5"]
                 ; Database
                 [org.clojure/java.jdbc "0.7.6"] 
                 [org.postgresql/postgresql "LATEST"]

                 ;; [ring-oauth2 "0.1.4"]
                 ]

  ; run the web server
  :main learn-web-db.core/start-server)
