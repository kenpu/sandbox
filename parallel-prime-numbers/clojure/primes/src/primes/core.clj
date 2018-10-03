(ns primes.core
  (:require [clojure.core.async :refer [chan go <! >! <!! close! alt!]]))

(defn now []
  (System/currentTimeMillis))

(defn prime? [n]
  (loop [i 2]
    (cond (= i n) true 
          (zero? (rem n i)) false
          :else (recur (inc i)))))

(defn worker [id workload output]
  (println "starting worker" id)
  (go (loop []
        (let [i (<! workload)]
          (when (prime? i)
            (>! output i)))
        (recur))))

(defn make-primes [output parallelism]
  (let [done (chan)
        workload (chan)]
    ;; start the workload
    (go (loop [i 2]
          (>! workload i)
          (recur (inc i))))

    ;; start the workers
    (dotimes [id parallelism]
      (worker id workload output))

    ; return done
    done))


(defn start
  [n]
  (let [primes (chan) 
        done (make-primes primes n)
        start (now)]
    (go (loop [count 0]
          (let [pn (<! primes)]
            (when (zero? (rem count 1000))
              (let [duration (/ (- (now) start) 1000.0) 
                    rate (/ (float count) duration)] 
                (printf "Found %d in %.2f seconds (%.2f pn/sec)\n" 
                        count duration rate))))
          (recur (inc count))))
    (<!! done)))
