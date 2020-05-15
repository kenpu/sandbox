(ns learn-reframe.events
  (:require
   [re-frame.core :as re-frame]
   [learn-reframe.db :as db]
   ))

(re-frame/reg-event-db
 ::initialize-db
 (fn [_ _]
   db/default-db))
