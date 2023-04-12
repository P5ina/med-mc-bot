from pony.orm import Database, Required

db = Database()


class User(db.Entity):
    telegram_user_id = Required(int, unique=True)
    minecraft_nickname = Required(str, unique=True)
    verified = Required(bool, default=False)
