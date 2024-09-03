from decimal import Decimal
from django.core.cache import cache
import requests
import logging

logger = logging.getLogger(__name__)

def fetch_and_cache_exchange_rate(currency):
    # Define the API key and the request URL for fetching exchange rates
    api_key = 'fafbeb3efd633397a2c59ecf'
    url = f'https://v6.exchangerate-api.com/v6/{api_key}/latest/{currency}'

    try:
        # Send a request to the exchange rate API
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()

        # Extract the exchange rate for EUR and cache it for future use
        rate = Decimal(data['conversion_rates']['EUR'])
        cache.set(f'exchange_rate_{currency}', rate, timeout=86400)  # Cache for 24 hours
        return rate

    except requests.RequestException as e:
        # Log and raise an error if the request fails
        logger.error(f'Error fetching exchange rate for {currency}: {e}')
        raise ValueError(f'Error fetching exchange rate for {currency}') from e

    except (KeyError, ValueError, TypeError) as e:
        # Log and raise an error for invalid response structure
        logger.error(f'Invalid response structure when fetching exchange rate for {currency}: {e}')
        raise ValueError(f'Invalid response structure when fetching exchange rate for {currency}') from e

def get_exchange_rate(currency):
    # Return the exchange rate for EUR as 1.00
    if currency == 'EUR':
        return Decimal('1.00')
    
    # Check the cache for the exchange rate
    cache_key = f'exchange_rate_{currency}'
    rate = cache.get(cache_key)

    # Fetch and cache the exchange rate if not found in cache
    if rate is None:
        rate = fetch_and_cache_exchange_rate(currency)

    return rate