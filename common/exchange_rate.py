from decimal import Decimal
import requests
from django.utils import timezone
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

def fetch_and_store_exchange_rates():
    ExchangeRate = apps.get_model('core', 'ExchangeRate')
    api_key = 'your_api_key_here'  # Replace with your actual API key
    url = f'https://v6.exchangerate-api.com/v6/{api_key}/latest/EUR'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        rates = data.get('conversion_rates', {})
        date = timezone.now().date()
        for currency, rate in rates.items():
            if currency != 'EUR':
                ExchangeRate.objects.update_or_create(
                    currency=currency,
                    date=date,
                    defaults={'rate_to_eur': Decimal(rate)}
                )
        logger.info('Successfully updated exchange rates')
    except requests.RequestException as e:
        logger.error(f'Error fetching exchange rates: {e}')
        raise ValueError('Error fetching exchange rates') from e

def get_exchange_rate(currency):
    ExchangeRate = apps.get_model('core', 'ExchangeRate')
    if currency == 'EUR':
        return Decimal('1.00')

    date = timezone.now().date()

    # Check if today's exchange rates are already stored
    if not ExchangeRate.objects.filter(date=date).exists():
        # If not, fetch and store the exchange rates
        fetch_and_store_exchange_rates()

    # Retrieve the rate for the requested currency
    rate_record = ExchangeRate.objects.filter(currency=currency, date=date).first()
    if rate_record:
        return rate_record.rate_to_eur
    else:
        raise ValueError(f'Exchange rate for {currency} not available for {date}')