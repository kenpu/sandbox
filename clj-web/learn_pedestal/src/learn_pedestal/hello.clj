(ns learn-pedestal.hello
  (:require [io.pedestal.http :as http]
            [io.pedestal.http.route :as route]
            [io.pedestal.test :as test]))

(defn response
  [status body & {:as headers}]
  {:status status
   :body body
   :headers (or headers {"Content-Type" "text/plain"})})

(def ok (partial response 200))
(def created (partial response 201))
(def accepted (partial response 202))

(def echo
  {:name :echo
   :enter (fn [context]
            (let [request (:request context)
                  response (ok context)]
              (assoc context :response response)))})

(def routes
  (route/expand-routes
   #{["/todo"                  :post     echo :route-name :list-create]
     ["/todo"                  :get      echo :route-name :list-query-form]
     ["/todo/:list-id"          :get      echo :route-name :list-view]
     ["/todo/:list-id"          :post     echo :route-name :list-item-create]
     ["/todo/:list-id/:item-id" :get      echo :route-name :list-item-view]
     ["/todo/:list-id/:item-id" :put      echo :route-name :list-item-update]
     ["/todo/:list-id/:item-id" :delete   echo :route-name :list-item-delete]}))

(defonce server (atom nil))
(defn start
  []
  (->> {::http/routes routes
        ::http/type :jetty
        ::http/port 8080
        ::http/join? false}
       (http/create-server)
       (http/start)
       (reset! server)))

(defn stop
  []
  (http/stop @server))
