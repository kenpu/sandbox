(ns clj-cloud.core
  (:require [clj-http.client :as client]
            [clj-http.core :as http]
            [clj-http.conn-mgr :as conn]
            ))

(defn foo
  "I don't do a whole lot."
  [x]
  (println x "Hello, World!"))

(def r (atom nil))

(defn stringify [action]
  (cond
    (keyword? action) (-> action 
                          name 
                          (clojure.string/replace "-" "_")
                          (clojure.string/lower-case))
    :else (str action)))

(def host "https://open.canada.ca")

(defn ckan [& [action]]
  (let [url (str host "/ckan/en/api/3/action/")]
    (if action
      (str url (stringify action))
      url)))

(defn start-session [host]
  (let [cm (conn/make-reuseable-async-conn-manager {:io-config {:so-keep-alive true}})
        cl (http/build-async-http-client {} cm host)]
    {:cm cm
     :client cl}))

(defn session-get [session url]
  (let [cm (:cm session)
        cl (:client session)]
    (client/get url {:connection-manager cm
                     :http-client cl})))

(defn main []
  (let [cm (conn/make-reusable-conn-manager {})
        resp (client/get host {:connection-manager cm})
        hclient (:http-client resp)]
    (println host)
    (client/get (ckan) {:connection-manager cm :http-client hclient})
    (println (ckan))
    (client/get (ckan :package-list) {:connection-manager cm :http-client hclient})
    (println (ckan :package-list))))

