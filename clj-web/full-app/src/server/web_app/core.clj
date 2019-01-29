(ns web-app.core
  (:require [ring.adapter.jetty :as jetty]
            [ring.middleware.reload :refer [wrap-reload]]
            [ring.middleware.defaults :refer [site-default wrap-defaults]]
            [ring.util.response :refer [response content-type]]
            [ring.util.http-response :refer [ok]]
            [compojure.core :refer [GET POST DELETE]]))
