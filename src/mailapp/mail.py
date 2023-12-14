import email
import getpass
import imaplib
import os
import shutil
import smtplib
import subprocess
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gnupg
from cryptography.fernet import Fernet
from sqlalchemy import Column, String, create_engine
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

def check_gpg_installed():
    try:
        subprocess.run(['gpg', '--version'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
    
def find_gpg_path():
    gpg_path = shutil.which('gpg')
    return gpg_path

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

def send_email(email_address, smtp_server, username, password, recipients, subject, body, attachments=None, encrypt=False):
    msg = MIMEMultipart()
    msg['From'] = username
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject

    if encrypt:
        encrypted_body = gpg.encrypt(body, recipients[0])
        body = str(encrypted_body)

    msg.attach(MIMEText(body, 'plain'))

    if attachments:
        for attachment in attachments:
            with open(attachment, 'rb') as file:
                part = MIMEApplication(file.read(), Name=os.path.basename(attachment))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment)}"'
                msg.attach(part)

    server = smtplib.SMTP(smtp_server)
    server.starttls()
    server.login(username, password)
    server.send_message(msg)
    server.quit()

def retrieve_emails_imap(imap_server, username, password, decrypt=False):
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

        if decrypt:
            encrypted_body = email_obj.get_payload()
            decrypted_body = gpg.decrypt(str(encrypted_body))
            email_obj.set_payload(str(decrypted_body))

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
    
    action = input('What would you like to do? (send(s)/retrieve(r)/attach(a)/quit(q)): ')
    
    if action.lower() == 'send' or action.lower() == 's':
        recipients = input('Enter the recipients (separated by commas): ').split(',')
        recipients = [recipient.strip() for recipient in recipients]
        
        subject = input('Enter the email subject: ')
        print('Enter the email body (press Ctrl+D on a new line to finish):')
        body = sys.stdin.read()
        
        attachments = []
        attach_file = input('Attach a file? (y/n): ')
        if attach_file.lower() == 'y':
            file_path = input('Enter the file path: ')
            attachments.append(file_path)
        
        encrypt = input('Encrypt the email body? (y/n): ')
        if encrypt.lower() == 'y' and check_gpg_installed == True:
            encrypt = True
        elif encrypt.lower() == 'y' and check_gpg_installed == False:
            encrypt = False
            print('GnuPG is not installed. Please install GnuPG to use GPG encryption/decryption.')
        else:
            encrypt = False
        
        send_email(email_address, smtp_server, username, password, recipients, subject, body, attachments, encrypt)
        print('Email sent!')
    
    elif action.lower() == 'retrieve' or action.lower() == 'r':
        decrypt = input('Decrypt the email body? (y/n): ')
        if decrypt.lower() == 'y':
            decrypt = True
        else:
            decrypt = False
        
        print('Retrieving emails...')
        emails = retrieve_emails_imap(imap_server, imap_username, imap_password, decrypt)
        for email in emails:
            print('From:', email['From'])
            print('Subject:', email['Subject'])
            print('Body:', email.get_payload())
            print('---')
    
    elif action.lower() == 'attach' or action.lower() == 'a':
        attachments = []
        attach_file = input('Enter the file path: ')
        attachments.append(attach_file)
        
        recipients = input('Enter the recipients (separated by commas): ').split(',')
        recipients = [recipient.strip() for recipient in recipients]
        
        subject = input('Enter the email subject: ')
        print('Enter the email body (press Ctrl+D on a new line to finish):')
        body = sys.stdin.read()
        
        encrypt = input('Encrypt the email body? (y/n): ')
        if encrypt.lower() == 'y' and check_gpg_installed:
            encrypt = True
        elif encrypt.lower() == 'y' and not check_gpg_installed:
            encrypt = False
            print('GnuPG is not installed. Please install GnuPG to use GPG encryption/decryption.')
        else:
            encrypt = False
        
        send_email(email_address, smtp_server, username, password, recipients, subject, body, attachments, encrypt)
        print('Email sent!')

    elif action.lower() == 'quit' or action.lower() == 'q':
        sys.exit(0)
    
    else:
        print('Invalid action')

if __name__ == '__main__':
    gpg = gnupg.GPG()
    main()
