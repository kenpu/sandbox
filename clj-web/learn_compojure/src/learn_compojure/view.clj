(ns learn-compojure.view
  (:require [hiccup.core :refer [html]]))

(defn page [v & args]
  (html [:html
         [:head
          [:title "Learning Clojure"]
          [:link {:rel "stylesheet" :href "static/style.css"}]]
         [:body (apply v args)]]))

(defn index [name access-token user-info]
  [:div
   [:p "This is " name]
   [:p "Access Token: " access-token]
   [:pre "User info\n" (str user-info)]
   [:ul
    [:li [:a {:href "session"} "session"]]
    [:li [:a {:href "oauth2/google"} "Login/Google"]]
    [:li [:a {:href "oauth2/github"} "Login/Github"]]
    ]])

(defn session [sess]
  [:div
   [:p "This is session."]
   [:pre "session=" (str sess)]
   [:p "You can clear it: " [:a {:href "/clear"} "here"]]])

(defn clear []
  [:div
   [:p "Session is cleared."]
   [:a {:href "/session"} "Go back"]])
