import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import { ApiProvider } from './src/context/ApiContext';
import LocationSetupScreen from './src/screens/LocationSetupScreen';
import ProductSearchScreen from './src/screens/ProductSearchScreen';

export type RootStackParamList = {
  LocationSetup: undefined;
  ProductSearch: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <ApiProvider>
      <NavigationContainer>
        <StatusBar style="auto" />
        <Stack.Navigator initialRouteName="LocationSetup">
          <Stack.Screen
            name="LocationSetup"
            component={LocationSetupScreen}
            options={{ title: 'Set Your Location' }}
          />
          <Stack.Screen
            name="ProductSearch"
            component={ProductSearchScreen}
            options={{ title: 'Product Search' }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </ApiProvider>
  );
}
