(ns learn-websocket.ws
  (:require [compojure.core :as c]
            [compojure.route :as r]
            [clojure.tools.logging :as log]
            [clojure.pprint :refer [pprint]]
            [org.httpkit.server :refer [with-channel on-close on-receive send! run-server]]))

(def ids (ref 100))

(defn get-id []
  (dosync
    (alter ids inc)))

(defn handler [req]
  (with-channel req ch
                (println "connected")
                (send! ch (str "hello there:" (get-id)))
                (on-receive ch (fn [data]
                                 (println "on-receive")))
                (on-close ch (fn [status]
                               (println "on-close")))))

(defn -main
  []
  (let [port 9876]
    (println "Websocket started:" port)
    (run-server handler {:port port})))
