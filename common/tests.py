from django.test import TestCase
from django.core.cache import cache
from common.utils import get_exchange_rate, fetch_and_cache_exchange_rate
from decimal import Decimal
from unittest.mock import patch, MagicMock
import requests
from requests.exceptions import RequestException
from datetime import timedelta
from django.utils import timezone
from common.exchange_rate_models import ExchangeRate

class ExchangeRateTests(TestCase):

    def setUp(self):
        # Don't clear cache globally - only clear in specific tests that need it
        pass

    @patch('common.utils.requests.get')
    def test_fetch_and_cache_exchange_rate_success(self, mock_get):
        # Clear cache for this specific test
        cache.clear()
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
        # Clear cache for this specific test
        cache.clear()
        """Test handling of API request failure."""
        mock_get.side_effect = RequestException("API request failed")

        with self.assertRaises(ValueError) as context:
            fetch_and_cache_exchange_rate('USD')

        self.assertEqual(str(context.exception), "Error fetching exchange rate for USD")

    @patch('common.utils.requests.get')
    def test_fetch_and_cache_invalid_response(self, mock_get):
        # Clear cache for this specific test
        cache.clear()
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
        # Clear cache for this specific test
        cache.clear()
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

    @patch('common.utils.requests.get')
    @patch('common.exchange_rate_models.ExchangeRate.objects')
    def test_cache_expiration(self, mock_exchange_rate_objects, mock_get):
        # Clear cache for this specific test
        cache.clear()
        """Test that cache expires and fetches new rate after expiration."""
        # Mock database to raise DoesNotExist
        mock_exchange_rate_objects.get.side_effect = ExchangeRate.DoesNotExist

        # Cache the rate manually
        cache.set('exchange_rate_USD', Decimal('1.15'), timeout=1)  # 1 second timeout

        # Wait for cache to expire
        import time
        time.sleep(3)

        mock_exchange_rate = MagicMock()
        mock_exchange_rate.rate = Decimal('1.22')
        mock_exchange_rate_objects.update_or_create.return_value = (mock_exchange_rate, True)

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

    @patch('common.utils.requests.get')
    @patch('common.exchange_rate_models.ExchangeRate.objects')
    def test_cache_expiration_24_hours(self, mock_exchange_rate_objects, mock_get):
        # Clear cache for this specific test
        cache.clear()
        """Test that cache expires after 24 hours and new API call is made."""
        # First mock response
        mock_response_1 = {
            'conversion_rates': {
                'EUR': '1.20'
            }
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response_1

        # Mock database operations
        mock_exchange_rate = MagicMock()
        mock_exchange_rate.rate = Decimal('1.20')
        mock_exchange_rate_objects.get.return_value = mock_exchange_rate
        mock_exchange_rate_objects.update_or_create.return_value = (mock_exchange_rate, True)

        # First call - should make API call
        rate1 = get_exchange_rate('USD')
        self.assertEqual(rate1, Decimal('1.20'))

        with patch('django.utils.timezone.now') as mock_now:
            current_time = timezone.now()
            mock_now.return_value = current_time + timedelta(hours=24)

            mock_exchange_rate_objects.get.side_effect = ExchangeRate.DoesNotExist

            # Still cached, should return same
            rate2 = get_exchange_rate('USD')
            self.assertEqual(rate2, Decimal('1.20'))

            # Now simulate cache expiration and change response
            mock_response_2 = {
                'conversion_rates': {
                    'EUR': '1.25'
                }
            }
            mock_get.return_value.json.return_value = mock_response_2

            cache.delete('exchange_rate_USD')
            mock_now.return_value = current_time + timedelta(hours=25)

            rate3 = get_exchange_rate('USD')
            self.assertEqual(rate3, Decimal('1.25'))

        # Verify API was called twice
        self.assertEqual(mock_get.call_count, 2)

    @patch('common.utils.requests.get')
    def test_get_exchange_rate_eur(self, mock_get):
        """Test that get_exchange_rate for EUR always returns 1.00 without API call."""
        # Call the function
        rate = get_exchange_rate('EUR')
        self.assertEqual(rate, Decimal('1.00'))
        
        # Verify that no API call was made
        mock_get.assert_not_called()