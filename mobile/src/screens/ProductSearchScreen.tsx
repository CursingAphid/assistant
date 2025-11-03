import React, { useMemo, useState } from 'react';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  FlatList,
  ActivityIndicator,
  Alert,
  Platform,
  KeyboardAvoidingView,
} from 'react-native';
import { TouchableOpacity } from 'react-native-gesture-handler';
import { RootStackParamList } from '../../App';
import { useApiContext } from '../context/ApiContext';
import { useSupermarketApi } from '../hooks/useSupermarketApi';
import ProductCard from '../components/ProductCard';
import SupermarketList from '../components/SupermarketList';
import MapPreview from '../components/MapPreview';
import { Product } from '../types';

export type ProductSearchProps = NativeStackScreenProps<RootStackParamList, 'ProductSearch'>;

export default function ProductSearchScreen({ navigation }: ProductSearchProps) {
  const { location, radiusKm, supermarkets, reset } = useApiContext();
  const api = useSupermarketApi();

  const [keyword, setKeyword] = useState('Knorr');
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);

  const locationSummary = useMemo(() => {
    if (!location) return 'Location not set';
    return `${location.address} (within ${radiusKm} km)`;
  }, [location, radiusKm]);

  if (!location) {
    // Safeguard if context resets unexpectedly
    navigation.replace('LocationSetup');
    return null;
  }

  const handleSearch = async () => {
    if (!keyword.trim()) {
      Alert.alert('Keyword required', 'Enter a product name or brand to search.');
      return;
    }

    try {
      setLoading(true);
      const response = await api.searchProducts({
        keyword,
        latitude: location.latitude,
        longitude: location.longitude,
        radius_km: radiusKm,
      });
      setProducts(response.products);
    } catch (error) {
      console.error('Error searching products', error);
      Alert.alert('Search failed', 'We could not fetch products. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChangeLocation = () => {
    reset();
    navigation.replace('LocationSetup');
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.locationTitle}>Searching near</Text>
        <Text style={styles.locationValue}>{locationSummary}</Text>
        <TouchableOpacity style={styles.linkButton} onPress={handleChangeLocation}>
          <Text style={styles.linkButtonText}>Change location</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.searchBar}>
        <TextInput
          style={styles.searchInput}
          value={keyword}
          onChangeText={setKeyword}
          placeholder="Search for products (e.g. Knorr, coffee, milk)"
          autoCapitalize="none"
          autoCorrect={false}
          editable={!loading}
        />
        <TouchableOpacity style={styles.searchButton} onPress={handleSearch} disabled={loading}>
          {loading ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.searchButtonText}>Search</Text>}
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Supermarkets in range</Text>
        <SupermarketList supermarkets={supermarkets} />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Map overview</Text>
        <MapPreview location={location} radiusKm={radiusKm} supermarkets={supermarkets} />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Products</Text>
        {loading ? (
          <ActivityIndicator size="large" color="#2563eb" style={styles.loadingIndicator} />
        ) : (
          <FlatList
            data={products}
            keyExtractor={(item, index) => `${item.title}-${item.supermarket}-${index}`}
            renderItem={({ item }) => <ProductCard product={item} />}
            ListEmptyComponent={<Text style={styles.emptyState}>Start a search to see results.</Text>}
            contentContainerStyle={products.length === 0 && styles.emptyContainer}
          />
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 16,
  },
  locationTitle: {
    fontSize: 14,
    color: '#64748b',
  },
  locationValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0f172a',
    marginTop: 4,
  },
  linkButton: {
    marginTop: 8,
  },
  linkButtonText: {
    color: '#2563eb',
    fontSize: 14,
    fontWeight: '600',
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    marginTop: 12,
  },
  searchInput: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginRight: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    fontSize: 16,
  },
  searchButton: {
    backgroundColor: '#2563eb',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
  },
  searchButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  section: {
    marginTop: 16,
    paddingHorizontal: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  loadingIndicator: {
    marginTop: 32,
  },
  emptyContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyState: {
    color: '#64748b',
    fontSize: 16,
    textAlign: 'center',
  },
});
