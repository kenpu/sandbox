(ns app.core
  (:require [reagent.core :as r]))

(enable-console-print!)

(defn on-message [e]
  (println (.-data e)))

(defn make-ws
  []
  (let [url (str "ws://" (.-hostname js/location) ":9876/ws")
        ws (js/WebSocket. url)]
    (aset ws "onmessage" on-message)))

(defn make-state
  []
  {:channel (make-ws)})

(defn App
  [state]
  [:div 
   [:p "Hello"]
   [:button "Send"]])

(defn main []
  (let [state (r/atom (make-state))]
    (r/render 
      [App state] 
      (.getElementById js/document "app"))))

(main)
