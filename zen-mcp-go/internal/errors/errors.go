package errors

import (
	"encoding/json"
	"fmt"
	"net/http"
)

type ErrorCode string

const (
	// Client errors (4xx)
	ErrInvalidInput   ErrorCode = "invalid_input"
	ErrNotFound       ErrorCode = "not_found"
	ErrUnauthorized   ErrorCode = "unauthorized"
	ErrForbidden      ErrorCode = "forbidden"
	ErrRequestTimeout ErrorCode = "request_timeout"

	// Server errors (5xx)
	ErrInternal           ErrorCode = "internal_error"
	ErrNotImplemented     ErrorCode = "not_implemented"
	ErrServiceUnavailable ErrorCode = "service_unavailable"
)

type AppError struct {
	Code     ErrorCode   `json:"code"`
	Message  string      `json:"message"`
	Details  interface{} `json:"details,omitempty"`
	Internal error       `json:"-"` // Internal error (not exposed to clients)
}

func (e *AppError) Error() string {
	if e.Internal != nil {
		return fmt.Sprintf("%s: %v", e.Message, e.Internal)
	}
	return e.Message
}

func (e *AppError) StatusCode() int {
	switch e.Code {
	case ErrInvalidInput, ErrRequestTimeout:
		return http.StatusBadRequest
	case ErrUnauthorized:
		return http.StatusUnauthorized
	case ErrForbidden:
		return http.StatusForbidden
	case ErrNotFound:
		return http.StatusNotFound
	case ErrNotImplemented:
		return http.StatusNotImplemented
	case ErrServiceUnavailable:
		return http.StatusServiceUnavailable
	default:
		return http.StatusInternalServerError
	}
}

// Error constructors
func NewError(code ErrorCode, message string) *AppError {
	return &AppError{
		Code:    code,
		Message: message,
	}
}

func ErrorWithDetails(code ErrorCode, message string, details interface{}) *AppError {
	return &AppError{
		Code:    code,
		Message: message,
		Details: details,
	}
}

func WrapError(err error, code ErrorCode, message string) *AppError {
	return &AppError{
		Code:     code,
		Message:  message,
		Internal: err,
	}
}

// HTTP response helpers
func WriteErrorResponse(w http.ResponseWriter, err error) {
	var appErr *AppError
	if !As(err, &appErr) {
		// Not an AppError, wrap it
		appErr = &AppError{
			Code:     ErrInternal,
			Message:  "An internal error occurred",
			Internal: err,
		}
	}

	statusCode := appErr.StatusCode()
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)

	// Don't expose internal errors to clients
	errResponse := struct {
		Error struct {
			Code    string      `json:"code"`
			Message string      `json:"message"`
			Details interface{} `json:"details,omitempty"`
		} `json:"error"`
	}{
		Error: struct {
			Code    string      `json:"code"`
			Message string      `json:"message"`
			Details interface{} `json:"details,omitempty"`
		}{
			Code:    string(appErr.Code),
			Message: appErr.Message,
			Details: appErr.Details,
		},
	}

	_ = json.NewEncoder(w).Encode(errResponse)
}

// Helper to check if error is of specific type
func Is(err, target error) bool {
	t, ok := target.(interface{ Is(error) bool })
	return ok && t.Is(err)
}

// Helper to convert to AppError
func As(err error, target **AppError) bool {
	if err == nil {
		return false
	}
	if appErr, ok := err.(*AppError); ok {
		*target = appErr
		return true
	}
	// Check for wrapped errors
	if x, ok := err.(interface{ Unwrap() error }); ok {
		return As(x.Unwrap(), target)
	}
	return false
}
