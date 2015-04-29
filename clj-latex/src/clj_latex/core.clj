(ns clj-latex.core
  (:import (java.awt Font Graphics2D Insets Color))
  (:import (java.awt.image BufferedImage))
  (:import (java.io File FileInputStream))
  (:import (javax.imageio ImageIO))
  (:import (javax.swing Icon JLabel))
  (:import (org.scilab.forge.jlatexmath 
             TeXConstants 
             TeXFormula 
             TeXFormula$TeXIconBuilder
             TeXIcon)))

(def latex "\\int_0^\\infty f(x)dx")

(println latex)

(let [formula (TeXFormula. latex)
      builder (TeXFormula$TeXIconBuilder. formula)
      icon (.build 
             (.setSize (.setStyle builder TeXConstants/STYLE_DISPLAY) 20))]
  (.setInsets icon (Insets. 5 5 5 5))
  (let [image (BufferedImage. (.getIconWidth icon)
                              (.getIconHeight icon)
                              BufferedImage/TYPE_INT_ARGB)
        ^Graphics2D g2 (.createGraphics image)]
    (.setColor g2 Color/white)
    (.fillRect g2 0 0 (.getIconWidth icon) (.getIconHeight icon))
    (let [jl (JLabel.)]
      (.setForeground jl (Color. 0 0 0))
      (.paintIcon icon jl g2 0 0)
      (let [file (File. "ex.png")]
        (ImageIO/write image "png" (.getAbsoluteFile file))))))





