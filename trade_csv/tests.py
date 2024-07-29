from django.contrib.auth.models import User
from decimal import Decimal
from django.core.files.storage import default_storage, FileSystemStorage
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
import os
from unittest.mock import patch
from trade_csv.models import Trade
from io import StringIO
from trade_csv.views import parse_decimal


class ParseDecimalTests(TestCase):
    def test_parse_decimal(self):
        self.assertEqual(parse_decimal('--'), Decimal('0'))
        self.assertEqual(parse_decimal('0.0'), Decimal('0'))
        self.assertEqual(parse_decimal('123.45'), Decimal('123.45'))
        self.assertEqual(parse_decimal('0.0000000001'), Decimal('0'))


class TradeDataValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            id=1, username='testuser', password='testpassword')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.test_media_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'test_media')
        self.local_storage = FileSystemStorage(location=self.test_media_dir)
        self.original_storage = default_storage
        default_storage._wrapped = self.local_storage

    def tearDown(self):
        default_storage._wrapped = self.original_storage
        if os.path.exists(self.test_media_dir):
            for root, dirs, files in os.walk(self.test_media_dir):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(self.test_media_dir)

    @patch('trade_csv.utils.get_current_price')
    def test_data_validation(self, mock_get_current_price):
        mock_get_current_price.return_value = Decimal('3600')

        csv_content = (
            b"Underlying Asset,Margin Mode,Leverage,Order Time,Side,Avg Fill,Price,Filled,Total,PNL,PNL%,Fee,Order Options,Reduce-only,Status\n"
            b"ETHUSDT,Isolated,3,07/29/2024 18:02:59,Buy,3387.35 USDT,Market,0.09 ETH,0.09 ETH,--,--,0.1829169 USDT,GTC,N,Filled"
        )
        csv_file = SimpleUploadedFile(
            "test_trades.csv", csv_content, content_type="text/csv")

        response = self.client.post(reverse('upload_csv'), {
                                    'file': csv_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'],
                         "CSV uploaded and processed successfully")

        self.assertEqual(Trade.objects.count(), 1)
        trade = Trade.objects.first()
        self.assertEqual(trade.user, self.user)

        if trade.user == self.user:
            print("Success: Trade instance created with the correct user.")
        else:
            print("Failure: Trade instance not created correctly.")

        print("Initial Response Data:", response.data)
        print("---------------------------------------------------------------------------------------------")


class TradeSingleUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            id=1, username='testuser', password='testpassword')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.test_media_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'test_media')
        self.local_storage = FileSystemStorage(location=self.test_media_dir)
        self.original_storage = default_storage
        default_storage._wrapped = self.local_storage

    def tearDown(self):
        default_storage._wrapped = self.original_storage
        if os.path.exists(self.test_media_dir):
            for root, dirs, files in os.walk(self.test_media_dir):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(self.test_media_dir)

    def test_upload_single_trade(self):
        # CSV content before upload
        csv_content = (
            b"Underlying Asset,Margin Mode,Leverage,Order Time,Side,Avg Fill,Price,Filled,Total,PNL,PNL%,Fee,Order Options,Reduce-only,Status\n"
            b"ETHUSDT,Isolated,3,07/29/2024 18:02:59,Buy,3387.35 USDT,Market,0.09 ETH,0.09 ETH,--,--,0.1829169 USDT,GTC,N,Filled"
        )
        csv_file = SimpleUploadedFile(
            "test_trades.csv", csv_content, content_type="text/csv")

        # Print CSV content before upload
        print("CSV Content Before Upload:")
        print(csv_content.decode('utf-8'))

        response = self.client.post(reverse('upload_csv'), {
                                    'file': csv_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'],
                         "CSV uploaded and processed successfully")

        self.assertEqual(Trade.objects.count(), 1)
        trade = Trade.objects.first()
        self.assertEqual(trade.user, self.user)

        # Print processed Trade instance
        print("Processed Trade Instance:")
        print(f"Underlying Asset: {trade.underlying_asset}")
        print(f"Margin Mode: {trade.margin_type}")
        print(f"Leverage: {trade.leverage}")
        print(f"Order Time: {trade.order_time}")
        print(f"Side: {trade.side}")
        print(f"Avg Fill: {trade.avg_fill}")
        print(f"Price: {trade.price}")
        print(f"Filled: {trade.filled}")
        print(f"PNL: {trade.pnl}")
        print(f"PNL%: {trade.pnl_percentage}")
        print(f"Fee: {trade.fee}")
        print(f"Order Options: {trade.order_options}")
        print(f"Reduce-only: {trade.reduce_only}")
        print(f"Status: {trade.status}")

        # Assert the conditions were applied correctly
        self.assertEqual(trade.price, Decimal('3387.35'))
        self.assertEqual(trade.pnl, Decimal('0'))
        self.assertEqual(trade.pnl_percentage, Decimal('0'))
        print("---------------------------------------------------------------------------------------------")


class TradeMultipleUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            id=1, username='testuser', password='testpassword')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.test_media_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'test_media')
        self.local_storage = FileSystemStorage(location=self.test_media_dir)
        self.original_storage = default_storage
        default_storage._wrapped = self.local_storage

    def tearDown(self):
        default_storage._wrapped = self.original_storage
        if os.path.exists(self.test_media_dir):
            for root, dirs, files in os.walk(self.test_media_dir):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(self.test_media_dir)

    @patch('trade_csv.utils.get_current_price')
    def test_upload_multiple_trades(self, mock_get_current_price):
        mock_get_current_price.return_value = Decimal('3600')

        csv_content = (
            b"Underlying Asset,Margin Mode,Leverage,Order Time,Side,Avg Fill,Price,Filled,Total,PNL,PNL%,Fee,Order Options,Reduce-only,Status\n"
            b"ETHUSDT,Isolated,3,07/29/2024 18:02:59,Buy,3387.35 USDT,Market,0.09 ETH,0.09 ETH,--,--,0.1829169 USDT,GTC,N,Filled\n"
            b"LDOUSDT,Isolated,2,07/29/2024 07:12:59,Sell,1.562 USDT,Market,52 LDO,52 LDO,-7.038872586872586772 USDT,-15.95%,0.0487344 USDT,GTC,Y,Filled\n"
            b"TURBOUSDT,Isolated,1,07/28/2024 22:50:32,Buy,0.0052893 USDT,Market,10000 TURBO,10000 TURBO,--,--,0.0158679 USDT,GTC,N,Filled\n"
        )
        csv_file = SimpleUploadedFile(
            "test_multiple_trades.csv", csv_content, content_type="text/csv")

        response = self.client.post(reverse('upload_csv'), {
                                    'file': csv_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'],
                         "CSV uploaded and processed successfully")

        self.assertEqual(Trade.objects.count(), 3)

        trades = Trade.objects.all()
        trade_data = {
            'ETHUSDT': {
                'margin_type': 'Isolated',
                'leverage': 3,
                'price': Decimal('3387.35'),
                'filled': Decimal('0.09'),
                'fee': Decimal('0.1829169'),
                'pnl': Decimal('0'),
                'pnl_percentage': Decimal('0'),
            },
            'LDOUSDT': {
                'margin_type': 'Isolated',
                'leverage': 2,
                'price': Decimal('1.562'),
                'filled': Decimal('52'),
                'fee': Decimal('0.0487344'),
                'pnl': Decimal('-7.038872586872586772'),
                'pnl_percentage': Decimal('-15.95'),
            },
            'TURBOUSDT': {
                'margin_type': 'Isolated',
                'leverage': 1,
                'price': Decimal('0.0052893'),
                'filled': Decimal('10000'),
                'fee': Decimal('0.0158679'),
                'pnl': Decimal('0'),
                'pnl_percentage': Decimal('0'),
            }
        }

        for trade in trades:
            data = trade_data.get(trade.underlying_asset)
            if data:
                self.assertEqual(trade.margin_type, data['margin_type'])
                self.assertEqual(trade.leverage, data['leverage'])
                self.assertEqual(trade.price, data['price'])
                self.assertEqual(trade.filled, data['filled'])
                self.assertEqual(trade.fee, data['fee'])
                if 'pnl' in data:
                    self.assertEqual(trade.pnl, data['pnl'])
                    self.assertEqual(trade.pnl_percentage,
                                     data['pnl_percentage'])

        print("Initial Response Data:", response.data)
        print("---------------------------------------------------------------------------------------------")
