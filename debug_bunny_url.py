import requests
import json

API_KEY = "7b43d33b-576e-4890-8fb1dae4d73d-9663-4f27"
LIB_ID = "581630"
VIDEO_ID = "46e679cf-30fa-498b-8a2c-87ae92eca174" # One from the showcase

url = "https://api.bunny.net/pullzone"
headers = {"AccessKey": "7b43d33b-576e-4890-8fb1dae4d73d-9663-4f27"} 
# Wait, Pull Zone API key might be different usually (Account Key vs Storage Key).
# The key I have looks like a Storage/Stream Key.
# Stream Libraries are separate. 
# Stream usually generates a Pull Zone automatically "vz-xxxx.b-cdn.net".

# Let's try to get the STREAM LIBRARY details.
url = f"https://video.bunnycdn.com/library/{LIB_ID}"
headers = {"AccessKey": API_KEY}

resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    print(json.dumps(resp.json(), indent=2))
else:
    print(f"Error: {resp.status_code} - {resp.text}")
exit()
