from rangifer.http.definitions import controller, endpoint


@controller(r'/clsctl/alpha')
class AlphaController:
    @endpoint(r'one')
    def do_one(self):
        """ A sample endpoint of a controller without parameters """
        return "abc"