package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"reflect"
)

type Printer struct {
	indent int
}

func (p *Printer) Visit(node ast.Node) (w ast.Visitor) {
	if node == nil {
		p.indent -= 1
		return nil
	} else {
		p.indent += 1
		node_t := reflect.TypeOf(node)
		for i := 0; i < p.indent; i++ {
			fmt.Print("|  ")
		}
		fmt.Printf("[%s] %s", node_t, node)
		fmt.Println()
		return p
	}
}

func main() {
	fset := token.NewFileSet()
	if f, err := parser.ParseFile(fset, os.Args[1], nil,
		parser.ParseComments); err == nil {
		p := &Printer{}
		ast.Walk(p, f)
	} else {
		fmt.Println("Err:", err)
	}
}
