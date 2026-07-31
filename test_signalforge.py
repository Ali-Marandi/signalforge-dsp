import unittest

from signalforge import dft_magnitudes, moving_average, rms


class SignalForgeTests(unittest.TestCase):
    def test_rms(self):
        self.assertAlmostEqual(rms([3, 4]), 3.5355339)

    def test_moving_average(self):
        self.assertEqual(moving_average([1, 2, 3, 4], 2), [1.5, 2.5, 3.5])

    def test_constant_signal_dft(self):
        spectrum = dft_magnitudes([2, 2, 2, 2])
        self.assertAlmostEqual(spectrum[0], 2)
        self.assertTrue(all(value < 1e-12 for value in spectrum[1:]))


if __name__ == "__main__":
    unittest.main()
