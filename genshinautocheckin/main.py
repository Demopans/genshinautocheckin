import asyncio, sys, genshin.client, genshin.utility, time

if __name__ == '__main__':
    # do on startup
    def configCookie(override=False) -> None:
        if override:
            for ln in open(sys.argv[1]).read().split('\n'):
                t = ln.split(' ')
                usr.append(genshin.client.Client({'ltoken': t[0], 'ltuid': t[1]}, game=genshin.Game.GENSHIN))
        else:
            usr.append(genshin.client.Client(genshin.utility.get_browser_cookies(), game=genshin.Game.GENSHIN))


    def task(c: genshin.client.Client):
        """
        attempt to auto check in upon starting program,
        """
        try:
            from platform import system
            if system() == 'Windows':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            reward = asyncio.run(c.claim_daily_reward())
        except genshin.AlreadyClaimed as e:
            txt = f"[{time.strftime('%Y-%m-%d')}] Already claimed the daily reward today."
        except RuntimeError as e:
            txt = f"[{time.strftime('%Y-%m-%d')}] RuntimeError: {e}"
        except Exception as e:
            txt = f"[{time.strftime('%Y-%m-%d')}] {e}"
        else:
            txt = f"Claimed {reward.amount}x\"{reward.name}"
        print(txt)
        log.write(txt+'\n')
        log.flush()


    def servideMgr():
        import schedule
        def service():
            import threading as tp
            pool = [tp.Thread(target=task, args=(i,)) for i in usr]
            for i in pool:
                i.start()
                time.sleep(1)
            for i in pool:
                i.join()

        schedule.every().day.at('00:00').do(service)
        schedule.run_all()
        while 1:
            schedule.run_pending()
            time.sleep(1)

    usr: list[genshin.client.Client] = []
    log = open("./log.txt", 'w+')
    configCookie(len(sys.argv) > 1)
    print('\n\n')
    sys.stdout.flush()
    servideMgr()
