"""
Configuration file for content validation testing
This content should appear only ONCE in any tool response
"""

# Configuration constants
MAX_CONTENT_TOKENS = 800_000  # This line should appear exactly once
TEMPERATURE_ANALYTICAL = 0.2  # This should also appear exactly once
UNIQUE_VALIDATION_MARKER = "CONTENT_VALIDATION_TEST_12345"

# Database settings  
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "name": "validation_test_db"
}
