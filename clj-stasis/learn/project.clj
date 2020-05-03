(defproject learn "0.1.0-SNAPSHOT"
  :description "FIXME: write description"
  :url "http://example.com/FIXME"
  :license {:name "EPL-2.0 OR GPL-2.0-or-later WITH Classpath-exception-2.0"
            :url "https://www.eclipse.org/legal/epl-2.0/"}
  :dependencies [[org.clojure/clojure "1.10.0"]
                 [stasis "2.5.0"]
                 [ring "1.8.1"]
                 [hiccup "1.0.5"]
                 [markdown-clj "1.10.4"]
                 [enlive "1.1.6"]
                 [clygments "2.0.0"]
                 ]
  :plugins [[lein-ring "0.12.5"]]
  :ring {:handler learn.core/app}
  :repl-options {:init-ns learn.core})
