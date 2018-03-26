(ns basic.core
  (:require [clojure.java.io]
            [compojure.core :refer [defroutes routes GET context]] 
            [compojure.route :as route]
            [hiccup.core :refer [html]]
            ;[jdbc.core :as jdbc]
            [clojure.java.jdbc :as j]
            [ring.adapter.jetty :refer [run-jetty]]
            [ring.middleware.reload :refer [wrap-reload]]
            [ring.middleware.json :refer [wrap-json-response]]
            [selmer.parser :as selmer]
            ))

(def data
  [:html
   [:head 
    [:title "Okay"]]
   [:body
    [:ul
     [:li "Hello"]
     [:li "World"]
     ]]])

(def dbspec {:subprotocol "postgresql"
             :subname "//172.17.0.2:5432/db"
             :user "user"
             :password "hello"})

(defn get-db-stuff []
  (with-open [conn (jdbc/connection dbspec)]
    (let [result (jdbc/fetch conn ["select a, b::text from t1 limit 10"])]
      {:result result})))

(defroutes app-routes
           (GET "/" [] (selmer/render-file "home.html" {:name "Hello"}))
           (GET "/hello" [] (str "Hello"))
           (GET "/hiccup" [] (html data))
           (GET "/sql" [] {:body (get-db-stuff)})
           (GET "/json" [] {:body {:a 1 :b [2 3 4]}})
           (GET "/page/:id" [id] (str "Page:" id)))

(defn main [& args]
  (selmer/set-resource-path! (clojure.java.io/resource "templates"))
  (run-jetty (routes
               (-> #'app-routes wrap-reload wrap-json-response)
               (route/not-found "Not found"))
             {:port 3000}))

