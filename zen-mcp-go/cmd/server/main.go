package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"zen-mcp-go/internal/api"
	"zen-mcp-go/internal/config"
	"zen-mcp-go/internal/middleware"
)

func main() {
    // Setup structured logging
    log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	// Load configuration
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to load configuration")
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
		log.Info().Msgf("Starting Zen MCP Go server on %s...", cfg.Server.Address)
		serverErrors <- srv.ListenAndServe()
	}()

	// Channel to listen for interrupt or terminate signals
	osSignals := make(chan os.Signal, 1)
	signal.Notify(osSignals, os.Interrupt, syscall.SIGTERM)

	// Block until we receive a signal or an error from the server
	select {
	case err := <-serverErrors:
        if err != http.ErrServerClosed {
		    log.Error().Err(err).Msg("Server error")
        }

	case sig := <-osSignals:
		log.Info().Msgf("Received %v signal. Shutting down...", sig)

		// Create a context with a timeout for graceful shutdown
		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()

		// Attempt graceful shutdown
		if err := srv.Shutdown(ctx); err != nil {
			log.Error().Err(err).Msg("Graceful shutdown failed")
			err = srv.Close() // Force close if graceful shutdown fails
			if err != nil {
				log.Fatal().Err(err).Msg("Could not stop server")
			}
		}

		log.Info().Msg("Server stopped gracefully")
	}
}
