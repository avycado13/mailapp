import unittest
from unittest.mock import patch
from io import StringIO

class TestEmailFunctions(unittest.TestCase):
    @patch('builtins.input', side_effect=['test@example.com', 'smtp.example.com', 'testuser', 'testpassword', 'imap.example.com', 'testuser', 'testpassword'])
    @patch('getpass.getpass', side_effect=['testkey'])
    def test_store_email_config(self, mock_getpass, mock_input):
        from ..main import store_email_config, session, EmailConfig
        store_email_config('test@example.com', 'smtp.example.com', 'testuser', 'testpassword', 'imap.example.com', 'testuser', 'testpassword')
        config = session.query(EmailConfig).filter_by(id='test@example.com').first()
        self.assertEqual(config.email_address, 'test@example.com')
        self.assertEqual(config.smtp_server, 'smtp.example.com')
        self.assertEqual(config.username, 'testuser')
        self.assertNotEqual(config.password, 'testpassword')
        self.assertNotEqual(config.imap_password, 'testpassword')

    @patch('builtins.input', side_effect=['1'])
    def test_retrieve_email_config(self, mock_input):
        from ..main import retrieve_email_config
        email_addresses, smtp_servers, usernames, passwords, imap_servers, imap_usernames, imap_passwords = retrieve_email_config()
        self.assertEqual(email_addresses, ['test@example.com'])
        self.assertEqual(smtp_servers, ['smtp.example.com'])
        self.assertEqual(usernames, ['testuser'])
        self.assertNotEqual(passwords, ['testpassword'])
        self.assertEqual(imap_servers, ['imap.example.com'])
        self.assertEqual(imap_usernames, ['testuser'])
        self.assertNotEqual(imap_passwords, ['testpassword'])

    @patch('builtins.input', side_effect=['test@example.com', 'smtp.example.com', 'testuser', 'testpassword', 'imap.example.com', 'testuser', 'testpassword'])
    @patch('getpass.getpass', side_effect=['testkey'])
    def test_send_email(self, mock_getpass, mock_input):
        from ..main import send_email
        recipients = ['recipient1@example.com', 'recipient2@example.com']
        subject = 'Test Subject'
        body = 'Test Body'
        with patch('smtplib.SMTP') as mock_smtp:
            send_email('test@example.com', 'smtp.example.com', 'testuser', 'testpassword', recipients, subject, body)
            mock_smtp.assert_called_once_with('smtp.example.com')
            mock_smtp.return_value.starttls.assert_called_once()
            mock_smtp.return_value.login.assert_called_once_with('testuser', 'testpassword')
            mock_smtp.return_value.sendmail.assert_called_once_with('testuser', recipients, f'Subject: {subject}\nTo: recipient1@example.com, recipient2@example.com\n\n{body}')
            mock_smtp.return_value.quit.assert_called_once()

    @patch('builtins.input', side_effect=['imap.example.com', 'testuser', 'testpassword'])
    def test_retrieve_emails_imap(self, mock_input):
        from ..main import retrieve_emails_imap
        with patch('imaplib.IMAP4_SSL') as mock_imap:
            mock_imap.return_value.login.return_value = ('OK', b'Success')
            mock_imap.return_value.select.return_value = ('OK', b'Success')
            mock_imap.return_value.search.return_value = ('OK', [b'1 2 3'])
            mock_imap.return_value.fetch.return_value = ('OK', [(b'1 (RFC822 {123}', b'raw_email_data'), (b'2 (RFC822 {456}', b'raw_email_data')])
            emails = retrieve_emails_imap('imap.example.com', 'testuser', 'testpassword')
            self.assertEqual(len(emails), 2)
            mock_imap.assert_called_once_with('imap.example.com')
            mock_imap.return_value.login.assert_called_once_with('testuser', 'testpassword')
            mock_imap.return_value.select.assert_called_once_with('inbox')
            mock_imap.return_value.search.assert_called_once_with(None, 'ALL')
            mock_imap.return_value.fetch.assert_called_once_with(b'1', '(RFC822)')
            mock_imap.return_value.logout.assert_called_once()

    @patch('builtins.input', side_effect=['1', 's', 'recipient1@example.com, recipient2@example.com', 'Test Subject', 'Test Body'])
    @patch('getpass.getpass', side_effect=['testkey'])
    def test_main_send_email(self, mock_getpass, mock_input):
        from ..main import main
        with patch('smtplib.SMTP') as mock_smtp, patch('sys.stdout', new=StringIO()) as mock_stdout:
            main()
            mock_smtp.assert_called_once_with('smtp.example.com')
            mock_smtp.return_value.starttls.assert_called_once()
            mock_smtp.return_value.login.assert_called_once_with('testuser', 'testpassword')
            mock_smtp.return_value.sendmail.assert_called_once_with('testuser', ['recipient1@example.com', 'recipient2@example.com'], 'Subject: Test Subject\nTo: recipient1@example.com, recipient2@example.com\n\nTest Body')
            mock_smtp.return_value.quit.assert_called_once()
            self.assertEqual(mock_stdout.getvalue().strip(), 'Email sent!')

    @patch('builtins.input', side_effect=['1', 'r'])
    @patch('getpass.getpass', side_effect=['testkey'])
    def test_main_retrieve_emails(self, mock_getpass, mock_input):
        from ..main import main
        with patch('imaplib.IMAP4_SSL') as mock_imap, patch('sys.stdout', new=StringIO()) as mock_stdout:
            mock_imap.return_value.login.return_value = ('OK', b'Success')
            mock_imap.return_value.select.return_value = ('OK', b'Success')
            mock_imap.return_value.search.return_value = ('OK', [b'1'])
            mock_imap.return_value.fetch.return_value = ('OK', [(b'1 (RFC822 {123}', b'raw_email_data')])
            main()
            mock_imap.assert_called_once_with('imap.example.com')
            mock_imap.return_value.login.assert_called_once_with('testuser', 'testpassword')
            mock_imap.return_value.select.assert_called_once_with('inbox')
            mock_imap.return_value.search.assert_called_once_with(None, 'ALL')
            mock_imap.return_value.fetch.assert_called_once_with(b'1', '(RFC822)')
            self.assertEqual(mock_stdout.getvalue().strip(), 'From: sender@example.com\nSubject: Test Subject\nBody: Test Body\n---')

if __name__ == '__main__':
    unittest.main()
