(defproject clojure_goog_or "0.1.0-SNAPSHOT"
  :dependencies [[org.clojure/clojure "1.8.0"]]
  :jvm-opts ["-Djava.library.path=../lib"]
  :resource-paths ["../lib/com.google.ortools.jar"]
  :native-path "../lib"
  :aot [clojure-goog-or.core]
  :jar-name "goog-or.jar"
  :main clojure-goog-or.core)
