package main

import (
	"flag"
	"fmt"
	"sync"
	"time"
)

func isprime(n int) bool {
	for i := 2; i < n; i++ {
		if n%i == 0 {
			return false
		}
	}
	return true
}

type Counter struct {
	mux   sync.Mutex
	Value int
}

func (this *Counter) Inc() {
	this.mux.Lock()
	this.Value += 1
	this.mux.Unlock()
}

func makeprimes(primes chan int, parallelism int) {
	var (
		count   *Counter
		numbers chan int
	)
	count = &Counter{}

	numbers = make(chan int)
	go func() {
		for i := 2; true; i++ {
			numbers <- i
		}
	}()

	for id := 0; id < parallelism; id++ {
		go worker(id, numbers, primes, count)
	}
}
func worker(id int, numbers chan int, primes chan int, count *Counter) {
	for i := range numbers {
		if isprime(i) {
			primes <- i
			count.Inc()
		}
	}
}

func main() {
	var (
		parallelism int
		primes      = make(chan int)
	)
	flag.IntVar(&parallelism, "n", 1, "threads")
	flag.Parse()

	fmt.Printf("=== parallelism: %d ===\n", parallelism)
	makeprimes(primes, parallelism)
	count := 0
	start := time.Now()
	for pn := range primes {
		count += 1
		if count%1000 == 0 {
			dur := time.Now().Sub(start)
			rate := float64(count) / dur.Seconds()
			fmt.Printf("Found %d primes in %.2f seconds (%.2f primes/second), last found %d\n", count, dur.Seconds(), rate, pn)
		}
	}
}
