from django.test import TestCase
from decimal import Decimal
from unittest.mock import patch
from common.utils import get_exchange_rate, fetch_and_cache_exchange_rate
from django.core.cache import cache
import requests

class UtilityFunctionTests(TestCase):

    @patch('requests.get')
    def test_get_exchange_rate_usd(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'conversion_rates': {
                'EUR': '1.12'
            }
        }
        rate = get_exchange_rate('USD')
        self.assertEqual(rate, Decimal('1.12'))

    @patch('requests.get')
    def test_get_exchange_rate_cache_expiry(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'conversion_rates': {
                'EUR': '1.12'
            }
        }
        cache.clear()
        rate = get_exchange_rate('USD')
        self.assertEqual(rate, Decimal('1.12'))

        mock_get.return_value.json.return_value = {
            'conversion_rates': {
                'EUR': '1.10'
            }
        }

        rate = get_exchange_rate('USD')
        self.assertEqual(rate, Decimal('1.12'))

    @patch('requests.get')
    def test_get_exchange_rate_invalid_currency(self, mock_get):
        mock_get.return_value.status_code = 404
        with self.assertRaises(ValueError):
            get_exchange_rate('XYZ')

    @patch('requests.get')
    def test_get_exchange_rate_default_currency(self, mock_get):
        rate = get_exchange_rate('EUR')
        self.assertEqual(rate, Decimal('1.00'))