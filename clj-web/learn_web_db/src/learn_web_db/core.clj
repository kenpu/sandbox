(ns learn-web-db.core
  (:require [ring.adapter.jetty :as jetty]
            [ring.util.response :as r]
            [ring.middleware.reload :refer [wrap-reload]]
            [ring.middleware.defaults :refer [wrap-defaults site-defaults]]
            [compojure.core :refer [GET routes] :as c]
            [compojure.route :as route]
            [hiccup.core :as h]
            [clojure.tools.logging :as log]
            [clojure.java.jdbc :as sql]))

(defn make-view [view-fn args]
  (let [body (apply view-fn args)]
    [:html
     [:head [:link {:rel :stylesheet
                    :href "/static/style.css"}]]
     [:body body]]))

;; Helper functions
(defn html-response [view-fn & args]
  (-> (make-view view-fn args)
      (h/html)
      (r/response)
      (r/content-type "text/html")))

;; # Database functions

(def db {:subprotocol "postgresql"
         :subname "//localhost:6432/mydb"
         :user "cljdb"
         :password "dbclj"})

(defn insert-name! [name]
  (sql/with-db-transaction 
    [tx db]
    (sql/execute! tx 
                  ["insert into names(name) values (?)" name])))

;; # View functions

; not found view
(defn <not-found>
  []
  [:h1 "Not found"])

; index view
(defn <index>
  []
  [:div 
   [:h1 "Welcome"]
   [:form {:action "/save"
           :method "get"}
    [:label "Name"]
    [:input {:type "text"
             :name "name"}]
    [:input {:type "submit"
             :value "Okay"}]]])

(defn save
  [name r]
  (let [url (get-in r [:headers "referer"])]
    (try (do (insert-name! name)
             [:div [:p "Name " name " is inserted"]])
         (catch Exception e [:div [:p "Name is not inserted: " (str e)]]))))

(def app (routes 
           (GET "/" r (html-response <index>))
           (GET "/save" [name :as r] (html-response save name r))
           (route/resources "/static" {:root "static"})
           (route/not-found (html-response <not-found>))))

(defn start-server
  []
  (log/info "hello world")
  (jetty/run-jetty (-> #'app
                       (wrap-defaults site-defaults)
                       (wrap-reload))
                   {:port 9876}))
