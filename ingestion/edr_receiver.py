


class EDRReceiver:

    def receive(self):

        event = {
            "source": "EDR",
            "hostname": "DESKTOP-01",
            "event_id": 4688,
            "process_name": "powershell.exe"
        }

        return event



