import os
import gnupg
import time
from datetime import datetime as dt
import configparser
import ftplib
import csv
import smtplib
import ssl
import pysftp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# TODO move completed file into completed folder
# TODO query completed date


class Globals:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read(os.path.join(os.curdir, 'config.ini'))

        self.source_path = config['PATHS']['source_path']
        self.destination_path = config['PATHS']['destination_path']
        self.passphrase = config['PATHS']['passphrase']
        self.encrypt_date = '12/05/2019'

        self.host = config['FTP']['host']
        self.user = config['FTP']['user']
        self.password = config['FTP']['password']
        self.path = config['FTP']['path']
        self.protocol = config['FTP']['protocol']

        self.email_to = config['EMAIL']['email_to']
        self.email_from = config['EMAIL']['email_from']
        self.email_user = config['EMAIL']['email_user']
        self.email_password = config['EMAIL']['email_password']
        self.email_server = config['EMAIL']['email_server']

    def set_encrypt_date(self):
        pass


def init_gpg():
    g_nupg = gnupg.GPG(gpgbinary=os.path.join(os.curdir, 'gpg_bin', 'gpg.exe'),
                       gnupghome='./keys', keyring='public.gpg',
                       secret_keyring='private.gpg')

    import_results = []

    key_data = open('./keys/medica.asc').read()
    import_result = g_nupg.import_keys(key_data)
    import_results.append((import_result.count, import_result.fingerprints))

    key_data = open('./keys/secret.asc').read()
    import_result = g_nupg.import_keys(key_data)
    import_results.append((import_result.count, import_result.fingerprints))

    print(import_results)

    return g_nupg


def decrypt_from_folder():
    """
    Decrypt ALL from relative folder
    :return:
    """

    pgp_files = [f for f in os.listdir(g.source_path) if f.upper()[-3:] == 'PGP']

    for pgp in pgp_files:
        print(f"Decrypting: {pgp}")
        with open(os.path.join(g.source_path, pgp), 'rb') as f:
            status = gpg.decrypt_file(f, passphrase=g.passphrase,
                                      output=os.path.join(g.destination_path, pgp[:-4]))

        print(status.stderr)
        if status.ok:
            print(f"Deleting: {pgp}")
            os.remove(os.path.join(g.source_path, pgp))
        time.sleep(.5)

    time.sleep(2)


def decrypt_files():
    pgp_files = [(f, os.path.getmtime(os.path.join(g.source_path, f)))
                 for f in os.listdir(g.source_path) if f.upper()[-3:] == 'PGP']

    for f in pgp_files:
        print(f[0], dt.strptime(time.ctime(f[1]), "%a %b %d %H:%M:%S %Y"))

    pgp_today = [f[0] for f in pgp_files
                 if dt.date(dt.strptime(time.ctime(f[1]), "%a %b %d %H:%M:%S %Y")) ==
                 dt.date(dt.today())]

    if pgp_today:
        for pgp in pgp_today:
            print(f"Decrypting: {pgp}")
            with open(os.path.join(g.source_path, pgp), 'rb') as f:
                status = gpg.decrypt_file(f, passphrase=g.passphrase,
                                          output=os.path.join(g.destination_path, pgp[:-4]))

            print(status.ok, status.status, status.stderr)
            time.sleep(2)
    else:
        print("No files posted today")


def encrypt_txt(search_path, csv_list):
    success = set()

    for f, n in csv_list:
        print(f"\nEncrypting: {f}")
        with open(os.path.join(search_path, f), 'rb') as e:
            status = gpg.encrypt_file(e,
                                      always_trust=True,
                                      armor=False,
                                      passphrase=g.passphrase,
                                      recipients='827C681A6B60682058AB00BC8BE7CA22B01C43A5',
                                      output=os.path.join(search_path, f"{f}.pgp"))

        print(status.stderr)
        if status.ok:
            print(f"Encrypted: {f}, {n} Records")
            success.add(f"{f}.pgp")
            # os.remove(os.path.join(search_path, pgp))
        time.sleep(.5)

    time.sleep(2)
    return success


def convert_to_csv(search_path, txt_files):
    success = set()

    for f in txt_files:
        print(f"Converting {f}")
        with open(f, 'r') as source:
            csv_source = csv.reader(source, delimiter='|')
            with open(f"{f[:-4]}.csv", 'w', newline='') as destination:
                csv_destination = csv.writer(destination, delimiter=',')
                for n, s in enumerate(csv_source):
                    if n == 0:
                        new_field = 'Completed Date'
                    else:
                        new_field = g.encrypt_date

                    s.append(new_field)
                    csv_destination.writerow(s)

        success.add((f"{f[:-4]}.csv", n))

    return success


def transfer_to_ftp(search_path, file_list):
    if g.protocol == 'ftp':
        with ftplib.FTP(host=g.host) as ftp_conn:
            ftp_conn.connect()
            ftp_conn.login(user=g.user, passwd=g.password)
            ftp_conn.cwd(g.path)

            for f in file_list:
                with open(os.path.join(search_path, f), 'rb') as transfer:
                    print(f"Transferring {f}")
                    ftp_conn.storbinary(f'STOR {f}', transfer)

            print(ftp_conn.retrlines('LIST'))

    if g.protocol == 'sftp':
        with pysftp.Connection(host=g.host, username=g.user, password=g.password) as sftp_conn:
            with sftp_conn.cd(g.path):
                for f in file_list:
                    sftp_conn.put(os.path.join(search_path, f))
                for attr in sftp_conn.listdir_attr():
                    print(attr.filename, attr)


def send_email(csv_list):
    port = 587
    smtp_server = g.email_server
    sender_email = g.email_user
    email_from = g.email_from
    receiver_email = g.email_to
    password = g.email_password

    fle_format = "file has" if len(csv_list) == 1 else "files have"
    table_data = ""
    for filename, records in csv_list:
        table_data += f"<tr><td>{filename[:-4]}.txt</td><td>{records}</td></tr>"

    text = "Transfer complete"

    html = ("<html> <head> <style> td, th {{ border: 1px solid #dddddd; text-align: left; padding: 8px;}}"
            "</style> </head> <body> <p>The following {fle_format} been added to user groups:<br> "
            "</p> <table width: 100%;> <tr> <th>File</th> <th>Records</th> </tr> "
            "{table_data} </table> </body> </html> "
            "<p>Matching files have been pgp encrypted and uploaded to "
            "the FTP site</p>".format(table_data=table_data, fle_format=fle_format))

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Add to new agency complete: {g.encrypt_date}"
    message["From"] = sender_email
    message["To"] = receiver_email

    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_server, port) as server:
        # server.set_debuglevel(1)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(email_from, receiver_email, message.as_string())


def run_decrypt():
    # decrypt_files()
    decrypt_from_folder()


def run_encrypt():
    search_path = os.curdir
    txt_files = [f for f in os.listdir(search_path) if f.upper()[-3:] == 'TXT']

    csv_list = convert_to_csv(search_path, txt_files)
    file_list = encrypt_txt(search_path, csv_list)
    transfer_to_ftp(search_path, file_list)
    send_email(csv_list)


def main():
    pass


if __name__ == '__main__':
    global g
    global gpg
    g = Globals()
    gpg = init_gpg()

    # run_decrypt()
    run_encrypt()
