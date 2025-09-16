import requests
import datetime
import json
import random

class RequestHIK:
    """"
    phai co: reqCode,podCode,indBind,positionCode \r\n
    co hoac khong: clientCode, tokenCode, pobDir, characterValue
    """
    def __init__(self, reqCode, podCode, positionCode, indBind, clientCode=None, tokenCode=None, pobDir=None, characterValue=None):
        self.reqCode = reqCode
        self.reqTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.clientCode = clientCode
        self.tokenCode = tokenCode
        self.podCode = podCode
        self.positionCode = positionCode
        self.pobDir = pobDir
        self.characterValue = characterValue
        self.indBind = indBind
        #validate inputs reqCode, podCode, indBind have to be string
        if not isinstance(self.reqCode, str):
            raise ValueError("reqCode must be a string")
        if not isinstance(self.podCode, str):
            raise ValueError("podCode must be a string")
        if not isinstance(self.indBind, str):
            raise ValueError("indBind must be a string")
        if not isinstance(self.positionCode, str):
            raise ValueError("positionCode must be a string")
        
        data = {
            "reqCode": self.reqCode,
            "reqTime": self.reqTime,
            "podCode": self.podCode,
            "indBind": self.indBind,
            "positionCode": self.positionCode,
        }
        
        if isinstance(self.clientCode, str):
            data["clientCode"] = self.clientCode
        if isinstance(self.tokenCode, str):
            data["tokenCode"] = self.tokenCode
        if isinstance(self.pobDir, str):
            data["pobDir"] = self.pobDir
        if isinstance(self.characterValue, str):
            data["characterValue"] = self.characterValue
        self.data = data 
    def to_dict(self):
        data = json.dumps(self.data, indent=4)
        return data
    
class HIKSERVER:
    def __init__(self, ip_address, port):
        self.ip_address = ip_address
        self.port = port
    
    def bind_pod_and_berth(self, hikreq:RequestHIK):
        url = f'http://{self.ip_address}:{self.port}/rcms/services/rest/hikRpcService/bindPodAndBerth'
        try:
            response = requests.post(url=url, json=hikreq.data, timeout=30)
            response.raise_for_status()  # Raise exception if status code >= 400
            return response
        except requests.exceptions.ConnectionError:
            print("Failed to connect to server.")
        return None  
    def random_string(self,length=6):
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(random.choice(letters) for i in range(length))
# ip_address='192.168.5.1'
# port='8181'
# hikreq = RequestHIK(random_string(8), "fgdasfdsa", "sadfds", "0")
# hikserver = HIKSERVER(ip_address=ip_address,port=port)
# result = hikserver.bind_pod_and_berth(hikreq=hikreq)
# if result is None:
#     print("Failed to bind pod and berth.")
# else:
#     print( result.json()['message'])