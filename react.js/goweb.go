package main

import (
	"log"
	"net/http"
)

var Scripts = []string{
	"react-0.12.2/build/react.js",
	"react-0.12.2/build/JSXTransformer.js",
}

func main() {
	http.Handle("/", http.StripPrefix("/", http.FileServer(http.Dir("."))))
	log.Fatal(http.ListenAndServe(":8080", nil))
}
