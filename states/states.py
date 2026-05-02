from aiogram.fsm.state import State, StatesGroup

class LinkState(StatesGroup):
    waiting_for_action = State()
    link_saved = State()

class BanDefDotaState(StatesGroup):
    waiting_for_photo = State()

class MessageState(StatesGroup):
    waiting_for_text = State()

class QrFriendState(StatesGroup):
    waiting_for_link = State()
    waiting_for_time = State()

class FriendState(StatesGroup):
    waiting_for_link = State()

class FriendNotFoundState(StatesGroup):
    waiting_for_link = State()
    waiting_for_id = State()

class OnlineCheckState(StatesGroup):
    waiting_for_profile_link = State()
    waiting_for_comment = State()

class QrCodeState(StatesGroup):
    waiting_for_photo = State()

class QrCodeEState(StatesGroup):
    waiting_for_photo = State()