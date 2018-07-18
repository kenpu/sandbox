(defproject learn_websocket "0.1.0-SNAPSHOT"
  :dependencies [[org.clojure/clojure "1.8.0"]
                 ;; server
                 [ring "1.6.3"]
                 [ring/ring-defaults "0.3.1"]
                 [compojure "1.6.1"]
                 [hiccup "1.0.5"]
                 [org.clojure/tools.logging "0.3.1"]
                 [http-kit "2.2.0"]

                 ;; client
                 [org.clojure/clojurescript "1.9.946"]
                 [reagent "0.7.0"]
                 [org.clojure/core.async "0.4.474"] 
                 ]

  :plugins [[lein-cljsbuild "1.1.7"]]

  :source-paths ["src/clj"]
  :main learn-websocket.core/main
  
  :cljsbuild {:builds [{:id "dev"
                        :source-paths ["src/cljs"]
                        :compiler {:main app.core
                                   :output-to "resources/public/js/main.js"
                                   :output-dir "resources/public/js/out"
                                   :asset-path "/static/js/out"
                                   :source-map true}}]}
  )
