// Command go-project is a minimal example app used to prove the Go
// reusable workflows in ci-pipeline-kit actually work end to end.
package main

import "fmt"

func greet(name string) string {
	return fmt.Sprintf("Hello, %s!", name)
}

func main() {
	fmt.Println(greet("world"))
}
