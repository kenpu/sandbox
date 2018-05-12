(defproject learn_compojure "0.1.0-SNAPSHOT"
  :description "FIXME: write description"
  :url "http://example.com/FIXME"
  :license {:name "Eclipse Public License"
            :url "http://www.eclipse.org/legal/epl-v10.html"}
  :dependencies [[org.clojure/clojure "1.8.0"]
                 [ring "1.6.3"]
                 [ring-oauth2 "0.1.4"]
                 [ring/ring-defaults "0.3.1"]
                 [compojure "1.6.1"]
                 [cheshire "5.8.0"]
                 [environ "1.1.0"]
                 [stuarth/clj-oauth2 "0.3.2"]
                 [org.clojure/tools.logging "0.4.1"]]
  :plugins [[lein-environ "1.1.0"]]
  :main learn-compojure.core
  :profiles {:dev {:env {:profile :dev}}}
  )
