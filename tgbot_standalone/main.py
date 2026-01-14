import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tgbot_standalone.bot import QQMusicBot


def main():
    bot = QQMusicBot()
    bot.run()


if __name__ == "__main__":
    main()
