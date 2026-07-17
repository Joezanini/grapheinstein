def greet(name):
    return f"Hello, {name}!"


class Greeter:
    def hello(self, name):
        return greet(name)
