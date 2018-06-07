(defproject server "0.1.0-SNAPSHOT"
  :dependencies [[org.clojure/clojure "1.8.0"]
                 [ring "1.6.3"]
                 [compojure "1.6.1"]
                 
                 ;; client
                 [org.clojure/clojurescript "1.9.946"]
                 [reagent "0.7.0"]]

  :plugins [[lein-cljsbuild "1.1.7"]
            [lein-less "1.7.5"]]

  :source-paths ["src/clj"]
  :resource-paths ["resource" "target/cljsbuild"]
  :cljsbuild {:builds [{:id "dev"
                        :source-paths ["src/cljs"]
                        :compiler {:main app.core
                                   :output-to "target/cljsbuild/public/js/app.js"
                                   :output-dir "target/cljsbuild/public/js/out"
                                   :asset-path "/static/js/out"
                                   :source-map true
                                   :optimizations :none
                                   :pretty-print true}}]}
  :main server.core)
