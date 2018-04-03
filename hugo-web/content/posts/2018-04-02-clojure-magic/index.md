---
title: "Clojure Magic"
date: 2018-04-02T13:37:18-04:00
draft: true
---

# Clojure Magic

We start with a sequence of integers:

>$1, 2, 3 \dots $.

`$$
\sum_0^\infty \frac{1}{r^i} = \frac{1}{1-r}
$$`

{{< highlight clojure >}}
(defn seq-sum [xs r]
  (apply 
    +
    (for [i xs]
      (Math/pow r i))))
{{< /highlight >}}

{{< highlight clojure >}}
(let [sum (seq-sum xs 0.5)]
  (print sum))
{{< /highlight >}}
