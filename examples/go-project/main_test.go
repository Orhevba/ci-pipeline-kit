package main

import "testing"

func TestGreet(t *testing.T) {
	if got, want := greet("world"), "Hello, world!"; got != want {
		t.Errorf("greet(%q) = %q, want %q", "world", got, want)
	}
}
