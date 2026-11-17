import unittest

from binarybitops.bitops import BitOpsError, compute, compute_from_strings, parse_operand, to_binary


class BitOpsTests(unittest.TestCase):
    def test_reference_example(self):
        result = compute(12, 10)
        self.assertEqual(result["and"], 8)
        self.assertEqual(result["or"], 14)
        self.assertEqual(result["xor"], 6)

    def test_binary_width_is_fixed(self):
        self.assertEqual(to_binary(0), "0000 0000 0000 0000")
        self.assertEqual(to_binary(65535), "1111 1111 1111 1111")
        self.assertEqual(to_binary(12), "0000 0000 0000 1100")
        self.assertTrue(all(len(to_binary(value)) == 19 for value in (0, 1, 255, 4096, 65535)))

    def test_accepts_documented_numeric_formats(self):
        self.assertEqual(parse_operand("12", "left"), 12)
        self.assertEqual(parse_operand(" 12 ", "left"), 12)
        self.assertEqual(parse_operand("0b1100", "left"), 12)
        self.assertEqual(parse_operand("0x0C", "left"), 12)
        self.assertEqual(parse_operand(12, "left"), 12)

    def test_rejects_invalid_operands(self):
        invalid = [-1, 65536, 999999, "", "12.5", "abc", "1 2", None, 1.5, True, False, [], {}, "0x"]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(BitOpsError):
                    parse_operand(value, "left")

    def test_rejects_overlong_strings(self):
        with self.assertRaises(BitOpsError):
            parse_operand("0" * 20, "right")

    def test_error_does_not_echo_untrusted_input(self):
        payload = "<script>alert(1)</script>"
        with self.assertRaises(BitOpsError) as caught:
            parse_operand(payload, "left")
        self.assertNotIn("script", str(caught.exception))

    def test_compute_from_strings_returns_full_document(self):
        result = compute_from_strings("0x0C", "10")
        self.assertEqual(result["left"], 12)
        self.assertEqual(result["right"], 10)
        self.assertEqual(result["bit_width"], 16)
        self.assertEqual(result["binary"]["xor"], "0000 0000 0000 0110")


if __name__ == "__main__":
    unittest.main()
