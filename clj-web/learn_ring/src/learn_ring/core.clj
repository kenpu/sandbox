(ns learn-ring.core
  (:require [ring.middleware.reload :refer [wrap-reload]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.middleware.session :refer [wrap-session]]
            [ring.middleware.session.cookie :refer [cookie-store]]
            [ring.util.response :refer [response]]
            [clojure.pprint :refer [pprint]])
  (:use ring.adapter.jetty))

(defn handler [request]
  (let [{:keys [params
                session]} request
        q (str (with-out-str (pprint params)))
        counter (get session :counter 0)]
    {:status 200
     :session {:counter (inc counter)}
     :headers {"Content-Type" "text/html"}
     :body (str "<h1>Params</h1>
                <pre>" 
                q
                "</pre>
                <h1>Counter</h1>
                <pre>"
                counter
                "</pre>")}))

(def app (-> #'handler
             (wrap-session {:store (cookie-store)})
             wrap-params
             wrap-reload))

(defn main [& args] (run-jetty app {:port 1234}))
