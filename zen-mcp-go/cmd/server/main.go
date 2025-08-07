package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"zen-mcp-go/internal/api"
	"zen-mcp-go/internal/config"
	"zen-mcp-go/internal/middleware"
)

func main() {
	// Load configuration
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Create a new router with middleware
	mux := api.NewRouter()

	// Add recovery and error handling middleware
	handler := middleware.Recovery(
		middleware.ErrorHandler(
			mux,
		),
	)

	// Configure HTTP server with timeouts
	srv := &http.Server{
		Addr:         cfg.Server.Address,
		Handler:      handler,
		ReadTimeout:  time.Duration(cfg.Server.ReadTimeout) * time.Second,
		WriteTimeout: time.Duration(cfg.Server.WriteTimeout) * time.Second,
		IdleTimeout:  time.Duration(cfg.Server.IdleTimeout) * time.Second,
	}

	// Channel to listen for errors coming from the listener
	serverErrors := make(chan error, 1)

	// Start the server in a goroutine
	go func() {
		log.Printf("Starting Zen MCP Go server on %s...", cfg.Server.Address)
		serverErrors <- srv.ListenAndServe()
	}()

	// Channel to listen for interrupt or terminate signals
	osSignals := make(chan os.Signal, 1)
	signal.Notify(osSignals, os.Interrupt, syscall.SIGTERM)

	// Block until we receive a signal or an error from the server
	select {
	case err := <-serverErrors:
		log.Printf("Server error: %v\n", err)

	case sig := <-osSignals:
		log.Printf("Received %v signal. Shutting down...\n", sig)

		// Create a context with a timeout for graceful shutdown
		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()

		// Attempt graceful shutdown
		if err := srv.Shutdown(ctx); err != nil {
			log.Printf("Graceful shutdown failed: %v\n", err)
			err = srv.Close() // Force close if graceful shutdown fails
			if err != nil {
				log.Fatalf("Could not stop server: %v\n", err)
			}
		}

		log.Println("Server stopped gracefully")
	}
}
