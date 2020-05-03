(defproject learn_pedestal "0.1.0-SNAPSHOT"
  :description "FIXME: write description"
  :url "http://example.com/FIXME"
  :license {:name "EPL-2.0 OR GPL-2.0-or-later WITH Classpath-exception-2.0"
            :url "https://www.eclipse.org/legal/epl-2.0/"}
  :dependencies [[org.clojure/clojure "1.10.0"]
                 [io.pedestal/pedestal.service       "0.5.7"]
                 [io.pedestal/pedestal.service-tools "0.5.7"] ;; Only needed for ns-watching; WAR tooling
                 [io.pedestal/pedestal.jetty         "0.5.7"]
                 [io.pedestal/pedestal.immutant      "0.5.7"]
                 [io.pedestal/pedestal.tomcat        "0.5.7"]
                 [io.pedestal/pedestal.aws           "0.5.7"] ;; API-Gateway, Lambda, and X-Ray support
                 [org.clojure/data.json "0.2.6"]
                 [org.slf4j/slf4j-simple "1.7.28"]
                 ]
  :repl-options {:init-ns learn-pedestal.core})
