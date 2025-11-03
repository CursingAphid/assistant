import { useMemo } from 'react';
import { SupermarketApiClient } from '../api/client';
import { useApiContext } from '../context/ApiContext';

export function useSupermarketApi() {
  const { apiUrl } = useApiContext();

  const client = useMemo(() => new SupermarketApiClient(apiUrl), [apiUrl]);

  return client;
}
