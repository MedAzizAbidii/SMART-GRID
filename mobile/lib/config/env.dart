class EnvConfig {
  // Backend API URLs - Change these based on your environment

  // For local testing on WiFi (iPhone on same WiFi)
  static const String apiBaseUrl = 'http://192.168.100.226:8000';
  static const String wsBaseUrl = 'ws://192.168.100.226:8000';

  // For localhost testing (Android emulator)
  // static const String apiBaseUrl = 'http://10.0.2.2:8000';
  // static const String wsBaseUrl = 'ws://10.0.2.2:8000';

  // For production deployment
  // static const String apiBaseUrl = 'https://api.smartgrid.com';
  // static const String wsBaseUrl = 'wss://api.smartgrid.com';

  // Blockchain configuration
  static const String blockchainRpcUrl = 'https://rpc-mumbai.maticvigil.com';
  static const String contractAddress = '0x...'; // Replace with deployed contract address

  // Firebase configuration (optional, requires google-services.json)
  static const bool firebaseEnabled = false; // Set to true after Firebase setup

  // Debug logging
  static const bool enableDebugLogging = true;
}
