#!/usr/bin/env python3
import os
import subprocess
import sys

MENU = "1) git status  2) git pull  3) list files  4) shell  5) up  q) quit"


def get_key():
    """Read a single keypress without requiring Enter."""
    if sys.platform.startswith("win"):
        import msvcrt

        ch = msvcrt.getch()
        try:
            return ch.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def run(cmd):
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, check=False)


def launch_shell():
    if sys.platform.startswith("win"):
        run(["cmd"])
    else:
        # Use the user's preferred shell if set, otherwise fall back to /bin/sh.
        shell = os.environ.get("SHELL", "/bin/sh")
        run([shell])


def main():
    print(f"cwd: {os.getcwd()}")
    print(MENU)
    while True:
        sys.stdout.write("\nSelect: ")
        sys.stdout.flush()
        ch = get_key()
        print(ch)  # echo the key pressed
        if ch == "1":
            run(["git", "status"])
        elif ch == "2":
            run(["git", "pull"])
        elif ch == "3":
            if sys.platform.startswith("win"):
                run(["cmd", "/c", "dir"])
            else:
                run(["ls"])
        elif ch == "4":
            launch_shell()
        elif ch == "5":
            try:
                os.chdir("..")
                print(f"Moved to parent: {os.getcwd()}")
            except OSError as exc:
                print(f"Could not move to parent: {exc}")
        elif ch.lower() == "q":
            print("Bye.")
            break
        else:
            print("Invalid choice.")
        print(f"\ncwd: {os.getcwd()}")
        print(MENU)


if __name__ == "__main__":
    main()
