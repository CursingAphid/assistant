import axios from 'axios';
import {
  GeocodeRequest,
  LocationResponse,
  FindSupermarketsResponse,
  SearchProductsParams,
  SearchProductsResponse,
} from '../types';

export class SupermarketApiClient {
  constructor(private readonly baseUrl: string) {}

  async geocode(request: GeocodeRequest): Promise<LocationResponse> {
    const { data } = await axios.post<LocationResponse>(`${this.baseUrl}/geocode`, request);
    return data;
  }

  async findSupermarkets(latitude: number, longitude: number, radiusKm: number): Promise<FindSupermarketsResponse> {
    const { data } = await axios.post<FindSupermarketsResponse>(`${this.baseUrl}/supermarkets`, {
      latitude,
      longitude,
      radius_km: radiusKm,
    });
    return data;
  }

  async searchProducts(params: SearchProductsParams): Promise<SearchProductsResponse> {
    const { data } = await axios.get<SearchProductsResponse>(`${this.baseUrl}/search`, {
      params: {
        keyword: params.keyword,
        latitude: params.latitude,
        longitude: params.longitude,
        radius_km: params.radius_km,
      },
    });
    return data;
  }
}
