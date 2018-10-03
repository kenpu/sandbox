package main

import (
	"flag"
	"fmt"
	"os"
	"os/signal"
	"sync"
	"time"
)

const N = 100000

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

func (this *Counter) Inc() int {
	this.mux.Lock()
	this.Value += 1
	this.mux.Unlock()
	return this.Value
}

func makeprimes(cancel chan struct{}, primes chan int, parallelism int) (done chan struct{}) {
	var (
		count   *Counter
		numbers chan int
	)
	count = &Counter{}
	done = make(chan struct{})

	numbers = make(chan int)
	go func() {
		for i := 2; true; i++ {
			select {
			case <-cancel:
				close(done)
				return
			case <-done:
				return
			case numbers <- i:
			}
		}
	}()

	for id := 0; id < parallelism; id++ {
		go worker(id, cancel, done, numbers, primes, count)
	}
	return done
}
func worker(id int, cancel chan struct{}, done chan struct{}, numbers chan int, primes chan int, count *Counter) {
	for i := range numbers {
		if isprime(i) {
			select {
			case <-cancel:
				return
			case <-done:
				return
			case primes <- i:
				if count.Inc() >= N {
					close(done)
				}
			}
		}
	}
}

func main() {
	var (
		parallelism int
		primes      = make(chan int)
		ticks       = time.Tick(5 * time.Second)
		done        chan struct{}
		cancel      = make(chan struct{})
		pn          int
	)
	flag.IntVar(&parallelism, "n", 1, "parallelism")
	flag.Parse()

	// interrupt handler
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, os.Interrupt)
	go func() {
		for _ = range sigs {
			fmt.Println("Interrupting all workers")
			close(cancel)
		}
	}()

	fmt.Printf("=== parallelism: %d ===\n", parallelism)
	done = makeprimes(cancel, primes, parallelism)

	go func() {
		<-done
		fmt.Println("done")
		close(primes)
	}()

	count := 0
	start := time.Now()
	for pn = range primes {
		count += 1
		select {
		case <-ticks:
			dur := time.Now().Sub(start)
			rate := float64(count) / dur.Seconds()
			fmt.Printf("Found %d primes in %.2f seconds (%.2f primes/second), last found %d\n", count, dur.Seconds(), rate, pn)
		default:
		}
	}
	dur := time.Now().Sub(start)
	rate := float64(count) / dur.Seconds()
	fmt.Printf("Found %d primes in %.2f seconds (%.2f primes/second), last found %d\n", count, dur.Seconds(), rate, pn)
}
