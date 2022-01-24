import time
from unittest.mock import patch

from telebot import types

from source.bot import bot


def capture_event(*args, **kwargs):
    print(args, kwargs)


def create_text_message(text):
    params = {'text': text}
    chat = types.User(11, False, 'test')
    return types.Message(1, chat, None, chat, 'text', params, "")


def check_reaction(text: str, capsys, msg=None):
    if msg is None:
        msg = create_text_message(text)
    bot.process_new_messages([msg])
    time.sleep(1)
    captured = capsys.readouterr()
    return captured.out


class FakeObj:
    format = 'GIF'


class FakeClient:
    @staticmethod
    def upload():
        return None


@patch('telebot.TeleBot.register_next_step_handler', return_value=None)
@patch('telebot.TeleBot.send_message', side_effect=capture_event)
class TestBot:
    def test_command_start(self, mock1, mock2, capsys):
        assert "Send me one or more pictures" \
               in check_reaction('/start', capsys)

    def test_command_help(self, mock1, mock2, capsys):
        assert "I can make a GIF" in check_reaction('/help', capsys)

    def test_command_download(self, mock1, mock2, capsys):
        assert "Here you go!" in check_reaction('/download', capsys)

    def test_command_download_all(self, mock1, mock2, capsys):
        assert "Type IDs of users" in check_reaction('/download_all', capsys)

    def test_text_handler(self, mock1, mock2, capsys):
        assert "Try to type /start" in check_reaction('test', capsys)

    def test_step_break_handler(self, mock1, mock2, capsys):
        from source.bot import process_photo_step, step_break_handler

        msg = create_text_message('/restart')
        step_break_handler(process_photo_step(msg))
        captured = capsys.readouterr()
        assert "Okay, I stop." in captured.out

    @patch('source.bot.process_photo', return_value=None)
    @patch('telebot.types.Message.parse_photo', return_value=[1])
    def test_process_photo_step(self, mock1, mock2, mock3, mock4, capsys):
        from source.bot import USERS, process_photo_step

        msg = create_text_message('main')

        process_photo_step(msg)
        assert "Please, send me pictures" in check_reaction('test', capsys)

        msg.photo = [1]
        process_photo_step(msg)
        assert "Upload another pictures" in check_reaction('', capsys, msg)

        USERS[msg.from_user.id] = [1]
        msg.text = '/done'
        process_photo_step(msg)
        del USERS[msg.from_user.id]
        assert "Next, give me" in check_reaction('', capsys, msg)

    @patch('source.bot.send_result_step', return_value=None)
    def test_text_process_step(self, mock1, mock2, mock3, capsys):
        from source.bot import process_text_step

        msg = create_text_message('')
        process_text_step(msg)
        assert "Please, send me some symbols" in check_reaction('', capsys)

        msg.text = 'test'
        process_text_step(msg)
        assert "Okay, wait a little bit" in check_reaction('', capsys)

    @patch('source.bot.client', return_value=FakeClient())
    @patch('source.bot.send_content', return_value=None)
    @patch(
        'source.transformer.ImageTransformer.transform', return_value=FakeObj()
    )
    def test_send_result_step(self, mock1, mock2, mock3, mock4, mock5, capsys):
        from source.bot import send_result_step, upload_result_step

        msg = create_text_message('')
        send_result_step(msg)
        assert "Type /publish to upload" in check_reaction('', capsys)

        obj = FakeObj()
        msg.text = '/publish'
        upload_result_step(msg, obj)
        assert "I kept it!" in check_reaction('', capsys)

        msg.text = '/save'
        upload_result_step(msg, obj)
        assert "I kept it!" in check_reaction('', capsys)
