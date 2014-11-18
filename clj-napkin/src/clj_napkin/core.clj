(ns clj-napkin.core
  (:import (javax.swing JFrame JLabel)
           (java.awt.image BufferedImage)
           (java.awt Dimension Color))
  (:gen-class))

(defn transform-one [[x y]]
  [0 (* 0.16 y)])

(defn transform-two [[x y]]
  [(- (* 0.2 x) (* 0.26 y))
   (+ (* 0.23 x) (* 0.22 y))])

(defn transform-three [[x y]]
  [(+ (* -0.15 x) (* 0.28 y))
   (+ (* 0.26 x) (* 0.24 y) 0.44)])

(defn transform
  [target]
  (let [p (rand-int 101)]
    (cond
      (<= p 10) (transform-one target)
      (<= p 20) (transform-two target)
      :else    (transform-three target))))

(defn paint-point
  [width height [x y] graphics]
  (let [scale (int (/ height 11))
        y     (- (- height 25) (* scale y))
        x     (+ (/ width 2) (* scale x))]
    (.drawLine graphics x y x y)))

(defn draw-fern [w h max-p graphics]
  (doseq [coord (take max-p (iterate transform [0 1]))]
    (paint-point w h coord graphics)))

(defn draw [w h points]
  (let [image (BufferedImage. w h BufferedImage/TYPE_INT_RGB)
        canvas (proxy [JLabel] []
                 (paint [g]
                   (.drawImage g image 0 0 this)))
        graphics (.createGraphics image)]
    (.setColor graphics Color/green)
    (draw-fern w h points graphics)
    (doto (JFrame. "Fractal")
      (.add canvas)
      (.setSize (Dimension. w h))
      (.setDefaultCloseOperation JFrame/EXIT_ON_CLOSE)
      (.show))))



(defn -main
  "I don't do a whole lot ... yet."
  [& args]
  (println "Hello, World!")
  (draw 400 400 10000))
