package middleware

import (
	"log"
	"net/http"
	"runtime/debug"

	"zen-mcp-go/internal/errors"
)

// Recovery is a middleware that recovers from panics, logs the panic, and returns a 500 response.
func Recovery(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if r := recover(); r != nil {
				// Log the panic
				log.Printf("Recovered from panic: %v\n%s", r, string(debug.Stack()))

				// Create a user-friendly error response
				err := errors.NewError(
					errors.ErrInternal,
					"An unexpected error occurred. Our team has been notified.",
				)

				// Write the error response
				errors.WriteErrorResponse(w, err)
			}
		}()

		next.ServeHTTP(w, r)
	})
}

// ErrorHandler is a middleware that wraps http.Handler and handles errors gracefully.
func ErrorHandler(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Create a response writer that captures the status code
		rw := &responseWriter{ResponseWriter: w}

		// Call the next handler
		next.ServeHTTP(rw, r)

		// Check if an error occurred (status code >= 400)
		if rw.status >= 400 {
			err := &errors.AppError{
				Code:    errors.ErrInternal,
				Message: http.StatusText(rw.status),
			}
			errors.WriteErrorResponse(w, err)
		}
	})
}

// responseWriter wraps http.ResponseWriter to capture the status code
type responseWriter struct {
	http.ResponseWriter
	status int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.status = code
	rw.ResponseWriter.WriteHeader(code)
}

func (rw *responseWriter) Write(b []byte) (int, error) {
	if rw.status == 0 {
		rw.status = http.StatusOK
	}
	return rw.ResponseWriter.Write(b)
}
