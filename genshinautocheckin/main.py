import asyncio, sys, genshin.client, genshin.utility, time, json, logging, requests, os
from random import randint
from time import sleep
from platform import system
from typing import Iterable, Any, Callable

# Global vars
CONFIG: dict
LOG: logging.Logger
async def asyncStarMap(func: Callable[..., Any], itr: Iterable[tuple[Any, ...]], s: int | None = None) -> tuple[Any]:
  """Pool.starmap analogue: one callable, many arg tuples, ordered results, optional concurrency bound."""
  if s is None:
    return await asyncio.gather(*[func(*args) for args in itr])
  sem = asyncio.Semaphore(s)
  
  async def run(*args) -> Any:
    async with sem:
      return await func(*args)
  return await asyncio.gather(*[run(*args) for args in itr])

def configCookie(override=False) -> list[genshin.client.Client]:
  users: list[genshin.Client]
  if override:
    users = [
      genshin.Client({
        'ltuid_v2': ltuid_v2,
        'account_id_v2': ltuid_v2,
        'ltoken_v2': keys['ltoken_v2'],
        'cookie_token_v2': keys['cookie_token_v2'],
        'ltmid_v2': keys['ltmid_v2'],
        'account_mid_v2': keys['ltmid_v2'],
      }, game=genshin.Game.GENSHIN)
      for ltuid_v2, keys in CONFIG['cookies'].items()]
  # email+password pathway
  else:
    # manage async handler
    async def tas(a, b):
      c = genshin.Client(game=genshin.Game.GENSHIN)
      await c.login_with_password(a, b)
      return c
    
    # poollike
    users = list(asyncio.run(asyncStarMap(tas, [(ltuid_v2, keys) for ltuid_v2, keys in CONFIG['auth'].items()], 3)))
    
  return users

def taskRuntime(func, *args):
  try:
    match system():
      case 'Linux':
        return asyncio.run(func(*args))
      case 'macOS':
        return asyncio.run(func(*args))  # Todo: Get someone to validate this case against Macs
      case 'Windows':
        return asyncio.run(func(*args), loop_factory=asyncio.SelectorEventLoop)
      case _:
        return asyncio.run(func(*args))
  # stuff common exceptions here
  except RuntimeError as e:
    LOG.error(f'[{time.strftime('%Y-%m-%d')}] RuntimeError: {e}')
  except genshin.RedemptionException as e:
    LOG.error(f'[{time.strftime('%Y-%m-%d')}] RedemptionError: {e} {args}')
  except genshin.InvalidCookies as e:
    LOG.critical(f'[{time.strftime('%Y-%m-%d')}] CookieError: {e}')
    sys.exit(1)
  except Exception as e:
    raise e

def taskAutoLogin(c: genshin.client.Client):
  """
  attempt to auto check in upon starting program,
  """
  try:
    r = taskRuntime(c.claim_daily_reward)
  except genshin.AlreadyClaimed:
    LOG.info(f'[{time.strftime('%Y-%m-%d')}] Already claimed the daily reward today.')
  except Exception as e:
    LOG.error(f'[{time.strftime('%Y-%m-%d')}] Exception: {e}')
  else:
    LOG.info(f'[{time.strftime('%Y-%m-%d')}] Successfully claimed the daily reward.')
    LOG.info(f'    userID: {c.cookie_manager.user_id} {r.amount}x\'{r.name}')

def taskAutoCode(c: genshin.client.Client):
  def task(c: genshin.client.Client):
    # get current active codes
    api: str = 'https://gachafeed-api.zashikiiii.workers.dev/api/codes/genshin'
    content = requests.get(api).json()['codes']
    content = filter(lambda x: 'expired' != x['status'], content)
    content = set(map(lambda x: x['code'], content))
    
    # load cache
    if not os.path.exists(CONFIG['codesDir']):
      with open(CONFIG['codesDir'], 'w') as f:
        f.write('')
        f.close()
        del f
    
    cd = dict()
    with open(CONFIG['codesDir'], 'r+') as f:
      try:
        cd = json.load(f)
      except json.decoder.JSONDecodeError:
        f.seek(0)
        f.write('')  # cannot read code cache, void cache
      f.close()
      del f
    
    with open(CONFIG['codesDir'], 'w') as f:
      UUID = str(c.cookie_manager.user_id)
      
      if UUID not in cd.keys():
        cd[UUID]: dict[dict] = dict()
      
      content -= cd[UUID].keys()
      
      for code in content:
        taskRuntime(c.redeem_code, code)
        sleep(randint(6, 12))
      
      cd[UUID] = {**cd[UUID], **{code: '' for code in content}}
      json.dump(cd, f, indent=2, sort_keys=True, )
      f.close()
      del f
  
  try:
    task(c)
  except Exception as e:
    LOG.error(f'[{time.strftime('%Y-%m-%d')}] Exception: {e}')
  else:
    LOG.info(f'[{time.strftime('%Y-%m-%d')}] All codes claimed.')
    LOG.info(f'    userID: {c.cookie_manager.user_id} ')

def servideMgr(usrs):
  import schedule
  def service():
    for i in usrs:
      taskAutoLogin(i)
      taskAutoCode(i)
  
  schedule.every().day.at('00:00').do(service)
  schedule.run_all()
  while 1:
    schedule.run_pending()
    time.sleep(1)

if __name__ == '__main__':
  if len(sys.argv) != 2:
    raise ValueError('Usage: genshin <config file>')
  
  with open(sys.argv[1], 'r') as f:
    CONFIG = json.load(f)
    usrs = configCookie(CONFIG['useCookie'])
    if CONFIG['log']:
      LOG = logging.getLogger('genshin')
      LOG.setLevel(logging.INFO)
      LOG.addHandler(logging.StreamHandler(sys.stdout))
      LOG.addHandler(logging.FileHandler(CONFIG['logDir']))
    f.close()
    del f
  
  # platform dependent logic set by user
  if CONFIG['asService']:
    servideMgr(usrs)
  else:
    for i in usrs:
      taskAutoLogin(i)
      taskAutoCode(i)
    
    # update config cookies as autoupdate bonus, config option
    if CONFIG['cacheCookies']:
      u = list(map(lambda i: {k:v for k,v in i.cookie_manager.cookies.items() if v!='' }, usrs))
      
      # if exist
      if 'cookies' not in CONFIG.keys():
        CONFIG['cookies'] = dict()
      
      for i in u:
        CONFIG['cookies'][i['ltuid_v2']] = {
          'ltoken_v2': i['ltoken_v2'],
          'cookie_token_v2': i['cookie_token_v2'],
          'ltmid_v2': i['ltmid_v2']
        }
    
      with open(sys.argv[1], 'r+') as f:
        f.seek(0)
        f.write('')  # void and update
        json.dump(CONFIG, f, indent=2, sort_keys=True)
        del f