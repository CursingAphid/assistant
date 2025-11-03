import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SupermarketLocation } from '../types';

type Props = {
  supermarkets: SupermarketLocation[];
};

export default function SupermarketList({ supermarkets }: Props) {
  if (!supermarkets.length) {
    return <Text style={styles.empty}>No supermarkets found within your travel distance.</Text>;
  }

  return (
    <View style={styles.container}>
      {supermarkets.map((store) => (
        <View key={`${store.brand}-${store.latitude}-${store.longitude}`} style={styles.badge}>
          <Text style={styles.badgeTitle}>{store.brand}</Text>
          <Text style={styles.badgeSubtitle}>{store.name}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  badge: {
    backgroundColor: '#e0f2fe',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
    marginBottom: 8,
  },
  badgeTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1d4ed8',
  },
  badgeSubtitle: {
    fontSize: 12,
    color: '#0f172a',
  },
  empty: {
    color: '#64748b',
    fontStyle: 'italic',
  },
});
