package utils

import "log"

func Info(msg string, args ...interface{}) {
	log.Printf("INFO: "+msg, args...)
}

func Error(msg string, args ...interface{}) {
	log.Printf("ERROR: "+msg, args...)
}
