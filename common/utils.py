from django.core.cache import cache
from django.conf import settings
from decimal import Decimal
import requests
from common.exchange_rate_models import ExchangeRate
from django.utils import timezone
from datetime import timedelta
from people.models import Agent, Driver, Staff
from django.db.models.functions import Lower
import pytz
import datetime
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

VEHICLE_CHOICES = [
    ('Car', 'Car'),
    ('Minivan', 'Minivan'),
    ('Van', 'Van'),
    ('Bus', 'Bus')
]

def fetch_and_cache_exchange_rate(currency):
    """Fetch the exchange rate from the API and store it in the database."""
    api_key = settings.EXCHANGE_RATE_API_KEY
    url = f'https://v6.exchangerate-api.com/v6/{api_key}/latest/{currency}'

    try:
        logger.info(f"Making API call to fetch exchange rate for {currency}")
        response = requests.get(url)
        logger.info(f"API response status code: {response.status_code}")
        response.raise_for_status()
        data = response.json()

        if 'conversion_rates' in data and 'EUR' in data['conversion_rates']:
            rate = Decimal(data['conversion_rates']['EUR'])
            logger.info(f"Successfully fetched exchange rate for {currency}: {rate}")

            # Update or create the exchange rate in the database
            exchange_rate, created = ExchangeRate.objects.update_or_create(
                currency=currency,
                defaults={'rate': rate},
            )
            if created:
                logger.info(f"Created new exchange rate for {currency}: {rate}")
            else:
                logger.info(f"Updated exchange rate for {currency}: {rate}")

            # Cache the rate for 24 hours
            cache_key = f'exchange_rate_{currency}'
            cache.set(cache_key, rate, timeout=86400)  # 24 hours in seconds
            
            return rate
        else:
            logger.error(f'Invalid response structure or missing EUR rate for {currency}')
            raise ValueError(f'Invalid response structure or missing EUR rate for {currency}')

    except requests.RequestException as e:
        logger.error(f'Error fetching exchange rate for {currency}: {e}')
        raise ValueError(f'Error fetching exchange rate for {currency}') from e

def get_exchange_rate(currency):
    """Retrieve the exchange rate for the given currency from the cache, database, or API."""
    if currency == 'EUR':
        return Decimal('1.00')

    # Try retrieving the rate from the cache first
    cache_key = f'exchange_rate_{currency}'
    rate = cache.get(cache_key)

    if rate is not None:
        logger.debug(f"Using cached exchange rate for {currency}: {rate}")
        return rate

    # Try retrieving the rate from the database
    try:
        exchange_rate = ExchangeRate.objects.get(currency=currency)
        if exchange_rate.last_updated < timezone.now() - timedelta(hours=24):
            logger.info(f"Exchange rate for {currency} is older than 24 hours. Fetching new rate.")
            return fetch_and_cache_exchange_rate(currency)
        logger.debug(f"Using database exchange rate for {currency}: {exchange_rate.rate}")
        return exchange_rate.rate
    except ExchangeRate.DoesNotExist:
        logger.debug(f"No database exchange rate found for {currency}.")

    logger.debug(f"No cached or database exchange rate found for {currency}. Fetching from API.")
    # Fetch and cache if not found
    return fetch_and_cache_exchange_rate(currency)
    
    
def assign_job_color(job, now):
    """
    Assigns a color to a job or hotel booking based on its status and conditions.
    
    Color logic:
    - For Jobs:
      - White: Until a driver (or agent acting as driver) is assigned.
      - Orange: If the driver (or agent acting as driver) is assigned.
      - Green: If the job is completed or paid.
      - Red: If the job is more than one day old, assigned, and unpaid.
    - For Hotels:
      - White: Until the booking is confirmed.
      - Orange: If the booking is confirmed.
      - Green: If the booking is completed.
      - Red: If the booking is more than one day old and unpaid.
    """
    
    # Determine if we're dealing with a job, shuttle, or hotel based on attributes
    is_shuttle = hasattr(job, 'shuttle_date')
    is_job = hasattr(job, 'driver') and not is_shuttle
    is_confirmed = getattr(job, 'is_confirmed', False)
    # driver = getattr(job, 'driver', None) if is_job else None
    job_date = getattr(job, 'job_date', None) or getattr(job, 'shuttle_date', None) or getattr(job, 'check_in', None)
    is_paid = getattr(job, 'is_paid', False)
    is_completed = getattr(job, 'is_completed', False)

    driver_assigned = False
    if is_job:
        driver_assigned = bool(getattr(job, 'driver', None) or getattr(job, 'driver_agent', None))


    # Convert job_date to date if it is a datetime object
    if isinstance(job_date, datetime.datetime):
        job_date = job_date.date()

    # Log values for debugging
    # logger.debug(f"Job: {job}")
    # logger.debug(f"Is Job: {is_job}")
    # logger.debug(f"Confirmed: {is_confirmed}")
    # logger.debug(f"Driver: {driver}")
    # logger.debug(f"Job Date: {job_date}")
    # logger.debug(f"Is Paid: {is_paid}")
    # logger.debug(f"Is Completed: {is_completed}")

    # Job-specific logic: remains white until driver/agent is assigned
    if is_job:
        if not driver_assigned:
            logger.debug("Assigned color: white (job without driver/agent)")
            return 'white'
    elif is_shuttle:
        if not is_confirmed:
            logger.debug("Assigned color: white (unconfirmed shuttle)")
            return 'white'
    else:
        # Hotel-specific logic: remains white until confirmed
        if not is_confirmed:
            logger.debug("Assigned color: white (unconfirmed hotel booking)")
            return 'white'

    # Calculate if the job/booking is more than one day old
    one_day_ago = now - timedelta(days=1)

    if job_date and job_date <= one_day_ago.date() and not is_paid:
        logger.debug("Assigned color: red")
        return 'red'  # Job/booking is old and unpaid

    # If the job/booking is completed, mark it as green
    if is_paid or is_completed:
        logger.debug("Assigned color: green")
        return 'green'  # Job/booking is completed

    # If none of the above, mark as orange (confirmed hotel or assigned job)
    logger.debug("Assigned color: orange")
    return 'orange'


def calculate_cc_fee(job_price, payment_type, cc_fee_percentage):
    """Calculate the credit card fee based on the job price and payment type."""
    if payment_type == 'Card':
        fee_percentage = cc_fee_percentage if cc_fee_percentage else Decimal('7.00')  # Default to 7%
        cc_fee = (job_price * fee_percentage / Decimal('100')).quantize(Decimal('0.01'))
        # logger.debug(f"Applying CC Fee: {cc_fee} on {job_price} with rate {fee_percentage}%")
        return cc_fee
    return Decimal('0.00')


def get_ordered_people():
    agents = Agent.objects.all().order_by(Lower('name'))
    drivers = Driver.objects.all().order_by(Lower('name'))
    staffs = Staff.objects.all().order_by(Lower('name'))
    return agents, drivers, None, staffs


def get_currency_symbol(currency_code):
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'HUF': 'Ft',
    }
    return currency_symbols.get(currency_code, currency_code)  # Fallback to code if symbol not found