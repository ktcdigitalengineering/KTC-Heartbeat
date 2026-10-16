from Modules.auth import get_access_token

print("Getting token...")
token = get_access_token()
print("Success!")
print(token[:30] + "...")