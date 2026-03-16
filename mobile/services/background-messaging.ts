import messaging from '@react-native-firebase/messaging';

// Must be registered outside of React lifecycle
messaging().setBackgroundMessageHandler(async (remoteMessage) => {
  // Data-only messages can be processed here
  // Summary data is NOT pre-fetched in background to avoid PHI in memory
  // The app will fetch on next foreground
  console.log('Background message received:', remoteMessage.messageId);
});
