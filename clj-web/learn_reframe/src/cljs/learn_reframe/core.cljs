(ns learn-reframe.core
  (:require
   [reagent.core :as r]
   [reagent.dom :as rdom]
   [re-frame.core :as rf]
   [clojure.string :as s]
   ))

(defn dispatch-timer-event
  []
  (let [now (js/Date.)]
    (rf/dispatch [:timer now])))

(defonce do-timer (js/setInterval dispatch-timer-event 1000))

(rf/reg-event-db
  :initialize
  (fn [db _]
    (assoc db 
           :time (js/Date.)
           :color "#f88")))

(rf/reg-event-db
  :timer
  (fn [db [_ new-time]]
    (assoc db :time new-time)))

(rf/reg-event-db
  :change-color
  (fn [db [_ color]]
    (assoc db :color color)))

(rf/reg-sub
  :time
  (fn [db _]
    (:time db)))

(rf/reg-sub
  :color
  (fn [db _]
    (:color db)))

(defn clock
  []
  (let [t @(rf/subscribe [:time])
        c @(rf/subscribe [:color])]
    [:div 
     {:style {:color c}}
     [:b "color=" c]
     [:i
     (-> t 
         (.toTimeString) 
         (s/split #" ") 
         (first))]]))

(defn color-pick
  []
  [:div
   [:input {:type "text"
            :value @(rf/subscribe [:color])
            :on-change (fn [e]
                         (rf/dispatch [:change-color (-> e .-target .-value)]))}]])

(defn app
  []
  [:div [clock] [color-pick]])

(defn dev-setup []
  (println "dev mode"))

(defn ^:dev/after-load mount-root []
  (rf/clear-subscription-cache!)
  (let [root-el (.getElementById js/document "app")]
    (rdom/unmount-component-at-node root-el)
    (rdom/render [app] root-el)))

(defn init []
  (rf/dispatch-sync [:initialize])
  (dev-setup)
  (mount-root))
