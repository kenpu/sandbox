(ns learn.core
  (:require [clojure.java.io :as io]
            [clojure.string :as s]
            [stasis.core :as stasis]
            [hiccup.page :refer [html5]]
            [markdown.core :as md]
            [clygments.core :as pygments]
            [net.cgrand.enlive-html :as enlive]))

(defn layout-page
  [page]
  (html5
   [:head
    [:meta {:charset "utf-8"}]
    [:title "Tech blog"]
    [:link {:rel "stylesheet"
            :href "/default.css"}]]
   [:body
    [:div [:h1 "Page"]]
    [:div.body page]]))

(defn highlight
  [code lang]
  (-> code
      (pygments/highlight lang :html)
      (java.io.StringReader.)
      (enlive/html-resource)
      (enlive/select [:pre])
      (first)
      (:content)))

(defn markdown
  [page]
  (as-> page $
        (md/md-to-html-string $)
        (enlive/sniptest $
                         [:pre :code] (fn [node]
                                        (let [code (->> node :content (apply str))
                                              lang (->> node :attrs :class keyword)]
                                          (assoc node :content (highlight code lang))))
                         [:pre :code] (fn [node]
                                        (assoc-in node [:attrs :class] "highlight")))))

(defn get-pages
  []
  (stasis/merge-page-sources
   {:public (stasis/slurp-directory "resources/public" #".*\.(html|css|js)$")
    :partials (into {}
                    (for [[path page] (stasis/slurp-directory "resources/partials" #".*\.html$")]
                      [path (layout-page page)]))
    :markdowns (into {}
                     (for [[path page] (stasis/slurp-directory "resources/markdowns" #".*\.md$")]
                       [(s/replace path #"\.md$" "/") (layout-page (markdown page))]))}))

(def app (stasis/serve-pages get-pages))

(def export-dir "dist")

(defn export
  []
  (stasis/empty-directory! export-dir)
  (stasis/export-pages (get-pages) export-dir))
