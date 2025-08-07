package config

import (
	"github.com/spf13/viper"
	"strings"
)

// Config holds the application configuration
type Config struct {
	Server struct {
		Address      string `mapstructure:"address"`
		ReadTimeout  int    `mapstructure:"read_timeout"`
		WriteTimeout int    `mapstructure:"write_timeout"`
		IdleTimeout  int    `mapstructure:"idle_timeout"`
	}
}

// LoadConfig loads the configuration from a file
func LoadConfig() (*Config, error) {
	viper.SetConfigName("config")
	// Add search paths for running from root and from cmd/server (for tests)
	viper.AddConfigPath("config")
	viper.AddConfigPath(".")
	viper.AddConfigPath("../../config")
	viper.AutomaticEnv()
	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	if err := viper.ReadInConfig(); err != nil {
		return nil, err
	}

	var config Config
	if err := viper.Unmarshal(&config); err != nil {
		return nil, err
	}

	return &config, nil
}
