(ns learn-cljava.core)

; object construction, method invocation
(defn a []
  (let [obj (new myobj.Hello 100)]
    (do (println "obj.f1" (. obj -f1)) 
        (. obj print))))

; static methods
(defn b []
  (do (println "Hello.pi" (. myobj.Hello -pi))
      (println "Hello/Pi")
      (myobj.Hello/Pi)))

;;
;; # Learning about Java interop
;; 

(defn main [& args]
  (do (a)
      (b)))

