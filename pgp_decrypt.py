import os
import gnupg
import time
from datetime import datetime as dt
import configparser


class Globals:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read(os.path.join(os.curdir, 'config.ini'))

        self.source_path = config['PATHS']['source_path']
        self.destination_path = config['PATHS']['destination_path']


def init_gpg():
    g_nupg = gnupg.GPG(gpgbinary=os.path.join(os.curdir, 'gpg_bin', 'gpg.exe'),
                       gnupghome='./keys', keyring='public.gpg',
                       secret_keyring='private.gpg')

    key_data = open('./keys/medica.asc').read()
    g_nupg.import_keys(key_data)

    key_data = open('./keys/secret.asc').read()
    g_nupg.import_keys(key_data)

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
            status = gpg.decrypt_file(f, passphrase='fGxD7F5c',
                                      output=os.path.join(g.destination_path, pgp[:-4]))

        print(status.ok, status.status, status.stderr)
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
                status = gpg.decrypt_file(f, passphrase='fGxD7F5c',
                                          output=os.path.join(g.destination_path, pgp[:-4]))

            print(status.ok, status.status, status.stderr)
            time.sleep(2)
    else:
        print("No files posted today")


def main():
    global g
    global gpg
    g = Globals()
    gpg = init_gpg()
    # decrypt_files()
    decrypt_from_folder()


if __name__ == '__main__':
    main()
