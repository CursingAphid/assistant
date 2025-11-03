import React, { useState } from 'react';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { View, Text, TextInput, StyleSheet, KeyboardAvoidingView, Platform, Alert, ActivityIndicator } from 'react-native';
import { TouchableOpacity } from 'react-native-gesture-handler';
import { RootStackParamList } from '../../App';
import { useApiContext } from '../context/ApiContext';
import { useSupermarketApi } from '../hooks/useSupermarketApi';

export type LocationSetupProps = NativeStackScreenProps<RootStackParamList, 'LocationSetup'>;

const MIN_RADIUS = 0.1;
const MAX_RADIUS = 50;

export default function LocationSetupScreen({ navigation }: LocationSetupProps) {
  const { setLocation, setRadiusKm, setSupermarkets } = useApiContext();
  const api = useSupermarketApi();

  const [address, setAddress] = useState('');
  const [radius, setRadius] = useState('5');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    const radiusValue = parseFloat(radius);
    if (!address.trim()) {
      Alert.alert('Address required', 'Please enter your address to continue.');
      return;
    }
    if (Number.isNaN(radiusValue) || radiusValue < MIN_RADIUS || radiusValue > MAX_RADIUS) {
      Alert.alert('Invalid distance', `Please choose a travel distance between ${MIN_RADIUS} km and ${MAX_RADIUS} km.`);
      return;
    }

    try {
      setLoading(true);
      const location = await api.geocode({ address });
      setLocation(location);
      setRadiusKm(radiusValue);

      const supermarkets = await api.findSupermarkets(location.latitude, location.longitude, radiusValue);
      setSupermarkets(supermarkets.supermarkets);

      navigation.replace('ProductSearch');
    } catch (error) {
      console.error('Error setting location', error);
      Alert.alert('Setup failed', 'We could not set up your location. Please try again with a more specific address.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.heading}>Where should we search?</Text>
        <Text style={styles.description}>
          Enter your address and how far you're willing to travel. We'll only show supermarkets within that area.
        </Text>

        <Text style={styles.label}>Address</Text>
        <TextInput
          style={styles.input}
          placeholder="Damrak 1, Amsterdam, Netherlands"
          value={address}
          onChangeText={setAddress}
          autoCapitalize="none"
          autoCorrect={false}
          editable={!loading}
        />

        <Text style={styles.label}>Travel distance (km)</Text>
        <TextInput
          style={styles.input}
          placeholder="5"
          keyboardType="decimal-pad"
          value={radius}
          onChangeText={setRadius}
          editable={!loading}
        />

        <TouchableOpacity style={styles.button} onPress={handleSubmit} disabled={loading}>
          {loading ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.buttonText}>Save and Continue</Text>}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  heading: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 12,
  },
  description: {
    fontSize: 16,
    color: '#606060',
    marginBottom: 24,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#d0d0d0',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    fontSize: 16,
  },
  button: {
    backgroundColor: '#2563eb',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});
