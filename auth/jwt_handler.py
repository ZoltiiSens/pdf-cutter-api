from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Request, HTTPException


def verify_jwt(jwtoken: str):
    tokens = []
    with open('auth/tokens.txt', 'r') as f:
        for line in f.readlines():
            if line.find('///') != -1:
                token = line.split('///')[0].strip()
                tokens.append(token)
            else:
                tokens.append(line.strip())
    if jwtoken in tokens:
        return True
    return False


class HTTPSpecialBearer(HTTPBearer):
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(HTTPSpecialBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            if not verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid token")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")


# import jwt

# JWT_SECRET = 'VlVR2FitQtvvfJWTVvBbeYZlHHA7YZO6'
# JWT_ALGORYTHM = 'HS256'
# def signJWT(userInfo: str):
#     payload = {
#         'userInfo': userInfo,
#     }
#     token = jwt.encode(payload=payload, key=JWT_SECRET, algorithm=JWT_ALGORYTHM)
#     return {
#         'token': token
#     }
#
#
# def decodeJWT(token: str):
#     decode_token = jwt.decode(jwt=token, key=JWT_SECRET, algorithm=JWT_ALGORYTHM)
#
#
# tokens = [
#     '1234',
#     '5678',
#     '9012'
# ]