import PyInstaller.__main__

def main():
  PyInstaller.__main__.run([
    './genshinautocheckin/main.py',
    '--onefile',
    '--specpath',
    './build',
    '--distpath',
    './dist',
    '--collect-all',
    'genshin'
  ])

if __name__ == '__main__':
    main()
