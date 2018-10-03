package main

import (
	"fmt"
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

func makeprimes() {
	var (
		count      int
		i          int
		pn         int
		start      time.Time
		epochstart time.Time
	)
	count = 0
	i = 2
	start = time.Now()
	epochstart = time.Now()
	for count < 1000000 {
		if isprime(i) {
			count += 1
			pn = i
		}
		i += 1
		if i%1000 == 0 {
			dur := time.Now().Sub(epochstart)
			if dur > 5*time.Second {
				totaldur := time.Now().Sub(start)
				rate := float64(count) / totaldur.Seconds()
				fmt.Printf("Found %d primes in %.2f seconds (%.2f primes/second), last found %d\n",
					count, totaldur.Seconds(), rate, pn)
				epochstart = time.Now()
			}
		}
	}
}

func main() {
	makeprimes()
}
