package main

import (
	"log"
	"net/http"

	"zen-mcp-go/internal/api"
)

func main() {
	mux := api.NewRouter()
	log.Println("Starting Zen MCP Go server on :8080...")
	if err := http.ListenAndServe(":8080", mux); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
