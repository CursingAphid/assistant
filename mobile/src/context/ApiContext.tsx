import React, { createContext, useContext, useMemo, useState, ReactNode } from 'react';
import Constants from 'expo-constants';
import { LocationResponse, SupermarketLocation } from '../types';

function resolveApiUrl(): string {
  const extra = Constants.expoConfig?.extra ?? Constants.manifestExtra ?? {};
  return (extra.apiUrl as string) ?? process.env.API_URL ?? 'http://localhost:8000';
}

export type ApiContextValue = {
  apiUrl: string;
  location: LocationResponse | null;
  radiusKm: number;
  supermarkets: SupermarketLocation[];
  setLocation: (location: LocationResponse | null) => void;
  setRadiusKm: (radius: number) => void;
  setSupermarkets: (supermarkets: SupermarketLocation[]) => void;
  reset: () => void;
};

const defaultValue: ApiContextValue = {
  apiUrl: resolveApiUrl(),
  location: null,
  radiusKm: 5,
  supermarkets: [],
  setLocation: () => undefined,
  setRadiusKm: () => undefined,
  setSupermarkets: () => undefined,
  reset: () => undefined,
};

const ApiContext = createContext<ApiContextValue>(defaultValue);

export function ApiProvider({ children }: { children: ReactNode }) {
  const [location, setLocation] = useState<LocationResponse | null>(null);
  const [radiusKm, setRadiusKm] = useState<number>(5);
  const [supermarkets, setSupermarkets] = useState<SupermarketLocation[]>([]);

  const apiUrl = resolveApiUrl();

  const value = useMemo<ApiContextValue>(
    () => ({
      apiUrl,
      location,
      radiusKm,
      supermarkets,
      setLocation,
      setRadiusKm,
      setSupermarkets,
      reset: () => {
        setLocation(null);
        setRadiusKm(5);
        setSupermarkets([]);
      },
    }),
    [apiUrl, location, radiusKm, supermarkets]
  );

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

export function useApiContext() {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error('useApiContext must be used within an ApiProvider');
  }
  return context;
}
