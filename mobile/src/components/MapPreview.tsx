import React from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';
import MapView, { Marker, Circle } from 'react-native-maps';
import { LocationResponse, SupermarketLocation } from '../types';

const brandColors: Record<string, string> = {
  'Albert Heijn': '#ef4444',
  Dirk: '#2563eb',
  Vomar: '#16a34a',
  Jumbo: '#facc15',
  Plus: '#f97316',
  Aldi: '#7c3aed',
  Hoogvliet: '#ec4899',
  Dekamarkt: '#22d3ee',
};

type Props = {
  location: LocationResponse;
  radiusKm: number;
  supermarkets: SupermarketLocation[];
};

export default function MapPreview({ location, radiusKm, supermarkets }: Props) {
  const region = {
    latitude: location.latitude,
    longitude: location.longitude,
    latitudeDelta: 0.05,
    longitudeDelta: 0.05,
  };

  return (
    <View style={styles.container}>
      <MapView style={styles.map} initialRegion={region}>
        <Marker coordinate={region} title="Your location" />
        <Circle
          center={region}
          radius={radiusKm * 1000}
          strokeColor="rgba(239,68,68,0.6)"
          fillColor="rgba(239,68,68,0.1)"
        />

        {supermarkets.map((store) => (
          <Marker
            key={`${store.brand}-${store.latitude}-${store.longitude}`}
            coordinate={{ latitude: store.latitude, longitude: store.longitude }}
            title={store.name}
            description={store.brand}
            pinColor={brandColors[store.brand] ?? '#22c55e'}
          />
        ))}
      </MapView>
      {Platform.OS === 'web' && (
        <Text style={styles.notice}>
          Map preview uses react-native-maps. Configure native keys for iOS/Android in app.json/app.config.
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    height: 220,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  map: {
    flex: 1,
  },
  notice: {
    padding: 8,
    fontSize: 12,
    color: '#64748b',
    textAlign: 'center',
  },
});
