(ns learn-websocket.core
  (:require [ring.adapter.jetty :as jetty]
            [ring.middleware.reload :refer [wrap-reload]]
            [ring.util.response :as response]
            [compojure.core :as c]
            [compojure.route :as route]
            [hiccup.core :as h]
            [clojure.tools.logging :as log]))

(defn Index [r]
  (h/html
    [:html
     [:head
      [:link {:rel "stylesheet"
              :href "/static/style.css"}]]
     [:body
      [:div {:id "app"}]
      [:script {:src "/static/js/main.js"}]]]))

;; ================================================
;; Web server
;; ================================================
(def app
  (c/routes
    (c/GET "/" r (-> (Index r)
                     (response/response)
                     (response/content-type "text/html")))
    (route/resources "/static" {:root "public"})
    (route/not-found (response/response "Not found"))))

(defn -main
  []
  (jetty/run-jetty (wrap-reload #'app) {:port 7654}))

