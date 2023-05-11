from caribou.http.definitions import endpoint


@endpoint(r'/clsctl/alpha')
class AlphaController:
    @endpoint(r'one')
    def do_one(self):
        return "abc"