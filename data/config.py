"""
User configuration should define categories and a function
called [categorize] that takes a LogEntry and return its category

Two categories are always defined, AFK and UNCAT,they can be found with
>>> from src.core import LogEntry, Category, AFK, UNCAT

The categorize function should always return a category, so
>>> def categorize(log):
>>>     return UNCAT
is the minimal function.
"""


from src.core import LogEntry, Category, AFK, UNCAT

# Categories
CODE = Category("Coding", 0xffffff)
CHAT = Category("Chat", 0xffa500)
ASSIST = Category("Assistanat", 0xffff00)
MOOC = Category("MOOCs", 0x4070c0)
CQFD = Category("CQFD", 0x222222)
EPFL = Category("EPFL", 0xff0000)
CHILL = Category("Chill", 0xff00ff)
TIMETRACK = Category("Time tracking", 0x0000ff)
NIXOS = Category("NixOs", 0x555555)
WONTFIX = Category("Wont fix", 0x000080)
ADMIN = Category("Administratif", 0xaaaaaa)


def categorize(log: LogEntry) -> Category:
    # Categorizing vim uses
    if log.name == "nvim":
        return CODE
    if "NVIM" in log.name:
        mapping = {
            "app_watch.py": TIMETRACK,
            "nixos-conf": NIXOS,
        }
        for pattern, cat in mapping.items():
            if pattern in log.name:
                return cat

    name_contains_map = {
        "cqfd": CQFD,  # High priority

        "Telegram": CHAT,
        "Discord": CHAT,
        "WhatsApp": CHAT,
        "chat.lama-corp.space": CHAT,
        "Courrier": CHAT,
        "aerc": CHAT,
        "zimbra": CHAT,

        "logement": ADMIN,
        "FMEL": ADMIN,

        "Mooc": MOOC,
        "Coursera": MOOC,
        "predproie.cc": MOOC,
        "biblio.cc": MOOC,

        "Google Drive": CQFD,
        "Agepoly": CQFD,
        "Pulls": CQFD,
        "Outlook": CQFD,
        "Association des Etudiants en Mathématiques": CQFD,
        "Liste séminaire 2020/2021": CQFD,
        "Journée des gymnasiens": CQFD,
        "Tous les logos": CQFD,
        "Vote des logos": CQFD,
        "docs.google.com": CQFD,
        "drive.google.com": CQFD,
        "www.batelier.fr/": CQFD,

        "app_watch.py": TIMETRACK,
        "ActivityWatch": TIMETRACK,
        "ARBTT": TIMETRACK,
        "Wakatime": TIMETRACK,
        "yatta": TIMETRACK,

        "home-manager": NIXOS,
        "nixos-conf": NIXOS,
        "Nixos": NIXOS,
        "configuration.nix": NIXOS,

        "Stack Overflow": CODE,
        "Python": CODE,
        "prog/vrac": CODE,
        "starship": CODE,
        "linux": CODE,
        "shell": CODE,
        "zsh": CODE,
        "Dark Lama": CODE,
        "color.firefox": CODE,

        "zoom": EPFL,
        "moodle.epfl.ch": EPFL,
        "Ex_GT_Ch": EPFL,
        "Graph_Lec": EPFL,
        "Course: ": EPFL,
        "Moodle": EPFL,
        "Kuratowski.pdf": EPFL,
        "VSCodium": EPFL,
        "wikipedia": EPFL,
        "theorem": EPFL,
        "examen": EPFL,
        "Epic Mountain": EPFL,
        "piazza": EPFL,
        "MATH-483": EPFL,
        "Sheet7": EPFL,
        "EPFL": EPFL,

        "diego@maple:": WONTFIX,

        "Reddit": CHILL,
        "Youtube": CHILL,
        "Google Photos": CHILL,
        "faireplusachetermoins.fr": CHILL,
    }

    for pattern, cat in name_contains_map.items():
        if pattern.casefold() in log.name.casefold():
            return cat

    class_contains_map = {
        "telegram": CHAT,
        "Spotify": CHILL,
        "krita": CHILL,
        # "terminator": CODE,
    }

    for pattern, cat in class_contains_map.items():
        if pattern in log.klass:
            return cat

    wontfix = [
        "/run/current-system/sw/bin/htop",
        "Mozilla Firefox",
        "Save As",
        "File Upload",
        "Unsaved*"
    ]
    for w in wontfix:
        if log.name == w or log.klass == w:
            return WONTFIX

    if log.name == log.klass == "":
        return AFK

    return UNCAT


