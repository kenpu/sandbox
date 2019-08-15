from pydrive.auth import GoogleAuth

gauth = GoogleAuth()
auth_url = gauth.GetAuthUrl()

code = input("Code: ")
# gauth.LocalWebserverAuth()
gauth.Auth(code)

drive = GoogleDrive(gauth)
