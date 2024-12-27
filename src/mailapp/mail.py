import email
import getpass
import imaplib
import os
import shutil
import smtplib
import subprocess
import sys
import base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import click
import gnupg
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class EmailConfig(Base):
    __tablename__ = 'email_config'
    id = Column(Integer, primary_key=True)
    email_address = Column(String)
    smtp_server = Column(String)
    username = Column(String)
    password = Column(String)
    imap_server = Column(String)
    imap_username = Column(String)
    imap_password = Column(String)
    salt = Column(String)  # Add salt column

engine = create_engine('sqlite:///email_config.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

def encrypt(text, key):
    try:
        cipher_suite = Fernet(key)
        cipher_text = cipher_suite.encrypt(text.encode())
        return cipher_text
    except Exception as e:
        raise Exception(f"Encryption failed: {str(e)}")

def decrypt(cipher_text, key):
    try:
        cipher_suite = Fernet(key)
        # Handle both string and bytes input
        if isinstance(cipher_text, str):
            cipher_text = cipher_text.encode()
        plain_text = cipher_suite.decrypt(cipher_text).decode()
        return plain_text
    except Exception as e:
        raise Exception(f"Decryption failed: {str(e)}")

def check_gpg_installed():
    try:
        subprocess.run(['gpg', '--version'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
    
def find_gpg_path():
    gpg_path = shutil.which('gpg')
    return gpg_path

def store_email_config(email_address, smtp_server, username, password, imap_server, imap_username, imap_password):
    master_password = getpass.getpass('Enter master password for encryption: ').encode()
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_password))
    
    encrypted_password = encrypt(password, key)
    encrypted_imap_password = encrypt(imap_password, key)
    
    config = EmailConfig(
        email_address=email_address,
        smtp_server=smtp_server,
        username=username,
        password=encrypted_password,
        imap_server=imap_server,
        imap_username=imap_username,
        imap_password=encrypted_imap_password,
        salt=base64.b64encode(salt).decode()  # Store salt
    )
    session.merge(config)
    session.commit()

def retrieve_email_config():
    configs = session.query(EmailConfig).all()
    if not configs:
        raise Exception("No email configuration found")
    
    master_password = getpass.getpass('Enter master password for decryption: ').encode()
    
    email_addresses = []
    smtp_servers = []
    usernames = []
    passwords = []
    imap_servers = []
    imap_usernames = []
    imap_passwords = []
    
    for config in configs:
        try:
            salt = base64.b64decode(config.salt)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password))
            
            # Ensure we're working with bytes for encrypted passwords
            imap_password_bytes = config.imap_password
            if isinstance(imap_password_bytes, str):
                imap_password_bytes = imap_password_bytes.encode()
                
            decrypted_password = decrypt(config.password, key)
            decrypted_imap_password = decrypt(imap_password_bytes, key)
            
            email_addresses.append(config.email_address)
            smtp_servers.append(config.smtp_server)
            usernames.append(config.username)
            passwords.append(decrypted_password)
            imap_servers.append(config.imap_server)
            imap_usernames.append(config.imap_username)
            imap_passwords.append(decrypted_imap_password)
        except Exception as e:
            print(f"Failed to decrypt configuration: {str(e)}")
            raise
    
    return email_addresses, smtp_servers, usernames, passwords, imap_servers, imap_usernames, imap_passwords

def send_email(email_address, smtp_server, username, password, recipients, subject, body, attachments=None, encrypt=False):
    try:
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject

        if encrypt:
            try:
                encrypted_body = gpg.encrypt(body, recipients[0])
                if not encrypted_body.ok:
                    raise Exception("GPG encryption failed")
                body = str(encrypted_body)
            except Exception as e:
                raise Exception(f"GPG encryption error: {str(e)}")

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
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")

