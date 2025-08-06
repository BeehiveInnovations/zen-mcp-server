package api

import (
	"net/http"
)

func NewRouter() http.Handler {
	mux := http.NewServeMux()
	// TODO: Register endpoint handlers here
	mux.HandleFunc("/health", healthHandler)
	return mux
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status":"ok"}`))
}
