(ns learn.core
  (:require [nio.core :as nio]
            [clojure.java.io :as io])
  (:import [java.util.zip ZipInputStream]))

(defn download [url]
  (let [out-chan (nio/channel (io/file "./a"))
        in-chan (-> url (io/input-stream) (nio/readable-channel))]
    (io/copy in-chan out-chan)))

(defn unzip [f]
  (let [zip-stream (-> f 
                      (io/input-stream)
                      (ZipInputStream.))]
    (loop [entry (.getNextEntry zip-stream)]
      (when-not (nil? entry)
        ; save the content
        (when-not (.isDirectory entry)
          (let [name (.getName entry)]
            (println ">" name)
            (io/copy (nio/readable-channel zip-stream) (nio/channel (io/file name)))))
        (recur (.getNextEntry zip-stream))))))




