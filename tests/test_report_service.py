import asyncio
import unittest

from main import PhoneReportService


class TestGetReportForPhone(unittest.TestCase):
    def setUp(self) -> None:
        self.get_report = PhoneReportService._get_report_for_phone.__wrapped__

    def test_empty_data(self):
        data = {}
        phone_numbers = [0]

        actual_result = asyncio.run(self.get_report(data, phone_numbers))
        expected_result = [
            {'phone': 0, 'cnt_all_attempts': 0, 'cnt_att_dur': {'10_sec': 0, '10_30_sec': 0, '30_sec': 0},
             'min_price_att': 0, 'max_price_att': 0, 'avg_dur_att': 0, 'sum_price_att_over_15': 0}
        ]

        self.assertEqual(actual_result, expected_result)

    def test_empty_phone_numbers(self):
        data = {
            0: [{"start_date": 0, "end_date": 10000}]
        }
        phone_numbers = []

        actual_result = asyncio.run(self.get_report(data, phone_numbers))
        expected_result = []

        self.assertEqual(actual_result, expected_result)

    def test_empty_phone_numbers_and_empty_data(self):
        data = {}
        phone_numbers = []

        actual_result = asyncio.run(self.get_report(data, phone_numbers))
        expected_result = []

        self.assertEqual(actual_result, expected_result)

    def test_valid_data_single_duration(self):
        data = {
            0: [{"start_date": 0, "end_date": 10000}],
            1: [{"start_date": 1000, "end_date": 30000}]
        }
        phone_numbers = [0, 1]

        actual_result = asyncio.run(self.get_report(data, phone_numbers))
        expected_result = [
            {'phone': 0, 'cnt_all_attempts': 1, 'cnt_att_dur': {'10_sec': 0, '10_30_sec': 1, '30_sec': 0},
             'min_price_att': 100.0, 'max_price_att': 100.0, 'avg_dur_att': 10.0, 'sum_price_att_over_15': 100.0},
            {'phone': 1, 'cnt_all_attempts': 1, 'cnt_att_dur': {'10_sec': 0, '10_30_sec': 1, '30_sec': 0},
             'min_price_att': 290.0, 'max_price_att': 290.0, 'avg_dur_att': 29.0, 'sum_price_att_over_15': 290.0}
        ]

        self.assertEqual(actual_result, expected_result)

    def test_valid_data_multiple_durations(self):
        data = {
            1: [{"start_date": 0, "end_date": 9000}, {"start_date": 0, "end_date": 12000}],
            2: [{"start_date": 0, "end_date": 40000}, {"start_date": 1000, "end_date": 30000}]
        }
        phone_numbers = [1, 2]

        actual_result = asyncio.run(self.get_report(data, phone_numbers))
        expected_result = [
            {"phone": 1, "cnt_all_attempts": 2, "cnt_att_dur": {"10_sec": 1, "10_30_sec": 1, "30_sec": 0},
             "min_price_att": 90.0, "max_price_att": 120.0, "avg_dur_att": 10.5, "sum_price_att_over_15": 0},
            {"phone": 2, "cnt_all_attempts": 2, "cnt_att_dur": {"10_sec": 0, "10_30_sec": 1, "30_sec": 1},
             "min_price_att": 290.0, "max_price_att": 400.0, "avg_dur_att": 34.5, "sum_price_att_over_15": 690.0}
        ]

        self.assertEqual(actual_result, expected_result)


if __name__ == '__main__':
    unittest.main()
