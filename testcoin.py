import logging
import os, time
import json
from datetime import datetime, timedelta
from web3 import Web3
from telegram import __version__ as TG_VER
from dotenv import load_dotenv

load_dotenv()  


try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

w3 = Web3(Web3.HTTPProvider(os.environ.get('HTTP_Provider')))
sender_address = os.environ.get('sender_address')
sender_private_key = os.environ.get('sender_private_key')

claim_limit = int(os.environ.get('claim_limit')) 
limit_duration = timedelta(hours=24)
user_claims = {}
def send_tokens(to_address, amount):
    gas_price = w3.eth.gas_price
    gas_limit = 21000
    value_in_wei = w3.to_wei(amount, 'ether')
    tx = {
        'from': sender_address,
        'to': to_address,
        'value': value_in_wei,
        'nonce': w3.eth.get_transaction_count(sender_address),
        'gas': gas_limit,
        'gasPrice': gas_price, 
        'chainId': int(os.environ.get('chainId')),
    }
    signed_tx = w3.eth.account.sign_transaction(tx, sender_private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    start_text = rf"Hi {user.mention_html()}!"
    start_text += '\nWelcome to the JaiHo coin faucet bot!\n \n'
    start_text += 'To receive JaiHo coin, simply send me your JaiHoChain address as a message!\n \n'
    start_text+= "/help command to display help message"
    await update.message.reply_html(
        start_text,
        reply_markup=ForceReply(selective=True),
    )
    
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) > 0 and w3.is_address(context.args[0]):
        balance = w3.eth.get_balance(context.args[0]) 
        balance_ether = w3.from_wei(balance, 'ether')
        balance_text = f'{context.args[0]} JaiHo coin balance : {balance_ether}'
    else:
        balance_text = "Please provide an valid address\n"
        balance_text+= "format : /balance 0xfc3e5C537bC66D283E8648A109d75F27b1DEc1E4"
    await update.message.reply_text(balance_text)
    
    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = "The following commands are available:\n\n"
    help_text += "/start - Start the bot\n"
    help_text += '🎁To receive JaiHo coin, simply send me your JaiHoChain address as a message!\n\n'
    help_text += "/balance - Check your JaiHo coin balance\n( format : /balance 0xfc3e5C537bC66D283E8648A109d75F27b1DEc1E4)\n"
    help_text += "/help - Display this help message"
    await update.message.reply_text(help_text)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    wallet_address = update.message.text.strip()
    if w3.is_address(wallet_address):
        if user_id not in user_claims:
            user_claims[user_id] = []
        
        if len(user_claims[user_id]) < claim_limit or datetime.now() - user_claims[user_id][-1] > limit_duration:
            amount = os.environ.get('coin_amount')
            tx_hash = send_tokens(wallet_address, amount)
            confirmation_text = f'{amount} JaiHo Coin sent to: {wallet_address} \nTransaction hash: {tx_hash.hex()}'
            user_claims[user_id].append(datetime.now())
        else:
            confirmation_text = f'Sorry, you have reached the maximum number of claims ({claim_limit}) within the past {limit_duration}. Please try again later.'
    else:
        confirmation_text = "Please provide an valid address to claim JaiHo coin \n"
        confirmation_text+= "/help command to display help message"
    await update.message.reply_text(confirmation_text)


def main() -> None:
    application = Application.builder().token(os.environ.get('coin_bot_key')).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.run_polling()


if __name__ == "__main__":
    main()
