(ns learn-compojure.view
  (:require [hiccup.core :refer [html]]))

(defn page [v & args]
  (html [:html
         [:head
          [:title "Learning Clojure"]
          [:link {:rel "stylesheet" :href "static/style.css"}]]
         [:body (apply v args)]]))

(defn index [name]
  [:div
   [:p "This is " name]
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
