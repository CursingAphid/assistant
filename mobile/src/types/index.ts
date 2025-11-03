export type GeocodeRequest = {
  address: string;
};

export type LocationResponse = {
  latitude: number;
  longitude: number;
  address: string;
};

export type SupermarketLocation = {
  name: string;
  brand: string;
  latitude: number;
  longitude: number;
};

export type FindSupermarketsRequest = {
  latitude: number;
  longitude: number;
  radius_km: number;
};

export type FindSupermarketsResponse = {
  supermarkets: SupermarketLocation[];
  count: number;
};

export type Product = {
  title: string;
  price: string;
  size: string;
  image: string;
  supermarket: string;
  on_discount: boolean;
  original_price?: string | null;
  discount_action?: string | null;
  discount_date?: string | null;
  discount_timestamp?: number | null;
};

export type SearchProductsParams = {
  keyword: string;
  latitude: number;
  longitude: number;
  radius_km: number;
};

export type SearchProductsResponse = {
  keyword: string;
  products: Product[];
  count: number;
};
