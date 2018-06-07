(ns server.core
  (:require [compojure.core :refer :all]
            [compojure.route :as route]
            [ring.util.response :refer [response content-type redirect]]
            [ring.adapter.jetty :refer [run-jetty]]
            [hiccup.core :refer [html]]
            [ring.middleware.reload :refer [wrap-reload]]))

(defn index-page
  []
  [:html
   [:body
    [:h1 "Site v1"]
    [:script {:src "/static/js/app.js"}]]])

(def app
  (routes
    (GET "/" _ (-> (index-page)
                   (html)
                   (response)
                   (content-type "text/html")))
    (route/resources "/static" {:root "public"})
    (route/not-found "Not found")))

(defn -main [& args]
  (run-jetty (-> #'app (wrap-reload))
             {:port 9876}))
