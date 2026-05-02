from . import start, add_friend, ban_dota, online_check, qr_friend, friend_page, qr_code, admin

def register_all_handlers(dp):
    start.register_handlers(dp)
    add_friend.register_handlers(dp)
    ban_dota.register_handlers(dp)
    online_check.register_handlers(dp)
    qr_friend.register_handlers(dp)
    friend_page.register_handlers(dp)
    qr_code.register_handlers(dp)
    admin.register_handlers(dp)