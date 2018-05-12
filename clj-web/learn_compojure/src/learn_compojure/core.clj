(ns learn-compojure.core
  (:require [compojure.core :refer :all]
            [compojure.route :as route]
            [ring.util.response :as response]
            [ring.middleware.reload :refer [wrap-reload]]
            [ring.middleware.session :refer [wrap-session]]
            [ring.middleware.session.cookie :refer [cookie-store]]
            [ring.middleware.cookies :refer [wrap-cookies]]
            [ring.middleware.oauth2 :refer [wrap-oauth2]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.middleware.defaults :refer :all]
            [clojure.tools.logging :as log]
            [cheshire.core :as parse]
            [environ.core :refer [env]]
            [clj-http.client :as client]
            [learn-compojure.view :as view])
  (:use ring.adapter.jetty))


(def google-oauth2
  {:google {:client-id     "241280927117-t592783lg2tv5ja53depp2phjhlgcae7.apps.googleusercontent.com" 
            :client-secret "ySEXBzpPUm0eWT1OV2Tm-nTE" 
            :authorize-uri "https://accounts.google.com/o/oauth2/v2/auth" 
            :access-token-uri "https://www.googleapis.com/oauth2/v4/token" 
            :launch-uri "/oauth2/google" 
            :redirect-uri "/oauth2/google/callback" 
            :landing-uri "/" 
            :scopes ["email" "profile"]
            }})

(def github-oauth2
  {:github {:authorize-uri    "https://github.com/login/oauth/authorize" 
            :access-token-uri "https://github.com/login/oauth/access_token" 
            :client-id        "f6a3517227cea833ecd4" 
            :client-secret    "24148d6fc1b8ad984885b2ca76dc8bb2e7f4fabe" 
            :scopes           ["user:email"] 
            :launch-uri       "/oauth2/github" 
            :redirect-uri     "/oauth2/github/callback" 
            :landing-uri      "/"}})

(defn- google-userinfo [access-token]
  (let [token (:token access-token)]
    (-> "https://www.googleapis.com/oauth2/v2/userinfo"
        (client/get {:headers {"Authorization" (str "Bearer " token)}})
        (get :body))))

(defroutes app
          (GET "/" r 
               (let [access-token (-> r :oauth2/access-tokens :google)
                     user-info (if access-token
                                 (google-userinfo access-token)
                                 "N/A")]
                 (view/page view/index (env :profile) access-token user-info)))

          (GET "/clear" req
               (-> (view/page view/clear)
                   (response/response)
                   (assoc :session nil)))

          (GET "/set-session" _
               (-> (response/redirect "/session")
                   (assoc :session {::title "Hi there"})))

          (GET "/session" req 
               (let [session (:session req)]
                 (-> (view/page view/session session)
                     (response/response)
                     (response/content-type "text/html")
                     (assoc :session 
                            (update session 
                                    :counter 
                                    (fn [x] (if (nil? x) 0 (inc x))))))))

          (GET "/user" req
               (response/response "user here"))

          (route/resources "/static/" {:root "public"})
          (route/not-found "<u>not found</u>"))

(defn wrap-log [handler]
  (fn [r]
    (log/spyf :info "> %s" (:uri r))
    (handler r)))

(def site (wrap-oauth2 app (merge github-oauth2 google-oauth2)))

(defn -main [& args]
  (run-jetty (-> #'site
                 (wrap-defaults (-> site-defaults (assoc-in [:session :cookie-attrs :same-site] :lax)))
                 (wrap-reload))
             {:port 9876}))
