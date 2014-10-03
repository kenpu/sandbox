package main

import (
	"fmt"
	"go/parser"
	"go/token"
	"os"
)

func main() {
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, os.Args[1], nil, 0)
	fmt.Println(f, err)
}
