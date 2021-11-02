import requests


class infoblox_lan:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.url = "https://infoblox.example.com/wapi/v2.1/record:a?_max_results=2000&zone=lan.example.com&view=Internal"

    def get(self):
        r = requests.get(self.url, auth=(self.username, self.password), verify=False)
        output = r.json()
        swlist = []
        for s in output:
            swlist.append((s["name"], s["name"]))
        return swlist
