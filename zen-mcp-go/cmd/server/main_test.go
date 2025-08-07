package main

import (
	"net/http"
	"os"
	"testing"
	"time"
)

func TestMain(m *testing.M) {
	// Run the main function in a goroutine
	go main()

	// Wait for the server to start
	time.Sleep(1 * time.Second)

	// Run the tests
	code := m.Run()

	// Exit with the test code
	os.Exit(code)
}

func TestHealthCheck(t *testing.T) {
	resp, err := http.Get("http://localhost:8080/health")
	if err != nil {
		t.Fatalf("Failed to make health check request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status code %d, but got %d", http.StatusOK, resp.StatusCode)
	}
}
