from netmiko import ConnectHandler
from config import SWITCH

def connect():
    connection = ConnectHandler(**SWITCH)
    connection.enable()  # au cas où enable password configuré
    connection.send_command("terminal length 0")
    return connection