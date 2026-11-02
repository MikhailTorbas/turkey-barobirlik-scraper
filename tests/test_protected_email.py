import unittest
from turkey_scraper import parse_detail, ExtractionError

class ProtectedEmailTests(unittest.TestCase):
    def html(self, value):
        return ('<table><tr><td>TBB Sicil No</td><td>123</td></tr>'
                '<tr><td>Baro Sicil No</td><td>456</td></tr>'
                f'<tr><td>E-Posta</td><td>{value}</td></tr></table>')

    def encoded(self, address):
        key = 67
        return bytes([key] + [b ^ key for b in address.encode()]).hex()

    def test_span_and_href_decode_like_rendered_page(self):
        for address in ('test@example.org', 'çağrı@example.org'):
            code = self.encoded(address)
            for markup in (f'<span data-cfemail="{code}">[email protected]</span>',
                           f'<a href="/cdn-cgi/l/email-protection#{code}">[email protected]</a>'):
                self.assertEqual(parse_detail(self.html(markup))['email'], address)

    def test_invalid_encoding_does_not_save_placeholder(self):
        for code in ('z123', '', '00'):
            with self.assertRaises(ExtractionError):
                parse_detail(self.html(f'<span data-cfemail="{code}">[email protected]</span>'))

    def test_empty_protected_link_remains_blank(self):
        code = self.encoded('test@example.org')
        result = parse_detail(self.html(f'<a href="/cdn-cgi/l/email-protection#{code}"></a>'))
        self.assertEqual(result['email'], '')
        self.assertEqual(result['_field_availability']['email'], 'blank_on_site')

    def test_truncated_source_address_is_audited_and_profile_completes(self):
        from turkey_scraper import merge_record
        code = self.encoded('person@gmail.')
        result = parse_detail(self.html(f'<a href="/cdn-cgi/l/email-protection#{code}">[email protected]</a>'))
        self.assertEqual(result['detail_status'], 'done')
        self.assertEqual(result['email'], '')
        self.assertEqual(result['_field_availability']['email'], 'invalid_on_site')
        self.assertEqual(result['_invalid_contact_values']['email'], ['person@gmail.'])
        merged = merge_record(result, {'email': ''})
        self.assertEqual(merged['_invalid_contact_values'], result['_invalid_contact_values'])
        valid = merge_record({'email': 'known@example.org'}, result)
        self.assertEqual(valid['email'], 'known@example.org')
        self.assertEqual(valid['_field_availability']['email'], 'present')

    def test_plain_truncated_address_and_protected_address_have_same_state(self):
        plain = parse_detail(self.html('person@gmail.'))
        code = self.encoded('person@gmail.')
        encoded = parse_detail(self.html(f'<span data-cfemail="{code}">[email protected]</span>'))
        for field in ('email', '_field_availability', '_invalid_contact_values', 'detail_status'):
            self.assertEqual(plain[field], encoded[field])
