(ns learn-api.core
  (:require [compojure.api.sweet :refer :all]
            [ring.util.http-response :refer :all]
            [schema.core :as s]))

(s/defschema Pizza {:name s/Str
                    (s/optional-key :description) s/Str
                    :size (s/enum :L :M :S)
                    :origin {:country (s/enum :FI :PO)
                             :city s/Str}})

(def app
  (api {:swagger {:ui "/"
                  :spec "/swagger.json"
                  :data {:info {:title "Dice API"
                                :description "some api"}
                         :tags [{:name "api" :description "api"}]}}}
        (context "/api" []
                 :tags ["api"]
                 (GET "/plus" []
                      :return {:result Long}
                      :query-params [x :- Long
                                     y :- Long]
                      :summary "add two numbers"
                      (ok {:result (+ x y)}))
                 (POST "/echo" []
                       :return Pizza
                       :body [pizza Pizza]
                       :summary "echo a pizza"
                       (ok pizza)))))
