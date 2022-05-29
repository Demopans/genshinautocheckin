import asyncio
import datetime
from typing import TextIO, Mapping, BinaryIO, Any, Coroutine
import os.path
import genshin.client
import genshin.utility
import sys


if __name__ == '__main__':
    # do on startup
    def configCookie(override=False) -> None:
        from cryptography.fernet import Fernet
        def writeData(strr: str) -> None:
            data: BinaryIO = open("./data", "ab+")

            key: bytes = Fernet.generate_key()
            with open("./key", "wb") as key_file:
                key_file.write(key)
                key_file.close()

            f = Fernet(key)
            enc = f.encrypt(strr.encode())
            data.write(enc+'\n'.encode())
            data.close()

        def readFromData():
            key = open("./key", "rb").read()
            data = open("./data", "rb+").read()
            f = Fernet(key)
            t = f.decrypt(data).decode().split("\n")
            for i in t:
                if i == '':
                    break
                tt = i.split()
                usr.append({"ltuid": tt[0], "ltoken": tt[1]})

        dataExists = os.path.exists("./data") and os.path.exists("./key")
        if override:
            #clear file
            data = open("./data", "wb+")
            data.close()

            writeData(open(sys.argv[1]).read())
            readFromData()
        else:
            if dataExists:
                readFromData()
            else:
                cookies: Mapping[str, str] = genshin.utility.get_browser_cookies()
                if len(cookies.keys()) == 0:
                    log.write(f"[{datetime.datetime.now()}]ERROR: Failed to get cookies, retrieving them from browser")
                    exit(-1)
                writeData(f"{cookies['ltuid']} {cookies['ltoken']}\n")

    def task(cookie):
        """
        attempt to auto check in upon starting program,
        """
        c: genshin.client.Client = genshin.client.Client()
        c.set_cookies(cookie)

        txt = ''
        try:
            reward = asyncio.run(c.claim_daily_reward())
        except Exception:
            txt = "Daily reward already claimed\n"
        else:
            txt = f"Claimed {reward.amount}x\"{reward.name}\""
        print(txt)
        log.write(txt)
        log.flush()

    def service():
        for u in usr:
            task(u)

    def servideMgr():
        import schedule
        while True:
            schedule.every().day.at('00:00').do(service)

    usr = []
    log = open("./log.txt", 'w+')
    configCookie(len(sys.argv) > 1)
    service()
    servideMgr()
