from caribou.http.definitions import endpoint


@endpoint(r'/')
def root():
    return 'hello, world'


@endpoint(r'/abc')
async def abc():
    return 'hello, world'