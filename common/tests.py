from django.test import TestCase
from django.core.cache import cache
from common.utils import get_exchange_rate, fetch_and_cache_exchange_rate
from decimal import Decimal
from unittest.mock import patch
import requests
from requests.exceptions import RequestException

class ExchangeRateTests(TestCase):

    def setUp(self):
        # Clear cache before each test to start fresh
        cache.clear()

    @patch('common.utils.requests.get')
    def test_fetch_and_cache_exchange_rate_success(self, mock_get):
        """Test fetching and caching the exchange rate successfully."""
        mock_response = {
            'conversion_rates': {
                'EUR': '1.20'
            }
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Test for USD to EUR
        rate = fetch_and_cache_exchange_rate('USD')

        # Ensure the correct rate is returned
        self.assertEqual(rate, Decimal('1.20'))

        # Ensure the rate is cached
        cached_rate = cache.get('exchange_rate_USD')
        self.assertEqual(cached_rate, Decimal('1.20'))

    @patch('common.utils.requests.get')
    def test_fetch_and_cache_exchange_rate_failure(self, mock_get):
        """Test handling of API request failure."""
        mock_get.side_effect = RequestException("API request failed")

        with self.assertRaises(ValueError) as context:
            fetch_and_cache_exchange_rate('USD')

        self.assertEqual(str(context.exception), "Error fetching exchange rate for USD")

    @patch('common.utils.requests.get')
    def test_fetch_and_cache_invalid_response(self, mock_get):
        """Test handling of invalid API response structure."""
        mock_response = {'unexpected_key': 'some_value'}
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            fetch_and_cache_exchange_rate('USD')

        self.assertEqual(str(context.exception), "Invalid response structure or missing EUR rate for USD")

    @patch('common.utils.requests.get')
    def test_get_exchange_rate_from_cache(self, mock_get):
        """Test fetching exchange rate from cache."""
        # Manually cache the rate
        cache.set('exchange_rate_USD', Decimal('1.15'))

        # Call get_exchange_rate and ensure API is not called
        rate = get_exchange_rate('USD')
        self.assertEqual(rate, Decimal('1.15'))
        mock_get.assert_not_called()

    @patch('common.utils.requests.get')
    def test_get_exchange_rate_not_cached(self, mock_get):
        """Test fetching exchange rate when it's not cached (API call happens)."""
        mock_response = {
            'conversion_rates': {
                'EUR': '1.20'
            }
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Call get_exchange_rate when it's not cached
        rate = get_exchange_rate('USD')
        self.assertEqual(rate, Decimal('1.20'))

        # Ensure the rate is now cached
        cached_rate = cache.get('exchange_rate_USD')
        self.assertEqual(cached_rate, Decimal('1.20'))

    def test_get_exchange_rate_eur(self):
        """Test that get_exchange_rate for EUR always returns 1.00 without API call."""
        rate = get_exchange_rate('EUR')
        self.assertEqual(rate, Decimal('1.00'))

    @patch('common.utils.requests.get')
    def test_cache_expiration(self, mock_get):
        """Test that cache expires and fetches new rate after expiration."""
        # Cache the rate manually
        cache.set('exchange_rate_USD', Decimal('1.15'), timeout=1)  # 1 second timeout

        # Wait for cache to expire
        import time
        time.sleep(2)

        mock_response = {
            'conversion_rates': {
                'EUR': '1.22'
            }
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Now the cache should be expired, and it should fetch a new rate
        rate = get_exchange_rate('USD')
        self.assertEqual(rate, Decimal('1.22'))

        # Ensure the new rate is cached
        cached_rate = cache.get('exchange_rate_USD')
        self.assertEqual(cached_rate, Decimal('1.22'))