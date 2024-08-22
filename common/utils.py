from decimal import Decimal
from django.core.cache import cache
import requests
import logging

logger = logging.getLogger(__name__)

def fetch_and_cache_exchange_rate(currency):
    api_key = 'fafbeb3efd633397a2c59ecf'
    url = f'https://v6.exchangerate-api.com/v6/{api_key}/latest/{currency}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        rate = Decimal(data['conversion_rates']['EUR'])
        cache.set(f'exchange_rate_{currency}', rate, timeout=86400)  # Cache for 1 day
        return rate
    except requests.RequestException as e:
        logger.error(f'Error fetching exchange rate for {currency}: {e}')
        raise ValueError(f'Error fetching exchange rate for {currency}') from e
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f'Invalid response structure when fetching exchange rate for {currency}: {e}')
        raise ValueError(f'Invalid response structure when fetching exchange rate for {currency}') from e

def get_exchange_rate(currency):
    if currency == 'EUR':
        return Decimal('1.00')

    cache_key = f'exchange_rate_{currency}'
    rate = cache.get(cache_key)
    if rate is None:
        rate = fetch_and_cache_exchange_rate(currency)
    return rate