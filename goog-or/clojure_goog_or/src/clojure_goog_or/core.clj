(ns clojure-goog-or.core
  (:gen-class)
  (:import (com.google.ortools.linearsolver MPConstraint
                                            MPObjective
                                            MPSolver
                                            MPSolver$OptimizationProblemType
                                            MPVariable)
           (com.google.ortools.constraintsolver DecisionBuilder
                                                IntVar
                                                Solver)))

(defn load-jni []
  (println "Loading JNI")
  (System/loadLibrary "jniortools")
  (println "Loaded."))

(defn run-example []
  (let [solver (new MPSolver 
                    "my_program" 
                    (MPSolver$OptimizationProblemType/valueOf "GLOP_LINEAR_PROGRAMMING"))
        x (. solver makeNumVar 0.0 0.1 "x")
        y (. solver makeNumVar 0.0 0.1 "y")
        objective (. solver objective)]
    (doto objective
      (.setCoefficient x -1)
      (.setCoefficient y 1)
      (.setMaximization))
    (. solver solve)
    (println "Done" 
             (. x solutionValue)
             (. y solutionValue))))

(defn -main [& args]
  (load-jni)
  (run-example)
  (println "Everything is okay"))
