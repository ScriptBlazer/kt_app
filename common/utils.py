from django.core.cache import cache
from django.conf import settings
from decimal import Decimal
import requests
from django.utils import timezone
import pytz
import logging

logger = logging.getLogger('kt')

BUDAPEST_TZ = pytz.timezone('Europe/Budapest')

def fetch_and_cache_exchange_rate(currency):
    """Fetch the exchange rate from the API and cache it until midnight in Budapest."""
    api_key = settings.EXCHANGE_RATE_API_KEY
    url = f'https://v6.exchangerate-api.com/v6/{api_key}/latest/{currency}'

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if 'conversion_rates' in data and 'EUR' in data['conversion_rates']:
            rate = Decimal(data['conversion_rates']['EUR'])

            # Calculate time remaining until midnight in Budapest
            now_budapest = timezone.now().astimezone(BUDAPEST_TZ)
            midnight_budapest = now_budapest.replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
            seconds_until_midnight = (midnight_budapest - now_budapest).total_seconds()

            # Cache the rate until midnight in Budapest
            cache_key = f'exchange_rate_{currency}'
            logger.debug(f"Caching exchange rate for {currency}: {rate} until midnight ({seconds_until_midnight} seconds)")
            cache.set(cache_key, rate, timeout=int(seconds_until_midnight))

            return rate
        else:
            raise ValueError(f'Invalid response structure or missing EUR rate for {currency}')

    except requests.RequestException as e:
        logger.error(f'Error fetching exchange rate for {currency}: {e}')
        raise ValueError(f'Error fetching exchange rate for {currency}') from e

def get_exchange_rate(currency):
    """Retrieve the exchange rate for the given currency from the cache or API."""
    if currency == 'EUR':
        return Decimal('1.00')

    # Try retrieving the cached rate
    cache_key = f'exchange_rate_{currency}'
    rate = cache.get(cache_key)

    if rate is not None:
        logger.debug(f"Using cached exchange rate for {currency}: {rate}")
    else:
        logger.debug(f"No cached exchange rate found for {currency}. Fetching from API.")
        # Fetch and cache if not found
        rate = fetch_and_cache_exchange_rate(currency)

    return rate