from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from requests.exceptions import RequestException

from common.exchange_rate_models import ExchangeRate
from common.utils import fetch_and_cache_exchange_rate, get_exchange_rate

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
    def test_refetch_after_cache_cleared_when_db_older_than_24h(self, mock_get):
        """
        After in-process cache is cleared, a row whose last_updated is >24h behind
        'now' must trigger a new HTTP fetch (covers the main production refresh path).
        """
        cache.clear()
        base = timezone.now()
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'conversion_rates': {'EUR': '1.2000'}}

        rate1 = get_exchange_rate('USD')
        self.assertEqual(rate1, Decimal('1.2000'))
        self.assertEqual(mock_get.call_count, 1)

        mock_get.return_value.json.return_value = {'conversion_rates': {'EUR': '1.2500'}}
        cache.delete('exchange_rate_USD')

        with patch('django.utils.timezone.now', return_value=base + timedelta(hours=25)):
            rate2 = get_exchange_rate('USD')

        self.assertEqual(rate2, Decimal('1.2500'))
        self.assertEqual(mock_get.call_count, 2)

    @patch('common.utils.requests.get')
    def test_uses_db_without_api_when_row_newer_than_24h(self, mock_get):
        """Cache miss but DB row 'fresh' (< 24h old): return stored rate, no HTTP."""
        cache.clear()
        base = timezone.now()
        er = ExchangeRate.objects.create(currency='USD', rate=Decimal('0.9100'))
        ExchangeRate.objects.filter(pk=er.pk).update(last_updated=base - timedelta(hours=3))

        with patch('django.utils.timezone.now', return_value=base):
            rate = get_exchange_rate('USD')

        self.assertEqual(rate, Decimal('0.9100'))
        mock_get.assert_not_called()

    @patch('common.utils.requests.get')
    def test_refetch_when_row_age_just_over_24h_even_if_cache_empty(self, mock_get):
        """Stale DB row (>=24h) with empty cache forces API (no MagicMock / real ORM)."""
        cache.clear()
        base = timezone.now()
        er = ExchangeRate.objects.create(currency='GBP', rate=Decimal('0.8800'))
        ExchangeRate.objects.filter(pk=er.pk).update(last_updated=base - timedelta(hours=25))

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'conversion_rates': {'EUR': '0.9000'}}

        with patch('django.utils.timezone.now', return_value=base):
            rate = get_exchange_rate('GBP')

        self.assertEqual(rate, Decimal('0.9000'))
        mock_get.assert_called_once()

    @patch('common.utils.requests.get')
    def test_boundary_exactly_24h_old_row_still_considered_fresh(self, mock_get):
        """
        Condition is strict < (older than 24h). A row exactly 24h behind 'now'
        still uses DB without calling the API.
        """
        cache.clear()
        base = timezone.now()
        er = ExchangeRate.objects.create(currency='HUF', rate=Decimal('0.0026'))
        ExchangeRate.objects.filter(pk=er.pk).update(last_updated=base - timedelta(hours=24))

        with patch('django.utils.timezone.now', return_value=base):
            rate = get_exchange_rate('HUF')

        self.assertEqual(rate, Decimal('0.0026'))
        mock_get.assert_not_called()

    @patch('common.utils.requests.get')
    def test_cache_wins_even_if_db_row_is_stale(self, mock_get):
        """Documented behaviour: while cache key exists, DB age is ignored."""
        cache.clear()
        base = timezone.now()
        er = ExchangeRate.objects.create(currency='USD', rate=Decimal('0.1000'))
        ExchangeRate.objects.filter(pk=er.pk).update(last_updated=base - timedelta(days=400))
        cache.set('exchange_rate_USD', Decimal('0.9200'), timeout=3600)

        with patch('django.utils.timezone.now', return_value=base):
            rate = get_exchange_rate('USD')

        self.assertEqual(rate, Decimal('0.9200'))
        mock_get.assert_not_called()

    @patch('common.utils.requests.get')
    def test_staleness_uses_rolling_24h_not_calendar_midnight_budapest(self, mock_get):
        """
        Refresh policy is a rolling 24h window vs last_updated (timezone-aware),
        not local calendar midnight. Uses a fixed UTC instant so the test is deterministic.
        """
        cache.clear()
        t0 = datetime(2024, 6, 15, 20, 0, 0, tzinfo=datetime_timezone.utc)

        er = ExchangeRate.objects.create(currency='USD', rate=Decimal('1.1000'))
        ExchangeRate.objects.filter(pk=er.pk).update(last_updated=t0 - timedelta(hours=26))

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'conversion_rates': {'EUR': '1.3333'}}

        with patch('django.utils.timezone.now', return_value=t0):
            rate = get_exchange_rate('USD')

        self.assertEqual(rate, Decimal('1.3333'))
        mock_get.assert_called_once()

    @patch('common.utils.requests.get')
    def test_get_exchange_rate_eur(self, mock_get):
        """Test that get_exchange_rate for EUR always returns 1.00 without API call."""
        # Call the function
        rate = get_exchange_rate('EUR')
        self.assertEqual(rate, Decimal('1.00'))
        
        # Verify that no API call was made
        mock_get.assert_not_called()