def retrieve_emails_imap(imap_server, username, password, decrypt=False):
    try:
        # Debug logging
        print(f"Connecting to IMAP server: {imap_server}")
        print(f"Username: {username}")
        
        # Ensure password is string
        if isinstance(password, bytes):
            password = password.decode()
        
        # Add port specification
        if ':' not in imap_server:
            imap_server = f"{imap_server}:993"
        
        mail = imaplib.IMAP4_SSL(imap_server.split(':')[0], 
                                int(imap_server.split(':')[1]) if ':' in imap_server else 993)
        
        try:
            print("Attempting IMAP login...")
            mail.login(username, password)
            print("IMAP login successful")
        except imaplib.IMAP4.error as e:
            print(f"IMAP login failed: {str(e)}")
            raise Exception(f"IMAP authentication failed: {str(e)}")
            
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
    except Exception as e:
        raise Exception(f"Failed to retrieve emails: {str(e)}")

@click.group()
def cli():
    pass

@cli.command()
@click.option("--creds_seperate",is_flag=True, help="Separate credentials for SMTP and IMAP")
def configure(creds_seperate):
    if creds_seperate:
        email_address = input('Enter your email address: ')
        smtp_server = input('Enter your SMTP server: ')
        username = input('Enter your SMTP username: ')
        password = getpass.getpass('Enter your SMTP password: ')
        imap_server = input('Enter your IMAP server: ')
        imap_username = input('Enter your IMAP username: ')
        imap_password = getpass.getpass('Enter your IMAP password: ')
        store_email_config(email_address, smtp_server, username, password, imap_server, imap_username, imap_password)
    else:
        email_address = input('Enter your email address: ')
        smtp_server = input('Enter your SMTP server: ')
        username = input('Enter your username: ')
        password = getpass.getpass('Enter your password: ')
        imap_server = input('Enter your IMAP server: ')
        store_email_config(email_address, smtp_server, username, password, imap_server, username, password)
    click.echo('Configuration saved!')

@cli.command()
@click.option('--account', prompt='Choose an account', type=int)
@click.option('--recipients', prompt='Enter the recipients (separated by commas)')
@click.option('--subject', prompt='Enter the email subject')
@click.option('--body', prompt='Enter the email body')
@click.option('--attachments', prompt='Attach a file? (y/n)', default='n')
@click.option('--encrypt', prompt='Encrypt the email body? (y/n)', default='n')
def send(account, recipients, subject, body, attachments, encrypt):
    email_addresses, smtp_servers, usernames, passwords, imap_servers, imap_usernames, imap_passwords = retrieve_email_config()
    email_address = email_addresses[account - 1]
    smtp_server = smtp_servers[account - 1]
    username = usernames[account - 1]
    password = passwords[account - 1]

    recipients = [recipient.strip() for recipient in recipients.split(',')]
    attachments_list = []
    if attachments.lower() == 'y':
        file_path = input('Enter the file path: ')
        attachments_list.append(file_path)

    encrypt = encrypt.lower() == 'y' and check_gpg_installed()
    if encrypt and not check_gpg_installed():
        click.echo('GnuPG is not installed. Please install GnuPG to use GPG encryption/decryption.')
        encrypt = False

    send_email(email_address, smtp_server, username, password, recipients, subject, body, attachments_list, encrypt)
    click.echo('Email sent!')

@cli.command()
@click.option('--account', prompt='Choose an account', type=int)
@click.option('--decrypt', prompt='Decrypt the email body? (y/n)', default='n')
def retrieve(account, decrypt):
    email_addresses, smtp_servers, usernames, passwords, imap_servers, imap_usernames, imap_passwords = retrieve_email_config()
    imap_server = imap_servers[account - 1]
    imap_username = imap_usernames[account - 1]
    imap_password = imap_passwords[account - 1]

    decrypt = decrypt.lower() == 'y'
    click.echo('Retrieving emails...')
    emails = retrieve_emails_imap(imap_server, imap_username, imap_password, decrypt)
    for email in emails:
        click.echo(f'From: {email["From"]}')
        click.echo(f'Subject: {email["Subject"]}')
        click.echo(f'Body: {email.get_payload()}')
        click.echo('---')

if __name__ == '__main__':
    gpg = gnupg.GPG()
    cli()
