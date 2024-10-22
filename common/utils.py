from django.core.cache import cache
from django.conf import settings
from decimal import Decimal
import requests
from django.utils import timezone
from datetime import timedelta
import pytz
import logging

logger = logging.getLogger('kt')

BUDAPEST_TZ = pytz.timezone('Europe/Budapest')

# Currency choices
CURRENCY_CHOICES = [
    ('EUR', 'Euros'),
    ('GBP', 'Pound Sterling'),
    ('HUF', 'Hungarian Forint'),
    ('USD', 'US Dollar')
]

# Agent fee percentage choices
AGENT_FEE_CHOICES = [
    ('5', '5% Turnover'),
    ('10', '10% Turnover'),
    ('50', '50% Profit')
]

# Payment type choices
PAYMENT_TYPE_CHOICES = [
    ('Cash', 'Cash'),
    ('Card', 'Card'),
    ('Transfer', 'Transfer'),
    ('Quick Pay', 'Quick Pay')
]

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


def assign_job_color(job, now):
    """
    Assigns color to a job based on its status and conditions.
    - White: Until the driver name is not empty.
    - Orange: If the driver is assigned.
    - Green: If the job is marked as completed and the driver is assigned.
    - Red: If the job is one day old, the driver is assigned, and the customer has not paid.
    """
    # Check if the driver is assigned
    if not job.driver:
        return 'white'  # No driver assigned yet
    
    # Check if the job is one day old and the customer has not paid
    one_day_ago = now - timedelta(days=1)
    if job.job_date <= one_day_ago.date() and job.is_paid == False:
        return 'red'  # Job is old, driver assigned, and customer hasn't paid
    
    # Check if the job is completed and the driver is assigned
    if job.is_completed:
        return 'green'  # Job is completed, driver is assigned
    
    # Default case when driver is assigned but job is not completed
    return 'orange'