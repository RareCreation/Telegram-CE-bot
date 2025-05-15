from colorama import init, Fore, Style

init(autoreset=True)

def logger(message: str):
    print(f"{Fore.RED}LOGGER:{Style.RESET_ALL} {message}")
