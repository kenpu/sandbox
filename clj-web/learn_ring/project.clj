(defproject learn_ring "0.1.0-SNAPSHOT"
  :description "FIXME: write description"
  :url "http://example.com/FIXME"
  :license {:name "Eclipse Public License"
            :url "http://www.eclipse.org/legal/epl-v10.html"}
  :dependencies [[org.clojure/clojure "1.8.0"]
                 [ring "1.6.3"]]
  :plugins [[lein-ring "0.12.1"]]
  :main learn-ring.core/main
  :ring {:handler learn-ring.core/app
         :port 1234}
  )
