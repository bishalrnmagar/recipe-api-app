"""
Sample tests
"""

from django.test import SimpleTestCase
from app import calc

class CalcTest(SimpleTestCase):
    def test_add_num(self):
        res = calc.add(6, 6)
        self.assertEqual(res, 12)
    
    def test_sub_num(self):
        res = calc.substract(10, 4)
        self.assertEqual(res, 6)
