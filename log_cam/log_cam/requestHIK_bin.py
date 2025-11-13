import requests
import datetime
import json
import random
from utils import random_string
from logger_config import get_logger
logger = get_logger(__name__)
class RequestHIK:
    """"
    phai co: reqCode,ctnrCod,indBind,positionCode \r\n
    co hoac khong: clientCode, tokenCode, pobDir, characterValue
    """
    def __init__(self, reqCode,ctnrTyp,ctnrCod, positionCode, indBind, clientCode=None, tokenCode=None, stgBinCode="100000A1501013", binName=None,characterValue=None):
        self.reqCode = reqCode
        self.reqTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.clientCode = clientCode
        self.tokenCode = tokenCode
        self.ctnrCod = ctnrCod
        self.ctnrTyp = ctnrTyp
        self.positionCode = positionCode
        self.stgBinCode = stgBinCode
        self.binName = binName
        self.characterValue = characterValue
        self.indBind = indBind
        #validate inputs reqCode, ctnrCod, indBind have to be string
        if not isinstance(self.reqCode, str):
            raise ValueError("reqCode must be a string")
        if not isinstance(self.ctnrCod, str):
            raise ValueError("ctnrCod must be a string")
        if not isinstance(self.ctnrTyp, str):
            raise ValueError("ctnrCod must be a string")
        if not isinstance(self.indBind, str):
            raise ValueError("indBind must be a string")
        if not isinstance(self.positionCode, str):
            raise ValueError("positionCode must be a string")
        
        data = {
            "reqCode": self.reqCode,
            "reqTime": self.reqTime,
            "ctnrCode": self.ctnrCod,
            "ctnrTyp": self.ctnrTyp,
            "indBind": self.indBind,
            "positionCode": self.positionCode,
            "stgBinCode": self.stgBinCode
        }
        
        if isinstance(self.clientCode, str):
            data["clientCode"] = self.clientCode
        if isinstance(self.tokenCode, str):
            data["tokenCode"] = self.tokenCode
        if isinstance(self.characterValue, str):
            data["characterValue"] = self.characterValue
        if isinstance(self.stgBinCode, str):
            data["stgBinCode"] = self.stgBinCode
        self.data = data 
    def to_dict(self):
        data = json.dumps(self.data, indent=4)
        return data
    
class HIKSERVER:
    def __init__(self, ip_address, port):
        self.ip_address = ip_address
        self.port = port
    
    def bind_ctnr_and_bin(self, hikreq:RequestHIK):
        url = f'http://{self.ip_address}:{self.port}/rcms/services/rest/hikRpcService/bindCtnrAndBin'
        try:
            response = requests.post(url=url, json=hikreq.data, timeout=30)
            response.raise_for_status()  # Raise exception if status code >= 400
            return response
        except requests.exceptions.ConnectionError:
            logger.exception("Failed to connect to server.")
        return None  
    def random_string(self,length=6):
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(random.choice(letters) for i in range(length))
if __name__=="__main__":
    ip_address='172.24.24.201'
    port='8181'
    hikreq = RequestHIK(random_string(8), "2", "2","G", "1",stgBinCode="100012A2501013")
    hikserver = HIKSERVER(ip_address=ip_address,port=port)
    result = hikserver.bind_ctnr_and_bin(hikreq=hikreq)
    if result is None:
        print("Failed to bind pod and Container Code.")
    else:
        print( result.json())