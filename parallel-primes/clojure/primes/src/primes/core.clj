(ns primes.core
  (:require [clojure.core.async 
             :refer [chan go timeout <! >! <!! close! alt!]]))

(defn now []
  (System/currentTimeMillis))

(defn prime? [n]
  (loop [i 2]
    (cond (= i n) true 
          (zero? (rem n i)) false
          :else (recur (inc i)))))

(defn worker [id lock cancel workload output]
  (println "starting worker" id)
  (go (loop []
        (let [v (alt! workload ([i] i)
                      cancel :cancelled)]
          (case v
            :cancelled (do (printf "worker [%d] cancelled\n" id)
                           (flush))
            (do (when (prime? v) (>! output v))
                (recur)))))
      (>! lock id)))

(defn make-primes [cancel output parallelism]
  (let [done (chan)
        lock (chan)
        workload (chan)]
    ;; start the workload
    (go (loop [i 2]
          (let [status (alt! [[workload i]] :sent 
                              cancel :cancelled)]
            (if (= :sent status) (recur (inc i))))))

    ;; start the cleanup
    (go (dotimes [i parallelism]
          (<! lock))
        (close! done))

    ;; start the workers
    (dotimes [id parallelism]
      (worker id lock cancel workload output))

    ; return done
    done))

(defn -main
  [& args]
  (let [n (Integer/parseInt (first args))
        primes (chan) 
        cancel (timeout 10000)
        done (make-primes cancel primes n)
        start (now)]
    (printf "====== %d =====\n" n)
    (flush)
    (go (loop [count 0]
          (let [pn (<! primes)]
            (when (zero? (rem count 1000))
              (let [duration (/ (- (now) start) 1000.0) 
                    rate (/ (float count) duration)] 
                (printf "Found %d in %.2f seconds (%.2f pn/sec)\n" 
                        count duration rate)
                (flush))))
          (recur (inc count))))
    (<!! done)))
