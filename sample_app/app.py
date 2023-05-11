from caribou.http.fast import Server

# Without the "if" block, the main block will run whenever "auto_import" is triggered.
if __name__ == '__main__':
    raise RuntimeError('You need to run the sample app via guvicorn.')
else:
    server = Server()\
        .auto_import()\
        .instance()
