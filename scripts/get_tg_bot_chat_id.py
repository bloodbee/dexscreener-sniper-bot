import requests

# In your telegram chat, just send a message like "Hello",
# then run this script to have the chat ID

API_TOKEN = 'YOUR_BOT_TOKEN_HERE'

response = requests.get(f'https://api.telegram.org/bot{API_TOKEN}/getUpdates')
print(response.json())
