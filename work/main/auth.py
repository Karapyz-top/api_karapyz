from rest_framework.authentication import TokenAuthentication


class Bearer(TokenAuthentication):
    keyword = 'Bearer'