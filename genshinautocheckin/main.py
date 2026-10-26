import asyncio, sys, genshin.client, genshin.utility, time, json, logging, requests
from random import randint
from time import sleep

# Global vars
CONFIG: dict
LOG: logging.Logger

def configCookie(override=False) -> list[genshin.client.Client]:
  if override:
    users = [
      genshin.client.Client({
        'ltuid_v2': ltuid_v2,
        'account_id_v2': ltuid_v2,
        'ltoken_v2': keys['ltoken_v2'],
        'cookie_token_v2': keys['cookie_token_v2'],
        'ltmid_v2': keys['ltmid_v2'],
        'account_mid_v2': keys['ltmid_v2'],
      }, game=genshin.Game.GENSHIN)
      for ltuid_v2, keys in CONFIG["cookies"].items()]
  # depreciated
  else: users = [genshin.client.Client(genshin.utility.get_browser_cookies(), game=genshin.Game.GENSHIN)]
  return users

def taskRuntime(func, *args):
  try:
    return taskOS(func, *args)
  # stuff common exceptions here
  except RuntimeError as e:
    LOG.error(f"[{time.strftime('%Y-%m-%d')}] RuntimeError: {e}")
  except genshin.RedemptionException as e:
    LOG.error(f"[{time.strftime('%Y-%m-%d')}] RedemptionError: {e} {args}")
  except genshin.InvalidCookies as e:
    LOG.critical(f"[{time.strftime('%Y-%m-%d')}] CookieError: {e}")
    exit(1)
  except Exception as e:
    raise e
  
def taskOS(func, *args):
  from platform import system
  match system():
    case 'Linux': return asyncio.run(func(*args))
    case 'macOS': return asyncio.run(func(*args)) # Todo: Get someone to validate this case against Macs
    case 'Windows': return asyncio.run(func(*args), loop_factory=asyncio.SelectorEventLoop)
    case _: return asyncio.run(func(*args))
  
def taskAutoLogin(c: genshin.client.Client):
  """
  attempt to auto check in upon starting program,
  """
  try:
    r = taskRuntime(c.claim_daily_reward)
  except genshin.AlreadyClaimed:
    LOG.info(f"[{time.strftime('%Y-%m-%d')}] Already claimed the daily reward today.")
  except Exception as e:
    LOG.error(f"[{time.strftime('%Y-%m-%d')}] Exception: {e}")
  else:
    LOG.info(f"[{time.strftime('%Y-%m-%d')}] Successfully claimed the daily reward.")
    LOG.info(f"    userID: {c.cookie_manager.user_id} {r.amount}x\"{r.name}")

def taskAutoCode(c: genshin.client.Client):
  def task(c: genshin.client.Client):
    # get current active codes
    api: str = "https://gachafeed-api.zashikiiii.workers.dev/api/codes/genshin"
    content = requests.get(api).json()["codes"]
    content = filter(lambda x: "expiresAt" not in x.keys(), content)
    content = set(map(lambda x: x["code"],content))
    
    # only unused per id
    with open(CONFIG["codesDir"], 'w+') as f:
      cd = dict()
      try:
        cd = json.load(f)
      except json.decoder.JSONDecodeError:
        f.seek(0)
        f.write('')
        json.dump(dict(), f) # cannot read code cache, void cache
      
      if c.cookie_manager.user_id not in cd.keys():
        cd[c.cookie_manager.user_id] = dict()
      
      content -= cd[c.cookie_manager.user_id].keys()
      
      for code in content:
        taskRuntime(c.redeem_code, code)
        sleep(randint(6,12))
        
      cd[c.cookie_manager.user_id] += {code: "" for code in content}
      json.dump(cd, f, indent=2, sort_keys=True)
    
  try:
    task(c)
  except Exception as e:
    LOG.error(f"[{time.strftime('%Y-%m-%d')}] Exception: {e}")
  else:
    LOG.info(f"[{time.strftime('%Y-%m-%d')}] All codes claimed.")
    LOG.info(f"    userID: {c.cookie_manager.user_id} ")

# Todo: Transition to a cronjob model in config
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

if __name__ == '__main__':
  if len(sys.argv) != 2:
    raise ValueError("Usage: genshin <config file>")
  
  with open(sys.argv[1], 'r') as f:
    CONFIG = json.load(f)
  
  usrs = configCookie(override=True)
  
  with open(sys.argv[1], 'r') as f:
    service, logEnable, logDir = (a:=json.load(f))["asService"], a["log"], a["logDir"]
    
    LOG = logging.getLogger("genshin")
    LOG.setLevel(logging.INFO)
    LOG.addHandler(logging.StreamHandler(sys.stdout))
    LOG.addHandler(logging.StreamHandler(sys.stderr))
    LOG.addHandler(logging.FileHandler(logDir))
    f.close()
    del f
  
  # platform dependent logic set by user
  if service:
    servideMgr()
  else:
    taskAutoLogin(usrs[0])
    taskAutoCode(usrs[0])