import time
import asyncio
from telethon.sync import TelegramClient
from telethon import errors
from dotenv import load_dotenv
import os

class TelegramForwarder:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient('session_' + phone_number, api_id, api_hash)

    async def list_chats(self):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            try:
                await self.client.sign_in(self.phone_number, input('Enter the code: '))
            except errors.rpcerrorlist.SessionPasswordNeededError:
                password = input('Two-step verification is enabled. Enter your password: ')
                await self.client.sign_in(password=password)

        # Get a list of all the dialogs (chats)
        dialogs = await self.client.get_dialogs()
        chats_file = open(f"chats_of_{self.phone_number}.txt", "w", encoding="utf-8")
        # Print information about each chat
        for dialog in dialogs:
            print(f"Chat ID: {dialog.id}, Title: {dialog.title}")
            chats_file.write(f"Chat ID: {dialog.id}, Title: {dialog.title} \n")
          

        print("List of groups printed successfully!")

    async def forward_messages_to_channel(self, source_chat_id, destination_channel_id, keywords):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        last_message_id = (await self.client.get_messages(source_chat_id, limit=1))[0].id

        while True:
            print("Checking for messages and forwarding them...")
            # Get new messages since the last checked message
            messages = await self.client.get_messages(source_chat_id, min_id=last_message_id, limit=None)

            for message in reversed(messages):
                try:
                    # Check if the message text includes any of the keywords
                    if keywords:
                        if message.text and any(keyword in message.text.lower() for keyword in keywords):
                            print(f"Message contains a keyword: {message.text}")
                            await self._handle_message_forward(message, destination_channel_id)
                    else:
                        await self._handle_message_forward(message, destination_channel_id)

                    # Update the last message ID
                    last_message_id = max(last_message_id, message.id)
                except Exception as e:
                    print(f"Error processing message: {str(e)}")
                    continue

            # Add a delay before checking for new messages again
            await asyncio.sleep(5)  # Adjust the delay time as needed

    async def _handle_message_forward(self, message, destination_channel_id):
        try:
            # 下載並重新上傳媒體檔案
            if message.media:
                print(f"Processing media message...")
                # 下載媒體檔案
                media_path = await self.client.download_media(message.media)
                if media_path:
                    print(f"Media downloaded to: {media_path}")
                    # 重新上傳媒體檔案
                    await self.client.send_file(
                        destination_channel_id,
                        media_path,
                        caption=message.text if message.text else None
                    )
                    # 刪除下載的檔案
                    os.remove(media_path)
                    print("Media forwarded successfully")
            else:
                # 純文字訊息直接轉發
                if message.text:
                    await self.client.send_message(destination_channel_id, message.text)
                    print("Text message forwarded")
        except Exception as e:
            print(f"Error in _handle_message_forward: {str(e)}")
            raise

# Function to read credentials from file
def read_credentials():
    try:
        with open("credentials.txt", "r") as file:
            lines = file.readlines()
            api_id = lines[0].strip()
            api_hash = lines[1].strip()
            phone_number = lines[2].strip()
            return api_id, api_hash, phone_number
    except FileNotFoundError:
        print("Credentials file not found.")
        return None, None, None

# Function to write credentials to file
def write_credentials(api_id, api_hash, phone_number):
    with open("credentials.txt", "w") as file:
        file.write(api_id + "\n")
        file.write(api_hash + "\n")
        file.write(phone_number + "\n")

async def main():
    # 載入環境變數
    load_dotenv()
    
    # Attempt to read credentials from file
    api_id, api_hash, phone_number = read_credentials()

    # If credentials not found in file, prompt the user to input them
    if api_id is None or api_hash is None or phone_number is None:
        api_id = input("Enter your API ID: ")
        api_hash = input("Enter your API Hash: ")
        phone_number = input("Enter your phone number: ")
        # Write credentials to file for future use
        write_credentials(api_id, api_hash, phone_number)

    forwarder = TelegramForwarder(api_id, api_hash, phone_number)
    
    print("Choose an option:")
    print("1. List Chats")
    print("2. Forward Messages")
    print("3. Forward Messages with Fixed IDs")
    
    choice = input("Enter your choice: ")
    
    if choice == "1":
        await forwarder.list_chats()
    elif choice == "2":
        source_chat_id = int(input("Enter the source chat ID: "))
        destination_channel_id = int(input("Enter the destination chat ID: "))
        print("Enter keywords if you want to forward messages with specific keywords, or leave blank to forward every message!")
        keywords = input("Put keywords (comma separated if multiple, or leave blank): ").split(",")
        
        await forwarder.forward_messages_to_channel(source_chat_id, destination_channel_id, keywords)
    elif choice == "3":
        # 從環境變數讀取固定的聊天 ID
        source_chat_id = int(os.getenv('SOURCE_CHAT_ID'))
        destination_channel_id = int(os.getenv('DESTINATION_CHAT_ID'))
        
        print(f"Use Read Environment Variable ID：")
        print(f"Source ID: {source_chat_id}")
        print(f"Destination ID: {destination_channel_id}")
        
        # 直接轉發所有訊息，不使用關鍵字過濾
        await forwarder.forward_messages_to_channel(source_chat_id, destination_channel_id, [])
    else:
        print("Invalid choice")

# Start the event loop and run the main function
if __name__ == "__main__":
    asyncio.run(main())
