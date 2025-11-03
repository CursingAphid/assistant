import React from 'react';
import { View, Text, StyleSheet, Image } from 'react-native';
import { Product } from '../types';

type Props = {
  product: Product;
};

export default function ProductCard({ product }: Props) {
  return (
    <View style={styles.card}>
      {product.image && product.image !== 'N/A' ? (
        <Image source={{ uri: product.image }} style={styles.image} resizeMode="contain" />
      ) : (
        <View style={[styles.image, styles.placeholder]}>
          <Text style={styles.placeholderText}>No image</Text>
        </View>
      )}

      <View style={styles.content}>
        <Text style={styles.title}>{product.title}</Text>
        <Text style={styles.supermarket}>🏪 {product.supermarket}</Text>

        <View style={styles.priceRow}>
          <Text style={styles.price}>{product.price}</Text>
          {product.on_discount && product.original_price ? (
            <Text style={styles.originalPrice}>{product.original_price}</Text>
          ) : null}
        </View>

        {product.discount_action ? <Text style={styles.discount}>🎁 {product.discount_action}</Text> : null}
        {product.discount_date ? <Text style={styles.discountDate}>📅 {product.discount_date}</Text> : null}
        {product.size && product.size !== 'N/A' ? <Text style={styles.size}>📦 {product.size}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    elevation: 2,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 4,
  },
  image: {
    width: 96,
    height: 96,
    borderRadius: 8,
    backgroundColor: '#f1f5f9',
  },
  placeholder: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    color: '#94a3b8',
    fontSize: 12,
  },
  content: {
    flex: 1,
    marginLeft: 16,
    justifyContent: 'space-between',
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  supermarket: {
    color: '#475569',
    marginBottom: 8,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 4,
  },
  price: {
    fontSize: 18,
    fontWeight: '700',
    color: '#2563eb',
    marginRight: 12,
  },
  originalPrice: {
    fontSize: 14,
    color: '#ef4444',
    textDecorationLine: 'line-through',
  },
  discount: {
    color: '#b45309',
    fontWeight: '600',
  },
  discountDate: {
    color: '#64748b',
  },
  size: {
    color: '#475569',
    marginTop: 4,
  },
});
