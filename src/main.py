import getpass
import sys
import email
import imaplib
import smtplib
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class EmailConfig(Base):
    __tablename__ = 'email_config'
    id = Column(String, primary_key=True)
    email_address = Column(String)
    smtp_server = Column(String)
    username = Column(String)
    password = Column(String)
    imap_server = Column(String)
    imap_username = Column(String)
    imap_password = Column(String)

engine = create_engine('sqlite:///email_config.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

def encrypt(text, key):
    cipher_suite = Fernet(key)
    cipher_text = cipher_suite.encrypt(text.encode())
    return cipher_text

def decrypt(cipher_text, key):
    cipher_suite = Fernet(key)
    plain_text = cipher_suite.decrypt(cipher_text).decode()
    return plain_text

def store_email_config(email_address, smtp_server, username, password, imap_server, imap_username, imap_password):
    key = getpass.getpass('Enter encryption key: ').encode()
    encrypted_password = encrypt(password, key)
    encrypted_imap_password = encrypt(imap_password, key)
    config = EmailConfig(id=email_address, email_address=email_address, smtp_server=smtp_server, username=username, password=encrypted_password, imap_server=imap_server, imap_username=imap_username, imap_password=encrypted_imap_password)
    session.merge(config)
    session.commit()

def retrieve_email_config():
    key = getpass.getpass('Enter encryption key: ').encode()
    configs = session.query(EmailConfig).all()
    email_addresses = []
    smtp_servers = []
    usernames = []
    passwords = []
    imap_servers = []
    imap_usernames = []
    imap_passwords = []
    for config in configs:
        email_addresses.append(config.email_address)
        smtp_servers.append(config.smtp_server)
        usernames.append(config.username)
        passwords.append(decrypt(config.password, key))
        imap_servers.append(config.imap_server)
        imap_usernames.append(config.imap_username)
        imap_passwords.append(decrypt(config.imap_password, key))
    return email_addresses, smtp_servers, usernames, passwords, imap_servers, imap_usernames, imap_passwords

def send_email(email_address, smtp_server, username, password, recipients, subject, body):
    server = smtplib.SMTP(smtp_server)
    server.starttls()
    server.login(username, password)
    message = f'Subject: {subject}\nTo: {", ".join(recipients)}\n\n{body}'
    server.sendmail(username, recipients, message)
    server.quit()

def retrieve_emails_imap(imap_server, username, password):
    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(username, password)
    mail.select('inbox')
    _, data = mail.search(None, 'ALL')
    email_ids = data[0].split()
    emails = []
    for email_id in email_ids:
        _, data = mail.fetch(email_id, '(RFC822)')
        raw_email = data[0][1]
        email_obj = email.message_from_bytes(raw_email)
        emails.append(email_obj)
    mail.logout()
    return emails

def main():
    email_addresses, smtp_servers, usernames, passwords, imap_servers, imap_usernames, imap_passwords = retrieve_email_config()
    if not email_addresses or not smtp_servers or not usernames or not passwords or not imap_servers or not imap_usernames or not imap_passwords:
        email_address = input('Enter your email address: ')
        smtp_server = input('Enter your SMTP server: ')
        username = input('Enter your username: ')
        password = getpass.getpass('Enter your password: ')
        imap_server = input('Enter your IMAP server: ')
        imap_username = input('Enter your IMAP username: ')
        imap_password = getpass.getpass('Enter your IMAP password: ')
        store_email_config(email_address, smtp_server, username, password, imap_server, imap_username, imap_password)
    else:
        print('Available accounts:')
        for i, email_address in enumerate(email_addresses):
            print(f'{i+1}. {email_address}')
        account_choice = int(input('Choose an account: ')) - 1
        email_address = email_addresses[account_choice]
        smtp_server = smtp_servers[account_choice]
        username = usernames[account_choice]
        password = passwords[account_choice]
        imap_server = imap_servers[account_choice]
        imap_username = imap_usernames[account_choice]
        imap_password = imap_passwords[account_choice]
    
    action = input('What would you like to do? (send(s)/retrieve(r)/quit(q)): ')
    
    if action.lower() == 'send' or action.lower() == 's':
        recipients = input('Enter the recipients (separated by commas): ').split(',')
        recipients = [recipient.strip() for recipient in recipients]
        
        subject = input('Enter the email subject: ')
        print('Enter the email body (press Ctrl+D on a new line to finish):')
        body = sys.stdin.read()
        
        send_email(email_address, smtp_server, username, password, recipients, subject, body)
        print('Email sent!')
    
    elif action.lower() == 'retrieve' or action.lower() == 'r':
        print('Retrieving emails...')
        emails = retrieve_emails_imap(imap_server, imap_username, imap_password)
        for email in emails:
            print('From:', email['From'])
            print('Subject:', email['Subject'])
            print('Body:', email.get_payload())
            print('---')
    elif action.lower() == 'quit' or action.lower() == 'q':
        sys.exit(0)
    else:
        print('Invalid action')

if __name__ == '__main__':
    main()
