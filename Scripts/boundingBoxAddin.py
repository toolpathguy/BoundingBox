from .commandDialog import start as commandDialogStart, stop as commandDialogStop

commands = [commandDialogStart]

def start():
    for command in commands:
        command()

def stop():
    for command in commands:
        command()
